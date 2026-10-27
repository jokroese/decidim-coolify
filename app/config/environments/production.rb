require "active_support/core_ext/integer/time"
require "uri"

Rails.application.configure do
  config.enable_reloading = false
  config.eager_load = true
  config.consider_all_requests_local = false
  config.action_controller.perform_caching = true
  config.public_file_server.enabled = true
  config.public_file_server.headers = { "cache-control" => "public, max-age=#{1.year.to_i}" }
  config.active_storage.service = :local

  # Coolify terminates HTTPS; the application port stays private.
  public_url = URI.parse(ENV.fetch("APP_URL"))
  raise "APP_URL must be an HTTPS origin" unless public_url.scheme == "https" && public_url.host && ["", "/"].include?(public_url.path)
  config.assume_ssl = true
  config.force_ssl = true
  config.hosts = [public_url.host]
  config.host_authorization = { exclude: ->(request) { request.path == "/ready" || request.path == "/up" } }
  config.action_mailer.default_url_options = { host: public_url.host, protocol: "https", port: public_url.port }
  Rails.application.routes.default_url_options = config.action_mailer.default_url_options

  config.log_tags = [:request_id]
  config.logger = ActiveSupport::TaggedLogging.logger(STDOUT)
  config.log_level = ENV.fetch("RAILS_LOG_LEVEL", "info")
  config.silence_healthcheck_path = "/ready"
  config.active_support.report_deprecations = false
  config.active_job.queue_adapter = :sidekiq

  implicit_tls = ActiveModel::Type::Boolean.new.cast(ENV.fetch("SMTP_TLS", "false"))
  config.action_mailer.delivery_method = :smtp
  config.action_mailer.raise_delivery_errors = true
  config.action_mailer.smtp_settings = {
    address: ENV.fetch("SMTP_ADDRESS", "localhost"),
    port: Integer(ENV.fetch("SMTP_PORT", "587")),
    authentication: ENV.fetch("SMTP_AUTHENTICATION", "plain"),
    user_name: ENV["SMTP_USERNAME"], password: ENV["SMTP_PASSWORD"],
    domain: ENV["SMTP_DOMAIN"],
    ssl: implicit_tls,
    enable_starttls: !implicit_tls,
    enable_starttls_auto: !implicit_tls,
    openssl_verify_mode: "peer",
    open_timeout: 10, read_timeout: 30
  }
  config.active_record.encryption.primary_key = ENV.fetch("ACTIVE_RECORD_ENCRYPTION_PRIMARY_KEY")
  config.active_record.encryption.deterministic_key = ENV.fetch("ACTIVE_RECORD_ENCRYPTION_DETERMINISTIC_KEY")
  config.active_record.encryption.key_derivation_salt = ENV.fetch("ACTIVE_RECORD_ENCRYPTION_KEY_DERIVATION_SALT")
  config.i18n.fallbacks = true
  config.active_record.dump_schema_after_migration = false
  config.active_record.attributes_for_inspect = [:id]
end
