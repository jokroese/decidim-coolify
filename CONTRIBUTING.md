# Contributing

Help collectives set up and maintain Decidim with less technical work. Keep the [setup guide](README.md) focused on their actions; put implementation details here or in the linked technical references.

## Help make setup ready

Public images are available, but public routing, real email delivery and backup/recovery still need verification on a target Coolify installation. Passing local or CI tests does not establish deployment readiness. Before describing setup as self-service:

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
| Editable development environment | [bin/dev](bin/dev), [compose.development.yaml](compose.development.yaml) |
| Check entry points and image selection | [bin/check](bin/check), [tools/image_checks.py](tools/image_checks.py) |
| Deployment validation and runtime checks | [validate.py](validate.py), [tests/](tests/) |
| CI and image publication | [images.yml](.github/workflows/images.yml) |

`app/` is the Rails application hosting Decidim. Decidim itself comes from locked upstream gems and frontend packages. Normal builds use the committed application; they do not regenerate it. Ruby and Node base images are pinned by digest. Node and compilation tools are excluded from the production runtime image; the development image includes them.

## Local development

Install Python 3, Git and Docker with Compose 2.32 or later. Start Docker before running these commands from the repository root. Ruby, Node and application dependencies run in containers; the first build needs network access and disk space. macOS with Docker Desktop and Linux Docker hosts are supported.

```sh
bin/dev up
```

This builds the development image, prepares isolated databases and starts Rails, PostgreSQL, Redis, Sidekiq and the asset watcher. It prints the local browser URL and synthetic administrator login. It does not run Decidim's application upgrade task or seed example organisations.

Open the reported URL with `/system` to sign in. Create an organisation for hostname `localhost`. Development email is captured at `/letter_opener`; no real SMTP credentials are needed. The production-only email-pending behaviour is covered by the production image smoke tests, not by development email capture.

Compose Watch synchronises source changes. Refresh the browser after editing a template or after the asset watcher recompiles JavaScript/CSS. Configuration changes restart affected processes; dependency manifest changes rebuild the development image. Installed dependencies remain inside the container. The scheduler is not part of the development stack.

Each worktree has its own Compose project, database, uploads and generated credentials. The browser listens on loopback port 3000. Set `DEV_PORT=3001 bin/dev up` to run a second worktree on a different port. Development credentials live in the ignored `.local/dev/` directory and remain stable across restarts. Do not copy production settings into that directory.

| Command | Result |
| --- | --- |
| `bin/dev up` | Prepare and start the editable environment, then watch source changes |
| `bin/dev logs` | Follow this worktree's service logs |
| `bin/dev logs web` | Follow one service's logs |
| `bin/dev down` | Stop this worktree's environment and keep its data |
| `bin/dev reset --yes` | Delete this worktree's development data and generated credentials |

Reset is destructive only to this development project. Use it deliberately; a normal restart does not require resetting data. Never use production volumes for development.

### Verify a browser change

1. Sign in at `/system`, including an unsuccessful attempt before the successful one.
2. Create an organisation, check validation messages and follow its administrator invitation from `/letter_opener`.
3. Use the keyboard to reach and operate the changed controls. Repeat organisation creation with JavaScript disabled, using another disposable organisation.
4. Edit a template and a JavaScript/CSS source file; confirm the changes appear after refresh without rebuilding the production image.
5. Restart the stack and confirm the organisation and an uploaded logo remain. Record any unverified step in the contribution.

If startup fails, read the named service's logs. An occupied browser port requires a different `DEV_PORT`; a Docker connection error requires starting Docker. Fix the failing source or configuration before retrying. `bin/dev --help` lists the supported commands. The generated application-level setup helpers are not a second supported development workflow.

## Build and check a change

Run checks from the repository root. The same entry points are used locally and in CI:

```sh
bin/check quick
bin/check full
```

`quick` checks internal documentation links and anchors, Compose configuration, Python contracts, Ruby unit behaviour and JavaScript organisation-name suggestions. Ruby and Node use the locked development tool image; quick checks do not start application services or compile production assets. The initial tool-image build can take time; subsequent runs reuse Docker build layers.

`full` runs quick checks, builds the production image and runs the image-level tests and full disposable smoke stack. Each build has a unique tag, and subsequent tests use the captured immutable image ID. Concurrent worktrees cannot silently replace each other's tested image. Output records the checkout revision, whether it has changes, the image ID and the selected platform.

Local builds default to the Docker host's architecture. To test another supported platform explicitly:

```sh
bin/check full --platform linux/amd64
bin/check full --platform linux/arm64
```

Emulation is slower. Release CI retains native amd64 and ARM64 jobs and uses `bin/check image` against each built image. To verify an existing local image or published digest, use `bin/check image --image IMAGE_REFERENCE --platform linux/amd64`, replacing `IMAGE_REFERENCE` with the actual reference. A supplied image ID must already exist for the requested platform; a published reference can be pulled.

Changes limited to root Markdown files and Markdown under `docs/` run documentation checks without building the application. All other changes, release tags and manual runs include quick checks and both container architectures. Use the always-running `CI` check for branch protection: it fails if change detection, documentation or required quick/container checks fail.

The smoke test starts web, worker, scheduler, PostgreSQL and Redis in a uniquely named disposable project. It supplies its own settings; it does not read the project's `.env`. It checks migrations, administrator bootstrap, sign-in and organisation requests, health, assets, API documentation, scheduled tasks, worker processing and upload persistence. It verifies both missing and configured SMTP behaviour without sending real email. Each checkpoint reports elapsed time.

Expect exit status 0 and passing checks. On failure, read the first failing check and service logs. Cleanup removes only the test's own project and volumes; failures to clean up are reported. Never remove another project's volumes. Direct invocation of `tests/smoke.py` requires an explicit `SMOKE_IMAGE` and accepts `SMOKE_PLATFORM`.

The production smoke loop has no browser port and does not establish working Coolify routing, real email delivery or recovery. Use an isolated Coolify pilot for the [manual setup checks](README.md#set-up). The editable development environment above serves a different purpose and does not replace release verification.

For documentation alone, run `bin/check docs`. It uses a pinned Lychee container with networking disabled to check tracked Markdown and local heading anchors. External URLs are excluded; the initial checker-image pull requires network access. Add new Markdown files to Git's index before checking them.

For optional Ruby style and security checks, run the application's `bin/ci` inside the development image. These checks remain separate from release CI.

## Choose checks for the change

| Change | Verification |
| --- | --- |
| Documentation only | `bin/check docs`; check documented commands against the source |
| Compose, configuration or release references | `bin/check quick`; full image checks if runtime behaviour changes |
| Application, dependencies, Dockerfile or process scripts | `bin/check full`; manually inspect changed browser behaviour |
| Development environment or command launchers | Quick checks plus clean startup, edits, restart and worktree-isolation checks |
| Coolify setup, email or recovery | Complete the affected procedure on an isolated installation and record the result |

Include the problem, resulting behaviour and any setup changes a collective must make in your contribution. Link the relevant [CI run](https://github.com/jokroese/decidim-coolify/actions/workflows/images.yml) for automated results. Record manual checks and remaining limits in the PR description or release notes; identify the tested revision/image and architecture for runtime or deployment checks. Keep durable procedures and known limitations in the relevant guide, rather than maintaining a test-run diary.

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

## Technical references

- [Configuration](docs/CONFIGURATION.md): required values, defaults and generated credentials.
- [Operations](docs/OPERATIONS.md): deployment, backups, recovery and maintenance checks.
- [Organisation setup and upstream plan](docs/ORGANISATION-SETUP.md): behaviour, audience, tests and local override removal.
- [Upstream decisions](UPSTREAM.md): why this project maintains an image and when to revisit it.
- [Dependency audit](DEPENDENCY-AUDIT.md): dated findings and follow-up work.
- [Decidim 0.32.1 release](https://github.com/decidim/decidim/releases/tag/v0.32.1) and [versioned installation guidance](https://github.com/decidim/decidim/blob/v0.32.1/docs/modules/install/pages/index.adoc).
