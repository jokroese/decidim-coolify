"""Check that production image selection cannot drift into dashboard settings."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("deployment_validation", ROOT / "validate.py")
validation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validation)


class ReleaseImageTests(unittest.TestCase):
    def test_digest_is_accepted(self):
        validation.validate_image_reference("ghcr.io/example/decidim@sha256:" + "a" * 64)

    def test_mutable_and_environment_references_are_rejected(self):
        for image in ("ghcr.io/example/decidim:latest", "ghcr.io/example/decidim:v1", "${DECIDIM_IMAGE}",
                      "ghcr.io/example/decidim@sha256:short"):
            for allow in (False, True):
                with self.subTest(image=image, allow=allow), self.assertRaises(RuntimeError):
                    validation.validate_image_reference(image, allow_unpublished=allow)

    def test_unpublished_marker_requires_explicit_development_exception(self):
        with self.assertRaises(RuntimeError):
            validation.validate_image_reference(validation.UNPUBLISHED_IMAGE)
        validation.validate_image_reference(validation.UNPUBLISHED_IMAGE, allow_unpublished=True)


if __name__ == "__main__":
    unittest.main()
