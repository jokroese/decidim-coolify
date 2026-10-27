# frozen_string_literal: true

namespace :deployment do
  desc "Check installed Decidim schema migrations and registered upstream data migrations"
  task check_migrations: :environment do
    # Use the loaded bundle and the same railties/path API as Rails' installer.
    engines = Rails.application.migration_railties.each_with_object({}) do |engine, result|
      scope = engine.railtie_name
      next unless scope == "decidim" || scope.start_with?("decidim_")

      result[scope] = {
        schema: Array(engine.paths["db/migrate"].first),
        data: [engine.root.join("db/data")]
      }
    end
    check = MigrationCompleteness.new(
      engines: engines,
      schema_paths: Rails.application.paths["db/migrate"].to_a,
      data_paths: DataMigrate::DataMigrator.migrations_paths
    )
    check.verify!
    puts "PASS: #{check.schema_count} upstream schema migrations installed; " \
         "#{check.data_count} upstream data migrations registered."
  end
end
