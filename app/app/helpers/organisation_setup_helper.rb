# frozen_string_literal: true

module OrganisationSetupHelper
  def setup_text(key, **options)
    # New copy falls back to English until reviewed translations are contributed.
    full_key = "organisation_setup.#{key}"
    t(full_key, **options, default: I18n.t(full_key, **options, locale: :en))
  end

  def setup_sign_in_page?
    controller_path == "decidim/system/devise/sessions"
  end

  def setup_first_run?
    @setup_first_run = Decidim::Organization.none? unless defined?(@setup_first_run)
    @setup_first_run
  end

  def setup_mail_pending?
    OrganisationSetup.mail_pending?
  end
end
