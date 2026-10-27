# frozen_string_literal: true

require "minitest/autorun"
require "tmpdir"
require "fileutils"
require "digest"
require_relative "../app/lib/migration_completeness"

class MigrationCompletenessTest < Minitest::Test
  def setup
    @root = Dir.mktmpdir("migration-completeness-")
    @schema = File.join(@root, "app/db/migrate")
    @data = File.join(@root, "gems/decidim/db/data")
    @engines = { "decidim" => {
      schema: [File.join(@root, "gems/decidim/db/migrate")], data: [@data]
    } }
    write(File.join(@engines["decidim"][:schema].first, "20160101000000_create_users.rb"))
    @installed = File.join(@schema, "20261026114620_create_users.decidim.rb")
    write(@installed)
    write(File.join(@data, "20260101000000_update_users.rb"))
    @data_paths = [@data]
  end

  def teardown
    FileUtils.remove_entry(@root)
  end

  def test_accepts_local_timestamps_and_custom_history_without_writing_files
    write(File.join(@schema, "20261027120000_custom_change.rb"))
    write(File.join(@schema, "20261027120001_removed_upstream_step.decidim.rb"))
    before = snapshot
    check = checker
    check.verify!
    assert_equal 1, check.schema_count
    assert_equal 1, check.data_count
    assert_equal before, snapshot
  end

  def test_missing_import_fails_and_does_not_recreate_it
    File.unlink(@installed)
    before = snapshot
    error = assert_raises(RuntimeError) { checker.verify! }
    assert_includes error.message, "Missing schema migration: decidim/20160101000000_create_users.rb"
    assert_includes error.message, "bundle exec rails decidim:upgrade"
    assert_equal before, snapshot
  end

  def test_new_migration_in_upgraded_gem_fails_until_imported
    write(File.join(@engines["decidim"][:schema].first, "20261027000000_add_setting.rb"))
    assert_raises(RuntimeError) { checker.verify! }
    write(File.join(@schema, "20261028120000_add_setting.decidim.rb"))
    checker.verify!
  end

  def test_another_engine_or_custom_migration_cannot_mask_a_missing_import
    File.unlink(@installed)
    write(File.join(@schema, "20261026114620_create_users.decidim_other.rb"))
    write(File.join(@schema, "20261026114621_create_users.rb"))
    assert_raises(RuntimeError) { checker.verify! }
  end

  def test_nested_upstream_scope_is_replaced_by_the_importing_engine_scope
    write(File.join(@engines["decidim"][:schema].first, "20210309190009_create_storage.active_storage.rb"))
    write(File.join(@schema, "20261028120000_create_storage.decidim.rb"))
    checker.verify!
    File.unlink(File.join(@schema, "20261028120000_create_storage.decidim.rb"))
    error = assert_raises(RuntimeError) { checker.verify! }
    assert_includes error.message, "expected *_create_storage.decidim.rb"
  end

  def test_checks_additional_engines_without_a_fixed_module_list
    path = File.join(@root, "gems/decidim_extra/db/migrate")
    @engines["decidim_extra"] = { schema: [path], data: [] }
    write(File.join(path, "20260101000000_create_extra.rb"))
    error = assert_raises(RuntimeError) { checker.verify! }
    assert_includes error.message, "decidim_extra/20260101000000_create_extra.rb"
    write(File.join(@schema, "20261028120000_create_extra.decidim_extra.rb"))
    checker.verify!
  end

  def test_data_migrations_must_be_registered_from_the_upstream_directory
    copied_data = File.join(@root, "app/db/data")
    write(File.join(copied_data, "20260101000000_update_users.rb"))
    @data_paths = [copied_data]
    error = assert_raises(RuntimeError) { checker.verify! }
    assert_includes error.message, "Unregistered data migration: decidim/20260101000000_update_users.rb"
  end

  def test_registered_data_directory_covers_new_upstream_files
    write(File.join(@data, "20261027000000_update_settings.rb"))
    check = checker
    check.verify!
    assert_equal 2, check.data_count
  end

  def test_empty_or_missing_engine_discovery_cannot_pass
    @engines = {}
    error = assert_raises(RuntimeError) { checker.verify! }
    assert_includes error.message, "No Decidim core engine found"
    assert_includes error.message, "No upstream schema migrations found"
  end

  private

  def checker
    MigrationCompleteness.new(engines: @engines, schema_paths: [@schema], data_paths: @data_paths)
  end

  def write(path)
    FileUtils.mkdir_p(File.dirname(path))
    File.write(path, "# Migration fixture: never execute this file.\n")
  end

  def snapshot
    Dir.glob(File.join(@root, "**/*")).select { |path| File.file?(path) }
       .to_h { |path| [path, Digest::SHA256.file(path).hexdigest] }
  end
end
