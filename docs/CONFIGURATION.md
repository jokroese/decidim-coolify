# Configuration reference

For developers and technical helpers. Collectives can use the required settings in [Set up](../README.md#set-up).

[compose.yaml](../compose.yaml) defines runtime mappings and defaults. Set installation values in Coolify. [.env.example](../.env.example) is an interpolation example for local Compose; its placeholders are not credentials. Copying it does not generate secrets or start a working installation.

## Required installation values

| Setting | Meaning |
| --- | --- |
| `SYSTEM_ADMIN_EMAIL` | Email for the initial system administrator, created only if no system administrator exists. Changing it does not update an existing account. |
| `DECIDIM_MAILER_SENDER` | Default sender address; use an address authorised by the mail provider. Also configure the organisation's sender in Decidim. |
| `SMTP_ADDRESS` | Outgoing SMTP server hostname. |
| `SMTP_DOMAIN` | Domain used in the SMTP greeting; obtain the required value from the provider. |
| `SMTP_USERNAME` | SMTP authentication username. |
| `SMTP_PASSWORD` | SMTP authentication password. |

## Domain

Set the web component's HTTPS domain in Coolify with internal port 3000. The `SERVICE_URL_WEB_3000: /` declaration in Compose lets Coolify generate the URL used by `APP_URL`. Keep that declaration unchanged. Confirm that the resulting public URL has the correct HTTPS hostname and no application path; port 3000 is the proxy's internal target, not the visitor's port.

The application accepts one canonical hostname. Use the same hostname, without the scheme, when creating the Decidim organisation. See [Coolify's Compose routing documentation](https://coolify.io/docs/applications/builds/docker-compose).

## Generated credentials

Let Coolify generate these values and preserve their identifiers and values across deployments. Verify generation on the actual Coolify version before first deployment. Local Docker Compose does not generate them.

| Coolify setting | Runtime use |
| --- | --- |
| `SERVICE_USER_DATABASE` | PostgreSQL username and application database connection |
| `SERVICE_PASSWORD_64_DATABASE` | PostgreSQL password and application database connection |
| `SERVICE_PASSWORD_64_REDIS` | Redis authentication and application queue connection |
| `SERVICE_PASSWORD_64_RAILS` | `SECRET_KEY_BASE` |
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

The shared `x-app-image` anchor pins all three application roles to one published digest. Change it through a reviewed deployment commit, not a Coolify environment variable.

PostgreSQL 17, Redis 8, local uploaded-file storage, non-root UID 1000, health checks and service dependencies are defined by the image and Compose file. Database and Redis have no published host ports. Run exactly one scheduler. Its tasks use UTC and run daily, weekly or every 15 minutes; see [crontab](../docker/crontab).
