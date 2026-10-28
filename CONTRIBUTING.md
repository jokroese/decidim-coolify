# Contributing

Help collectives set up and maintain Decidim with less technical work. Keep the [setup guide](README.md) focused on their actions; put implementation details here or in the linked technical references.

## Help make setup ready

The [verification record](VERIFICATION.md) distinguishes completed checks from untested deployment steps. Before describing setup as self-service:

1. Publish an image, test its digest and pin it in the deployment configuration.
2. Follow the README on a clean Coolify installation. Record the Coolify version, server architecture and resource usage; correct missing or misleading steps.
3. Complete organisation setup, real email delivery, upload persistence and background-job checks on that installation.
4. Provide and verify a repeatable backup schedule, failure reporting, secret export and isolated recovery. Document what the collective must arrange and what the project provides.
5. Ask someone outside the development team to follow the setup guide. Resolve the points where they need undocumented help.

## Find the code

| Change | Start here |
| --- | --- |
| Images, installed tools and asset compilation | [Dockerfile](Dockerfile) |
| Coolify settings, roles, storage and startup order | [compose.yaml](compose.yaml) |
| Process startup and administrator creation | [entrypoint](docker/entrypoint), [prepare.rb](docker/prepare.rb) |
| Readiness, worker and scheduler checks | [healthcheck.rb](docker/healthcheck.rb) |
| Recurring jobs | [crontab](docker/crontab), [maintenance.rb](docker/maintenance.rb) |
| Rails configuration and dependency versions | [app/](app/) |
| Deployment validation and runtime checks | [validate.py](validate.py), [tests/](tests/) |
| CI and image publication | [images.yml](.github/workflows/images.yml) |

`app/` is the Rails application hosting Decidim. Decidim itself comes from locked upstream gems and frontend packages. Normal builds use the committed application; they do not regenerate it. Ruby and Node base images are pinned by digest. Node and compilation tools remain in the build stage.

## Build and check a change

Clone the repository and run the following commands from its root. Install Docker with Compose v2, Node.js 22 or later and Python 3; builds also need network access and free disk space for dependencies and compiled assets. Python tests use the standard library. Ruby migration tests run inside the image.

Run the quick checks first:

```sh
node --test tests/organisation_setup_test.mjs
python3 validate.py --allow-unpublished-image
python3 -m unittest discover -s tests -p "test_*.py"
```

Validation uses disposable values and does not read the project's `.env` or start containers. The unpublished-image exception permits only the initial marker for development; it is never a deployment setting.

Build the changed source, then run the migration tests and full stack:

```sh
docker build --platform linux/amd64 -t decidim-coolify:test .
docker run --rm --network none --entrypoint bundle \
  --mount "type=bind,source=$PWD/tests,target=/tests,readonly" \
  decidim-coolify:test exec ruby /tests/migration_completeness_test.rb
docker run --rm --network none --entrypoint ruby \
  --mount "type=bind,source=$PWD/tests,target=/tests,readonly" \
  decidim-coolify:test /tests/deployment_configuration_test.rb
SMOKE_IMAGE=decidim-coolify:test SMOKE_PLATFORM=linux/amd64 python3 tests/smoke.py
```

For a native ARM64 check, replace both `linux/amd64` values with `linux/arm64`. Emulation is slower. CI is configured to build and test both architectures on native runners.

The smoke test starts web, worker, scheduler, PostgreSQL and Redis in a uniquely named disposable project. It supplies its own test settings; no email account or Coolify installation is needed. Expect `PASS` output and exit status 0. It checks migrations, initial administrator creation, health, compiled assets, API documentation, scheduled tasks, a worker job and upload persistence across restarts. It starts without SMTP, verifies the setup notice and explicit delivery failure, then adds SMTP and checks that delivery settings and the notice change.

Read the failure output to identify the failed check and service logs. Fix the source, rebuild the image and rerun the relevant checks. The smoke test removes its own project and volumes on exit; if Docker becomes unavailable, confirm cleanup once it recovers. Never remove another project's volumes.

This is the supported container test loop. It exposes no browser port and does not send real email or test Coolify routing. Use an isolated Coolify pilot for the [manual setup checks](README.md#set-up). A documented interactive development environment is still missing: `app/config/database.yml` configures production only, and `app/bin/dev` runs `decidim:upgrade` as well as migrations. Do not treat the generated Rails helpers as a ready-made local setup.

For optional Ruby style and security checks, install the application bundle including development dependencies, then run `bin/ci` from `app/`. Those checks are separate from release CI.

## Choose checks for the change

| Change | Verification |
| --- | --- |
| Documentation only | Follow the reader's path; check relative links, anchors and commands against the source. |
| Compose, configuration or release references | Run validation and Python tests; run the smoke test if runtime behaviour changes. |
| Application, dependencies, Dockerfile or process scripts | Rebuild; run migration tests and the full smoke test. |
| Coolify setup, email or recovery | Complete the affected procedure on an isolated installation and record the result. |

Include the problem, resulting behaviour and checks run in your contribution. Describe any setup changes a collective must make. If a required check could not run, record that limitation rather than claiming it passed.

## Source and generated files

Commit configuration, custom code, asset entry points, dependency manifests and lockfiles, installed migrations, required scripts and the licence. Keep secrets, installed dependencies, caches, logs, uploads and generated assets out of Git and the build context.

Preserve installed engine migration filenames. Regenerating migrations can give them new timestamps and make Rails attempt changes again.

The build runs `deployment:check_migrations` against the locked bundle before compiling assets. It checks that loaded Decidim engines' schema migrations exist locally and their upstream data migration paths are registered. It does not compare historical file contents or query a database. Decidim 0.32 loads data migrations from its gems; local copies are unnecessary.

The build also runs `decidim_api:generate_docs`. Its output in `app/app/views/static/api/docs/` is excluded from Git and the build context, included in the final image and served at `/api/docs`. With the application bundle and configuration available, regenerate it from `app/` using `bundle exec rails decidim_api:generate_docs`.

## Preparing a Decidim upgrade

Use a development checkout with the target release's Ruby and Node versions, Bundler, npm and application dependencies installed. Configure that checkout for an isolated development or restored test database. Keep production credentials out of this environment. These commands run from `app/`; use a development bundle that permits dependency updates, not the production image's frozen bundle.

1. Read the [Decidim release notes](https://github.com/decidim/decidim/releases) for each required upgrade step. Follow the supported version sequence and any release-specific actions. Update the Decidim version pins in `Gemfile`, including `decidim-dev` and any optional Decidim modules.
2. Update the bundle and run Decidim's application upgrade task:

   ```sh
   bundle update decidim
   bin/rails decidim:upgrade
   ```

   The upgrade task imports missing schema migrations. In Decidim 0.32.1 it can also patch historical migration contents and update frontend configuration. Preserve existing migration filenames and review every change. Do not delete and regenerate the migration directory. Changes to an already-applied migration do not rerun that migration on an existing database; follow the release notes for any required corrective action.

3. Check that every `@decidim/*` dependency in `package.json` matches the selected Ruby Decidim release. Correct any version drift introduced by the generator, then update the npm lockfile and check migration completeness:

   ```sh
   npm install
   bundle exec rails deployment:check_migrations
   ```

   Expect a `PASS` message with schema and data migration counts. A missing schema migration requires importing and reviewing the upstream migration. An unregistered data migration requires correcting the engine initialisers or data migration paths. Decidim 0.32 registers `db/data` directories inside the installed gems; do not copy those files into the app to satisfy the check. The check compares migration names and engine scopes, allowing the local timestamps assigned by Rails. It does not compare historical migration contents or query the database.

4. Review and commit the manifests, lockfiles, imported migrations and required application configuration together. Run the local build and checks in [Build and check a change](#build-and-check-a-change). The Docker build repeats the completeness check against its locked production bundle and fails before asset compilation if migrations are missing.
5. Rehearse the new image against an isolated restore before production deployment. Image startup runs `db:migrate` followed by `data:migrate`. If testing directly from the development checkout, apply them to the isolated database with:

   ```sh
   bin/rails db:migrate
   bin/rails data:migrate
   ```

   Confirm both commands succeed and complete any release-specific data repair tasks. Verify the affected application behaviour as well as the smoke checks. Then follow the [technical deployment and rollback procedure](docs/OPERATIONS.md#upgrades-and-rollback).

## Publishing a release

For maintainers with repository and registry publishing access. Publish and pin each release once; collectives then pull the same prebuilt image. They do not run these steps. Publishing an image does not deploy it.

1. Make the repository available on GitHub. The workflow derives its GHCR image name from the repository owner and name.
2. Once this workflow is on the default branch, run **Container image → Run workflow** on the reviewed source revision, or push a reviewed `v*` release tag. Wait for both architecture test jobs and the publication job to succeed. The workflow publishes a commit SHA tag, an SBOM and provenance; version-tag runs also publish the version tag. Pushes to `main` only build and test. The `.dockerbuild` artefacts are diagnostic build records, not pullable images.
3. Make the package public so collectives can pull it without registry credentials. For a private pilot, configure registry access in Coolify instead.
4. Copy the complete `ghcr.io/OWNER/REPOSITORY@sha256:…` reference from the workflow summary. Set `SMOKE_IMAGE` to that actual reference and run `tests/smoke.py` for each supported architecture, setting `SMOKE_PLATFORM` accordingly. The example ellipsis is not a usable digest.
5. Dependabot checks for new versions on its daily weekday schedule and opens a PR updating the shared image's version tag and digest. Review the release notes, published-image smoke results and PR checks, then merge it. No image reference needs copying into Compose. The `deployment-compose` artefact remains available for a standalone installation. This deployment commit does not need another image-release tag.
6. Give the technical helper the repository URL, deployment branch, exact deployment commit and release notes. Include required settings or migration actions. They follow the [manual deployment procedure](docs/OPERATIONS.md#deploying-a-reviewed-upgrade).

### Automatic image updates

[Dependabot](https://docs.github.com/en/code-security/concepts/supply-chain-security/dependabot-version-updates) is GitHub's maintained dependency-update service. The [.github/dependabot.yml](.github/dependabot.yml) configuration enables its Docker Compose support when present on the default branch. It checks only this project's application image; PostgreSQL and Redis upgrades remain separate maintenance work. It needs no custom updater, personal access token or extra GitHub Actions write permissions.

Publish versioned tags such as `v0.1.0-rc.2` or `v0.1.0` for updates to be discoverable. Commit-SHA tags from manual publication are available for testing and do not define a release sequence. Keep both the readable version tag and immutable digest in Compose: Dependabot uses the tag to identify newer versions and updates the digest with it. The shared mapping keeps all three application roles on the same image.

Dependabot preserves Docker tag families. While this pilot uses `-rc`, it follows later `-rc` tags. Moving to the first stable release is one reviewed change to the version and digest in the shared mapping; subsequent stable releases are proposed automatically. See [Dependabot’s tag policy](https://github.com/dependabot/dependabot-core/tree/main/docker#supported-tag-schemas).

Checks run daily on weekdays; publication does not create a PR immediately. This project's own image is excluded from Dependabot's cooldown because publication already requires both architecture tests. To check sooner or inspect a failure, open **Insights → Dependency graph → Dependabot**, select the Docker Compose update job and use **Check for updates**. Dependabot PRs run the normal pull-request CI. Review and merging remain required; Coolify deployment remains manual.

Keep the [verification record](VERIFICATION.md) current, with revision/image, architecture, commands, results and remaining limits.

## Technical references

- [Configuration](docs/CONFIGURATION.md): required values, defaults and generated credentials.
- [Operations](docs/OPERATIONS.md): deployment, backups, recovery and maintenance checks.
- [Organisation setup and upstream plan](docs/ORGANISATION-SETUP.md): behaviour, audience, tests and local override removal.
- [Upstream decisions](UPSTREAM.md): why this project maintains an image and when to revisit it.
- [Dependency audit](DEPENDENCY-AUDIT.md): dated findings and follow-up work.
- [Decidim 0.32.1 release](https://github.com/decidim/decidim/releases/tag/v0.32.1) and [versioned installation guidance](https://github.com/decidim/decidim/blob/v0.32.1/docs/modules/install/pages/index.adoc).
