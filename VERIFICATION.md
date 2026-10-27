# Verification

For developers preparing releases and technical helpers assessing deployment readiness. This records test evidence, not setup instructions.

## Current status — 27 October 2026

| Area | Recorded result |
| --- | --- |
| Latest Linux amd64 image | Local build and full smoke test passed, including generated API documentation. |
| Latest Linux ARM64 image | Not retested locally after the cleanup; both architectures are configured in release CI. |
| Published release | No remote CI run or image publication recorded; Compose still has an unusable image marker. |
| Coolify deployment | Not verified on a target instance. |
| Real email and organisation onboarding | Not verified on a deployed site. |
| Backups and recovery | No verified automated backup schedule or isolated recovery rehearsal. |

## Work remaining before self-service setup

Follow [Help make setup ready](CONTRIBUTING.md#help-make-setup-ready). Record the tested source revision, image digest, architecture and Coolify version with each new result. A passing local smoke test does not establish working public HTTPS, real email delivery or recovery.

## Recorded evidence

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

The earlier application passed local ARM64 build and smoke checks on 26 October. That result does not cover the subsequent cleanup or documentation-generation change. Release CI is configured to repeat the checks for both architectures, but has not run remotely.
