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
        values = {key: value for key, value in values.items() if value is not None}
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

    def test_missing_domain_fails_before_container_startup(self):
        for value in ("", None):
            with self.subTest(value=value), self.assertRaisesRegex(RuntimeError, "Save an HTTPS domain for web"):
                self.resolve({"SERVICE_URL_WEB": value})

    def test_missing_administrator_email_fails_before_container_startup(self):
        for value in ("", None):
            with self.subTest(value=value), self.assertRaisesRegex(RuntimeError, "Set SYSTEM_ADMIN_EMAIL in Coolify Environment Variables"):
                self.resolve({"SYSTEM_ADMIN_EMAIL": value})

    def test_domain_changes_reach_all_roles_despite_old_saved_values(self):
        for domain in ("https://first.example.invalid", "https://renamed.example.invalid"):
            services = self.resolve({
                "SERVICE_URL_WEB": domain,
                "SERVICE_URL_WEB_3000": "https://generated.example.invalid:3000",
                "APP_URL": "https://stale.example.invalid:3000",
            })
            for role in ("web", "worker", "scheduler"):
                self.assertEqual(services[role]["environment"]["APP_URL"], domain)

    def test_rails_secret_uses_the_128_character_generator_for_every_role(self):
        secret = "ab12" * 32
        services = self.resolve({"SERVICE_HEX_128_RAILS": secret, "SERVICE_PASSWORD_64_RAILS": "old-value"})
        for role in ("web", "worker", "scheduler"):
            self.assertEqual(services[role]["environment"]["SECRET_KEY_BASE"], secret)
        self.assertIn("SERVICE_HEX_128_RAILS", validation.required_variable_names())
        self.assertNotIn("SERVICE_PASSWORD_64_RAILS", validation.compose_variable_names())

    def test_app_roles_pull_the_same_git_owned_image(self):
        services = self.resolve({})
        images = {services[role]["image"] for role in ("web", "worker", "scheduler")}
        self.assertEqual(len(images), 1)
        for role in ("web", "worker", "scheduler"):
            self.assertNotIn("build", services[role])


if __name__ == "__main__":
    unittest.main()
