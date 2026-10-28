# Configuration reference

For developers and technical helpers. Collectives can use the required settings in [Set up](../README.md#set-up).

[compose.yaml](../compose.yaml) defines runtime mappings and defaults. Set installation values in Coolify. [.env.example](../.env.example) is an interpolation example for local Compose; its placeholders are not credentials. Copying it does not generate secrets or start a working installation.

## First-run settings

Set the required `SYSTEM_ADMIN_EMAIL` to the initial system administrator's email address, and configure the web domain as described below. Compose rejects an empty administrator email or generated public URL before starting containers. The administrator is created only if no system administrator exists. Changing the bootstrap settings does not change an existing account.

Email is optional for initial setup. Leave `SMTP_ADDRESS`, `SMTP_USERNAME` and `SMTP_PASSWORD` empty together. When any is supplied, all three are required. The startup check reports incomplete settings together before loading Rails. With no SMTP settings, the system administrator screens show a notice and email delivery raises an explicit error; the initial organisation administrator invitation is saved without a delivery job and can be sent with **Resend invitation** after configuration. Other queued delivery jobs can retry after configuration is completed. It does not use a log-only or silently successful mail backend.

## Email settings

| Setting | Meaning |
| --- | --- |
| `SMTP_ADDRESS` | Outgoing SMTP server hostname; set with username and password to enable email. |
| `SMTP_USERNAME` | SMTP authentication username. |
| `SMTP_PASSWORD` | SMTP authentication password. |
| `DECIDIM_MAILER_SENDER` | Defaults to `no-reply@` followed by the public URL hostname. Override with an address authorised by the provider. Organisation email settings inherit this value when blank; override the organisation sender only when a different authorised address is needed. |
| `SMTP_DOMAIN` | Defaults to the public URL hostname. Override if the provider requires another SMTP greeting domain. |

Completing these settings enables SMTP; it does not prove deliverability. Test a real invitation before onboarding participants.

## Domain

Under Access → Public access, select web, protocol https, the hostname, port 3000 and an empty path. The `SERVICE_URL_WEB_3000: /` declaration associates the web component with its internal proxy port. The application’s `APP_URL` reads the base `SERVICE_URL_WEB` variable directly: Coolify derives this public URL from the saved web domain without appending the internal port. There is no separate editable `APP_URL` input and no nested default to retain an old address.

Keep the generated URL declaration unchanged. Changing the web domain and redeploying should update all three application roles. Existing saved `APP_URL` entries are no longer used by the Compose mapping. For local Compose only, supply `SERVICE_URL_WEB` in the disposable environment as shown in `.env.example`; Docker does not generate Coolify variables.

If a saved domain is missing or incorrect in the effective `SERVICE_URL_WEB`, inspect the source and deployable Compose views and record the installed Coolify version. This is a domain-generation problem to investigate, not a reason to ask every installer to maintain duplicate URLs.

The application accepts one canonical hostname. Use the same hostname, without the scheme, when creating the Decidim organisation. See [Coolify's Compose routing documentation](https://coolify.io/docs/applications/builds/docker-compose).

## Generated credentials

Let Coolify generate these values and preserve their identifiers and values across deployments. Verify generation on the actual Coolify version before first deployment. Local Docker Compose does not generate them.

| Coolify setting | Runtime use |
| --- | --- |
| `SERVICE_USER_DATABASE` | PostgreSQL username and application database connection |
| `SERVICE_PASSWORD_64_DATABASE` | PostgreSQL password and application database connection |
| `SERVICE_PASSWORD_64_REDIS` | Redis authentication and application queue connection |
| `SERVICE_HEX_128_RAILS` | `SECRET_KEY_BASE` |
| `SERVICE_PASSWORD_64_ENCRYPTIONPRIMARY` | `ACTIVE_RECORD_ENCRYPTION_PRIMARY_KEY` |
| `SERVICE_PASSWORD_64_ENCRYPTIONDETERMINISTIC` | `ACTIVE_RECORD_ENCRYPTION_DETERMINISTIC_KEY` |
| `SERVICE_PASSWORD_64_ENCRYPTIONSALT` | `ACTIVE_RECORD_ENCRYPTION_KEY_DERIVATION_SALT` |
| `SERVICE_PASSWORD_64_ADMIN` | `INITIAL_SYSTEM_ADMIN_PASSWORD`, used only to create the first system administrator |

The bootstrap email and password are passed only to web. Change the initial administrator password after sign-in. Editing the bootstrap variable later does not reset that account.

Include current credentials and all four Rails secrets in encrypted backups. Losing encryption keys can make stored data unreadable; replacing `SECRET_KEY_BASE` invalidates sessions and other signed or encrypted Rails data. Renaming a generated variable can produce a different credential. See [Coolify's generated values](https://coolify.io/docs/services/configuration/docker-compose) and the [backup procedure](OPERATIONS.md#backups).

## Optional settings

| Setting | Default | Use |
| --- | --- | --- |
| `SMTP_PORT` | `587` | Outgoing mail port. Use `465` with `SMTP_TLS=true` if required by the provider. |
| `SMTP_TLS` | `false` | `false` requires STARTTLS; `true` uses implicit TLS. Certificate verification stays enabled. |
| `SMTP_AUTHENTICATION` | `plain` | SMTP authentication mechanism; change only to match the provider. |
| `DECIDIM_APPLICATION_NAME` | `Community participation` | Application name. |
| `RAILS_LOG_LEVEL` | `info` | Application log level. |
| `ENABLE_INACTIVE_ACCOUNT_CLEANUP` | `false` | Scheduler-only setting. Enable with `true` only after the collective agrees its inactive-account retention policy. |

## Settings owned by the repository

The shared `x-app-image` anchor pins all three application roles to one published digest. Dependabot proposes version and digest updates after maintainers publish a release; every collective can then pull it without compiling Decidim. Change the digest through a reviewed deployment commit, not a Coolify environment variable.

PostgreSQL 17, Redis 8, local uploaded-file storage, non-root UID 1000, health checks and service dependencies are defined by the image and Compose file. Database and Redis have no published host ports. Run exactly one scheduler. Its tasks use UTC and run daily, weekly or every 15 minutes; see [crontab](../docker/crontab).

## Upgrading the Rails secret from the first pilot

New installations use Coolify's `SERVICE_HEX_128_RAILS` generator: 128 hexadecimal characters, matching Decidim's existing form validation. No Decidim validation override is installed. The startup check reports an incompatible supplied length without revealing the value.

**Before reloading this Compose revision on an existing installation**, export and back up the current secrets and database. The earlier `SERVICE_PASSWORD_64_RAILS` variable generated 64 characters. Renaming the generator causes Coolify to create a different value; that is not an automatic migration.

- If the existing `SECRET_KEY_BASE` already has 128 characters, copy that same value securely into `SERVICE_HEX_128_RAILS` before deployment. Keep all application roles on the same value.
- If setup has not created an organisation or stored encrypted application settings, the new generated value can be used after the backup. Existing system-dashboard sessions will expire; sign in again with the existing administrator credentials. This does not reset that account or its password.
- If an organisation or encrypted settings already exist, stop before deploying the new secret. A technical maintainer must inventory data encrypted with the old key, rehearse decryption/re-encryption and any signing-key transition against a restored copy, and verify the result before changing production. This repository does not yet provide a general secret-rotation migration. Retain the old key securely until the migration and rollback window are complete.

Do not change database/Redis credentials or the separate Active Record encryption keys for this correction. See [Coolify's documented generators](https://coolify.io/docs/applications/builds/docker-compose#generated-stack-values).
