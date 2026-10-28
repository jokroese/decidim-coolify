"""Safety and lifecycle checks for the host-side development CLI."""

from __future__ import annotations

import contextlib
import importlib.util
import importlib.machinery
import io
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SOURCE_LOADER = importlib.machinery.SourceFileLoader("dev_cli", str(ROOT / "bin" / "dev"))
SPEC = importlib.util.spec_from_loader("dev_cli", SOURCE_LOADER)
assert SPEC and SPEC.loader
dev_cli = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dev_cli)


class DevelopmentCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "project"
        self.root.mkdir()
        self.state_dir = self.root / ".local" / "dev"
        self.env_file = self.state_dir / "env"
        self.lock_file = self.state_dir / ".lock"
        self.patches = [
            mock.patch.object(dev_cli, "ROOT", self.root),
            mock.patch.object(dev_cli, "COMPOSE_FILE", self.root / "compose.development.yaml"),
            mock.patch.object(dev_cli, "STATE_DIR", self.state_dir),
            mock.patch.object(dev_cli, "ENV_FILE", self.env_file),
            mock.patch.object(dev_cli, "LOCK_FILE", self.lock_file),
        ]
        for patcher in self.patches:
            patcher.start()
            self.addCleanup(patcher.stop)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_project_name_is_stable_and_worktree_specific(self) -> None:
        first = dev_cli.project_name()
        self.assertEqual(first, dev_cli.project_name())
        dev_cli.ROOT = self.root / "another-worktree"
        self.assertNotEqual(first, dev_cli.project_name())

    def test_docker_environment_does_not_inherit_app_secrets(self) -> None:
        with mock.patch.dict(os.environ, {
            "PATH": "/bin", "HOME": "/home/test", "DEV_PORT": "4321",
            "DATABASE_URL": "postgresql://real-user:real-password/db",
            "SECRET_KEY_BASE": "production-secret", "APP_URL": "https://live.example",
        }, clear=True):
            self.assertEqual(dev_cli.docker_environment(), {
                "PATH": "/bin", "HOME": "/home/test", "DEV_PORT": "4321",
            })

    def test_state_is_private_stable_and_port_override_persists(self) -> None:
        with mock.patch.dict(os.environ, {"DEV_PORT": "4321"}, clear=True):
            dev_cli.ensure_state()
            original = dev_cli.read_state()
            dev_cli.ensure_state()
        self.assertEqual(self.env_file.stat().st_mode & 0o777, 0o600)
        self.assertEqual(len(original["SECRET_KEY_BASE"]), 128)
        self.assertEqual(dev_cli.read_state()["SECRET_KEY_BASE"], original["SECRET_KEY_BASE"])
        self.assertEqual(dev_cli.read_state()["DEV_PORT"], "4321")

    def test_reset_without_state_uses_no_new_credentials(self) -> None:
        calls: list[list[str]] = []

        def fake_run(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            calls.append(args)
            return subprocess.CompletedProcess(args, 0)

        with mock.patch.object(dev_cli, "check_compose_version"), mock.patch.object(dev_cli, "run", side_effect=fake_run), mock.patch.object(dev_cli, "ensure_state") as ensure:
            self.assertEqual(dev_cli.main(["reset", "--yes"]), 0)
        ensure.assert_not_called()
        self.assertFalse(self.env_file.exists())
        self.assertIn("--volumes", calls[0])
        self.assertIn("--remove-orphans", calls[0])

    def test_missing_reset_confirmation_fails_before_docker(self) -> None:
        with self.assertRaisesRegex(SystemExit, "Confirm with: bin/dev reset --yes"):
            dev_cli.main(["reset"])
        self.assertFalse(self.state_dir.exists())

    def test_invalid_extra_arguments_are_rejected(self) -> None:
        with self.assertRaisesRegex(SystemExit, "Unexpected arguments"):
            dev_cli.main(["down", "--volumes"])
        with self.assertRaisesRegex(SystemExit, "Usage: bin/dev logs"):
            dev_cli.main(["logs", "web", "worker"])

    def test_no_arguments_runs_up(self) -> None:
        calls: list[list[str]] = []

        def fake_run(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            calls.append(args)
            return subprocess.CompletedProcess(args, 0)

        with mock.patch.object(dev_cli, "check_compose_version"), mock.patch.object(dev_cli, "prepare_environment"), mock.patch.object(dev_cli, "run", side_effect=fake_run), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(dev_cli.main([]), 0)
        self.assertIn("--watch", calls[0])

    def test_command_failure_returns_exit_code_without_traceback(self) -> None:
        error = subprocess.CalledProcessError(17, ["docker", "compose", "build"])
        stderr = io.StringIO()
        with mock.patch.object(dev_cli, "check_compose_version"), mock.patch.object(dev_cli, "ensure_state"), mock.patch.object(dev_cli, "prepare_environment", side_effect=error), contextlib.redirect_stderr(stderr):
            self.assertEqual(dev_cli.main(["up"]), 17)
        self.assertIn("exit status 17", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_interrupt_stops_services_and_preserves_state(self) -> None:
        self.state_dir.mkdir(parents=True)
        dev_cli.write_state({
            "COMPOSE_PROJECT_NAME": dev_cli.project_name(), "DEV_PORT": "3000",
            "DB_PASSWORD": "db", "REDIS_PASSWORD": "redis", "SECRET_KEY_BASE": "a" * 128,
            "ACTIVE_RECORD_ENCRYPTION_PRIMARY_KEY": "b" * 64,
            "ACTIVE_RECORD_ENCRYPTION_DETERMINISTIC_KEY": "c" * 64,
            "ACTIVE_RECORD_ENCRYPTION_KEY_DERIVATION_SALT": "d" * 64,
            "SYSTEM_ADMIN_EMAIL": "admin@example.test", "SYSTEM_ADMIN_PASSWORD": "password",
        })
        calls: list[list[str]] = []

        def interrupt_up(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            calls.append(args)
            if "--watch" in args:
                raise KeyboardInterrupt
            return subprocess.CompletedProcess(args, 0)

        with mock.patch.object(dev_cli, "check_compose_version"), mock.patch.object(dev_cli, "prepare_environment"), mock.patch.object(dev_cli, "run", side_effect=interrupt_up), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(dev_cli.main(["up"]), 130)
        self.assertIn("stop", calls[-1])
        self.assertTrue(self.env_file.exists())


if __name__ == "__main__":
    unittest.main()
