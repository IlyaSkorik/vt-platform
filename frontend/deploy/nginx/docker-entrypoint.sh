#!/bin/sh
# Publish this image's SPA bundle and nginx configuration into the volumes the running stack
# reads from, then exit.
#
# **Why this is a separate one-shot container rather than the nginx entrypoint.**
#
# nginx used to run from this image, which meant every frontend build produced a new image tag,
# which meant compose recreated the nginx container on every deploy. Measured, that cost ~14
# seconds during which the published port had no listener at all — clients got a refused
# connection, not even a 502. A backend-only deploy, where nginx was left alone, cost 1.4 s.
#
# So the bundle and the configuration are treated as *data*: this container writes them into
# volumes and leaves. nginx runs from the stock upstream image, mounts those volumes, and its
# service definition therefore never changes between deploys — so compose has no reason to
# recreate it, and the only restart left in a deploy is the API's.
#
# Django reads `index.html` out of the same bundle volume to inject the `<head>` (SPA_INDEX_PATH),
# and caches it by mtime, so it picks up a new bundle without a restart either.
set -eu

SPA_SRC=/opt/spa
SPA_DST=/srv/spa
CONF_SRC=/opt/nginx-conf
CONF_DST=/srv/nginx-conf

[ -f "$SPA_SRC/index.html" ] || { echo "publish: no SPA build at $SPA_SRC — the image is broken" >&2; exit 1; }
[ -f "$CONF_SRC/default.conf" ] || { echo "publish: no nginx config at $CONF_SRC — the image is broken" >&2; exit 1; }

mkdir -p "$SPA_DST" "$CONF_DST"

# Replace everything except /assets, and merge that instead of clearing it.
#
# The asymmetry is deliberate. `config/spa.py` serves the document with `Cache-Control:
# public, max-age=300` — a considered choice, since the head varies per competition and should not
# be re-rendered for every crawler. But a client holding that document for five minutes after a
# deploy asks for the *previous* build's asset names, and if this cleared /assets those are 404s:
# a blank app for anyone who reloads inside the window.
#
# Keeping them costs nothing to correctness because Vite's filenames are content-hashed — an old
# name can only ever mean the old bytes. It costs disk: roughly the bundle size per deploy,
# accumulating in the volume. Worth pruning by mtime if that ever matters; ~2 MB a deploy is not
# the thing to optimise first.
#
# Root-level files (index.html, favicon.svg, the images) are *not* hashed, so those are replaced
# outright — a file dropped from the build must not linger.
find "$SPA_DST" -mindepth 1 -maxdepth 1 ! -name assets -exec rm -rf {} +

# `-r`, not `-a`: this runs unprivileged, so preserving ownership is both impossible and
# unwanted — the copies should belong to the user that has to read them. `-a` "worked" but printed
# a permission warning per file, which buries anything real in the log.
cp -r "$SPA_SRC"/. "$SPA_DST"/

# The configuration is replaced wholesale: unlike assets, a stale server block is never wanted.
rm -rf "${CONF_DST:?}"/*
cp -r "$CONF_SRC"/. "$CONF_DST"/

echo "publish: $(find "$SPA_DST" -type f | wc -l) bundle files -> $SPA_DST"
echo "publish: $(find "$CONF_DST" -type f | wc -l) config files -> $CONF_DST"

# Nothing to exec by default; the caller may still pass a command (the image can be run as a
# standalone nginx for local inspection).
[ "$#" -eq 0 ] && exit 0
exec "$@"
