threads_count = Integer(ENV.fetch("RAILS_MAX_THREADS", "5"))
threads threads_count, threads_count
bind "tcp://0.0.0.0:3000"
environment ENV.fetch("RAILS_ENV", "production")
