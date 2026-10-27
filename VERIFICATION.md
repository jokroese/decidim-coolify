# Verification

For developers preparing releases and technical helpers assessing deployment readiness. This records test evidence, not setup instructions.

## Current status — 28 October 2026

| Area | Recorded result |
| --- | --- |
| Latest Linux amd64 image | Release CI and full smoke tests against the anonymously pulled published digest passed. |
| Latest Linux ARM64 image | Release CI and full smoke tests against the anonymously pulled published digest passed. |
| Published release | `v0.1.0-rc.1` is published to public GHCR for both architectures; Compose pins its version and digest. |
| Coolify deployment | First target attempt fetched `6544f71` and reached healthy PostgreSQL/Redis, then web rejected its URL/admin configuration. Successful target deployment is not yet verified. |
| Real email and organisation onboarding | Not verified on a deployed site. |
| Backups and recovery | No verified automated backup schedule or isolated recovery rehearsal. |

## Work remaining before self-service setup

Follow [Help make setup ready](CONTRIBUTING.md#help-make-setup-ready). Record the tested source revision, image digest, architecture and Coolify version with each new result. A passing local smoke test does not establish working public HTTPS, real email delivery or recovery.

## Recorded evidence

### Domain source and required settings — 28 October 2026

The first target deployment demonstrated that a passing Docker smoke test did not establish a usable Coolify setup. Its deployment log hid web's configuration error behind an unhealthy dependency. The user had saved the intended domain, but the separate `APP_URL` setting still displayed Coolify's generated hostname with internal port 3000; the runtime error also reported a missing administrator email. The displayed URL alone would pass the existing syntax validator, so the exact failed container's URL remains unconfirmed.

The revised Compose definition maps runtime `APP_URL` directly from Coolify's base `SERVICE_URL_WEB` and marks that generated value and `SYSTEM_ADMIN_EMAIL` required with native Compose diagnostics. The port-specific declaration remains on web for routing. No new image or custom setup service is required.

- Compose validation and all 12 Python tests passed, including unset/empty required values, a stale saved `APP_URL`, a port-suffixed generated value and a domain change reaching all three application roles.
- Reviewed Coolify's upstream Application parser and `syncComposeServiceUrlVariables`: base URL variables derive from the saved domain without the internal port; port-suffixed variants include that port. These source checks do not establish the installed Coolify version's behaviour.
- A generated wildcard hostname can satisfy the URL requirement. The installer still selects or confirms the intended web domain.
- The revised clean-install and domain-change flows still need verification on the target Coolify instance. The next target test must use the documented domain/email inputs, without an `APP_URL` workaround.


### First public image — 28 October 2026

[Release CI run 40592231575](https://github.com/jokroese/decidim-coolify/actions/runs/40592231575) passed native amd64 and ARM64 builds, migration/configuration tests and full smoke tests, then published `v0.1.0-rc.1` from source revision `7a95f089ccfbd91171b48f5748628f5af9203aa8`.

- Published image: `ghcr.io/jokroese/decidim-coolify:v0.1.0-rc.1@sha256:3ec809133f230ee7ddd2aa28ea80fc9c13e16ffc83d84f462e70e1b30247598a`.
- Anonymous manifest inspection and pulls succeeded for both Linux architectures with an isolated Docker configuration containing no credentials.
- Full smoke tests against that published digest passed for both `SMOKE_PLATFORM=linux/amd64` and `SMOKE_PLATFORM=linux/arm64`. The amd64 check ran under emulation on Apple Silicon.
- Both runs verified all five healthy services, initial setup without SMTP, enabling SMTP configuration without losing administrator state, migrations, API documentation and assets, scheduled execution, encrypted uploads surviving restarts and Sidekiq processing. Real email was not sent.
- The disposable smoke projects `decidim-smoke-99b4eac96b` and `decidim-smoke-34a40a2bd4` were removed with their volumes.
- The release deployment reference is committed separately from the image's source tag. No Coolify deployment or live recovery rehearsal has been performed.

### Simpler first-run setup — 27 October 2026

The default deployment still pulls one digest-pinned GHCR image for all three app roles. No source build was added to the deployment definition. At the time of these local checks, the first release was unpublished. These changes have not been deployed to Coolify.

- `docker build --platform linux/amd64 -t decidim-coolify:first-run-test .` passed, including upstream migration checks, API documentation and asset compilation. Docker reported image identifier `sha256:a2ff42fbb99665a8c1896aba3409e62df0e8e4da1f54e4d8ee16c8a955aef2de`.
- Compose validation with the development marker exception and all 10 Python configuration/release tests passed.
- Ruby configuration tests passed: 9 tests, 38 assertions. Migration completeness tests passed: 9 tests, 26 assertions.
- The actual startup check reported missing domain and administrator settings together before Rails or database access, with no stack trace.
- `SMOKE_IMAGE=decidim-coolify:first-run-test SMOKE_PLATFORM=linux/amd64 python3 tests/smoke.py` passed. All five services became healthy without SMTP; the system sign-in page displayed the setup notice and attempted email delivery raised an explicit error.
- Adding SMTP settings and recreating the app roles enabled verified STARTTLS, applied the sender/greeting-domain defaults and removed the setup notice. No real SMTP connection or delivery was attempted.
- The same run verified migrations, bootstrap, compiled assets, scheduled execution, encrypted upload persistence after restarts, Sidekiq processing and generated API documentation. The disposable project `decidim-smoke-2fbc09016e` was removed with its volumes.
- A preliminary smoke run failed because its test called a nonexistent mailer class method; the test was corrected and the complete stack rerun successfully.
- Changed Markdown links and whitespace checks passed. A separate code review found no blocking issues. ARM64 coverage for these new changes will run in CI before publication.


### Remote image checks — 27 October 2026

[GitHub Actions run 40587635392](https://github.com/jokroese/decidim-coolify/actions/runs/40587635392) passed native amd64 and ARM64 builds, migration tests and smoke tests for commit `a51c8a7d76876221f8dcf4d20b8996b2bc7e0cb8`. The publication job was skipped because this was a push to `main`, not a version-tag release. The `.dockerbuild` artefacts contain build diagnostics, not deployable images.


### Generated documentation and source boundaries — 27 October 2026

The image build now runs `decidim_api:generate_docs` before asset compilation. The 199 previously generated files were removed from the source directory; Git and Docker ignore local copies. All 641 installed migrations, dependency lockfiles and the application licence are unchanged by this step. Application ignore rules now cover vendored gems, generated documentation and assets, caches, runtime data and both shared and per-environment Rails credentials.

- Two documentation-generation runs in a disposable container without network or database access produced identical file hashes.
- The production generator emits 198 files. The only omitted path compared with the old development-generated inventory is the `DummyResource` page.
- `docker build --platform linux/amd64 -t decidim-coolify:generated-docs-test .` passed with documentation absent from the source directory and excluded from the context.
- Local image identifier: `sha256:7e6813b477090d308f275100615d65893533ca0ca0e675686cb70fd81282448a`.
- Compose validation, all three release-reference tests, ignore/source inventory checks and migration hash checks passed.
- `SMOKE_IMAGE=decidim-coolify:generated-docs-test SMOKE_PLATFORM=linux/amd64 python3 tests/smoke.py` passed after Docker Desktop was running again. The full test verified service health, UID 1000, migrations, bootstrap without sample organisations, sign-in HTML and assets, scheduled-task execution, SMTP TLS configuration, upload persistence across restarts and Sidekiq job processing.
- The new HTTP checks passed for `/api/docs`, `/api/docs/object/user` and their compiled assets, using a disposable organisation created after the no-demo-seeding checks.
- The interrupted project (`decidim-smoke-477f75d297`) and the successful rerun (`decidim-smoke-d3fddb4cab`) were removed, including their containers, volumes and networks. Nothing was published or deployed to Coolify. This verification used Linux amd64 under emulation on Apple Silicon; ARM64 remains covered by the configured release CI, not by this local rerun.

### Earlier cleanup — 27 October 2026

Verified locally with Docker Desktop on Apple Silicon. The cleaned application was rebuilt for Linux amd64 under emulation; nothing was published or deployed to Coolify.

- **Image:** `decidim-coolify:lean-test`
- **Local image ID:** `sha256:31a6b67d007b2a377d984a8711dd401a10517c517a798198c47747ef16863ba0`
- **Build:** `docker build --platform linux/amd64 -t decidim-coolify:lean-test .` passed, including locked Ruby/npm installation and production asset compilation.
- **Runtime:** `SMOKE_IMAGE=decidim-coolify:lean-test SMOKE_PLATFORM=linux/amd64 python3 tests/smoke.py` passed.

The full smoke test verified:

- All five services becoming healthy, with application roles running as UID 1000.
- Schema/data migrations, one initial system administrator and no sample organisations.
- Sign-in HTML, a compiled asset, available scheduled tasks and an actual scheduled-task execution.
- SMTP configuration requiring TLS and certificate verification; no real email delivery was attempted.
- An encrypted upload and administrator state surviving application-role restarts, followed by Sidekiq consuming a real ActiveStorage purge job.

Static checks passed: Compose validation with the explicit unpublished-image exception, three release-reference tests, changed Ruby syntax, documentation links and changed-file whitespace checks. The optional developer lint and security commands in `app/bin/ci` were retained but were not run as part of this cleanup.

### Dependency and scope checks

Regenerating the lockfiles removed **401 npm development-only package entries** and **seven unused Ruby gems** associated with S3. Versions of retained packages did not change. The fresh build and smoke test used these new lockfiles. The refreshed npm audit still reports one high-severity finding; see [DEPENDENCY-AUDIT.md](DEPENDENCY-AUDIT.md).

The earlier cleanup retained all 199 generated API documentation files; the subsequent change above moves their generation into the image build. Installed migrations, lockfiles, runtime/bootstrap/health scripts and backup/restore procedures remain. Historical research inventory, duplicate audit material and old short smoke logs were removed. Reproduced upstream build issues remain summarised in [UPSTREAM.md](UPSTREAM.md).

### Earlier architecture evidence

The earlier application passed local ARM64 build and smoke checks on 26 October. That result does not cover the subsequent cleanup or documentation-generation change. The later remote run for `a51c8a7` recorded above now covers both architectures.
