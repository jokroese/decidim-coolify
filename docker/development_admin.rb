# frozen_string_literal: true

email = ENV.fetch("SYSTEM_ADMIN_EMAIL")
password = ENV.fetch("SYSTEM_ADMIN_PASSWORD")
admin = Decidim::System::Admin.find_by(email: email)
created = admin.nil?

Decidim::System::Admin.create!(email: email, password: password, password_confirmation: password) if created

puts(created ? "Created the local development administrator." : "Local development administrator already exists.")
