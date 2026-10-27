# Decidim for Coolify

Run a Decidim participation site for your collective on Coolify. Start with a domain and an administrator email; connect your email provider afterwards.

Coolify pulls a prebuilt application image. Collectives do not need to compile Decidim or publish an image themselves.

**Pilot releases are available** for Linux amd64 and ARM64. `compose.yaml` pins a public image by version and digest; no registry credentials are needed. See the [release notes](https://github.com/jokroese/decidim-coolify/releases).

**Pilot setup:** public routing, real email delivery and recovery still need verification on Coolify. [Verification status](VERIFICATION.md).

## Set up

1. Add an **Application from a Git repository**. Select **Docker Compose**, base directory `/` and Compose file `compose.yaml`. Leave **Raw Compose**, **Auto Deploy** and production previews off. Save and load the configuration.
2. Under **Access → Public access**, add a domain for **web**:

   | Field | Value |
   | --- | --- |
   | Protocol | `https` |
   | Domain | Your hostname, such as `participate.example.org` |
   | Port | `3000` |
   | Path | Empty |

   Point the hostname's DNS to your Coolify server and save. If your version uses a single domain field, enter `https://participate.example.org:3000`. Visitors use `https://participate.example.org`.
3. In **Environment Variables**, fill the required **`SYSTEM_ADMIN_EMAIL`** with your email address. Keep Coolify's generated credentials unchanged. Save them securely for recovery.
4. **Deploy**. Coolify pulls the pinned image and starts all five components. Wait until they are healthy.
5. Open `https://participate.example.org/system`. Sign in with `SYSTEM_ADMIN_EMAIL` and the generated **`SERVICE_PASSWORD_64_ADMIN`** value in Coolify. Change your password.
6. Create your organisation with hostname `participate.example.org`, without `https://`. Set its name, languages and sender address. Complete email setup below before sending administrator invitations or inviting participants.

The administrator screens show **Email setup is pending** until SMTP is configured. You can sign in and create an organisation, but invitations, password resets and notifications cannot be delivered. Delivery attempts fail explicitly and background jobs can retry; they are not silently discarded.

The web domain is the single public-URL setting. The application reads Coolify’s generated `SERVICE_URL_WEB` directly; you do not enter `APP_URL` separately. Port 3000 remains the internal proxy target. A missing generated URL or empty administrator email stops Compose before containers start, with instructions identifying the setting to complete. Coolify can supply a generated hostname initially; confirm that the web domain is the address you intend to use.

## Connect email

In Coolify's **Environment Variables**, set:

| Setting | What to enter |
| --- | --- |
| `SMTP_ADDRESS` | Your provider's outgoing mail server |
| `SMTP_USERNAME` | Your provider's SMTP username |
| `SMTP_PASSWORD` | Your provider's SMTP password |

The default sender is `no-reply@YOUR-SITE-HOSTNAME`. Your provider must authorise that address, or you must set **`DECIDIM_MAILER_SENDER`** to an address it permits. Also use an authorised sender in the Decidim organisation settings. **`SMTP_DOMAIN`** defaults to the site hostname; override it if your provider requires a different greeting domain.

Email uses STARTTLS on port 587. For a provider requiring implicit TLS on port 465, set **`SMTP_TLS=true`** and **`SMTP_PORT=465`**.

Save and redeploy. The setup notice disappears once all three SMTP settings are present; this does not confirm that the provider accepts them. Send an organisation administrator invitation and verify that it arrives before inviting participants. If you need to return to setup without email, clear all three SMTP settings together.

## Updating an existing first attempt

Load the updated Git Compose configuration from `main` in Coolify so it picks up the published image and optional mail settings. Preserve your saved web domain, generated credentials and volumes. Previously entered SMTP values are retained: either complete them or clear all three SMTP settings for initial setup.

Earlier versions exposed an editable `APP_URL`. The current Compose mapping ignores that old saved value and uses the web domain directly. Set the required `SYSTEM_ADMIN_EMAIL`; keep generated credentials unchanged.

Missing required values are reported during deployment configuration, before container startup. Invalid values or incomplete optional SMTP settings are explained in the **web runtime log**. If a saved web domain is not reflected in `SERVICE_URL_WEB`, record the Coolify version and report the generated-configuration mismatch; do not introduce a second URL setting.

## Before participants join

Check real email delivery, background jobs and an uploaded organisation logo. Arrange encrypted backups outside the server and test [backup and recovery](docs/OPERATIONS.md) with a technical helper.

[Look after your site and get help](OPERATIONS.md).

[Help develop this project](CONTRIBUTING.md).

[Coolify's Compose guide](https://coolify.io/docs/applications/builds/docker-compose) explains routing and generated variables; labels can vary by version.
