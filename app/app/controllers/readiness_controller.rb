# Dependency readiness for the proxy and container health checks.
class ReadinessController < ActionController::API
  def show
    ActiveRecord::Base.connection_pool.with_connection { |connection| connection.select_value("SELECT 1") }
    Sidekiq.redis { |connection| connection.call("PING") }
    head :ok
  rescue StandardError
    head :service_unavailable
  end
end
