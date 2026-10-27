"""Check that production image selection cannot drift into dashboard settings."""
import importlib.util
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pin_release import pin

spec = importlib.util.spec_from_file_location("deployment_validation", ROOT / "validate.py")
validation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validation)


class ReleaseImageTests(unittest.TestCase):
    def test_digest_is_accepted(self):
        validation.validate_image_reference("ghcr.io/example/decidim@sha256:" + "a" * 64)

    def test_version_and_digest_are_accepted(self):
        validation.validate_image_reference("ghcr.io/example/decidim:v0.1.0-rc.1@sha256:" + "a" * 64)

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


class ReleasePinTests(unittest.TestCase):
    def test_pinning_changes_only_the_image_anchor(self):
        source = (ROOT / "compose.yaml").read_text()
        image = "ghcr.io/example/decidim:v0.2.0@sha256:" + "b" * 64
        result = pin(source, image)
        self.assertIn("x-app-image: &app-image\n  image: " + image, result)
        old_image = re.search(r"^x-app-image: &app-image\n  image: (\S+)$", source, re.MULTILINE).group(1)
        self.assertEqual(result.replace(image, old_image), source)

    def test_missing_or_duplicate_anchor_is_rejected(self):
        image = "ghcr.io/example/decidim@sha256:" + "b" * 64
        for source in ("services: {}", "x-app-image: &app-image\n  image: old\nx-app-image: &app-image\n  image: duplicate"):
            with self.assertRaises(RuntimeError):
                pin(source, image)

    def test_mutable_tag_cannot_be_pinned(self):
        with self.assertRaises(RuntimeError):
            pin("x-app-image: &app-image\n  image: old", "ghcr.io/example/decidim:latest")


if __name__ == "__main__":
    unittest.main()
