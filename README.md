# Decidim for Coolify

Run a Decidim participation site for your collective on Coolify.

**Not ready for self-service setup yet.** There is no deployable release pinned in this repository. Setup and recovery still need testing on Coolify. [Developers: help finish this work](CONTRIBUTING.md#help-make-setup-ready).

## Before you begin

For a pilot installation, arrange:

- A technical helper and a published release they have checked.
- Access to Coolify with a server connected.
- A domain pointing to that server, such as `participate.example.org`.
- An email provider's SMTP settings and an approved sender address.
- A backup destination outside the server. Your helper must test [backup and recovery](docs/OPERATIONS.md) before participants join.

## Set up

These steps are for a pilot with your technical helper, once a release is available.

1. In Coolify, add an **Application from a Git repository**, using the repository and deployment branch supplied by your helper. Select **Docker Compose**, base directory `/` and Compose file `compose.yaml`. Leave **Raw Compose**, **Auto Deploy** and production previews off. Save and load the configuration.
2. Set the **web** domain to `https://participate.example.org:3000`, replacing the hostname with yours. Visitors will use `https://participate.example.org`.
3. In **Environment Variables**, enter:

   | Setting | What to enter |
   | --- | --- |
   | `SYSTEM_ADMIN_EMAIL` | Your initial site administrator's email address |
   | `DECIDIM_MAILER_SENDER` | The sender address approved by your email provider |
   | `SMTP_ADDRESS` | Your provider's outgoing mail server |
   | `SMTP_DOMAIN` | The domain your provider requires for the SMTP greeting |
   | `SMTP_USERNAME` | Your email provider's SMTP username |
   | `SMTP_PASSWORD` | Your email provider's SMTP password |

   Email uses STARTTLS on port 587. If your provider requires TLS on port 465, also set `SMTP_TLS=true` and `SMTP_PORT=465`.
4. Keep Coolify's generated credentials. Have your helper confirm the deployment revision and save the credentials for recovery, then **Deploy**. Wait for all five components to show healthy.
5. Open `https://participate.example.org/system`. Sign in with `SYSTEM_ADMIN_EMAIL` and the `SERVICE_PASSWORD_64_ADMIN` value from Coolify. Change your password.
6. Create your organisation with hostname `participate.example.org`, without `https://`. Set its name, languages and sender address. Invite an organisation administrator and follow the invitation email to sign in.
7. Upload an organisation logo, save it and check that it appears on the public site. Ask your helper to confirm background jobs and backups work before inviting participants.

Coolify labels can vary by version; its [Compose guide](https://coolify.io/docs/applications/builds/docker-compose) illustrates the controls.

## After setup

[Look after your site and get help](OPERATIONS.md).

[Help develop this project](CONTRIBUTING.md).
