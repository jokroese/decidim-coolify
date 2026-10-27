# Looking after your site

For collectives running Decidim. Arrange a technical helper who can maintain the server and recover the site. Share the [technical procedures](docs/OPERATIONS.md) with them.

## Protect your work

Ask your helper to set up daily encrypted backups outside the server, report failures and test recovery before you invite participants. Backups must include the site's data, uploaded files, queued work and recovery secrets.

Keep access to your domain, Coolify, email provider and recovery credentials in your collective's password manager. Decide who can use them if your usual helper is unavailable.

The project does not automate backups or alerts yet. Agree how you will check that yesterday's backup succeeded. If it failed, contact your helper.

## Update your site

Arrange updates with your helper at a time when nobody needs to use the site. They should test the release and recovery first, then take a fresh backup before updating.

Afterwards, sign in, open an existing uploaded file and send an administrator invitation. Confirm that the invitation arrives and its link works. Report any failure before resuming participation.

## When something goes wrong

| Problem | First check |
| --- | --- |
| The site will not open | Open the address saved in Coolify. Ask your helper to check the domain, certificate and component health. |
| An invitation does not arrive | Check spam and the recipient address. Ask your helper to check email settings and the worker. |
| A file is missing | Ask your helper to check storage and backups before making changes. |
| An update fails | Ask your helper to use the recovery procedure. Keep the existing data and volumes. |

Give your helper the time, what you tried and the error message. Share passwords and recovery keys only through your password manager. Your helper should remove personal data and secrets before sharing logs with project developers.
