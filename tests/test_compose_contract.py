"""Exercise first-run interpolation without real settings or a Docker daemon."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("deployment_validation", ROOT / "validate.py")
validation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validation)


class ComposeSetupTests(unittest.TestCase):
    def resolve(self, changes):
        values = validation.environment_fixture()
        values.update(changes)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.env"
            validation.write_fixture(path, values)
            return json.loads(validation.run_config(path).stdout)["services"]

    def test_email_can_be_omitted_on_first_start(self):
        services = self.resolve({key: "" for key in (
            "SMTP_ADDRESS", "SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_DOMAIN", "DECIDIM_MAILER_SENDER"
        )})
        for role in ("web", "worker", "scheduler"):
            self.assertEqual(services[role]["environment"]["SMTP_ADDRESS"], "")
            self.assertEqual(services[role]["environment"]["APP_URL"], "https://example.invalid")

    def test_runtime_settings_do_not_block_build_interpolation(self):
        services = self.resolve({"APP_URL": "", "SERVICE_URL_WEB_3000": "", "SYSTEM_ADMIN_EMAIL": ""})
        self.assertEqual(services["web"]["environment"]["APP_URL"], "")

    def test_explicit_url_can_recover_missing_generated_url(self):
        services = self.resolve({"APP_URL": "https://custom.example.invalid", "SERVICE_URL_WEB_3000": ""})
        for role in ("web", "worker", "scheduler"):
            self.assertEqual(services[role]["environment"]["APP_URL"], "https://custom.example.invalid")

    def test_app_roles_pull_the_same_git_owned_image(self):
        services = self.resolve({})
        images = {services[role]["image"] for role in ("web", "worker", "scheduler")}
        self.assertEqual(len(images), 1)
        for role in ("web", "worker", "scheduler"):
            self.assertNotIn("build", services[role])


if __name__ == "__main__":
    unittest.main()
