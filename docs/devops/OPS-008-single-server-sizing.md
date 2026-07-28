# OPS-008 — Single-server sizing & tuning

**Status:** Active · **Sizes for:** ~3 000 registered users, ~200 concurrent online at peak,
media in object storage ([OPS-007](OPS-007-object-storage.md))

Everything on one machine: gunicorn/uvicorn, one Celery worker, Celery beat, PostgreSQL,
Redis, nginx. The numbers below come from what the platform actually does, not from a
template — where a figure was measured, it says so.

## 1. What creates load

| Profile | Cost |
|---|---|
| 200 programme screens polling every 5 s | 40 req/s, ~95 % of them a `304` answered from **one indexed query** (1–3 ms) → **~0.1 vCPU** |
| 200 people working in cabinets | realistically 20–40 req/s of real reads at 20–80 ms → **1–2 vCPU at peak** |
| Registration opening | a burst of writes in transactions; PostgreSQL is the limit here, not CPU |
| Diploma generation (Celery) | reportlab at ~30–80 ms/page: 3 000 diplomas ≈ **2–4 minutes of one core** |
| Programme PDF export | **synchronous, in a web worker** — see §8 |

The measured public-programme payload is 2.4 KB for four rows; a 60-row running order is
25–40 KB. With `ETag` revalidation in place, 200 viewers cost ~40 Kbit/s instead of ~5
Mbit/s.

## 2. The machine

| | vCPU | RAM | Disk |
|---|---|---|---|
| **Start here** | **2** | **6 GB** | **50 GB SSD** |
| Comfortable | 4 | 8 GB | 60 GB NVMe |
| Headroom for 500+ online | 8 | 16 GB | 80 GB |

Two vCPU are enough to begin with because **the three load profiles never overlap in
time**: the registration burst is weeks before the event, the programme polling is during
it, and the diploma run is after. There is no hour in the calendar where all three stack.

Memory budget:

| Service | 2 vCPU / 6 GB | 4 vCPU / 8 GB |
|---|---|---|
| PostgreSQL | ~2 GB | ~2.5 GB |
| gunicorn | 2 workers, ~700 MB | 3 workers, ~1.2 GB |
| Celery worker | concurrency 1, ~300 MB | concurrency 2, ~600 MB |
| Celery beat + nginx | ~150 MB | ~200 MB |
| Redis | 256 MB | 512 MB |
| OS + page cache | the rest (~2.5 GB) | the rest (~3 GB) |

The database is 1–3 GB per season, so on either box it sits in page cache in its entirety.
That is why 6 GB is not a compromise here — and why going to 5 GB buys almost nothing while
removing all the headroom.

### Settings that change on the smaller box

| Setting | 4 vCPU / 8 GB | 2 vCPU / 6 GB |
|---|---|---|
| `shared_buffers` | 2GB | 1500MB |
| `effective_cache_size` | 5GB | 3500MB |
| `work_mem` | 24MB | 16MB |
| `max_connections` | 100 | 50 |
| gunicorn `workers` | 3 | 2 |
| Celery `--concurrency` | 2 | 1 |
| Redis `maxmemory` | 512mb | 256mb |

Disk is small because uploads and generated documents live in a bucket: what stays is the
database (1–3 GB per season), WAL, and temporary files. **Keep ~15 GB of it free**: a print
run spools the diploma archive to disk on its way to the bucket (§8), and that archive is as
large as the tirage times the template.

## 3. PostgreSQL

`/etc/postgresql/16/main/conf.d/vt-platform.conf` (values for 4 vCPU / 8 GB — see §2 for the
smaller box):

```ini
# 4 vCPU / 8 GB, media in S3, one application on the box.
shared_buffers = 2GB                  # ~25% of RAM
effective_cache_size = 5GB            # what the planner may assume the OS caches
work_mem = 24MB                       # per sort/hash node - not per query
maintenance_work_mem = 512MB
max_connections = 100                 # CONN_MAX_AGE=60 keeps the real count well under this

wal_compression = on
min_wal_size = 1GB
max_wal_size = 4GB
checkpoint_completion_target = 0.9

random_page_cost = 1.1                # NVMe, not a spinning disk
effective_io_concurrency = 200

autovacuum_vacuum_scale_factor = 0.05 # applications and programme items churn
autovacuum_analyze_scale_factor = 0.02

log_min_duration_statement = 500ms    # the only slow-query signal you get on one box
log_checkpoints = on
log_lock_waits = on
```

`CONN_MAX_AGE` is already 60 s in `config/settings/base.py`, so connections are reused
rather than reopened per request. pgbouncer is unnecessary at this size — 3 web workers plus
2 Celery slots cannot approach 100 connections.

## 4. gunicorn

`backend/gunicorn.conf.py`:

```python
# ASGI: Django's sync views run in a thread pool inside each worker, so processes are for
# CPU parallelism and the pool absorbs concurrency. Three workers on 4 vCPU leaves a core
# for PostgreSQL; nine would only take RAM away from it.
bind = "0.0.0.0:8000"
worker_class = "uvicorn.workers.UvicornWorker"
workers = 3

# reportlab and pypdf hold on to memory across a big print run. Recycling workers keeps a
# long-lived process from growing indefinitely; the jitter avoids all three restarting at once.
max_requests = 1000
max_requests_jitter = 100

timeout = 120            # a large synchronous PDF export must not be killed mid-render
graceful_timeout = 30
keepalive = 5

accesslog = "-"
errorlog = "-"
# nginx terminates TLS, so the real client address arrives in a header.
forwarded_allow_ips = "127.0.0.1"
```

The image's `CMD` currently passes `--workers 3` inline. Point it at this file instead
(`gunicorn -c gunicorn.conf.py config.asgi:application`) so the settings live in one place.

## 5. Celery

```bash
celery -A config worker -l info \
  --concurrency 2 \
  --max-tasks-per-child 50 \
  --time-limit 3600 --soft-time-limit 3300
```

`--concurrency 2` leaves the API responsive while a print package renders. The child limit
matters more than usual: a run holds a template PDF and every rendered page, and uploads
each one to the bucket. Uploads are network calls now, not disk writes, so keep the time
limits generous and let boto3 retry the provider's occasional `503`.

Beat runs as its own process with `--schedule` on a writable path (the unpaid-order sweep is
the only periodic job today, and it recomputes from the database each run — it survives
restarts).

## 6. Redis

```ini
maxmemory 512mb
maxmemory-policy volatile-lru     # NOT allkeys-lru - see below
appendonly yes
appendfsync everysec
```

**`volatile-lru` is load-bearing.** One Redis instance carries three databases: `0` the
cache, `1` the Celery broker, `2` results. Under `allkeys-lru` Redis would happily evict
**queued task messages** from database 1 to make room for cache entries. `volatile-lru`
evicts only keys with a TTL — which is exactly the cache (public programmes expire in 60 s)
and never a queue.

`appendonly yes` because a Redis restart otherwise loses whatever was queued. For this
workload the queue is small and the fsync cost is irrelevant.

## 7. nginx

```nginx
server {
    listen 443 ssl http2;
    server_name app.example.com;

    ssl_certificate     /etc/letsencrypt/live/app.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/app.example.com/privkey.pem;

    # Video attachments are allowed up to 200 MB by the upload policy, music up to the
    # competition's configured limit (default 25 MB, max 512 MB). nginx defaults to 1 MB and
    # would reject those with a 413 before Django ever sees them.
    client_max_body_size 512m;
    client_body_timeout 300s;

    gzip on;
    gzip_types application/json application/javascript text/css image/svg+xml;

    # The built SPA. Vite emits hashed filenames, so assets are immutable and index.html
    # must never be cached - otherwise a deploy is invisible until a hard refresh.
    root /srv/vt-platform/frontend/dist;
    location /assets/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    location / {
        try_files $uri /index.html;
        add_header Cache-Control "no-store";
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        # production.py sets SECURE_PROXY_SSL_HEADER and SECURE_SSL_REDIRECT; without this
        # header Django thinks every request is plain HTTP and redirects in a loop.
        proxy_set_header X-Forwarded-Proto $scheme;

        # A large programme's PDF export renders synchronously.
        proxy_read_timeout 120s;

        # Do NOT touch ETag here. The public programme endpoint relies on the client
        # revalidating with If-None-Match; strip or rewrite the header and every poll starts
        # sending the whole table again (~5 Mbit/s with a hall of phones on it).
    }

    # Only needed while S3_BUCKET is unset. With a bucket configured, files are served from
    # it and nothing reaches this location.
    location /media/ {
        alias /srv/vt-platform/backend/media/;
        expires 30d;
    }
}

server {
    listen 80;
    server_name app.example.com;
    return 301 https://$host$request_uri;
}
```

## 8. Known limits of this shape

- **A print run spools its archive to disk, not to RAM.** Worth knowing because it used to be
  the other way round, and that — not the web workers — was what decided how much memory the
  box needed: one archive holds every diploma of a competition, each diploma is a full copy
  of its template, so 3 000 participants with a 2 MB template make a ~6 GB archive, and
  buffering it took twice that. It now streams member by member through a spool
  (`_ARCHIVE_SPOOL_BYTES`, 4 MB) that rolls over to disk, so peak memory is a chunk plus the
  threshold whatever the tirage. The cost moved to disk — hence the free-space note in §2.
- **The programme PDF export is synchronous.** 60 rows take 100–300 ms; a 300-row programme
  occupies one of three workers for far longer. When programmes get that big, move the
  export to Celery the way diploma generation already is.
- **No redundancy.** One machine means one failure domain: a lost disk takes the database
  with it. Media survives — it is in the bucket.
- **Whitenoise serves Django's own static** (admin, DRF, Spectacular UI). The SPA is nginx's
  job, as above.

## 9. Backups

| What | How | Where |
|---|---|---|
| Database | `pg_dump -Fc` nightly + before every deploy | **off the machine** — object storage or another host |
| Provider snapshot | daily volume snapshot | provider |
| Bucket | object versioning + lifecycle rule expiring noncurrent versions after 30 days | provider |
| Secrets | `SECRET_KEY` and S3 credentials in a password manager | — |

Restore rehearsal is the part that gets skipped: a dump nobody has restored is a hope, not a
backup. Note that rotating `SECRET_KEY` changes where *future* diploma files are written
(see OPS-007) — restoring an old dump against a new key is fine for already-issued diplomas,
because their references are in the dump and the objects are untouched.

## 10. S3 volume

Per season, 3 000 participants. The full derivation is in [OPS-007](OPS-007-object-storage.md).

| Item | Size |
|---|---|
| Backing tracks (3 000 × ~6 MB) | 18 GB |
| Payment receipts (3 000 × ~1.5 MB) | 4.5 GB |
| Participant documents and photos | ~3 GB |
| Diplomas (3 000 × the template's size, ~2 MB) | 6 GB |
| ZIP of the diplomas (PDFs barely compress) | 6 GB |
| Thank-you letters and their archives | ~4 GB |
| Competition assets (posters, landings, regulations) | < 1 GB |
| **Without video** | **≈ 45 GB** |
| Video, 30 % of participants remote (900 × ~100 MB) | +90 GB |
| Video, everyone remote | +300 GB |

Buy **100 GB** for an offline festival, **250 GB** if part of the field competes remotely,
**500 GB** for a fully remote format.

**The template's size is the biggest lever there is.** Every diploma is a full copy of the
backing PDF (`PdfWriter(clone_from=…)` in `apps/diplomas/infrastructure/pdf/renderer.py`), so
a 2 MB template costs 12 GB across diplomas and their archive, and a 10 MB one costs 90 GB.
The upload limit is 20 MB, which would be 180 GB for a single festival. Compressing the
background inside the template saves more than every other measure here combined.

Egress is billed too: diploma downloads are ~6 GB per season and organizers re-downloading
archives add 30–50 GB. If a jury reviews 3 000 videos, that is ~300 GB — the point at which a
CDN in front of the bucket (`S3_CUSTOM_DOMAIN`) pays for itself.
