# frozen_string_literal: true
require "net/http"
case ARGV.fetch(0, "web")
when "web"
  http = Net::HTTP.new("127.0.0.1", 3000, nil)
  http.open_timeout = 3
  http.read_timeout = 5
  request = Net::HTTP::Get.new("/ready")
  request["X-Forwarded-Proto"] = "https"
  abort "Web is not ready" unless http.request(request).code == "200"
when "worker"
  require "bundler/setup"
  require "socket"
  require "sidekiq/api"
  live = Sidekiq::ProcessSet.new.any? do |process|
    process["hostname"] == Socket.gethostname && process["beat"].to_f > Time.now.to_f - 90
  end
  abort "Worker heartbeat missing" unless live
when "scheduler"
  abort "Scheduler heartbeat missing" unless File.exist?("/tmp/scheduler-heartbeat") &&
    File.mtime("/tmp/scheduler-heartbeat") > Time.now - 150
else
  abort "Unknown healthcheck role"
end
