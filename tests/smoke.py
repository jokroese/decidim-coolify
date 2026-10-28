#!/usr/bin/env python3
"""Disposable end-to-end checks for the Decidim Git-backed Compose Application.

This test creates one uniquely named Compose project, uses disposable settings,
creates no host ports, and removes only that project and its volumes on exit.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "compose.yaml"
ENV_EXAMPLE = ROOT / ".env.example"
UP_TIMEOUT = 600


def compose_variables() -> set[str]:
    return set(re.findall(r"\$\{([A-Z0-9_]+)", COMPOSE.read_text()))


def fixture_values() -> dict[str, str]:
    values: dict[str, str] = {}
    for line in ENV_EXAMPLE.read_text().splitlines():
        match = re.match(r"^([A-Z][A-Z0-9_]*)=", line)
        if match:
            values[match.group(1)] = "fixture-value"
    values.update({
        "DECIDIM_APPLICATION_NAME": "Disposable smoke test",
        "DECIDIM_MAILER_SENDER": "",
        "SERVICE_USER_DATABASE": "smokeuser",
        "SERVICE_URL_WEB": "https://smoke.example.invalid",
        "SERVICE_FQDN_WEB_3000": "smoke.example.invalid",
        "SMTP_ADDRESS": "",
        "SMTP_DOMAIN": "",
        "SMTP_USERNAME": "",
        "SMTP_PASSWORD": "",
        "SMTP_PORT": "587",
        "SMTP_AUTHENTICATION": "plain",
        "SMTP_TLS": "false",
        "ENABLE_INACTIVE_ACCOUNT_CLEANUP": "false",
        "RAILS_LOG_LEVEL": "info",
        "SYSTEM_ADMIN_EMAIL": "smoke-admin@example.invalid",
    })
    values.update({
        name: "aB7cD9eF2gH4iJ6k" * 4
        for name in compose_variables() if name.startswith("SERVICE_PASSWORD")
    })
    values["SERVICE_HEX_128_RAILS"] = "a1b2c3d4" * 16
    return values


def clean_environment() -> dict[str, str]:
    env = os.environ.copy()
    for key in compose_variables():
        env.pop(key, None)
    env["COMPOSE_DISABLE_ENV_FILE"] = "true"
    platform = os.environ.get("SMOKE_PLATFORM")
    if platform:
        env["DOCKER_DEFAULT_PLATFORM"] = platform
    else:
        env.pop("DOCKER_DEFAULT_PLATFORM", None)
    return env


def redact(output: str, values: dict[str, str]) -> str:
    for value in sorted(values.values(), key=len, reverse=True):
        if value and value != "fixture-value":
            output = output.replace(value, "[redacted]")
    return output


def main() -> int:
    if not COMPOSE.is_file() or not ENV_EXAMPLE.is_file():
        print("FAIL: run this script from the project containing compose.yaml and .env.example", file=sys.stderr)
        return 2

    project = "decidim-smoke-" + secrets.token_hex(5)
    values = fixture_values()
    env = clean_environment()
    with tempfile.TemporaryDirectory(prefix="decidim-compose-smoke-") as temp_dir:
        env_file = Path(temp_dir) / "fixture.env"
        env_file.write_text("".join(f"{key}={value}\n" for key, value in values.items()))
        # A disposable override selects the test build without making the
        # production image configurable through Coolify environment variables.
        image = os.environ.get("SMOKE_IMAGE", "decidim-coolify:test")
        override = Path(temp_dir) / "smoke.compose.json"
        override.write_text(json.dumps({"services": {
            role: {"image": image} for role in ("web", "worker", "scheduler")
        }}))
        base = [
            "docker", "compose", "--project-name", project,
            "--env-file", str(env_file), "-f", str(COMPOSE), "-f", str(override),
        ]

        def run(args: list[str], *, timeout: int = 120, check: bool = True) -> subprocess.CompletedProcess[str]:
            result = subprocess.run(base + args, cwd=ROOT, env=env, text=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    timeout=timeout)
            if check and result.returncode:
                raise RuntimeError(redact(result.stdout[-12000:], values))
            return result

        def runner(code: str) -> str:
            result = run([
                "exec", "-T", "web", "/app/docker/entrypoint", "rails", "runner", code,
            ], timeout=120)
            return result.stdout.strip()

        checkpoint = time.monotonic()

        def report(message: str) -> None:
            nonlocal checkpoint
            now = time.monotonic()
            print(f"PASS: {message} ({now - checkpoint:.1f}s)", flush=True)
            checkpoint = now

        started = False
        try:
            resolved = run(["config", "--format", "json"])
            config = json.loads(resolved.stdout)
            services = config["services"]
            expected_services = {"web", "worker", "scheduler", "database", "redis"}
            if set(services) != expected_services:
                raise RuntimeError(f"Expected exactly {sorted(expected_services)}, got {sorted(services)}")
            if any(service.get("ports") for service in services.values()):
                raise RuntimeError("Compose publishes a host port; the smoke test requires no host ports")
            if any("build" in service for service in services.values()):
                raise RuntimeError("Compose must use the supplied app image, not build from a local context")
            if {services[role]["image"] for role in ("web", "worker", "scheduler")} != {image}:
                raise RuntimeError("The temporary override must select the same test image for all app roles")
            for key in ("SYSTEM_ADMIN_EMAIL", "INITIAL_SYSTEM_ADMIN_PASSWORD"):
                if key in services["worker"].get("environment", {}) or key in services["scheduler"].get("environment", {}):
                    raise RuntimeError(f"Bootstrap-only variable {key} must be set on web only")

            # Fetch the selected architecture even if another variant is cached locally.
            run(["pull", "database", "redis"], timeout=UP_TIMEOUT)
            started = True
            run(["up", "--no-build", "--pull", "never", "--detach", "--wait", "--wait-timeout", str(UP_TIMEOUT)], timeout=UP_TIMEOUT + 60)
            report(f"all five services became healthy in disposable project {project}")

            for role in ("web", "worker", "scheduler"):
                uid = run(["exec", "-T", role, "id", "-u"]).stdout.strip()
                if uid != "1000":
                    raise RuntimeError(f"Expected {role} UID 1000, got {uid!r}")
                run(["exec", "-T", role, "ruby", "docker/healthcheck.rb", role], timeout=30)
            report("app roles run as UID 1000 and their health commands pass")

            task_check = r'''require "rake"; Rails.application.load_tasks
required = %w[db:migrate data:migrate]
missing = required.reject { |name| Rake::Task.task_defined?(name) }
raise "Missing migration tasks: #{missing.join(", ")}" unless missing.empty?
source = File.read("docker/crontab")
groups = File.read("docker/maintenance.rb").scan(/^  (\w+): \[/).flatten
scheduled = source.scan(/maintenance\.rb (\w+)/).flatten.uniq
raise "Missing scheduled groups: #{(scheduled - groups).join(", ")}" unless (scheduled - groups).empty?
scheduled.each do |group|
  body = File.read("docker/maintenance.rb").match(/^  #{Regexp.escape(group)}: \[(.*?)^  \]\.freeze/m)&.[](1)
  raise "Missing task list for schedule group #{group}" unless body
  names = body.scan(/"([^\"]+)"/).flatten
  missing = names.reject { |name| Rake::Task.task_defined?(name) }
  raise "Missing rake tasks for #{group}: #{missing.join(", ")}" unless missing.empty?
end
puts "SMOKE_TASKS_OK"'''
            route_check = r'''require "net/http"; require "uri"
public_uri = URI(ENV.fetch("APP_URL"))
http = Net::HTTP.new("127.0.0.1", 3000, nil)
http.open_timeout = 3; http.read_timeout = 10
request = lambda do |path|
  req = Net::HTTP::Get.new(path)
  host = public_uri.host
  host += ":#{public_uri.port}" unless [80, 443].include?(public_uri.port)
  req["Host"] = host
  req["X-Forwarded-Proto"] = "https"
  http.request(req)
end
response = request.call("/system")
2.times do
  break unless response.code.to_i.between?(300, 399)
  location = URI.join(public_uri.to_s, response["location"])
  abort "Sign-in redirect changed host" if location.host && location.host != public_uri.host
  response = request.call(location.request_uri.empty? ? "/" : location.request_uri)
end
abort "Unexpected sign-in response: #{response.code}" unless response.code == "200"
abort "Email instructions appeared before sign-in" if response.body.include?("Outgoing email") || response.body.include?("Email is not configured")
abort "Sign-in response is not HTML" unless response["content-type"].to_s.include?("text/html")
abort "Sign-in page has no HTML document" unless response.body.match?(/<html\b/i)
assets = response.body.scan(/(?:href|src)=["']([^"']+)["']/i).flatten
asset_path = assets.map { |path| URI.join(public_uri.to_s, path).request_uri }.find { |path| path.match?(%r{/(?:assets|packs|decidim-packs)/}) }
abort "Sign-in HTML has no compiled asset link" unless asset_path
asset = request.call(asset_path)
abort "Compiled asset returned #{asset.code}" unless asset.code == "200"
abort "Compiled asset body is empty" if asset.body.to_s.empty?
puts "SMOKE_SIGNIN_HTML_AND_ASSET_OK"'''
            mail_disabled = r'''raise "Email should be pending" unless Rails.application.config.action_mailer.delivery_method == :setup_required
class SetupSmokeMailer < ActionMailer::Base
  def probe
    mail(from: Decidim.mailer_sender, to: "nobody@example.invalid", subject: "setup test", body: "test")
  end
end
begin
  SetupSmokeMailer.probe.deliver_now
  raise "Unconfigured email was silently discarded"
rescue DeploymentConfiguration::EmailNotConfigured
  puts "SMOKE_EMAIL_PENDING_OK"
end'''
            initial_checks = runner("\n".join((task_check, route_check, mail_disabled)))
            for marker in ("SMOKE_TASKS_OK", "SMOKE_SIGNIN_HTML_AND_ASSET_OK", "SMOKE_EMAIL_PENDING_OK"):
                if marker not in initial_checks:
                    raise RuntimeError(f"Initial application checks did not confirm {marker}")
            report("migration/data tasks, sign-in assets and unconfigured email checks passed")
            run(["exec", "-T", "scheduler", "bundle", "exec", "ruby", "docker/maintenance.rb", "quarter_hour"], timeout=120)
            report("scheduled maintenance tasks ran successfully")

            sign_in_check = (ROOT / "tests" / "system_sign_in_check.rb").read_text()
            if "SMOKE_SYSTEM_SIGN_IN_OK" not in run(["exec", "-T", "web", "bundle", "exec", "ruby", "-e", sign_in_check]).stdout:
                raise RuntimeError("System sign-in HTTP checks did not complete")
            report("failed sign-in shows its error and valid credentials reach organisation setup")

            setup_check = (ROOT / "tests" / "organisation_setup_check.rb").read_text()
            if "SMOKE_ORGANISATION_SETUP_OK" not in runner(setup_check):
                raise RuntimeError("Organisation setup without email failed")
            report("organisation form, validation, access controls and deferred invitation")

            # Complete email setup without replacing volumes or bootstrap secrets.
            values.update({"SMTP_ADDRESS": "smtp.example.invalid", "SMTP_USERNAME": "smoke-user",
                           "SMTP_PASSWORD": "disposable-smtp-password"})
            env_file.write_text("".join(f"{key}={value}\n" for key, value in values.items()))
            run(["up", "--no-build", "--pull", "never", "--detach", "--wait", "--wait-timeout", str(UP_TIMEOUT)], timeout=UP_TIMEOUT + 60)
            smtp_check = 'settings = Rails.application.config.action_mailer.smtp_settings; raise "SMTP TLS verification disabled" unless settings[:openssl_verify_mode] == "peer" && settings[:enable_starttls] == true; raise "SMTP not enabled" unless Rails.application.config.action_mailer.delivery_method == :smtp; raise "SMTP domain default missing" unless settings[:domain] == "smoke.example.invalid"; raise "Sender default missing" unless Decidim.mailer_sender == "no-reply@smoke.example.invalid"'
            if "SMOKE_SIGNIN_HTML_AND_ASSET_OK" not in runner(smtp_check + "\n" + route_check):
                raise RuntimeError("Sign-in page failed after email configuration")
            report("adding SMTP enables verified TLS, applies domain defaults and preserves sign-in")

            if "SMOKE_ORGANISATION_SETUP_OK" not in runner(setup_check):
                raise RuntimeError("Organisation setup with configured email failed")
            report("configured organisation invitations and resend enqueue normally")

            initial_state = r'''count = Decidim::System::Admin.count; orgs = Decidim::Organization.count; raise "Expected exactly one system admin, got #{count}" unless count == 1; raise "Expected no sample organisations, got #{orgs}" unless orgs.zero?'''
            create_blob = r'''require "stringio"; payload = "decidim-coolify-smoke-#{Process.pid}-#{Time.now.to_i}"; encrypted = ActiveRecord::Encryption.encryptor.encrypt(payload); blob = ActiveStorage::Blob.create_and_upload!(io: StringIO.new(encrypted), filename: "decidim-coolify-smoke.txt", content_type: "text/plain", identify: false); blob.open { |file| raise "Upload read-back mismatch" unless ActiveRecord::Encryption.encryptor.decrypt(file.read) == payload }; puts "SMOKE_BLOB_ID=#{blob.id}"'''
            blob_output = runner(initial_state + "\n" + create_blob)
            match = re.search(r"SMOKE_BLOB_ID=(\d+)", blob_output)
            if not match:
                raise RuntimeError("Could not read the created ActiveStorage blob ID")
            blob_id = match.group(1)
            report("bootstrap created one administrator, no sample organisations and a readable encrypted upload")

            run(["restart", "web", "worker", "scheduler"], timeout=120)
            run(["up", "--no-build", "--pull", "never", "--detach", "--wait", "--wait-timeout", str(UP_TIMEOUT)], timeout=UP_TIMEOUT + 60)
            verify_blob = f'''blob = ActiveStorage::Blob.find({blob_id}); blob.open {{ |file| raise "Persistent upload contents changed" unless ActiveRecord::Encryption.encryptor.decrypt(file.read).start_with?("decidim-coolify-smoke-") }}; puts "SMOKE_BLOB_PERSISTED"'''
            if "SMOKE_BLOB_PERSISTED" not in runner(initial_state + "\n" + verify_blob):
                raise RuntimeError("Upload did not survive app-role restarts")
            report("the encrypted upload and administrator state survived web, worker and scheduler restarts")

            purge_check = f'''ActiveStorage::PurgeJob.perform_later(ActiveStorage::Blob.find({blob_id}))
deadline = Process.clock_gettime(Process::CLOCK_MONOTONIC) + 90
while ActiveRecord::Base.uncached {{ ActiveStorage::Blob.exists?({blob_id}) }}
  raise "Sidekiq did not process the queued ActiveStorage purge job within 90 seconds" if Process.clock_gettime(Process::CLOCK_MONOTONIC) >= deadline
  sleep 3
end
puts "SMOKE_BLOB_PURGED"'''
            if "SMOKE_BLOB_PURGED" not in runner(purge_check):
                raise RuntimeError("Sidekiq did not confirm the ActiveStorage purge job")
            report("Sidekiq consumed the ActiveStorage purge job")

            # Only create a tenant after checking that bootstrap/restarts do not
            # seed organisations. The disposable project owns all test data.
            docs_check = r'''require "net/http"; require "uri"
public_uri = URI(ENV.fetch("APP_URL"))
Decidim::Organization.create!(
  name: { en: "Documentation smoke test" }, host: public_uri.host,
  reference_prefix: "SMOKE", available_locales: ["en"], default_locale: "en",
  time_zone: "UTC"
)
http = Net::HTTP.new("127.0.0.1", 3000, nil)
http.open_timeout = 3; http.read_timeout = 10
request = lambda do |path|
  req = Net::HTTP::Get.new(path)
  req["Host"] = public_uri.host
  req["X-Forwarded-Proto"] = "https"
  http.request(req)
end
{"/api/docs" => "About the GraphQL API", "/api/docs/object/user" => "User"}.each do |path, text|
  response = request.call(path)
  raise "API documentation failed at #{path}: #{response.code}" unless response.code == "200"
  raise "API documentation content missing at #{path}" unless response.body.include?(text) && response.body.match?(/<html\b/i)
  assets = response.body.scan(/(?:href|src)=["']([^"']+)["']/i).flatten
  asset = assets.find { |url| url.include?("decidim_api_docs") && url.match?(/\.(?:css|js)(?:\?|$)/) }
  raise "API documentation has no compiled asset link" unless asset
  response = request.call(URI.join(public_uri.to_s, asset).request_uri)
  raise "API documentation asset failed" unless response.code == "200" && !response.body.to_s.empty?
end
puts "SMOKE_API_DOCS_OK"'''
            if "SMOKE_API_DOCS_OK" not in runner(docs_check):
                raise RuntimeError("Generated API documentation or its compiled asset failed")
            report("generated API documentation, a schema page and their compiled assets are served")
            print("SMOKE TEST PASSED")
            return 0
        except KeyboardInterrupt:
            print("Interrupted; removing only the disposable smoke project.", file=sys.stderr)
            return 130
        except (OSError, subprocess.SubprocessError, RuntimeError, json.JSONDecodeError) as error:
            print("SMOKE TEST FAILED: " + redact(str(error), values), file=sys.stderr)
            if started:
                logs = run(["logs", "--tail", "100", "web", "worker", "scheduler", "database", "redis"], timeout=60, check=False)
                print("Recent disposable-project logs:\n" + redact(logs.stdout, values), file=sys.stderr)
            return 1
        finally:
            # The generated project name scopes volume removal to this test only.
            subprocess.run(base + ["down", "--volumes", "--remove-orphans"], cwd=ROOT,
                           env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=120, check=False)


if __name__ == "__main__":
    raise SystemExit(main())
