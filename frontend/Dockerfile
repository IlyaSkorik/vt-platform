# VT Platform frontend image — `vt-frontend` (ARCH-001 §17.2).
#
# Multi-stage: the SPA is built with Node and the artifacts are copied into an nginx runtime, so
# the shipped image carries no build tooling (ARCH-001 §17.1, §17.4). This image is also the
# reverse proxy for the single-server deployment — ARCH-001 §17.2 lists `vt-nginx` separately for
# the multi-node topology, where a proxy tier scales independently of the asset tier; on one box
# a second nginx whose only job is to proxy to the first would be pure overhead.

# --- Stage 1: build the SPA -----------------------------------------------
FROM node:22-alpine AS builder

# pnpm via corepack, pinned by the lockfile's own version field.
RUN corepack enable

WORKDIR /app

# Dependencies first so a source-only change reuses this layer.
COPY package.json pnpm-lock.yaml ./
RUN --mount=type=cache,target=/root/.local/share/pnpm/store \
    pnpm install --frozen-lockfile

COPY . .

# The typed API client is generated, not committed — `src/shared/api/generated` holds only a
# `.gitkeep`, while the contracts it is generated from (`openapi/*.yaml`) are checked in. So the
# build has to produce it, or `tsc -b` fails on a few hundred missing modules. Generating it here
# from the committed schema is also the stronger guarantee: the client in the image always matches
# the contract in the commit, rather than whatever a developer last ran locally.
RUN pnpm api:generate

# `pnpm build` is `tsc -b && vite build`: the type check is part of the build on purpose, so an
# image can never be produced from code that does not type-check.
#
# VITE_* values are inlined at build time, which is what makes them a build argument rather than
# runtime configuration. Left empty the client calls the same origin it was served from — which
# is what the deployment does, since nginx fronts both.
ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
# The analytics counters, for the same reason: an id compiled into the bundle is the
# only way the client knows which counter it belongs to. Empty means this image
# carries no counter at all, which is the right default for every build but the one
# that becomes production.
ARG VITE_YANDEX_METRICA_ID=""
ENV VITE_YANDEX_METRICA_ID=$VITE_YANDEX_METRICA_ID
ARG VITE_GA_MEASUREMENT_ID=""
ENV VITE_GA_MEASUREMENT_ID=$VITE_GA_MEASUREMENT_ID
RUN pnpm build

# --- Stage 2: the publisher ------------------------------------------------
#
# This image does not serve anything. It carries the built bundle and the nginx configuration and,
# when run, copies both into the volumes the stack reads from — then exits. nginx itself runs from
# the stock upstream image (see `docker-compose.prod.yml`).
#
# **Why it works that way.** When nginx ran from this image, every frontend build produced a new
# image tag, so compose recreated the nginx container on every deploy: measured, ~14 seconds during
# which the published port had no listener at all — a refused connection, not even a 502. Treating
# the bundle and the config as data leaves nginx's service definition unchanged between deploys, so
# there is nothing for compose to recreate, and the only restart left is the API's (~1.4 s).
#
# Still based on the *unprivileged* nginx image: it already has the right uid and the nginx binary,
# which keeps `nginx -t` available for validating the config that ships here (ARCH-001 §17.1).
FROM nginxinc/nginx-unprivileged:1.27-alpine AS runtime

# Root only to place files; the image drops back to nginx below.
USER root

COPY --from=builder /app/dist /opt/spa
# Every config file, by glob rather than one COPY per name: the server block includes the
# others, so a new include forgotten here is a container that will not start — and the
# failure shows up at deploy time, not in review. `docker-entrypoint.sh` does not match.
COPY deploy/nginx/*.conf* /opt/nginx-conf/
COPY deploy/nginx/docker-entrypoint.sh /usr/local/bin/vt-publish.sh
RUN chmod +x /usr/local/bin/vt-publish.sh

# The publish targets. Created here so the volumes mount onto directories the runtime user owns.
RUN mkdir -p /srv/spa /srv/nginx-conf /srv/media \
    && chown -R nginx:nginx /srv/spa /srv/nginx-conf

USER nginx

ENTRYPOINT ["/usr/local/bin/vt-publish.sh"]
