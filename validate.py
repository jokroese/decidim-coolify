#!/usr/bin/env python3
"""Statically validate Compose using a disposable environment fixture.

This script calls `docker compose config`; it does not require or contact a
Docker daemon, start containers, or read the project's real `.env` file.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
COMPOSE = ROOT / "compose.yaml"
ENV_EXAMPLE = ROOT / ".env.example"
EXPECTED_SERVICES = {"web", "worker", "scheduler", "database", "redis"}
UNPUBLISHED_IMAGE = "registry.invalid/decidim-coolify:unpublished"


def validate_image_reference(image: str, *, allow_unpublished: bool = False) -> None:
    if image == UNPUBLISHED_IMAGE and allow_unpublished:
        return
    if not re.fullmatch(r"ghcr\.io/[a-z0-9._-]+/[a-z0-9._/-]+(?::[A-Za-z0-9_][A-Za-z0-9_.-]{0,127})?@sha256:[a-f0-9]{64}", image):
        raise RuntimeError("Pin x-app-image in compose.yaml to the published GHCR digest before deployment. "
                           "--allow-unpublished-image permits only the initial marker for development/CI.")


def compose_variable_names() -> set[str]:
    return set(re.findall(r"\$\{([A-Z0-9_]+)", COMPOSE.read_text()))


def required_variable_names() -> set[str]:
    return set(re.findall(r"\$\{([A-Z0-9_]+):\?", COMPOSE.read_text()))


def environment_fixture() -> dict[str, str]:
    fixture: dict[str, str] = {}
    for line in ENV_EXAMPLE.read_text().splitlines():
        match = re.match(r"^([A-Z][A-Z0-9_]*)=", line)
        if match:
            fixture[match.group(1)] = "disposable-fixture-value"
    fixture.update({
        "DECIDIM_APPLICATION_NAME": "Disposable validation",
        "DECIDIM_MAILER_SENDER": "test@example.invalid",
        "SERVICE_USER_DATABASE": "fixtureuser",
        "SERVICE_URL_WEB": "https://example.invalid",
        "SERVICE_FQDN_WEB_3000": "example.invalid",
        "SMTP_ADDRESS": "smtp.example.invalid",
        "SMTP_DOMAIN": "example.invalid",
        "SMTP_USERNAME": "fixture-user",
        "SMTP_PASSWORD": "disposable-smtp-password",
        "SMTP_PORT": "587",
        "SMTP_AUTHENTICATION": "plain",
        "SMTP_TLS": "false",
        "RAILS_LOG_LEVEL": "info",
        "SYSTEM_ADMIN_EMAIL": "admin@example.invalid",
    })
    fixture.update({
        key: "aB7cD9eF2gH4iJ6k" * 4
        for key in compose_variable_names() if key.startswith("SERVICE_PASSWORD")
    })
    return fixture


def write_fixture(path: Path, values: dict[str, str]) -> None:
    path.write_text("".join(f"{key}={value}\n" for key, value in sorted(values.items())))


def compose_environment() -> dict[str, str]:
    environment = os.environ.copy()
    # Compose gives the process environment precedence over --env-file. Remove
    # every variable used by this file so host or real deployment values cannot
    # override the disposable fixture.
    for key in compose_variable_names():
        environment.pop(key, None)
    environment["COMPOSE_DISABLE_ENV_FILE"] = "true"
    return environment


def run_config(env_file: Path, *, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["docker", "compose", "--env-file", str(env_file), "-f", str(COMPOSE), "config", "--format", "json"],
        cwd=ROOT,
        env=compose_environment(),
        capture_output=True,
        text=True,
    )
    if check and result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def validate_config(config: dict, *, allow_unpublished: bool = False) -> None:
    source = COMPOSE.read_text()
    match = re.search(r"^x-app-image: &app-image\n  image: (\S+)$", source, re.MULTILINE)
    require(match is not None, "Declare one literal x-app-image anchor in compose.yaml")
    image = match.group(1)
    validate_image_reference(image, allow_unpublished=allow_unpublished)
    require(source.count("<<: *app-image") == 3, "All three app roles must use the image anchor")
    require("APP_URL" not in compose_variable_names(),
            "The public URL must follow the Coolify web domain, not a separate saved APP_URL")
    require("DECIDIM_IMAGE" not in compose_variable_names(), "The production image must be owned by Git")
    services = config.get("services", {})
    require(set(services) == EXPECTED_SERVICES,
            f"Expected services {sorted(EXPECTED_SERVICES)}, got {sorted(services)}")

    application_images = {services[name].get("image") for name in ("web", "worker", "scheduler")}
    require(application_images == {image},
            "web, worker and scheduler must use the literal Git-owned application image")
    require(not any("build" in service for service in services.values()),
            "The Application must use published images without building on the deployment server")
    require(not any(service.get("ports") for service in services.values()),
            "No service may publish a host port")

    web_env = services["web"].get("environment", {})
    worker_env = services["worker"].get("environment", {})
    scheduler_env = services["scheduler"].get("environment", {})
    require(web_env.get("SERVICE_URL_WEB_3000") == "/",
            "Coolify's web URL magic variable must be declared as the literal path `/`")
    require(web_env.get("APP_URL") == "https://example.invalid",
            "APP_URL must use the fixture URL, not the web component's `/` magic-variable value")
    require("SERVICE_URL_WEB_3000" not in worker_env and "SERVICE_URL_WEB_3000" not in scheduler_env,
            "Coolify's web URL magic variable must be mapped only on web")

    for key in ("DATABASE_URL", "REDIS_URL", "SECRET_KEY_BASE", "QUEUE_ADAPTER"):
        require(web_env.get(key) == worker_env.get(key) == scheduler_env.get(key),
                f"web, worker and scheduler must share {key}")
    for key in ("SYSTEM_ADMIN_EMAIL", "INITIAL_SYSTEM_ADMIN_PASSWORD"):
        require(key not in worker_env and key not in scheduler_env,
                f"Bootstrap-only variable {key} must be set on web only")
    for name in ("web", "worker", "scheduler", "database", "redis"):
        require("healthcheck" in services[name], f"{name} must define a health check")
    require(services["web"].get("command") == ["web"], "web must select the web image role")
    require(services["worker"].get("command") == ["worker"], "worker must select the worker image role")
    require(services["scheduler"].get("command") == ["scheduler"], "scheduler must select the scheduler image role")

    web_deps = services["web"].get("depends_on", {})
    require({"database", "redis"} <= set(web_deps), "web must wait for database and Redis")
    for role in ("worker", "scheduler"):
        deps = services[role].get("depends_on", {})
        require({"web", "redis"} <= set(deps), f"{role} must wait for healthy web and Redis")
        require(deps["web"].get("condition") == "service_healthy",
                f"{role} must wait for web health, not only container start")

    expected_mounts = {
        name: {mount.get("source") for mount in services[name].get("volumes", [])}
        for name in ("web", "worker", "scheduler")
    }
    require("uploads" in expected_mounts["web"] and expected_mounts["web"] == expected_mounts["worker"] == expected_mounts["scheduler"],
            "web, worker and scheduler must share the uploads volume")
    require(any(mount.get("source") == "database-data" for mount in services["database"].get("volumes", [])),
            "PostgreSQL must have a persistent named volume")
    require(any(mount.get("source") == "redis-data" for mount in services["redis"].get("volumes", [])),
            "Redis must have a persistent named volume")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-unpublished-image", action="store_true",
                        help="Allow only the initial unpublished marker for development/CI, never deployment")
    args = parser.parse_args()
    if not COMPOSE.is_file() or not ENV_EXAMPLE.is_file():
        print("FAIL: compose.yaml or .env.example is missing", file=sys.stderr)
        return 2
    try:
        fixture = environment_fixture()
        required = required_variable_names()
        require(required <= set(fixture),
                "Missing fixture values for required Compose variables: " + ", ".join(sorted(required - set(fixture))))
        with tempfile.TemporaryDirectory(prefix="decidim-compose-validation-") as directory:
            env_file = Path(directory) / "fixture.env"
            write_fixture(env_file, fixture)
            resolved = run_config(env_file)
            validate_config(json.loads(resolved.stdout), allow_unpublished=args.allow_unpublished_image)

            for key in sorted(required):
                missing = fixture.copy()
                missing.pop(key, None)
                write_fixture(env_file, missing)
                result = run_config(env_file, check=False)
                require(result.returncode != 0,
                        f"Compose accepted missing required variable {key}")

        if args.allow_unpublished_image and UNPUBLISHED_IMAGE in COMPOSE.read_text():
            print("WARNING: unpublished image marker accepted for development; deployment remains blocked.")
        print("PASS: Git-owned image reference, Compose schema and disposable interpolation")
        print("PASS: five services, shared image and credentials, Coolify URL mapping, health checks, dependencies and persistent volumes")
        print("PASS: every required Compose variable rejects an absent fixture value")
        print("Docker daemon startup and Coolify behaviour are not tested by this script.")
        return 0
    except (OSError, subprocess.SubprocessError, RuntimeError, json.JSONDecodeError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
