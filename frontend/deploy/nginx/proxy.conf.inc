# The proxy policy for every location that reaches Django: how to get there, plus the
# ordinary waiting limits. Include this and nothing else.
#
# The one exception is `proxy-archive.conf.inc`, which pairs the same `proxy-common.conf.inc`
# with limits of its own — see there for why the archives need their own.

include /etc/nginx/conf.d/proxy-common.conf.inc;

# A large programme's PDF export renders synchronously (OPS-008 §8), and an attachment upload
# is worse: nginx buffers the whole body first, so the clock only starts once 124 MB of video
# are already on disk here — and Django still has to parse the multipart and push the bytes to
# the bucket before it can answer. At 120 s that answer was cut off after the applicant had
# already spent the entire upload, which reads as "видео не грузится" with nothing in the
# backend log to show for it. Matches `client_body_timeout` in default.conf.
proxy_read_timeout 300s;

# The other half of the same request: nginx forwarding the buffered body upstream. Left at the
# default 60 s a slow bucket-side write can stall the write long enough to drop it.
proxy_send_timeout 300s;
