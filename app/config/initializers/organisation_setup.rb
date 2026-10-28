# frozen_string_literal: true

Rails.application.config.to_prepare do
  Decidim::System::OrganizationsController.prepend(OrganisationSetup::Controller)
  Decidim::System::OrganizationsController.helper(OrganisationSetupHelper)
  Decidim::User.prepend(OrganisationSetup::Invitation)
end
