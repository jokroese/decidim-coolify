# frozen_string_literal: true
require_relative "../config/environment"
require "rake"
Rails.application.load_tasks

# Serialise preparation even if an operator accidentally starts a second web.
# Deployments still require stopping old workers before changing the schema.
ActiveRecord::Base.connection_pool.with_connection do |connection|
  connection.execute("SELECT pg_advisory_lock(739204611)")
  begin
    Rake::Task["db:migrate"].invoke
    Rake::Task["data:migrate"].invoke
    unless Decidim::System::Admin.exists?
      password = ENV.fetch("INITIAL_SYSTEM_ADMIN_PASSWORD")
      Decidim::System::Admin.create!(email: ENV.fetch("SYSTEM_ADMIN_EMAIL"),
        password: password, password_confirmation: password)
      puts "Created the initial system administrator."
    end
  ensure
    connection.execute("SELECT pg_advisory_unlock(739204611)")
  end
end
