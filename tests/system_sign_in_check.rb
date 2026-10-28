# frozen_string_literal: true

# Exercise Devise's failure recall through the real server, with its session cookie
# and CSRF token. Used only by the disposable smoke stack; no mail is sent.
require "net/http"
require "uri"
require "nokogiri"

public_uri = URI(ENV.fetch("APP_URL"))
http = Net::HTTP.new("127.0.0.1", 3000, nil)
http.open_timeout = 3
http.read_timeout = 30
cookies = {}
request = lambda do |path, fields = nil|
  req = fields ? Net::HTTP::Post.new(path) : Net::HTTP::Get.new(path)
  req["Host"] = public_uri.host
  req["X-Forwarded-Proto"] = "https"
  req["Cookie"] = cookies.map { |name, value| "#{name}=#{value}" }.join("; ")
  req.set_form_data(fields) if fields
  response = http.request(req)
  response.get_fields("set-cookie").to_a.each do |cookie|
    name, value = cookie.split(";", 2).first.split("=", 2)
    cookies[name] = value
  end
  response
end
follow = lambda do |response|
  3.times do
    break unless response.is_a?(Net::HTTPRedirection)

    location = URI.join(public_uri.to_s, response.fetch("location"))
    raise "Sign-in redirect changed host" unless location.host == public_uri.host

    response = request.call(location.request_uri)
  end
  response
end
response = request.call("/system/admins/sign_in")
page = Nokogiri::HTML(response.body)
form = page.at_css("#new_admin")
raise "Sign-in form missing" unless response.code == "200" && form

# Rails UJS refreshes hidden CSRF inputs from the page meta token in the browser.
response = follow.call(request.call(form["action"], {
  "authenticity_token" => page.at_css('meta[name="csrf-token"]')["content"],
  "admin[email]" => ENV.fetch("SYSTEM_ADMIN_EMAIL"),
  "admin[password]" => "incorrect-disposable-password"
}))
page = Nokogiri::HTML(response.body)
raise "Failed sign-in error missing" unless page.text.include?("Invalid email or password.")
raise "Submitted email was lost" unless page.at_css("#admin_email")&.[]("value") == ENV.fetch("SYSTEM_ADMIN_EMAIL")
raise "Password was echoed" unless page.at_css("#admin_password") && page.at_css("#admin_password")["value"].to_s.empty?

form = page.at_css("#new_admin")
response = follow.call(request.call(form["action"], {
  "authenticity_token" => page.at_css('meta[name="csrf-token"]')["content"],
  "admin[email]" => ENV.fetch("SYSTEM_ADMIN_EMAIL"),
  "admin[password]" => ENV.fetch("INITIAL_SYSTEM_ADMIN_PASSWORD")
}))
raise "Successful sign-in did not reach organisation setup" unless response.code == "200" && Nokogiri::HTML(response.body).at_css("#new_organization")

puts "SMOKE_SYSTEM_SIGN_IN_OK"
