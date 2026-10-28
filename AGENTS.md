# AGENTS.md

## Purpose and decision rule

Help collectives run and maintain Decidim with less technical work. Optimise for their long-term autonomy, reliable participation sites and low maintenance burden. Getting a deployment past an error is insufficient if it leaves collectives with repeated manual repairs or permanent compatibility code.

- Check the pinned upstream version's requirements and correct this project's integration to meet them. Prefer supported Decidim and Coolify behaviour over custom overrides or duplicated settings.
- Make new installations correct by default. When existing installations need a migration, document and verify the procedure. Do not weaken upstream validation or security requirements to preserve a mistaken default.
- Assess recurring work for collectives and maintainers, not just implementation effort. If a temporary workaround is unavoidable, document its reason, maintenance cost and removal condition.
- Keep changes focused on the requested outcome. Improving the maintained default does not justify unrelated rewrites or silently changing a running installation.

For example, if Decidim requires a 128-character Rails secret but our configuration generates 64 characters, fix secret generation rather than overriding validation. Separately assess existing installations for affected sessions and encrypted data, and verify the transition before replacing their secrets. Migration risk calls for a migration plan, not a permanent invalid default.

Use implementation and tests to establish current behaviour. Resolve intended behaviour from the task, supported upstream requirements and documented project decisions; do not assume existing code is correct when these disagree.

## Find the relevant context

Read the documents relevant to the change:

| Change | Start here |
| --- | --- |
| Setup or collective-facing instructions | [README.md](README.md), [OPERATIONS.md](OPERATIONS.md) |
| Code, builds, dependencies or releases | [CONTRIBUTING.md](CONTRIBUTING.md), including its source map |
| Runtime configuration | [compose.yaml](compose.yaml), [docs/CONFIGURATION.md](docs/CONFIGURATION.md) |
| Deployment, migration or recovery | [docs/OPERATIONS.md](docs/OPERATIONS.md), [VERIFICATION.md](VERIFICATION.md) |

## Repository constraints and pitfalls

- `app/` is the committed Rails host application; Decidim comes from locked upstream gems and frontend packages. Normal builds do not regenerate the application.
- Git owns the shared, version-and-digest-pinned image for web, worker and scheduler. Coolify owns installation settings and secrets. Collectives must not need to build or publish their own image.
- Keep the Coolify web domain as the single public-URL source. Fix domain propagation instead of introducing another setting to keep in sync.
- Preserve installed migration filenames. Follow [Preparing a Decidim upgrade](CONTRIBUTING.md#preparing-a-decidim-upgrade) for dependency and migration changes; do not delete and regenerate migrations.
- `app/bin/dev` runs upgrade and migration tasks and is not a supported local setup shortcut. Use the documented container test loop.
- Keep failed deliveries, migrations and background jobs visible; do not convert failures into apparent success.
- Rendered production Compose configuration can contain secrets. Keep it, credentials, uploads, generated assets and installed dependencies out of commits and reports.

## Verification

Run commands from the task worktree root. For configuration and code changes, the quick checks are:

```sh
python3 validate.py --allow-unpublished-image
python3 -m unittest discover -s tests -p 'test_*.py'
```

These require Python 3 and Docker Compose v2. Validation uses disposable settings, does not read the project's `.env` and does not start containers. Deployment validation must pass without `--allow-unpublished-image`.

Select further checks using [Choose checks for the change](CONTRIBUTING.md#choose-checks-for-the-change); use [Build and check a change](CONTRIBUTING.md#build-and-check-a-change) for exact build, Ruby test and smoke-test commands. Builds and smoke tests require a running Docker daemon. Test runtime changes against an image rebuilt from the changed source, including the failure that prompted the change.

For documentation-only changes, check links, anchors and commands against the source; no image build is needed. The smoke test creates and removes its own disposable project and volumes. Do not direct it at a running installation or remove another project's resources.

Smoke tests do not establish working Coolify routing, real email delivery or recovery. Record new deployment or release evidence in [VERIFICATION.md](VERIFICATION.md), including revision/image, architecture, results and unverified steps. Historical results do not verify new changes.

## Documentation and handover

- Keep collective-facing instructions focused on actions and outcomes; put implementation details in contributor or technical documentation. Update affected references and examples when configuration changes.
- For stateful changes, document migration and recovery requirements using [Upgrades and rollback](docs/OPERATIONS.md#upgrades-and-rollback). An image rollback alone may not undo schema or data changes.
- Follow the existing lower-case, scoped Conventional Commit style, for example `docs(agents): add repository guidance`.
- Report the resulting behaviour, benefit to collectives, checks run and remaining limitations or upgrade actions. Distinguish source changes, image publication and deployment.

Keep this file focused on durable project decisions and non-obvious pitfalls. Update it when those change; keep detailed procedures in the linked documents.
