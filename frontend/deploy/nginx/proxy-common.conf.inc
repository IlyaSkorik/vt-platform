# Everything a location needs to reach Django **except** how long it may wait.
#
# Kept in one file because `X-Forwarded-Proto` is the load-bearing line: `production.py` sets
# both `SECURE_PROXY_SSL_HEADER` and `SECURE_SSL_REDIRECT`, so a location that forgets it makes
# Django read the request as plain HTTP and redirect to HTTPS — in a loop (OPS-008 §7).
# Duplicating these per location is exactly how one gets forgotten.
#
# The timeouts are *not* here, and that is the whole reason this file exists: nginx refuses a
# duplicated `proxy_read_timeout` in one context, so a location that needs a longer one cannot
# include the shared policy and then override it. Include this plus exactly one timeout policy —
# `proxy.conf.inc` for everything, `proxy-archive.conf.inc` for the programme archives.

# No port here: `backend` is the named upstream declared in default.conf, which already carries
# one, and nginx refuses to start on the duplication ("upstream may not have port").
proxy_pass http://backend;

# 1.1 plus an empty Connection header is what actually enables the upstream keepalive pool the
# upstream block declares; left as-is nginx sends `Connection: close` and reopens a socket per
# request, which the programme screens' 5-second polling would do 40 times a second.
proxy_http_version 1.1;
proxy_set_header Connection "";

proxy_set_header Host              $host;
proxy_set_header X-Real-IP         $remote_addr;
proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
# `$forwarded_proto`, not `$scheme` — see the map in default.conf for why the difference is a
# redirect loop rather than a detail.
proxy_set_header X-Forwarded-Proto $forwarded_proto;

# While the backend is being replaced there is a window with nothing listening. Fail fast and
# retry rather than hang: a client waiting out the default 60 s connect timeout experiences a
# deploy as the site being broken, not as a blip.
#
# `non_idempotent` is deliberately absent — a retried POST would submit an application twice. Only
# reads and connection-level failures are retried, which is the difference between a deploy the
# reader does not notice and a deploy that duplicates their entry.
proxy_connect_timeout 2s;
proxy_next_upstream error timeout http_502 http_503 http_504;
proxy_next_upstream_tries 3;
proxy_next_upstream_timeout 10s;

# Do NOT touch ETag here. The public programme endpoint relies on the client revalidating
# with If-None-Match; strip or rewrite the header and every poll starts sending the whole
# table again — ~5 Mbit/s with a hall of phones on it instead of ~40 Kbit/s (OPS-008 §1).
