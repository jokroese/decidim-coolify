# frozen_string_literal: true

require "set"

# File-only checks: do not execute migrations, copy files or query the database.
class MigrationCompleteness
  attr_reader :schema_count, :data_count

  def initialize(engines:, schema_paths:, data_paths:)
    @engines = engines
    @schema_paths = schema_paths
    @data_paths = data_paths
  end

  def verify!
    problems = []
    @schema_count = @data_count = 0
    installed = files_in(@schema_paths).map do |file|
      File.basename(file).sub(/\A\d+_/, "")
    end.to_set
    registered_data = files_in(@data_paths).map { |file| File.realpath(file) }.to_set

    problems << "No Decidim core engine found; check the application bundle." unless @engines.key?("decidim")
    @engines.sort.each do |scope, paths|
      files_in(paths.fetch(:schema)).each do |file|
        @schema_count += 1
        # Rails replaces an existing source scope (e.g. .active_storage)
        # with the importing engine's scope when it copies a migration.
        name = File.basename(file).sub(/\A\d+_/, "").split(".").first
        expected = "#{name}.#{scope}.rb"
        problems << "Missing schema migration: #{scope}/#{File.basename(file)} (expected *_#{expected})" unless installed.include?(expected)
      end
      files_in(paths.fetch(:data)).each do |file|
        @data_count += 1
        next if registered_data.include?(File.realpath(file))

        problems << "Unregistered data migration: #{scope}/#{File.basename(file)}"
      end
    end
    problems << "No upstream schema migrations found; check Decidim migration paths." if @schema_count.zero?
    return if problems.empty?

    raise "Migration completeness check failed:\n#{problems.join("\n")}\n" \
          "From app/, run bundle exec rails decidim:upgrade and review the changes. " \
          "For unregistered data migrations, check the engine initialisers and DataMigrate paths. " \
          "Preserve existing migration filenames."
  end

  private

  def files_in(paths)
    Array(paths).flat_map { |path| Dir.glob(File.join(path.to_s, "[0-9]*_*.rb")) }.uniq.sort
  end
end
