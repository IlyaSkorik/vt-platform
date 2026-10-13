# The proxy policy for a programme's ZIP archives, which are not like any other request here.
#
# Several hundred uploaded files are read out of storage and written into one archive *before*
# the first byte leaves the backend, so nginx waits in silence for as long as that takes. On a
# festival-sized programme that silence is longer than the 300 s the ordinary policy allows,
# and the organizer gets a 504 for work the backend then finishes and discards — which is what
# "архив не скачивается" was. The client's own half of this limit is `DOWNLOAD_TIMEOUT_MS`
# (`src/shared/api/config.ts`), set to the same half hour.

include /etc/nginx/conf.d/proxy-common.conf.inc;

proxy_read_timeout 1800s;
proxy_send_timeout 1800s;

# Nothing worth buffering: the body is a file already spooled upstream, and holding a second
# copy of a multi-gigabyte archive on this container's disk before passing it on helps nobody.
proxy_buffering off;
