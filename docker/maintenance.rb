# frozen_string_literal: true

ENV["RAILS_ENV"] ||= "production"

require "rake"
require File.expand_path("../config/environment", __dir__)

Rails.application.load_tasks

TASKS = {
  daily: [
    "decidim:delete_download_your_data_files",
    "decidim:open_data:export",
    "decidim_meetings:clean_registration_forms",
    "decidim:reminders:all",
    "decidim:mailers:notifications_digest_daily"
  ].freeze,
  weekly: [
    "decidim:mailers:notifications_digest_weekly"
  ].freeze,
  quarter_hour: [
    "decidim_participatory_processes:change_active_step"
  ].freeze
}.freeze


def enabled?(name)
  ENV.fetch(name, "false").casecmp?("true")
end


def run_tasks(task_names)
  failures = []

  task_names.each do |name|
    begin
      Rake::Task[name].invoke
      puts "[maintenance] completed task=#{name}"
    rescue StandardError => error
      warn "[maintenance] failed task=#{name} error_class=#{error.class}"
      failures << name
    end
  end

  failures
end

category = ARGV.fetch(0, "")
unless TASKS.key?(category.to_sym)
  warn "[maintenance] invalid category"
  exit 64
end

tasks = TASKS.fetch(category.to_sym)

if category == "daily" && enabled?("ENABLE_INACTIVE_ACCOUNT_CLEANUP")
  tasks = tasks + ["decidim:participants:delete_inactive_participants"]
elsif category == "daily"
  puts "[maintenance] skipped inactive-account cleanup; ENABLE_INACTIVE_ACCOUNT_CLEANUP is not true"
end

failed_tasks = run_tasks(tasks)
exit(failed_tasks.empty? ? 0 : 1)
