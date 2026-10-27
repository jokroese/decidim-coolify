# frozen_string_literal: true
require_relative "../lib/deployment_configuration"

begin
  settings = DeploymentConfiguration.read(bootstrap: ARGV.first == "web" || ARGV.first == "prepare")
  unless settings[:mail_enabled]
    warn "Initial setup: email is not configured. Administrator sign-in is available; invitations, password resets and notifications need SMTP settings."
  end
rescue DeploymentConfiguration::Error => error
  warn error.message
  exit 1
end
