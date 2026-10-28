# frozen_string_literal: true

# Local adaptations for Decidim 0.32.1. See docs/ORGANISATION-SETUP.md before upgrading.
module OrganisationSetup
  def self.mail_pending?
    Rails.env.production? && Rails.application.config.x.deployment[:mail_enabled] == false
  end

  module Controller
    def create
      # A default language is always an available language, including without JS.
      attributes = params[:organization]
      locale = attributes&.[](:default_locale)
      if Decidim.available_locales.map(&:to_s).include?(locale)
        attributes[:available_locales] ||= ActionController::Parameters.new
        if attributes[:available_locales].is_a?(ActionController::Parameters)
          attributes[:available_locales][locale] = locale
        end
      end
      super
      if OrganisationSetup.mail_pending? && response.redirect? && flash[:notice].present?
        flash[:notice] = helpers.setup_text("created_pending")
      end
    end

    def resend_invitation
      if OrganisationSetup.mail_pending?
        flash[:alert] = helpers.setup_text("invitation_pending")
        redirect_to organizations_path
      else
        super
      end
    end

    private

    def default_params
      super.merge(organization_admin_name: nil)
    end
  end

  module Invitation
    def invite!(invited_by = nil, options = {}, &block)
      return super unless OrganisationSetup.mail_pending? &&
                          options[:invitation_instructions] == "organization_admin_invitation_instructions"

      # Devise persists a pending invitation without enqueueing undeliverable mail.
      # The system dashboard's existing resend action sends it after email setup.
      super(invited_by, options) do |user|
        block&.call(user)
        user.skip_invitation = true
      end
    end
  end
end
