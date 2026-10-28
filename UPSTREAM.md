# Upstream assessment: decidim/docker

For developers maintaining the application image. See [Contributing](CONTRIBUTING.md) for the build and release workflow.

For the organisation creation form, see the separate [usability contribution plan](docs/ORGANISATION-SETUP.md). Those changes target `decidim/decidim`, rather than the Docker packaging repository.

## Decision

Use a custom, repository-built Decidim 0.32.1 image for this Coolify deployment. The application image available in the investigation was 0.31.6, and the 0.32.1 generator did not produce a complete production runtime without changes. Keeping the image here allows deployment work to proceed while upstream improvements are reviewed independently.

The custom image packages the generated application, pinned Ruby and frontend dependencies, production runtime configuration, web and worker processes, recurring tasks, and deployment checks. Keep the application itself aligned with Decidim releases. Propose packaging or runtime fixes upstream as small changes with focused reproductions; do not treat open issues or PRs as accepted or tested work.

Revisit the custom image when an official image supports the required Decidim release and architectures, offers equivalent runtime configuration, persistence, jobs and upgrade behaviour, and passes this repository's deployment checks. Test migration and restoration against a copy of the organisation's database and uploads, preserve secrets and volume identities, and retire the custom image only after that transition succeeds.

## Reproduced during the 0.32.1 build

The following findings come from this repository's build investigation; they are not claims that current upstream defects remain open. The investigation was recorded on **26 October 2026** and has not been refreshed against upstream since then.

- The pinned official GHCR 0.32.1 generator failed because `libvips.so.42` was absent. Adding Debian `libvips-tools` allowed generation to finish.
- Generation selected `@decidim/*` frontend packages at 0.32.2 for a Ruby Decidim 0.32.1 application. This repository pins the frontend packages to 0.32.1 and commits both lockfiles. A focused upstream fix should derive frontend versions from the selected application release.
- Production eager loading imports `decidim/seeds` through the comments model and failed when `faker` was excluded with development gems. This repository declares the already-locked Faker version at runtime without invoking seeds. A focused fix should remove production dependence on seed code.
- Generated production SMTP configuration disabled certificate verification. This repository requires peer verification and supports an explicit implicit-TLS setting for port 465.
- The investigation identified a stale COPY/chmod pair in `Dockerfile-dev`; [`dev-image-build-fix.patch`](dev-image-build-fix.patch) is a candidate patch, not an upstream contribution or confirmed fix. The historical release-dispatch HTTP error had a separate, unknown cause.

Reproduce each issue against the current upstream revision before proposing a change. The local findings above do not establish that upstream still has these defects.

## Actionable upstream context

These links were assessed during the dated investigation. They are starting points for coordination, not statements about their current status.

- [docker #131: installer improvements](https://github.com/decidim/docker/issues/131) — follow the installer direction; its host setup, firewall and Traefik ownership are outside this Git-backed Coolify application.
- [docker #128: multi-architecture builds](https://github.com/decidim/docker/pull/128) and [docker #99: ARM64 image request](https://github.com/decidim/docker/issues/99) — coordinate on a tested, application-focused scope rather than expanding image pipelines without maintainer alignment.
- [docker #120: production workflow issues](https://github.com/decidim/docker/issues/120) and [docker #130: Decidim in Docker](https://github.com/decidim/docker/issues/130) — useful runtime context; verify current behaviour before filing focused reports.
- [docker #121: PostgreSQL version pin](https://github.com/decidim/docker/pull/121), [#123: Compose instructions](https://github.com/decidim/docker/pull/123), and [#132: installer CI](https://github.com/decidim/docker/pull/132) — existing proposals that may overlap with future upstream work. Check their current state and scope before duplicating changes.
- [docker #126: SMTP STARTTLS type report](https://github.com/decidim/docker/issues/126) — the inspected 0.31.6 source appeared to address the reported Boolean type symptom; certificate verification was a separate concern in that investigation.
