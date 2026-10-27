# Technical operations

For developers and technical helpers responsible for a collective's installation. For the collective's responsibilities, read [Looking after your site](../OPERATIONS.md).

These procedures require Docker Compose and server administration experience. They have not yet been verified on a live Coolify installation. See [verification status](../VERIFICATION.md) before using them.

## Before the first installation

The deployment configuration pins a published image by version and digest. Coolify can pull it anonymously for Linux amd64 or ARM64. Maintainers follow the [release procedure](../CONTRIBUTING.md#publishing-a-release) for subsequent versions; collectives do not build or publish images.

On the target Coolify instance, verify the [setup instructions](../README.md#set-up), generated variables, persistent volumes and public HTTPS route. Record the Coolify version, deployment revision and supported server architecture. No minimum server capacity has been established.

Before collecting participant data, implement and test scheduled encrypted backups, failure reporting and an isolated restore. This repository supplies manual examples only. The helper must document the actual project context, off-server destination and secure method for exporting and restoring Coolify secrets; those installation-specific steps are not supplied here. Give the collective a way to check backup results and a contact for failures.

## Deployment contract

Use the resource settings in [Set up](../README.md#set-up). Git owns the Compose definition and literal `x-app-image` digest; Coolify owns installation-specific variables and secrets. Deploy reviewed Git revisions manually. Image publication does not trigger deployment. Confirm that the server architecture and published image manifest match.

The stack contains:

- **web**, **worker** and **scheduler**, all on the exact same Decidim 0.32.1 image digest.
- **PostgreSQL 17** and **Redis 8**, private to the Compose network.
- Persistent PostgreSQL and Redis volumes.
- A named local uploads volume mounted at **/app/storage** in all three application roles.
- Application processes running as the image's non-root **UID 1000**.

Do not add a host port for database or Redis. Coolify's proxy should route only the web role. Do not override the image user to root to resolve a permissions problem; correct the volume ownership or image instead. Configure exactly one scheduler instance.

Keep these application secrets stable across redeployments and restores:

- **SECRET_KEY_BASE**
- **ACTIVE_RECORD_ENCRYPTION_PRIMARY_KEY**
- **ACTIVE_RECORD_ENCRYPTION_DETERMINISTIC_KEY**
- **ACTIVE_RECORD_ENCRYPTION_KEY_DERIVATION_SALT**

Preserve the database and Redis credentials, SMTP credentials, administrator bootstrap values, the canonical hostname and Coolify's generated variable names too. Losing or replacing encryption keys can make encrypted application data unreadable. Losing **SECRET_KEY_BASE** invalidates sessions and other signed/encrypted Rails data.

## Backups

Back up **daily** to storage outside the Coolify host. Each dated backup set must contain:

1. A PostgreSQL custom-format dump.
2. The complete uploads volume.
3. A Redis data archive containing the AOF/RDB persistence files and queued jobs.
4. An encrypted export of the Coolify environment secrets, including the four stable Rails secrets above.
5. The effective Compose file encrypted with age, because Coolify's rendered configuration may contain secrets.
6. Plain, non-secret metadata with the deployed Git revision and each running container's configured image reference and immutable image ID.

The backup procedure below stops application writers; schedule it outside workshop hours. Verify backup capabilities for this Git-backed Compose Application on the installed Coolify version; do not assume standalone Database or Service backup controls apply. This package does not implement automatic backups. The operator must schedule and monitor the procedure, verify that the destination is off-server, and retain the decryption key separately from the backup destination. Generate or refresh the encrypted secrets export after every secret change; include the current export with the daily backup set. Never place plaintext secrets in shell history, logs, tickets or the off-server backup.

### Example for an operator-managed local Compose project

These commands are for an operator deliberately managing a local Compose project. Replace each value with the actual project name, Compose file path and mounted off-server destination. The PROJECT and COMPOSE_FILE values are not supplied by this package.

For a Coolify-managed Application, use the effective project and file context shown by the Coolify UI/host, and confirm the target resource before every command. Do not substitute a new unmanaged Compose deployment against production.

The operator environment needs Docker Compose v2, age and an off-server backup mount. Run from the actual project directory with the correct protected Compose environment file available. Set AGE_RECIPIENT to the public age recipient key and SECRET_EXPORT to a mode-600 temporary file containing the current Coolify secrets exported using the installation-specific method established above. Run in Bash:

~~~bash
set -euo pipefail
umask 077

PROJECT='REPLACE_WITH_ACTUAL_PROJECT'
COMPOSE_FILE='/replace/with/actual/compose.yaml'
ENV_FILE='/secure/path/to/operator.env'
BACKUP_DIR='/mounted/off-server-backups/decidim'
AGE_RECIPIENT='REPLACE_WITH_AGE_PUBLIC_RECIPIENT'
SECRET_EXPORT='/private/tmp/coolify-secrets.env'
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

dc() {
  docker compose --env-file "$ENV_FILE" --project-name "$PROJECT" --file "$COMPOSE_FILE" "$@"
}

mkdir -p "$BACKUP_DIR/$STAMP"

# Stop writers so the database dump and upload archive describe the same
# application state. PostgreSQL and Redis stay running.
resume_stack() {
  dc start redis
  dc start web worker scheduler
}
trap resume_stack EXIT

# Record immutable image IDs separately from the encrypted effective config.
{
  for service in web worker scheduler database redis; do
    container_id="$(dc ps -aq "$service")"
    test -n "$container_id"
    docker inspect --format='{{.Name}} configured={{.Config.Image}} image_id={{.Image}}' "$container_id"
  done
} > "$BACKUP_DIR/$STAMP/container-images.txt"

dc stop web worker scheduler

# Flush Redis state, then stop it before archiving its persistent volume.
# REDISCLI_AUTH is set in the Redis service environment.
dc exec -T redis sh -ec 'redis-cli SAVE'
dc stop redis

# Database dump, encrypted directly to the off-server destination.
dc exec -T database sh -ec \
  'pg_dump --format=custom --username="$POSTGRES_USER" --dbname="$POSTGRES_DB"' \
  | age --recipient "$AGE_RECIPIENT" \
      --output "$BACKUP_DIR/$STAMP/database.dump.age"

# Read the shared uploads volume through a one-off web-image container.
dc run --rm --no-deps -T --entrypoint tar web \
  -czf - -C /app storage \
  | age --recipient "$AGE_RECIPIENT" \
      --output "$BACKUP_DIR/$STAMP/uploads.tar.gz.age"

# Coolify secret export is a secure operator step, not a shell command:
# create a mode-600 file in a private temporary location without displaying
# its contents, then set SECRET_EXPORT to that path.
test -f "$SECRET_EXPORT"
age --recipient "$AGE_RECIPIENT" \
  --output "$BACKUP_DIR/$STAMP/coolify-secrets.env.age" \
  "$SECRET_EXPORT"
rm -f "$SECRET_EXPORT"

# Redis AOF/RDB and queue state. Redis is stopped while its volume is read.
dc run --rm --no-deps -T --entrypoint tar redis \
  -czf - -C /data . \
  | age --recipient "$AGE_RECIPIENT" \
      --output "$BACKUP_DIR/$STAMP/redis-data.tar.gz.age"

# Encrypt the effective Compose file; never assume it contains no secrets.
age --recipient "$AGE_RECIPIENT" \
  --output "$BACKUP_DIR/$STAMP/compose.yaml.age" \
  "$COMPOSE_FILE"

trap - EXIT
dc start redis
dc start web worker scheduler
~~~

Save the deployed Git revision alongside `container-images.txt` in the dated backup directory; read it from the actual Coolify deployment, not an unrelated local checkout.

If a command fails, the trap attempts to start Redis and the application roles. Treat that dated backup set as incomplete and do not count it as a successful backup. Investigate the first error, then rerun and verify the complete set. Check the resulting files, sizes, timestamps and off-server availability; do not print secret exports or decrypted data to logs.

## Restore to an isolated application

Restore to a **new Git-backed Coolify Application with new, distinct volumes**. Never restore over production and never delete production volumes to make a restore work.

1. Create an isolated recovery Application from the recorded deployment Git revision, with Auto Deploy and previews disabled, a unique Compose project and new database, Redis and uploads volumes. Use the exact image digest, Compose definition, secrets and canonical Decidim hostname from the backup.
2. Keep the recovery web, worker and scheduler roles stopped. Do not attach the production public domain while production is serving it.
3. Start only PostgreSQL in the recovery resource. The PostgreSQL database must be empty and freshly initialised; leave Redis stopped until its data archive has been restored.
4. Decrypt and restore the database dump into that empty database. Decrypt and extract the uploads archive into the recovery uploads volume, preserving the container's UID 1000 ownership. Restore Redis's AOF/RDB archive into its distinct recovery volume while Redis is stopped.

For a local Compose recovery project, decrypt the saved Compose file into a protected location and configure the isolated resource's saved secrets first. These commands assume that the full saved Compose file defines all roles but the web, worker and scheduler have not been started. Set the recovery project to a unique name and set the Coolify variables to the saved secret values before starting the services:

~~~bash
set -euo pipefail

PROJECT='UNIQUE_RECOVERY_PROJECT'
COMPOSE_FILE='/path/to/recovery/compose.yaml'
ENV_FILE='/secure/path/to/recovery.env'
BACKUP_DIR='/mounted/off-server-backups/decidim'
STAMP='BACKUP_TIMESTAMP'
AGE_IDENTITY='/secure/path/to/age-identity.txt'

dc() {
  docker compose --env-file "$ENV_FILE" --project-name "$PROJECT" --file "$COMPOSE_FILE" "$@"
}

# Import the encrypted secrets through Coolify first when this is a
# Coolify-managed resource. Start only stateful dependencies.
dc up -d database
# Wait until PostgreSQL reports healthy before restoring.

age --decrypt --identity "$AGE_IDENTITY" \
  "$BACKUP_DIR/$STAMP/database.dump.age" \
  | dc exec -T database sh -ec \
      'pg_restore --no-owner --exit-on-error --username="$POSTGRES_USER" --dbname="$POSTGRES_DB"'

age --decrypt --identity "$AGE_IDENTITY" \
  "$BACKUP_DIR/$STAMP/uploads.tar.gz.age" \
  | dc run --rm --no-deps -T --entrypoint tar web -xzf - -C /app

# Restore queue/persistence files only into the isolated, stopped Redis volume.
age --decrypt --identity "$AGE_IDENTITY" \
  "$BACKUP_DIR/$STAMP/redis-data.tar.gz.age" \
  | dc run --rm --no-deps -T --entrypoint tar redis -xzf - -C /data
dc up -d redis
# Wait for Redis health; it may replay queued or retryable jobs from the archive.

# Web runs migrations. Wait for healthy before starting job processes.
dc up -d web
# Confirm web health and migration logs in Coolify or docker compose logs.
dc up -d worker scheduler
~~~

For a Coolify-managed restore, use the Coolify UI/console for the isolated resource and its actual project context. Do not point these example values at production.

5. Confirm web is healthy and its migration logs are clean, then confirm worker and scheduler start on the same image.
6. Verify sign-in, existing encrypted data, uploads, mail, worker jobs and scheduled-task logs. Keep recovery isolated until the restore is accepted.
7. For a real cutover, arrange a maintenance window. Stop writes on production, take a final backup, then transfer the domain to the recovered resource in Coolify. Do not serve two active instances under the same canonical hostname.

Restoring Redis can replay pending or retryable jobs, including work that was in progress around the backup. Review job effects and allow for duplicate delivery where tasks are not idempotent. Never attach a restored queue to the live production application/database. Keep the age identity/private key needed to decrypt backups outside the production host and test that it works. A backup that cannot be decrypted and restored is not a usable backup.

## Upgrades and rollback

Developers first [prepare and test the upgrade](../CONTRIBUTING.md#preparing-a-decidim-upgrade) and [publish the release](../CONTRIBUTING.md#publishing-a-release). The technical helper then follows this deployment procedure.

### Deploying a reviewed upgrade

For every application or database change:

1. Record the current deployment Git revision, image digest and effective Compose definition. Obtain the maintainer’s reviewed deployment revision and release notes, including any installation-specific actions. Confirm that its image is published and pinned; run `python3 validate.py` in that checkout without `--allow-unpublished-image`.
2. Rehearse the target image and any database changes against a fresh isolated restore.
3. Schedule maintenance. Stop the old **web, worker and scheduler** so no old process can write while the database is changing.
4. Take and verify fresh database, uploads and Redis backups, and confirm the encrypted Compose and secrets exports are current.
5. In Coolify reload the Git Compose configuration for the reviewed deployment revision and verify its literal image digest. Do not edit the generated Compose or supply an image override through environment variables. Keep PostgreSQL 17, Redis 8, credentials, hostname and volume identities unchanged unless the tested upgrade explicitly requires a change.
6. Manually deploy that revision through Coolify after confirming old app processes are stopped. The dependency checks let web migrate first and start worker and scheduler only after web is healthy. Check migration logs, the deployed Git revision and the image digest on all three app roles. Auto Deploy must remain disabled; a Git push alone must not restart the workshop.
7. Confirm background jobs, scheduled tasks, mail and uploads before ending maintenance.

A code-only rollback is safe only when the new code has not made a database change that the old code cannot understand. After a schema or data migration, do not simply point the old image at the changed database. Restore the matching pre-upgrade database, uploads and Redis backups into an isolated recovery resource using the matching image versions, verify them, and plan a controlled cutover. Never destroy the production database or volumes as a rollback shortcut.

## Redis and background jobs

Redis is part of the application state, not a disposable cache. Configure its persistent volume with **AOF enabled** and **maxmemory-policy noeviction**. The worker queue depends on Redis; eviction or volume loss can lose queued jobs. Include the Redis AOF/RDB data in the encrypted backup set and restore it only to an isolated service using the same Redis version. Monitor Redis memory, persistence and errors. **noeviction** protects queued keys from silent eviction, but a full Redis instance can reject writes and prevent new jobs from being queued. Keep the Redis volume across redeployments and upgrades.

Run only one scheduler instance. Review task logs and failures after every release, and check that no recurring job is duplicated. Do not assume a healthy web process means the worker or scheduler is healthy.

## Regular manual checks

**Daily**

- Confirm the off-server backup set is complete: database, uploads, Redis data, encrypted Compose/secrets and image-ID metadata.
- Check all service health, recent errors, HTTPS and certificate validity; watch Redis memory and persistence.

**Weekly**

- Complete a real invitation email; submit a background job and confirm worker and scheduler logs show successful, non-duplicated execution.
- Upload a representative file, restart/redeploy web, and confirm that the file still opens.

**Monthly and after a major upgrade**

- Restore the latest backup to an isolated application and verify login, encrypted data, uploads, mail, worker execution and scheduled tasks.
- Record the restore result and elapsed recovery time. Do not call a backup verified until this restore succeeds.

These are manual operating checks; no automatic backup, alerting or restore rehearsal is implemented by this package.
