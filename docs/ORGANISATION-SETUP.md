# Setup flow: behaviour and upstream contribution plan

## Purpose and status

This document records why the system sign-in and organisation creation forms differ from Decidim 0.32.1, what the local implementation promises, and how to propose the shared improvements upstream. It is for maintainers and upstream reviewers. The [setup guide](../README.md#set-up) remains the instructions for people installing the platform.

The starting evidence is one person's walkthrough of a deployed new-organisation form on 28 October 2026, supported by the supplied HTML and inspection of the pinned Decidim source. This is concrete usability feedback, not a representative user study. Do not publish the original HTML: it contains an administrator email address, a host and an authenticity token. Use synthetic data in screenshots and reproductions.

The local implementation is a candidate contribution. No upstream proposal, issue or PR has been submitted or accepted. These changes require a new application image; editing the deployment Compose file alone does not install them.

## What belongs to whom

| Change | Classification | Why it matters to self-organised groups | Upstream destination |
| --- | --- | --- | --- |
| Explain the existing system account and organisation creation as the next step | General usability | Helps a person carrying both administrator roles understand the sequence | `decidim-system` sign-in copy and notices |
| Locate bootstrap email/password in Coolify; link to the exact procedure | Deployment-specific instructions | Avoids requiring a technical helper for the first sign-in | This repository |
| Use password-manager autocomplete and retain real sign-in errors | General usability and accessibility | Reduces typing and credential confusion | `decidim-system` sign-in view |
| Explain the reference prefix with a concrete reference number | General usability | Removes an unexplained technical decision | `decidim-system` form copy |
| Suggest editable short names and reference prefixes | General usability | Reduces work for occasional administrators | `decidim-system` creation form and JavaScript |
| Ask for the administrator's display name instead of guessing from email | General usability | Shared mailboxes often have unsuitable names such as `info` or `decidim` | `decidim-system` controller defaults and copy |
| Distinguish system administrator and organisation administrator accounts | General usability | A single person may perform both roles and expect the same account | `decidim-system` help text |
| Explain website domains; move additional domains under advanced settings | General usability; placement needs product review | Most small installations have one domain | `decidim-system` form layout and copy |
| Search languages and enable the selected default automatically | General usability and accessibility | Multilingual groups need a comprehensible language choice | `decidim-system` form, JavaScript and server validation path |
| Explain viewing, account creation and verification separately | General usability | A group can make its own membership and access decisions | `decidim-system` form copy |
| Keep verification optional and explain that it is configured per activity | General usability, particularly relevant to self-organised groups | Does not imply that every group needs identity documents or a formal census | `decidim-system` help text; preserve available workflows |
| Keep advanced settings available with inherited defaults explained | General usability; layout needs product review | Occasional administrators can finish without understanding infrastructure | `decidim-system` layout and generic help text |
| Explain field validation failures | General usability and accessibility | Reduces trial and error | Form-scoped validation copy and system specs |
| Configure installation email in Coolify and show its inherited sender | Deployment-specific | Makes a small self-hosted installation easier to operate | This repository; upstream may use generic inheritance wording |
| Defer the first administrator invitation while installation email is unconfigured | Deployment-specific implementation; potentially general capability | Allows setup to progress before acquiring/configuring an email service | Keep the current adapter here; discuss a generic explicit invitation policy separately |

None of the implemented changes requires a self-organised group to use a particular governance model. Public browsing, open registration and the available verification workflows retain upstream defaults. Restricted registration does not make the site private; enabling a verification workflow does not require verification everywhere. Do not present these defaults as a consensus about how collectives should organise.

The group-specific emphasis is the ability to start with little technical administration, defer infrastructure work, and avoid unnecessary identity checks. Municipalities, associations and other organisations can benefit from the same usability improvements. Future presets that change membership or verification policy would need separate discussion and evidence.

## Interface writing approach

Apply [GOV.UK’s interface-writing guidance](https://www.gov.uk/service-manual/design/writing-for-user-interfaces): start with little copy, use clear labels, and add help for demonstrated confusion. Improve controls instead of explaining how to operate them. Keep each sentence focused and make links meaningful on their own.

The copy review removed explanations of automatic suggestions, redundant name/language/viewing hints, returning-user instructions and email guidance before sign-in. It shortened access, verification and advanced-settings help. Keep the reference example and account distinction because the walkthrough exposed confusion there. Keep email consequences and recovery actions where invitations are created or resent. Technical setup procedures belong in the linked guide.

This is a design approach, not a claim of GOV.UK compliance or completed user research. The upstream sign-in layout still uses the Decidim brand as its main heading; a task-based main heading belongs in the upstream layout review.

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

## Is the code the documentation?

Code describes what runs, and tests demonstrate selected behaviours. Neither records why a default was chosen, the people affected, the local/upstream boundary, or the evidence behind a product decision. Keep four complementary records:

1. **User guidance:** labels and help on the form, plus the short setup and email procedure in the README. A person should not need this design document to create an organisation.
2. **Design rationale:** this document, including the audience classification, trade-offs and deliberately unchanged policies.
3. **Executable evidence:** behaviour tests and [CI build/smoke results](https://github.com/jokroese/decidim-coolify/actions/workflows/images.yml). Put browser checks and unverified steps in the corresponding PR.
4. **Contribution history:** link each proposal, issue and PR below once it actually exists. Each PR should include its own before/after description and checks, so review does not depend on this chat.

Keep these records alongside the change. Do not duplicate implementation line by line in prose. Comments explain only non-obvious decisions such as deferring delivery without accepting the account.

## Upstream route and proposed change sets

Decidim's published [governance process](https://docs.decidim.org/en/develop/contribute/governance.html) asks for feature proposals on Metadecidim and product-team review before a PR. Use that route for behaviour and layout changes. Confirm the preferred route with maintainers for small copy corrections. The [translation rules](https://docs.decidim.org/en/v0.32/contribute/translations) place English source copy in YAML and other translations in Crowdin. Do not submit direct edits to upstream non-English YAML files.

1. **Reproduce on current upstream.** Check the current supported release and `develop`, review the repository's current contribution instructions, and search GitHub and Metadecidim for overlapping work. This implementation is verified against our pinned 0.32.1; it does not establish that every issue still exists on `develop`. The initial web search did not establish a matching existing proposal.
2. **Prepare a sanitised evidence packet.** Include the task (create an organisation), confusing labels, synthetic before/after screenshots, keyboard/no-JavaScript observations, and the acceptance criteria above. Say that the initial evidence came from one setup walkthrough. Ask several administrators, including someone outside self-organised groups, to try the revised form; record where they stop or need explanation.
3. **Propose shared behaviour and layout on Metadecidim.** Keep a clear boundary between general usability and the optional ability to defer an invitation. Explain which defaults are unchanged. Obtain product feedback before investing in a direct upstream port.
4. **Port the accepted parts into the owning engine.** Change upstream source files and tests directly. Do not contribute the downstream view override, initializer or Coolify environment checks. Adapt the JavaScript to the engine's existing conventions and use its RSpec/system and JavaScript test suites.
5. **Submit independently reviewable change sets.** Use the groups below. Each should include the problem, final behaviour, compatibility considerations, relevant tests and the approved proposal link. Follow the target branch's current PR template and checks.
6. **Complete translation and documentation work.** Put accepted English keys in the owning engine. Route other languages through Crowdin. Update the system-administration guide for changed decisions or invitation timing; ordinary help-text corrections need no separate manual chapter. Use [Decidim's documentation contribution process](https://docs.decidim.org/en/develop/contribute/documentation.html).
7. **Track acceptance and removal.** Record proposal/PR URLs and the first release containing each change. Upgrade our pinned gems and frontend packages together, run the deployment checks, then delete the corresponding local override or adapter. Remove whole view overrides only after all local responsibilities have another home. Keep Coolify-specific copy and transport behaviour here unless an accepted generic extension replaces them.

| Proposed change set | Evidence and tests | Status |
| --- | --- | --- |
| Sign-in sequence, scoped messages and password-manager support | First-time/returning sign-in, failed/successful authentication, no credential disclosure | Local candidate; not submitted |
| Plain-language fields, reference example and useful validation messages | Before/after copy; render, escaping and accessible-label tests | Local candidate; not submitted |
| Editable name suggestions and administrator-name default | Typing/manual override/revalidation tests; accents, non-Latin text and length boundaries | Local candidate; product review needed |
| Language search and default-language consistency | Keyboard, search, default selection and no-JavaScript tests | Local candidate; product review needed |
| Advanced placement and access/verification explanations | Existing policy values unchanged; additional domains retained; form works without JavaScript | Local candidate; product review needed |
| Optional deferred administrator invitation | Explicit delivery state, later resend, normal configured delivery and no access bypass | Local implementation; generic upstream design not agreed |

The generic deferral proposal should expose an explicit invitation policy or delivery capability. Upstream must not infer that SMTP is unavailable merely because particular environment variables are missing: other installations can use other delivery transports. The current local check uses our deployment configuration and is intentionally not an upstream API.

## Deployment prerequisite discovered during testing

A real creation request exposed a mismatch that earlier smoke tests missed: the pilot Compose file generated a 64-character Rails secret, while Decidim 0.32.1 requires exactly 128 characters in its organisation form. This is a packaging defect, not a usability requirement or a reason to override Decidim validation.

The deployment now uses `SERVICE_HEX_128_RAILS`, and test fixtures match that length. A startup diagnostic catches incompatible supplied values. Existing installations follow the [secret upgrade check](CONFIGURATION.md#upgrading-the-rails-secret-from-the-first-pilot) before changing configuration. No existing secret is changed by this code edit. Keep this correction in a separate deployment change set; it does not need a Decidim feature proposal.

## Upgrade and release checklist

1. Compare the pinned upstream sign-in and creation views, Devise message scopes, organisation controller, `Decidim::User#invite!` and Devise invitation behaviour against the target version. Check that pending invitations still appear in the organisation list and that resend still uses the intended administrator.
2. Run `node --test tests/organisation_setup_test.mjs`, the repository validation/Python tests, image build, migration/configuration tests and full smoke test. See [Contributing](../CONTRIBUTING.md#build-and-check-a-change) for commands.
3. Check first-time and returning sign-in in a browser, including failed authentication and password-manager attributes. Check the creation form: suggestions, independent manual edits, failed submission, keyboard language search/default selection, native advanced disclosure, and both email states. Repeat with JavaScript disabled and at a narrow viewport.
4. Verify a real invitation and acceptance on an isolated Coolify installation. Confirm the organisation administrator can sign in after acceptance and that the system administrator account remains separate.
5. Publish and test a new versioned image, then update the pinned deployment reference through the normal release process. Publishing and deployment are separate steps.

## Contribution tracker

No external submissions yet. Add actual URLs, review decisions, release versions and local-removal commits here as work proceeds. Do not treat a plan, draft or open PR as an upstream fix.
