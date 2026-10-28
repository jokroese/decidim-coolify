import importlib.machinery
import importlib.util
import contextlib
import io
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "bin" / "check"
loader = importlib.machinery.SourceFileLoader("check_cli", str(SCRIPT))
spec = importlib.util.spec_from_loader(loader.name, loader)
check_cli = importlib.util.module_from_spec(spec)
loader.exec_module(check_cli)


class CheckCliTests(unittest.TestCase):
    def setUp(self):
        # Expected CLI failures must not look like failures of the outer suite.
        output = contextlib.ExitStack()
        self.addCleanup(output.close)
        output.enter_context(contextlib.redirect_stdout(io.StringIO()))
        output.enter_context(contextlib.redirect_stderr(io.StringIO()))

    def test_image_command_requires_a_reference(self):
        with self.assertRaises(SystemExit) as raised:
            check_cli.parser().parse_args(["image"])
        self.assertEqual(raised.exception.code, 2)

    def test_interruption_reports_interrupted_status_and_exit_code(self):
        stdout = io.StringIO()
        stderr = io.StringIO()

        def interrupt() -> None:
            with check_cli.timed_stage("docs stage"):
                raise KeyboardInterrupt

        with patch.object(check_cli, "docs_check", side_effect=interrupt), \
                contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = check_cli.main(["docs"])

        self.assertEqual(result, 130)
        self.assertIn("INTERRUPTED docs stage (", stdout.getvalue())
        self.assertIn("INTERRUPTED total docs (", stdout.getvalue())
        self.assertIn("check interrupted", stderr.getvalue())

    def test_platform_is_limited_to_supported_architectures(self):
        with self.assertRaises(SystemExit) as raised:
            check_cli.parser().parse_args(["full", "--platform", "linux/s390x"])
        self.assertEqual(raised.exception.code, 2)

    def test_docs_command_checks_tracked_paths_offline_and_read_only(self):
        with patch.object(check_cli, "ROOT", Path("/tmp/a checkout")), \
                patch.object(check_cli, "markdown_files", return_value=[
                    "/tmp/a checkout/README.md", "/tmp/a checkout/docs/guide with spaces.md"
                ]), patch.object(check_cli, "check_docker"), \
                patch.object(check_cli, "run") as run:
            check_cli.docs_check()

        command = run.call_args.args[0]
        self.assertIn("--network", command)
        self.assertIn("none", command)
        self.assertIn("readonly", command[command.index("--mount") + 1])
        self.assertIn("--offline", command)
        self.assertIn("--include-fragments", command)
        self.assertEqual(command[-2:], ["/workspace/README.md", "/workspace/docs/guide with spaces.md"])

    def test_smoke_environment_contains_only_docker_client_settings_and_image(self):
        with patch.dict("os.environ", {
            "DATABASE_URL": "postgres://production", "RAILS_MASTER_KEY": "secret",
            "DOCKER_HOST": "unix:///tmp/docker.sock", "SMTP_PASSWORD": "password"
        }, clear=True):
            env = check_cli.sanitized_smoke_environment("sha256:" + "a" * 64, "linux/arm64")

        self.assertEqual(env, {
            "DOCKER_HOST": "unix:///tmp/docker.sock",
            "SMOKE_IMAGE": "sha256:" + "a" * 64,
            "SMOKE_PLATFORM": "linux/arm64",
        })

    def test_docker_commands_use_native_platform_unless_cli_overrides_it(self):
        with patch.dict("os.environ", {
            "PATH": "/bin", "DOCKER_DEFAULT_PLATFORM": "linux/amd64"
        }, clear=True):
            env = check_cli.docker_process_environment()
        self.assertEqual(env, {"PATH": "/bin"})
        self.assertEqual(check_cli.docker_process_environment({
            "PATH": "/bin", "DOCKER_DEFAULT_PLATFORM": "linux/arm64"
        }), {"PATH": "/bin"})

    def test_development_image_override_is_resolved_to_an_immutable_id(self):
        image_id = "sha256:" + "b" * 64
        with patch.dict("os.environ", {"CHECK_TOOL_IMAGE": "tools:cached"}), \
                patch("tools.image_checks.resolve_image", return_value=image_id) as resolve, \
                patch("tools.image_checks.image_platform", return_value="linux/amd64"), \
                patch.object(check_cli, "check_docker"), \
                patch.object(check_cli.subprocess, "run", return_value=SimpleNamespace(
                    returncode=0, stdout=image_id)):
            self.assertEqual(check_cli.build_development_image(), image_id)
        resolve.assert_called_once_with(image_id)

    def test_development_image_override_must_already_be_local(self):
        with patch.dict("os.environ", {"CHECK_TOOL_IMAGE": "tools:missing"}), \
                patch.object(check_cli, "check_docker"), \
                patch.object(check_cli.subprocess, "run", return_value=SimpleNamespace(
                    returncode=1, stdout="")), \
                patch("tools.image_checks.resolve_image") as resolve:
            with self.assertRaisesRegex(RuntimeError, "is not available locally"):
                check_cli.build_development_image()
        resolve.assert_not_called()

    def test_image_checks_use_immutable_image_read_only_tests_and_requested_platform(self):
        image_id = "sha256:" + "c" * 64
        with patch.object(check_cli, "ROOT", Path("/tmp/review checkout")), \
                patch.object(check_cli, "check_docker"), \
                patch.object(check_cli, "repository_state", return_value=("abc123", "dirty")), \
                patch("tools.image_checks.resolve_image", return_value=image_id) as resolve, \
                patch("tools.image_checks.image_platform", return_value="linux/arm64"), \
                patch.object(check_cli, "run") as run:
            check_cli.image_checks("release:tag", "linux/arm64")

        resolve.assert_called_once_with("release:tag", "linux/arm64")
        self.assertEqual(run.call_count, 3)
        ruby_test_commands = [call.args[0] for call in run.call_args_list[:2]]
        for command in ruby_test_commands:
            self.assertIn("--network", command)
            self.assertIn("none", command)
            self.assertIn("--platform", command)
            self.assertIn("linux/arm64", command)
            mount = command[command.index("--mount") + 1]
            self.assertEqual(mount, "type=bind,source=/tmp/review checkout/tests,target=/tests,readonly")
            self.assertIn(image_id, command)
            self.assertNotIn("DATABASE_URL", command)
        smoke_env = run.call_args_list[2].kwargs["env"]
        self.assertEqual(smoke_env["SMOKE_IMAGE"], image_id)
        self.assertEqual(smoke_env["SMOKE_PLATFORM"], "linux/arm64")

    def test_development_image_lockfiles_must_match_read_only_checkout(self):
        files = ("Gemfile", "Gemfile.lock", "package.json", "package-lock.json")
        lines = []
        for index, name in enumerate(files):
            digest = f"{index:064x}"
            lines.extend([f"{digest}  /app/{name}", f"{digest}  /workspace/app/{name}"])
        with patch.object(check_cli, "ROOT", Path("/tmp/checkout")), \
                patch.object(check_cli, "run_capture", return_value="\n".join(lines)) as run_capture:
            check_cli.verify_development_image_lockfiles("sha256:" + "d" * 64)

        command = run_capture.call_args.args[0]
        self.assertIn("none", command)
        self.assertIn("readonly", command[command.index("--mount") + 1])
        self.assertIn("/app/Gemfile.lock", command)
        self.assertIn("/workspace/app/package-lock.json", command)

        stale = lines.copy()
        stale[2] = f"{'f' * 64}  /app/Gemfile.lock"
        with patch.object(check_cli, "ROOT", Path("/tmp/checkout")), \
                patch.object(check_cli, "run_capture", return_value="\n".join(stale)):
            with self.assertRaisesRegex(RuntimeError, "CHECK_TOOL_IMAGE is stale: /app/Gemfile.lock"):
                check_cli.verify_development_image_lockfiles("sha256:" + "d" * 64)


if __name__ == "__main__":
    unittest.main()
