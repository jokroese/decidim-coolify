"""Mocked checks for immutable smoke image selection and isolated cleanup."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from smoke import app_image_override, cleanup_project
from tools import image_checks


IMAGE_AMD64 = "sha256:" + "a" * 64
IMAGE_ARM64 = "sha256:" + "b" * 64


class ImageResolutionTests(unittest.TestCase):
    def test_local_image_id_with_platform_mismatch_fails_without_pull(self) -> None:
        with patch.object(image_checks, "_inspect", return_value=(IMAGE_AMD64, ("linux", "amd64", None))), \
                patch.object(image_checks, "_docker") as docker:
            with self.assertRaisesRegex(RuntimeError, "image IDs are never pulled"):
                image_checks.resolve_image(IMAGE_AMD64, "linux/arm64")
        docker.assert_not_called()

    def test_native_docker_info_architecture_aliases_match_image_architecture(self) -> None:
        cases = (("linux/aarch64", "arm64"), ("linux/x86_64", "amd64"))
        for daemon_platform, image_architecture in cases:
            with self.subTest(daemon_platform=daemon_platform), \
                    patch.object(image_checks, "_docker", return_value=SimpleNamespace(stdout=daemon_platform)) as docker, \
                    patch.object(image_checks, "_inspect", return_value=(IMAGE_ARM64, ("linux", image_architecture, None))):
                self.assertEqual(image_checks.resolve_image("local:tag"), IMAGE_ARM64)
            docker.assert_called_once_with(["info", "--format", "{{.OSType}}/{{.Architecture}}"])

    def test_inspect_distinguishes_missing_image_from_docker_daemon_failure(self) -> None:
        missing = SimpleNamespace(returncode=1, stdout="Error: No such image: local:tag")
        daemon_failure = SimpleNamespace(returncode=1, stdout="permission denied while trying to connect to the Docker API")
        with patch("tools.image_checks.subprocess.run", return_value=missing):
            self.assertIsNone(image_checks._inspect("local:tag"))
        with patch("tools.image_checks.subprocess.run", return_value=daemon_failure):
            with self.assertRaisesRegex(RuntimeError, "docker image inspect.*permission denied"):
                image_checks._inspect("local:tag")

    def test_mutable_tag_is_resolved_once_and_roles_keep_immutable_id(self) -> None:
        # The tag starts on amd64, so resolution pulls its arm64 variant. A later
        # mutation of that tag cannot affect the service override, which stores ID.
        with patch.object(image_checks, "_inspect", side_effect=[
                (IMAGE_AMD64, ("linux", "amd64", None)),
                (IMAGE_ARM64, ("linux", "arm64", None)),
        ]), patch.object(image_checks, "_docker") as docker:
            selected = image_checks.resolve_image("registry.example/app:latest", "linux/arm64")
        self.assertEqual(selected, IMAGE_ARM64)
        docker.assert_called_once_with(["pull", "--platform", "linux/arm64", "registry.example/app:latest"])
        roles = app_image_override(selected)
        self.assertEqual(set(roles), {"web", "worker", "scheduler"})
        self.assertEqual({config["image"] for config in roles.values()}, {IMAGE_ARM64})


class CleanupIsolationTests(unittest.TestCase):
    def test_concurrent_cleanup_stays_scoped_and_reports_a_leaked_volume(self) -> None:
        calls: list[list[str]] = []

        def fake_run(args: list[str], **kwargs: object) -> SimpleNamespace:
            calls.append(args)
            project = args[args.index("--project-name") + 1] if "--project-name" in args else None
            if "down" in args and project == "smoke-one":
                return SimpleNamespace(returncode=1, stdout="volume busy")
            if "volume" in args and "ls" in args and "label=com.docker.compose.project=smoke-one" in args:
                return SimpleNamespace(returncode=0, stdout="smoke-one-db\n")
            return SimpleNamespace(returncode=0, stdout="")

        bases = {
            name: ["docker", "compose", "--project-name", name, "-f", f"{name}.yaml"]
            for name in ("smoke-one", "smoke-two")
        }
        with patch("smoke.subprocess.run", side_effect=fake_run):
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = dict(zip(bases, pool.map(
                    lambda name: cleanup_project(bases[name], name, {}), bases
                )))

        self.assertTrue(any("compose down failed" in error for error in results["smoke-one"]))
        self.assertTrue(any("still owns volumes" in error for error in results["smoke-one"]))
        self.assertEqual(results["smoke-two"], [])
        for args in calls:
            if "--project-name" in args:
                name = args[args.index("--project-name") + 1]
                self.assertEqual(name, "smoke-one" if "smoke-one" in args else "smoke-two")
            filters = [arg for arg in args if arg.startswith("label=com.docker.compose.project=")]
            for item in filters:
                self.assertIn(item.rsplit("=", 1)[1], ("smoke-one", "smoke-two"))


if __name__ == "__main__":
    unittest.main()
