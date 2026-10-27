#!/usr/bin/env python3
"""Pin a published GHCR digest in the matching source revision's Compose file."""
import argparse
from pathlib import Path
import re

from validate import validate_image_reference


def pin(source: str, image: str) -> str:
    validate_image_reference(image)
    updated, count = re.subn(r"^x-app-image: &app-image\n  image: \S+$",
                             "x-app-image: &app-image\n  image: " + image, source, flags=re.MULTILINE)
    if count != 1:
        raise RuntimeError("Expected exactly one x-app-image anchor")
    return updated


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", help="Complete ghcr.io/owner/repository@sha256:… reference")
    args = parser.parse_args()
    path = Path(__file__).resolve().parent / "compose.yaml"
    path.write_text(pin(path.read_text(), args.image))
    print("Pinned the published image in compose.yaml. Validate and smoke-test before deployment.")
