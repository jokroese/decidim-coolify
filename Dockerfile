# syntax=docker/dockerfile:1
FROM node:22-bookworm-slim@sha256:de170b39439eb0e5a3444ad7d60b015614a381e10fecae2e30ec9e735122f38d AS node
FROM ruby:3.4-slim-trixie@sha256:09125b2be429d65151802d2a04a60e0817fb8f380195fedbc3e3d8b51b12c049 AS runtime
ENV RAILS_ENV=production \
    BUNDLE_DEPLOYMENT=1 \
    BUNDLE_PATH=/usr/local/bundle \
    BUNDLE_WITHOUT=development:test \
    RAILS_LOG_TO_STDOUT=1 \
    RAILS_SERVE_STATIC_FILES=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates libpq5 libvips-tools libicu76 libyaml-0-2 tzdata \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1000 decidim \
    && useradd --uid 1000 --gid 1000 --home-dir /app --no-create-home decidim

FROM runtime AS build
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential git curl pkg-config libpq-dev libicu-dev libyaml-dev libssl-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -s /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx
COPY app/Gemfile app/Gemfile.lock ./
RUN bundle install --jobs 4 && rm -rf /usr/local/bundle/cache
COPY app/package.json app/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY app/ ./
# Build-only dummy inputs: no production secret or service connection is needed.
RUN SECRET_KEY_BASE_DUMMY=1 \
    ACTIVE_RECORD_ENCRYPTION_PRIMARY_KEY=build-only-primary-key \
    ACTIVE_RECORD_ENCRYPTION_DETERMINISTIC_KEY=build-only-deterministic-key \
    ACTIVE_RECORD_ENCRYPTION_KEY_DERIVATION_SALT=build-only-key-derivation-salt \
    APP_URL=https://build.invalid \
    DATABASE_URL=postgresql://build:build@127.0.0.1/build \
    bundle exec rails deployment:check_migrations decidim_api:generate_docs assets:precompile \
    && rm -rf node_modules tmp/cache log/*
ARG TARGETARCH
RUN case "$TARGETARCH" in \
      amd64) checksum=cc232108374e8e2b537045f2d5eaa1229f619db314c3ba6a14d38b35dc0aa123 ;; \
      arm64) checksum=4ae22576a78223d8ccdf5f3b3660a5cbb5288416bf0ca96afc4a36d195932b94 ;; \
      *) exit 1 ;; \
    esac \
    && curl -fsSL --retry 3 "https://github.com/aptible/supercronic/releases/download/v0.2.51/supercronic-linux-${TARGETARCH}" -o /usr/local/bin/supercronic \
    && echo "$checksum  /usr/local/bin/supercronic" | sha256sum -c - \
    && chmod 755 /usr/local/bin/supercronic

FROM runtime AS app
COPY --from=build /usr/local/bundle /usr/local/bundle
COPY --from=build /usr/local/bin/supercronic /usr/local/bin/supercronic
COPY --from=build --chown=decidim:decidim /app /app
COPY --chown=decidim:decidim docker/ /app/docker/
RUN mkdir -p storage tmp/pids log && chown -R decidim:decidim storage tmp log \
    && chmod 755 docker/entrypoint
USER 1000:1000
EXPOSE 3000
STOPSIGNAL SIGTERM
HEALTHCHECK --interval=30s --timeout=10s --start-period=180s --retries=5 CMD ["ruby", "docker/healthcheck.rb", "web"]
ENTRYPOINT ["/app/docker/entrypoint"]
CMD ["web"]
