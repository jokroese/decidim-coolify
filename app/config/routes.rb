require "sidekiq/web"

Rails.application.routes.draw do
  get "/ready", to: "readiness#show"
  if Rails.env.development?
    mount LetterOpenerWeb::Engine, at: "/letter_opener"
  end

  mount Decidim::Core::Engine => '/'
  authenticate :user, ->(u) { u.admin? } do
    mount Sidekiq::Web => "/sidekiq"
  end
  # Liveness complements the dependency-aware /ready endpoint.
  get "up" => "rails/health#show", as: :rails_health_check
end
