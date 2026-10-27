# frozen_string_literal: true

require "uri"

# Shared by the startup check and Rails; does not load Rails or contact services.
module DeploymentConfiguration
  class Error < StandardError; end
  class EmailNotConfigured < StandardError; end

  # Keep failed deliveries visible and retryable instead of silently discarding mail.
  class SetupRequiredDelivery
    def initialize(*) = nil

    def deliver!(_mail)
      raise EmailNotConfigured, "Email is not configured. Add SMTP_ADDRESS, SMTP_USERNAME and SMTP_PASSWORD in Coolify, then redeploy."
    end
  end

  def self.read(env = ENV, bootstrap: false)
    errors = []
    value = env["APP_URL"].to_s.strip
    begin
      url = URI.parse(value)
      valid_url = url.scheme == "https" && url.host && !url.host.empty? &&
                  ["", "/"].include?(url.path) && !url.userinfo && !url.query && !url.fragment
    rescue URI::InvalidURIError
      valid_url = false
    end
    unless valid_url
      errors << "Set the web domain in Coolify: protocol https, your hostname, internal port 3000, empty path. If its generated URL is unavailable, set APP_URL to your public HTTPS URL (without :3000)."
    end

    if bootstrap
      unless env["SYSTEM_ADMIN_EMAIL"].to_s.match?(URI::MailTo::EMAIL_REGEXP)
        errors << "Set SYSTEM_ADMIN_EMAIL to the initial administrator's email address."
      end
      if env["INITIAL_SYSTEM_ADMIN_PASSWORD"].to_s.empty?
        errors << "Check that Coolify generated SERVICE_PASSWORD_64_ADMIN for the initial administrator password."
      end
    end

    smtp_keys = %w[SMTP_ADDRESS SMTP_USERNAME SMTP_PASSWORD]
    mail_enabled = smtp_keys.any? { |key| !env[key].to_s.empty? }
    if mail_enabled
      missing = smtp_keys.select { |key| env[key].to_s.empty? }
      unless missing.empty?
        errors << "Email settings are incomplete: set #{missing.join(', ')}, or clear all three SMTP settings to finish initial setup without email."
      end
    end
    begin
      port = Integer(env.fetch("SMTP_PORT", "587"))
      raise ArgumentError unless (1..65_535).cover?(port)
    rescue ArgumentError, TypeError
      errors << "SMTP_PORT must be a number from 1 to 65535 (usually 587)."
    end
    unless %w[true false].include?(env.fetch("SMTP_TLS", "false"))
      errors << "SMTP_TLS must be true (implicit TLS) or false (STARTTLS)."
    end
    raise Error, "Setup needs attention:\n- #{errors.join("\n- ")}" unless errors.empty?

    sender = env["DECIDIM_MAILER_SENDER"].to_s.strip
    domain = env["SMTP_DOMAIN"].to_s.strip
    {
      public_url: url,
      mail_enabled: mail_enabled,
      mailer_sender: sender.empty? ? "no-reply@#{url.host}" : sender,
      smtp_domain: domain.empty? ? url.host : domain,
      smtp_port: port
    }
  end
end
