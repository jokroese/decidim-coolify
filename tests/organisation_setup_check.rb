# frozen_string_literal: true

# Run through rails runner in the disposable smoke project, before and after SMTP
# configuration. No real messages are delivered and database changes roll back.
require "nokogiri"
require "action_dispatch/testing/integration"

def setup_assert(condition, message)
  raise "Organisation setup: #{message}" unless condition
end

def setup_document(session)
  Nokogiri::HTML(session.response.body)
end

def setup_token(session)
  setup_document(session).at_css('input[name="authenticity_token"]')&.[]("value") ||
    setup_document(session).at_css('meta[name="csrf-token"]')&.[]("content")
end

setup_assert(Rails.application.secret_key_base.length == 128, "deployment secret must meet Decidim's unchanged requirement")
cryptor = Decidim::AttributeEncryptor.new
setup_assert(cryptor.decrypt(cryptor.encrypt("disposable encryption probe")) == "disposable encryption probe", "deployment secret must encrypt and decrypt")

original_log_level = Rails.logger.level
Rails.logger.level = Logger::WARN
original_adapter = ActiveJob::Base.queue_adapter
ActiveJob::Base.queue_adapter = :test
adapter = ActiveJob::Base.queue_adapter
pending = OrganisationSetup.mail_pending?

begin
  ActiveRecord::Base.transaction do
    session = ActionDispatch::Integration::Session.new(Rails.application)
    session.host! URI(ENV.fetch("APP_URL")).host
    session.https!
    session.get "/system/organizations/new"
    setup_assert(session.response.redirect?, "anonymous access must be refused")
    session.get "/system/admins/sign_in"
    setup_assert(session.response.status == 200, "system sign-in must render")
    sign_in = setup_document(session)
    setup_assert(sign_in.at_css("h2").text == "Set up your Decidim site", "first setup page must explain its purpose")
    setup_assert(sign_in.text.include?("Next, create your organisation"), "organisation creation must be presented as the next step")
    setup_assert(sign_in.text.include?("SYSTEM_ADMIN_EMAIL") && sign_in.text.include?("SERVICE_PASSWORD_64_ADMIN"), "first sign-in must locate bootstrap credentials")
    setup_assert(!sign_in.text.include?("create an account before continuing"), "admin sign-in must not suggest self-registration")
    setup_assert(!sign_in.text.include?("You must create an organization") && !sign_in.text.include?("Email is not configured"), "later-step warnings must not precede sign-in")
    setup_assert(!sign_in.text.include?("Outgoing email"), "email instructions must not appear before sign-in")
    setup_assert(sign_in.at_css('#admin_email')["autocomplete"] == "username", "email must support password managers")
    setup_assert(sign_in.at_css('#admin_password')["autocomplete"] == "current-password", "password must support password managers")
    setup_assert(sign_in.at_css('a[href="https://github.com/jokroese/decidim-coolify#find-your-setup-credentials"]'), "credential help must link to the specific procedure")
    setup_assert(!session.response.body.include?(ENV.fetch("INITIAL_SYSTEM_ADMIN_PASSWORD")), "bootstrap password must not be rendered")

    session.post "/system/admins/sign_in", params: {
      authenticity_token: setup_token(session),
      admin: { email: ENV.fetch("SYSTEM_ADMIN_EMAIL"), password: ENV.fetch("INITIAL_SYSTEM_ADMIN_PASSWORD") }
    }
    setup_assert(session.response.redirect?, "system administrator sign-in must succeed")
    session.get "/system/organizations/new"
    setup_assert(session.response.status == 200, "new form must render: #{session.response.status}")
    page = setup_document(session)
    setup_assert(page.at_css('[data-organisation-setup]'), "enhanced form missing")
    setup_assert(page.at_css('#organization_organization_admin_name')["value"].to_s.empty?, "admin name must not come from email")
    setup_assert(page.at_css('details #organization_secondary_hosts'), "additional domains must be advanced")
    setup_assert(page.at_css('#organization_short_name')["maxlength"] == "12", "short name limit missing")
    setup_assert(page.css('script[src]').any? { |script| script["src"].include?("organisation_setup") }, "setup pack missing")
    setup_assert(page.at_css('button[type="submit"]').text.include?(pending ? "later" : "invite administrator"), "submit copy must match email state")
    # Submit the same defaults as the rendered form, including advanced upload settings.
    fields = page.css("#new_organization input[name], #new_organization textarea[name]").filter_map do |input|
      next if %w[checkbox radio].include?(input["type"]) && !input.key?("checked")
      next if input["type"] == "submit"

      [input["name"], input["value"] || input.text]
    end
    defaults = Rack::Utils.parse_nested_query(URI.encode_www_form(fields)).fetch("organization").deep_symbolize_keys
    attributes = defaults.merge(
      name: "<script>alert('name')</script> Community", short_name: "Test group", reference_prefix: "TEST",
      host: "setup-test.example.invalid", organization_admin_name: "Test Administrator",
      organization_admin_email: "setup-admin@example.invalid", available_locales: { en: "en" },
      default_locale: "es", users_registration_mode: "enabled"
    )

    # Browser-independent server validation and escaping on an invalid submission.
    session.post "/system/organizations", params: { authenticity_token: setup_token(session), organization: attributes.merge(short_name: "xx") }
    setup_assert(session.response.status == 422, "invalid short name must be rejected")
    page = setup_document(session)
    setup_assert(page.at_css('#organization_name')["value"] == attributes[:name], "submitted name must survive validation")
    setup_assert(!session.response.body.include?("<script>alert('name')</script>"), "submitted HTML must be escaped")
    setup_assert(page.at_css('#organization_short_name')["value"] == "xx", "manual short name must survive validation")
    setup_assert(page.at_css('details[open]'), "advanced field errors must be discoverable")
    setup_assert(Decidim::Organization.find_by(host: attributes[:host]).nil?, "invalid form must not create organisation")

    session.post "/system/organizations", params: { authenticity_token: setup_token(session), organization: attributes }
    setup_assert(session.response.redirect?, "valid creation must redirect: #{session.response.status} #{session.request.controller_instance.instance_variable_get(:@form)&.errors&.to_hash}")
    organisation = Decidim::Organization.find_by!(host: attributes[:host])
    setup_assert(organisation.available_locales.include?("es"), "default language must also be enabled without JavaScript")
    setup_assert(organisation.default_locale == "es", "default language must be preserved")
    setup_assert(organisation.users_registration_mode == "enabled", "registration policy must not change")
    setup_assert(!organisation.force_users_to_authenticate_before_access_organization, "public viewing default must not change")
    admin = organisation.users.find_by!(email: attributes[:organization_admin_email])
    setup_assert(admin.admin? && admin.invitation_pending?, "administrator must have a pending invitation")
    mail_jobs = -> { adapter.enqueued_jobs.select { |job| job[:job].to_s.include?("MailDelivery") } }
    if pending
      setup_assert(admin.invitation_sent_at.nil?, "deferred invitation must not be marked sent")
      setup_assert(mail_jobs.call.empty?, "deferred invitation must not enqueue mail")
      setup_assert(session.flash[:notice].include?("has not been sent"), "success must explain deferred invitation")
    else
      setup_assert(admin.invitation_sent_at.present?, "configured invitation must use normal delivery")
      setup_assert(mail_jobs.call.any?, "configured invitation must enqueue mail")
    end
    session.get "/system/"
    setup_assert(session.response.status == 200, "existing-organisation system dashboard must render for an authenticated administrator: #{session.response.status}")
    dashboard = setup_document(session)
    expected_heading = I18n.t("decidim.system.dashboard.show.current_organizations", locale: :en)
    setup_assert(dashboard.css("h2").any? { |heading| heading.text == expected_heading }, "existing-organisation dashboard content is missing")
    session.get "/system/organizations"
    setup_assert(session.response.body.include?("resend_invitation"), "pending invitation must be recoverable from list")
    before = mail_jobs.call.length
    session.post "/system/organizations/#{organisation.id}/resend_invitation", params: { authenticity_token: setup_token(session) }
    setup_assert(session.response.redirect?, "resend must return to list")
    setup_assert(mail_jobs.call.length == before + (pending ? 0 : 1), "resend must respect delivery configuration")

    if pending
      # Simulate completing email setup; reload persisted state as a new request does.
      Rails.application.config.x.deployment[:mail_enabled] = true
      session.get "/system/organizations"
      session.post "/system/organizations/#{organisation.id}/resend_invitation", params: { authenticity_token: setup_token(session) }
      setup_assert(admin.reload.invitation_sent_at.present?, "saved invitation must be sendable after email setup")
      setup_assert(mail_jobs.call.length == before + 1, "later resend must enqueue exactly one email")
      Rails.application.config.x.deployment[:mail_enabled] = false
    end

    returning = ActionDispatch::Integration::Session.new(Rails.application)
    returning.host! URI(ENV.fetch("APP_URL")).host
    returning.https!
    returning.get "/system/admins/sign_in"
    returning_page = setup_document(returning)
    setup_assert(returning_page.at_css("h2").text == "System administration", "returning sign-in must have an administration heading")
    setup_assert(!returning_page.text.include?("SERVICE_PASSWORD_64_ADMIN") && !returning_page.text.include?("SYSTEM_ADMIN_EMAIL"), "bootstrap guidance must disappear after an organisation exists")
    setup_assert(!returning_page.text.include?("Outgoing email can be configured afterwards"), "returning administrators must not see first-run reassurance")
    setup_assert(returning_page.at_css("#admin_password")["autocomplete"] == "current-password", "returning sign-in must keep password manager support")

    # CSRF remains enforced even for an authenticated administrator.
    session.post "/system/organizations", params: { organization: attributes.merge(host: "csrf-test.example.invalid") }
    setup_assert(session.response.status == 422, "missing CSRF token must be rejected")
    setup_assert(!Decidim::Organization.exists?(host: "csrf-test.example.invalid"), "CSRF request must not create organisation")
    raise ActiveRecord::Rollback
  end
ensure
  Rails.logger.level = original_log_level
  ActiveJob::Base.queue_adapter = original_adapter
  Rails.application.config.x.deployment[:mail_enabled] = !pending
end
puts "SMOKE_ORGANISATION_SETUP_OK"
