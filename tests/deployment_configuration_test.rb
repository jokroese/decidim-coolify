# frozen_string_literal: true
require "minitest/autorun"
require "erb"
require "yaml"
require_relative "../app/lib/deployment_configuration"

class DeploymentConfigurationTest < Minitest::Test
  def setup
    @env = {
      "APP_URL" => "https://participate.example.org",
      "SYSTEM_ADMIN_EMAIL" => "admin@example.org",
      "INITIAL_SYSTEM_ADMIN_PASSWORD" => "disposable-password"
    }
  end

  def test_secret_matches_decidim_without_changing_it
    assert DeploymentConfiguration.read(@env.merge("SECRET_KEY_BASE" => "a" * 128))
    ["", "a" * 64, "a" * 127, "a" * 129].each do |secret|
      error = assert_raises(DeploymentConfiguration::Error) do
        DeploymentConfiguration.read(@env.merge("SECRET_KEY_BASE" => secret))
      end
      assert_includes error.message, "128-character SECRET_KEY_BASE"
      assert_includes error.message, "existing installation"
    end
  end

  def test_first_run_without_email_uses_domain_defaults
    settings = DeploymentConfiguration.read(@env, bootstrap: true)
    refute settings[:mail_enabled]
    assert_equal "no-reply@participate.example.org", settings[:mailer_sender]
    assert_equal "participate.example.org", settings[:smtp_domain]
    assert_equal 587, settings[:smtp_port]
  end

  def test_blank_optional_values_use_defaults
    settings = DeploymentConfiguration.read(@env.merge("SMTP_DOMAIN" => "", "DECIDIM_MAILER_SENDER" => ""))
    assert_equal "no-reply@participate.example.org", settings[:mailer_sender]
    assert_equal "participate.example.org", settings[:smtp_domain]
  end

  def test_configured_mail_preserves_provider_overrides
    settings = DeploymentConfiguration.read(@env.merge(
      "SMTP_ADDRESS" => "smtp.example.org", "SMTP_USERNAME" => "user", "SMTP_PASSWORD" => "secret",
      "SMTP_DOMAIN" => "mail.example.org", "DECIDIM_MAILER_SENDER" => "Participation <hello@example.org>",
      "SMTP_PORT" => "465", "SMTP_TLS" => "true"
    ))
    assert settings[:mail_enabled]
    assert_equal "mail.example.org", settings[:smtp_domain]
    assert_equal "Participation <hello@example.org>", settings[:mailer_sender]
    assert_equal 465, settings[:smtp_port]
  end

  def test_errors_are_aggregated_without_echoing_values
    error = assert_raises(DeploymentConfiguration::Error) do
      DeploymentConfiguration.read({"SMTP_PASSWORD" => "do-not-print-me"}, bootstrap: true)
    end
    assert_includes error.message, "web domain"
    assert_includes error.message, "SYSTEM_ADMIN_EMAIL"
    assert_includes error.message, "SERVICE_PASSWORD_64_ADMIN"
    assert_includes error.message, "SMTP_ADDRESS, SMTP_USERNAME"
    refute_includes error.message, "do-not-print-me"
  end

  def test_partial_mail_configuration_is_never_silently_disabled
    %w[SMTP_ADDRESS SMTP_USERNAME SMTP_PASSWORD].each do |key|
      assert_raises(DeploymentConfiguration::Error) { DeploymentConfiguration.read(@env.merge(key => "partial")) }
    end
  end

  def test_invalid_origins_are_rejected
    ["", "http://example.org", "https://example.org/path", "https://example.org?x=y",
     "https://example.org#fragment", "https://user:secret@example.org", "not a URL"].each do |url|
      assert_raises(DeploymentConfiguration::Error) { DeploymentConfiguration.read(@env.merge("APP_URL" => url)) }
    end
  end

  def test_invalid_mail_transport_settings_are_rejected
    ["0", "65536", "smtp", ""].each do |port|
      assert_raises(DeploymentConfiguration::Error) { DeploymentConfiguration.read(@env.merge("SMTP_PORT" => port)) }
    end
    assert_raises(DeploymentConfiguration::Error) { DeploymentConfiguration.read(@env.merge("SMTP_TLS" => "maybe")) }
  end

  def test_workers_do_not_need_bootstrap_credentials
    assert DeploymentConfiguration.read({"APP_URL" => @env["APP_URL"]})
  end

  def test_disabled_delivery_fails_explicitly
    delivery = DeploymentConfiguration::SetupRequiredDelivery.new({})
    assert_raises(DeploymentConfiguration::EmailNotConfigured) { delivery.deliver!(Object.new) }
  end

  def test_production_database_url_is_not_required_by_development_or_test
    %w[development test].each do |environment|
      config = evaluate_database_config(environment)
      assert_nil config.fetch("production").fetch("url"), "#{environment} must not resolve the production URL"
    end
  end

  def test_production_database_url_remains_required_and_is_preserved
    assert_raises(KeyError) { evaluate_database_config("production") }
    config = evaluate_database_config("production", "postgresql://db.example/decidim")
    assert_equal "postgresql://db.example/decidim", config.fetch("production").fetch("url")
  end

  private

  def evaluate_database_config(environment, database_url = nil)
    original_environment = ENV.to_hash
    ENV["RAILS_ENV"] = environment
    database_url ? ENV["DATABASE_URL"] = database_url : ENV.delete("DATABASE_URL")
    source = File.read(File.expand_path("../app/config/database.yml", __dir__))
    YAML.safe_load(ERB.new(source).result)
  ensure
    ENV.replace(original_environment)
  end
end
