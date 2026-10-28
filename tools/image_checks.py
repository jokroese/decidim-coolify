"""Resolve Docker image references to platform-specific immutable IDs."""
from __future__ import annotations

import json
import re
import subprocess


_IMAGE_ID = re.compile(r"^sha256:[0-9a-f]{64}$")


def _docker(args: list[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["docker", *args], text=True, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, check=False,
    )
    if result.returncode:
        raise RuntimeError(f"docker {' '.join(args)} failed: {result.stdout.strip()}")
    return result


def _platform(value: str) -> tuple[str, str, str | None]:
    parts = value.strip().lower().split("/")
    if len(parts) not in (2, 3) or not all(re.fullmatch(r"[a-z0-9_.-]+", p) for p in parts):
        raise RuntimeError(f"Invalid Docker platform {value!r}; expected os/architecture[/variant]")
    architecture = parts[1]
    aliases = {"x86_64": "amd64", "x86-64": "amd64", "x64": "amd64", "aarch64": "arm64"}
    architecture = aliases.get(architecture, architecture)
    variant = parts[2] if len(parts) == 3 else None
    arm_match = re.fullmatch(r"armv([0-9]+)l?", architecture)
    if arm_match:
        architecture, variant = "arm", variant or f"v{arm_match.group(1)}"
    parts[1] = architecture
    if variant is None:
        return parts[0], architecture, None
    return parts[0], architecture, variant


def _inspect(reference: str) -> tuple[str, tuple[str, str, str | None]] | None:
    result = subprocess.run(
        ["docker", "image", "inspect", reference], text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
    )
    if result.returncode:
        message = result.stdout.strip()
        lower_message = message.lower()
        if any(marker in lower_message for marker in ("no such image", "no such object", "not found")):
            return None
        raise RuntimeError(f"docker image inspect {reference!r} failed: {message}")
    try:
        image = json.loads(result.stdout)[0]
        image_id = image["Id"]
        actual = _platform(f"{image['Os']}/{image['Architecture']}" +
                           (f"/{image['Variant']}" if image.get("Variant") else ""))
    except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Could not read Docker image metadata for {reference!r}: {error}") from error
    if not _IMAGE_ID.fullmatch(image_id):
        raise RuntimeError(f"Docker returned a non-canonical image ID for {reference!r}: {image_id!r}")
    return image_id, actual


def _is_image_id(reference: str) -> bool:
    # Docker accepts full and abbreviated IDs. Treat a hexadecimal ID prefix as
    # immutable too, so a platform mismatch can never trigger a registry pull.
    return bool(re.fullmatch(r"(?:sha256:)?[0-9a-fA-F]{12,64}", reference))


def _matches(actual: tuple[str, str, str | None], requested: tuple[str, str, str | None]) -> bool:
    return actual[:2] == requested[:2] and (requested[2] is None or actual[2] == requested[2])


def image_platform(image_id: str) -> str:
    """Return the platform recorded for a locally available immutable ID."""
    found = _inspect(image_id)
    if found is None:
        raise RuntimeError(f"Resolved image ID {image_id!r} is no longer available locally")
    return "/".join(part for part in found[1] if part)


def resolve_image(image: str, platform: str | None = None) -> str:
    """Return the immutable local image ID for ``image`` on ``platform``.

    Tags and digests are pulled for the selected platform when they are absent
    locally or point at a different local platform. An explicit image ID is
    never pulled: a missing or mismatched ID is an error.
    """
    reference = image.strip()
    if not reference:
        raise RuntimeError("SMOKE_IMAGE must name a local image or published image reference")
    requested = _platform(platform) if platform else _platform(_docker(["info", "--format", "{{.OSType}}/{{.Architecture}}"]).stdout.strip())
    found = _inspect(reference)
    if found is not None and _matches(found[1], requested):
        return found[0]

    if _is_image_id(reference):
        if found is None:
            raise RuntimeError(f"Local image ID {reference!r} is unavailable; image IDs are never pulled")
        actual = "/".join(part for part in found[1] if part)
        wanted = "/".join(part for part in requested if part)
        raise RuntimeError(f"Local image ID {reference!r} has platform {actual}, requested {wanted}; image IDs are never pulled")

    platform_text = "/".join(part for part in requested if part)
    _docker(["pull", "--platform", platform_text, reference])
    found = _inspect(reference)
    if found is None:
        raise RuntimeError(f"Image {reference!r} was pulled but is not available locally")
    if not _matches(found[1], requested):
        actual = "/".join(part for part in found[1] if part)
        raise RuntimeError(f"Image {reference!r} resolved to platform {actual}, requested {platform_text}")
    return found[0]
