# Organisation setup behaviour and maintenance

This document defines the maintained system sign-in and organisation creation behaviour, the local implementation and the checks needed when upgrading Decidim. The [setup guide](../README.md#set-up) is for people installing the platform.

The [research and upstream contribution plan](https://github.com/jokroese/decidim-lab/blob/main/research/organisation-setup.md) lives in decidim-lab. Keep evidence, comparative designs and contribution tracking there; keep the behaviour contract, regression tests and removal of local overrides with this application. Source changes require a new image release before installations receive them.

## Behaviour and acceptance criteria

### First page: system administrator sign-in

- Before any organisation exists, the sign-in page explains that deployment created the system administrator account and that organisation creation comes next.
- Credential help names `SYSTEM_ADMIN_EMAIL` and `SERVICE_PASSWORD_64_ADMIN`, but never renders their values. It explains that a changed account password supersedes the initial generated password.
- The admin-scoped English unauthenticated message asks the person to sign in. It does not suggest a self-registration route that this page does not offer. Authentication failure messages remain visible.
- The sign-in page suppresses the shared email and organisation-creation warning banners. Email guidance appears on the organisation page, where it affects invitations.
- The help link points directly to the README's credential procedure. Email and password inputs use `username` and `current-password` autocomplete respectively.
- Once an organisation exists, the heading becomes “System administration”, bootstrap guidance disappears. Existing organisations, accounts, authentication and password-reset behaviour remain unchanged.
- An installation without an organisation can still have a returning system administrator. The first-run password hint explicitly covers a password already changed in that state.

### Names and validation

- The administrator's name starts blank. The existing administrator email and detected website domain remain prefilled.
- While a derived field has never been edited, changing the organisation name updates that field's suggestion. Editing the short name does not stop prefix suggestions, or vice versa.
- A manually edited field stays unchanged, including if the person clears it. Values returned after a failed submission are treated as deliberate choices and are never replaced automatically.
- Short names retain names of at most 12 Unicode code points. Longer names use initials when there are 3–12 initials, then whole words that fit, then a 12-character truncation as a last resort. The existing minimum of 3 characters still applies. The interface does not invent padding for a 1- or 2-character name.
- Prefix suggestions use the uppercase initial of every word, including two-word names. A single-word name supplies its first character. Accents are normalised and punctuation separates words; letters and digits from any script are supported. The short-name field’s 12-character limit does not apply to prefixes. Suggestions remain editable.
- Suggestions do not guarantee uniqueness. The existing server checks remain authoritative and return conflicts for correction.
- The form works without JavaScript: names are entered manually, all languages remain visible, and advanced settings use native HTML disclosure.
- Required-field client messages identify the field and relevant constraint. Existing server validation messages remain intact. Submitted HTML is escaped on a failed submission.

### Languages and access

- Language search filters the displayed rows without changing selected languages. Every available/default control has an accessible name.
- Choosing a default enables that language. A selected default cannot be deselected from available languages while it remains the default.
- The server also enables the selected supported default on creation, including a submission without JavaScript.
- No registration, authentication or verification policy changes automatically.
- Additional domains are in advanced settings. Existing SMTP, sign-in, upload and content security policy controls remain available. Advanced settings open after a failed server submission so errors can be found.

### Email and invitations

- When production installation email is unconfigured, creation saves the organisation and a pending administrator invitation without enqueueing an email. The invitation has no sent timestamp.
- The submit button, help, notice and success message explain that the invitation has not been sent. They identify the next action: configure email in Coolify, redeploy, then use **Resend invitation** in the organisations list.
- The pending account cannot be used as an accepted administrator account. The system administrator account remains available to complete setup.
- Resending while email is pending shows an explanation and sends nothing. After email is configured, resending the persisted invitation uses Decidim's normal invitation path.
- With installation email configured, creation and resending use the normal upstream delivery path. Configuration does not prove delivery; verify receipt of a real invitation before onboarding participants.
- Deferral applies only to the organisation administrator invitation type. Other mail still fails explicitly when installation email is unconfigured. No invitations are automatically sent merely because the deployment configuration changes.
- Organisation SMTP fields can remain blank to inherit the installation settings. An organisation sender override is optional and must be permitted by the provider. These fields do not activate the deployment's disabled mail transport.
- Authentication, authorisation and CSRF protection remain in upstream controllers. No token or password is exposed to bypass email confirmation.

## Where the implementation lives

| File | Responsibility and upstream counterpart |
| --- | --- |
| `app/app/views/decidim/system/devise/sessions/new.html.erb` | Local sign-in view override; preserves the upstream form action, CSRF and Devise links |
| `app/app/views/decidim/system/organizations/new.html.erb` | Local override of the 0.32.1 creation view; preserves upstream advanced partials |
| `app/app/packs/src/organisation_setup/form.js` | Suggestions, edit tracking, language search and client error hints |
| `app/app/packs/entrypoints/organisation_setup.js` | Loads enhancement only on the creation page |
| `app/config/locales/organisation_setup.en.yml` | User-visible English copy |
| `app/app/helpers/organisation_setup_helper.rb` | Scoped copy with explicit English fallback for untranslated locales |
| `app/lib/organisation_setup.rb` | Controller defaults/default language handling and deployment-specific invitation adapter |
| `app/config/initializers/organisation_setup.rb` | Rails reload-safe registration of those adapters |
| `tests/organisation_setup_test.mjs` | Name suggestion examples and character limits |
| `tests/system_sign_in_check.rb` | Real HTTP failed/successful sign-in, retained email and cleared password |
| `tests/organisation_setup_check.rb` | Real Rails requests, escaping, server validation, policy preservation, invitation lifecycle and access protection in the disposable smoke stack |

New copy is British English. Other locales currently fall back to English for these keys; the rest of Decidim continues to use its translations. That limitation must be addressed through upstream's translation workflow before describing the change as fully localised. No schema migration is required. The existing organisation edit page is not replaced.

## Deployment prerequisite discovered during testing

A real creation request exposed a mismatch that earlier smoke tests missed: the pilot Compose file generated a 64-character Rails secret, while Decidim 0.32.1 requires exactly 128 characters in its organisation form. This is a packaging defect, not a usability requirement or a reason to override Decidim validation.

The deployment now uses `SERVICE_HEX_128_RAILS`, and test fixtures match that length. A startup diagnostic catches incompatible supplied values. Existing installations follow the [secret upgrade check](CONFIGURATION.md#upgrading-the-rails-secret-from-the-first-pilot) before changing configuration. Changing the source does not rotate an existing installation’s secret. This packaging requirement remains separate from the usability proposals.

## Upgrade and release checklist

1. Compare the pinned upstream sign-in and creation views, Devise message scopes, organisation controller, `Decidim::User#invite!` and Devise invitation behaviour against the target version. Check that pending invitations still appear in the organisation list and that resend still uses the intended administrator.
2. Run `node --test tests/organisation_setup_test.mjs`, the repository validation/Python tests, image build, migration/configuration tests and full smoke test. See [Contributing](../CONTRIBUTING.md#build-and-check-a-change) for commands.
3. Check first-time and returning sign-in in a browser, including failed authentication and password-manager attributes. Check the creation form: suggestions, independent manual edits, failed submission, keyboard language search/default selection, native advanced disclosure, and both email states. Repeat with JavaScript disabled and at a narrow viewport.
4. Verify a real invitation and acceptance on an isolated Coolify installation. Confirm the organisation administrator can sign in after acceptance and that the system administrator account remains separate.
5. Publish and test a new versioned image, then update the pinned deployment reference through the normal release process. Publishing and deployment are separate steps.
