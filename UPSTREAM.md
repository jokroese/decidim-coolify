# Application image decision

Use the repository-built application image for this Coolify deployment. It packages the committed Rails application, aligned Ruby and frontend dependencies, runtime configuration, jobs, persistence and deployment checks. See [Contributing](CONTRIBUTING.md) for development, verification and releases.

Prefer supported upstream behaviour and keep local changes small. The [historical Docker investigation](https://github.com/jokroese/decidim-lab/blob/main/research/upstream-docker/UPSTREAM.md) and [organisation setup contribution plan](https://github.com/jokroese/decidim-lab/blob/main/research/organisation-setup.md) live in decidim-lab. Open proposals and experimental patches are not dependencies of the maintained deployment.

## When to reconsider

Reconsider the custom image when an official image provides the required Decidim release and architectures, equivalent runtime settings, persistence, jobs and upgrade behaviour, and passes this project's deployment checks.

Before switching, test migration and restoration against an isolated copy of the organisation's database and uploads. Preserve secrets and volume identities. Retire the custom image only after the transition succeeds. Keep the [organisation setup contract](docs/ORGANISATION-SETUP.md) and its local override responsibilities with the application until accepted upstream changes replace them.
