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
RUN pnpm build

# --- Stage 2: nginx runtime ------------------------------------------------
#
# The *unprivileged* variant, not plain `nginx:alpine`. ARCH-001 §17.1 asks for non-root
# containers, and the stock image fights that: run it as a normal user and it cannot write
# `/run/nginx.pid`, warns that its own `user` directive is meaningless, and needs a handful of
# chowns and a patched nginx.conf to behave. This image is built for it — uid 101, pid under
# /tmp, listening on 8080 already — so the requirement costs nothing instead of a pile of fixes.
FROM nginxinc/nginx-unprivileged:1.27-alpine AS runtime

# Root only to place files and fix ownership; the image drops back to nginx below.
USER root

# The bundle lives at /opt/spa and is published to the shared volume at start-up; see
# docker-entrypoint.sh for why it is a copy and not the served directory itself.
COPY --from=builder /app/dist /opt/spa

COPY deploy/nginx/default.conf /etc/nginx/conf.d/default.conf
COPY deploy/nginx/proxy.conf /etc/nginx/vt-proxy.conf
COPY deploy/nginx/docker-entrypoint.sh /usr/local/bin/vt-entrypoint.sh
RUN chmod +x /usr/local/bin/vt-entrypoint.sh

# /srv/spa is written by the entrypoint on every start, so it has to belong to the runtime user;
# /srv/media is a read-only mount and only needs to exist.
RUN mkdir -p /srv/spa /srv/media \
    && chown -R nginx:nginx /srv/spa

USER nginx

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -q -O /dev/null http://127.0.0.1:8080/nginx-health || exit 1

ENTRYPOINT ["/usr/local/bin/vt-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
