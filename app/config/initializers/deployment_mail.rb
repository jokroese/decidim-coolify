# frozen_string_literal: true

if Rails.env.production?
  Decidim.mailer_sender = Rails.application.config.x.deployment[:mailer_sender]
  ActiveSupport.on_load(:action_mailer) do
    add_delivery_method :setup_required, DeploymentConfiguration::SetupRequiredDelivery
  end
end
