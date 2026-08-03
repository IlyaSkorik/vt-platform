#!/bin/sh
# Publish the SPA this image was built with into the volume the backend also reads.
#
# Why a copy instead of just serving from the image: Django needs the same `index.html` on disk
# to inject the `<head>` into (SPA_INDEX_PATH), and it lives in a different container. A shared
# volume is the only place both can see it.
#
# Why on every start rather than relying on Docker's populate-empty-volume behaviour: that copy
# happens only when the volume is empty, so the second deploy would serve the *first* deploy's
# bundle forever — a stale-frontend bug that looks like caching and is not. Syncing here makes
# the running bundle always the one in this image.
set -eu

SPA_SRC=/opt/spa
SPA_DST=/srv/spa

if [ ! -f "$SPA_SRC/index.html" ]; then
  echo "entrypoint: no SPA build at $SPA_SRC — the image is broken" >&2
  exit 1
fi

mkdir -p "$SPA_DST"

# Replace everything except /assets, and merge that instead of clearing it.
#
# The asymmetry is deliberate. `config/spa.py` serves the document with `Cache-Control:
# public, max-age=300` — a considered choice, since the head varies per competition and should
# not be re-rendered for every crawler. But a client holding that document for five minutes
# after a deploy asks for the *previous* build's asset names, and if this had cleared /assets
# those are 404s: a blank app for anyone who reloads inside the window.
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
# unwanted — the copies should belong to the nginx user that has to read them. `-a` "worked"
# but printed a permission warning per file, which buries anything real in the start-up log.
cp -r "$SPA_SRC"/. "$SPA_DST"/

echo "entrypoint: published $(find "$SPA_DST" -type f | wc -l) files to $SPA_DST"

exec "$@"
