# OPS-001 — Deployment runbook (single server)

**Status:** Active · **Shape:** one machine running the stack in
[`docker-compose.prod.yml`](../../docker-compose.prod.yml), sized by
[OPS-008](OPS-008-single-server-sizing.md), media in a bucket per
[OPS-007](OPS-007-object-storage.md).

Everything in the repository is ready to deploy: both images build, the stack boots, migrations
run as a pre-deploy job, and CI checks all of it. What is *not* in the repository is a server, a
domain, a certificate and a set of secrets — that is what this document is for.

Work through it once and every later deploy is a push to `main` plus an approval.

---

## 1. What you need before starting

| | Why |
|---|---|
| A server: 2 vCPU / 6 GB / 50 GB SSD to begin | OPS-008 §2 derives it; 4 vCPU / 8 GB is the comfortable size |
| Docker Engine + the compose plugin on it | the stack is compose, not systemd units |
| A domain with an A record at the server | `DJANGO_ALLOWED_HOSTS` and the certificate both name it |
| A TLS certificate, or a provider LB that terminates TLS | production settings force HTTPS; see §4 |
| SMTP credentials | verification links, password resets, invitations. Quotas in OPS-009 |
| An S3-compatible bucket | recommended, not required — see §3 on what changes without one |

Keep ~15 GB of the disk free: a print run spools the diploma archive to disk on its way to the
bucket (OPS-008 §2, §8).

---

## 2. Prepare the server and register the runner

The rollout runs **on the machine itself**, through a self-hosted GitHub Actions runner. There are
no SSH keys to manage and no remote shell to quote through; the deploy steps are ordinary local
commands, and the runner's workspace is a checkout of the exact commit being deployed — so the
compose file and the configuration it mounts can never be a different version from the images.

```bash
# As root, once.
adduser --disabled-password --gecos "" deploy
usermod -aG docker deploy

# Only the real .env, the pre-deploy dumps and an optional TLS block live here. The application
# files come from the runner's own workspace, so there is no second checkout to keep in step.
install -d -o deploy -g deploy \
  /srv/vt-platform/backend /srv/vt-platform/backups /srv/vt-platform/nginx/tls
```

Register the runner as the `deploy` user. Take the exact download URL and token from
**Settings → Actions → Runners → New self-hosted runner** — the token is single-use and expires:

```bash
sudo -u deploy -i
mkdir -p ~/actions-runner && cd ~/actions-runner
curl -o runner.tar.gz -L <the URL that page gives you>
tar xzf runner.tar.gz

./config.sh --url https://github.com/IlyaSkorik/vt-platform \
            --token <the token that page gives you> \
            --labels production \
            --name "$(hostname)" --unattended
exit
```

The `production` label is what `deploy.yml` selects on. Then install it as a service so it
survives a reboot:

```bash
cd /home/deploy/actions-runner
sudo ./svc.sh install deploy
sudo ./svc.sh start
sudo ./svc.sh status        # should say "active (running)"
```

> **One rule about this runner.** A self-hosted runner must never execute code from a fork, or
> anyone who opens a pull request runs commands on the production host. `deploy.yml` is triggered
> only by pushes to `main` and manual dispatch, which is what keeps that true — do not add
> `pull_request` to it. For the same reason, CI (`ci.yml`) runs on GitHub-hosted runners only.

---

## 3. Write the real `backend/.env` on the server

Never in git, and deliberately **outside** the runner's workspace — the workspace is replaced on
every deploy.

```bash
sudo -u deploy cp <this repo>/backend/.env.example /srv/vt-platform/backend/.env
sudo -u deploy chmod 600 /srv/vt-platform/backend/.env
sudo -u deploy vi /srv/vt-platform/backend/.env
```

Every line marked **REQUIRED IN PRODUCTION** in that file has to change. The ones that stop the
stack if they do not:

```ini
DJANGO_SETTINGS_MODULE=config.settings.production
DJANGO_SECRET_KEY=<python -c 'import secrets; print(secrets.token_urlsafe(64))'>
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=vzlettalantov.by,www.vzlettalantov.by
POSTGRES_PASSWORD=<a long random string>
```

`config/settings/production.py` refuses to import on the example's secret key or an unset
`ALLOWED_HOSTS`, and the compose file refuses to start without `POSTGRES_PASSWORD`. That is
deliberate: a container that exits is a problem you see, and one that boots on a known key is a
problem you do not.

Then the ones that are merely important:

```ini
FRONTEND_BASE_URL=https://vzlettalantov.by      # every sitemap entry and emailed link is built on this
DJANGO_CORS_ALLOWED_ORIGINS=https://vzlettalantov.by
DIPLOMA_VERIFICATION_BASE_URL=                  # empty reuses FRONTEND_BASE_URL; the printed QR uses it

EMAIL_HOST=<provider>
EMAIL_PORT=465
EMAIL_USE_SSL=true
EMAIL_HOST_USER=<mailbox>
EMAIL_HOST_PASSWORD=<password>
EMAIL_DEFAULT_FROM=no-reply@vzlettalantov.by

S3_BUCKET=<bucket>
S3_ENDPOINT_URL=https://s3.<provider>          # leave empty for AWS itself
S3_ACCESS_KEY_ID=<key>
S3_SECRET_ACCESS_KEY=<secret>
```

`SPA_INDEX_PATH` is set by the compose file, not here — leave it alone.

**Without `S3_BUCKET`** the stack still works: uploads and generated documents go to a shared
`media` volume that the API, the workers and nginx all mount, so a worker-rendered diploma is
still downloadable. What you lose is statelessness — that volume now holds data OPS-008 §9 has to
back up, and it does not survive the machine.

---

## 4. Decide where TLS terminates

The stack publishes plain HTTP on `HTTP_PORT` (80 by default) and expects HTTPS in front. Pick one:

**A — provider load balancer.** Point it at the server's port 80 and let it terminate. Nothing to
configure here: nginx forwards the `X-Forwarded-Proto` the LB sends, which is what tells Django
the request was secure.

**B — nginx or Caddy on the host.** Terminate there and proxy to `127.0.0.1:80`. Pass
`X-Forwarded-Proto $scheme` and keep `client_max_body_size` at least `512m`, or a video upload
dies with a 413 before Django sees it. OPS-008 §7 has the full server block.

**C — inside the stack's nginx.** Put a server block in `/srv/vt-platform/nginx/tls/` (the
container includes `/etc/nginx/tls/*.conf`), mount the certificates, and publish 443 in the compose
file. A path on the host, not in the repository: the deploy replaces the checkout, and a bind mount
whose source disappears breaks the container on its next restart. Certificate renewal then becomes
this container's problem, which is why it is not the default.

Whichever you choose, HTTPS is not optional: `SECURE_SSL_REDIRECT` answers plain HTTP with a 301,
and `SECURE_HSTS_SECONDS` is a year with preload.

### Renewal, and the half of it that is not automatic

Let's Encrypt renewal *is* automatic: the certbot package installs a systemd timer that runs
`certbot renew` twice a day and renews once fewer than 30 days remain. Nothing to schedule.

What is not automatic is **reloading the server that serves the certificate**. certbot writes the
new file and the running process keeps the old one in memory until something tells it otherwise.

* **Option B** — `certbot --nginx` installs the reload hook itself. Nothing to do.
* **Option C** — certbot has no idea a container exists. Without a hook the renewal is invisible to
  it, and roughly ninety days after launch the site serves an expired certificate while a valid one
  sits on disk beside it. Add the hook when you choose this option, not later:

  ```bash
  # /etc/letsencrypt/renewal-hooks/deploy/reload-vt-nginx.sh   (chmod +x)
  #!/bin/sh
  cd /srv/vt-platform || exit 0
  docker compose -f docker-compose.prod.yml --env-file ./backend/.env exec -T nginx nginx -s reload
  ```

  Then prove it works rather than waiting three months to find out:
  `certbot renew --dry-run --run-deploy-hooks`.

Either way, put an expiry check somewhere you will see it — a 90-day certificate is exactly long
enough for everyone to forget it exists.

---

## 5. Configure the GitHub environment

Repository → Settings → Environments → **New environment** → `production`.

**Required reviewers:** add yourself. This is the thing that makes the production deploy gated
(ARCH-001 §18.4) — without it the job runs unattended.

Variables:

| Name | Value |
|---|---|
| `ENV_FILE_PATH` | `/srv/vt-platform/backend/.env` — the default, so it can be omitted |
| `PUBLIC_URL` | `https://vzlettalantov.by` — the post-deploy check calls `/healthz` on it |

No secrets. The runner authenticates to the registry with the token Actions gives it, and every
real credential stays in the host's `.env` — nothing sensitive passes through the workflow.

---

## 6. First deploy

Do it by hand once. If something is wrong with the environment, you want to be standing next to it
rather than reading it out of a workflow log:

```bash
sudo -u deploy -i
git clone https://github.com/IlyaSkorik/vt-platform /tmp/first-deploy
cd /tmp/first-deploy

export ENV_FILE=/srv/vt-platform/backend/.env
set -a; . "$ENV_FILE"; set +a       # compose needs POSTGRES_PASSWORD in its own environment

docker compose -f docker-compose.prod.yml --env-file "$ENV_FILE" up -d --build --wait
```

`--build` only here: afterwards the workflow supplies prebuilt, SHA-tagged images. Expect the
migration job to apply ~90 migrations and exit, then the API to go healthy, then nginx. The
compose project name is fixed in the file, so the containers and volumes this creates are the same
ones the workflow will later manage from its own workspace — `/tmp/first-deploy` can be deleted
afterwards.

Then create the first administrator:

```bash
docker compose -f docker-compose.prod.yml --env-file "$ENV_FILE" \
  run --rm backend python manage.py createsuperuser
```

Check it from outside the machine:

```bash
curl -si https://vzlettalantov.by/healthz            # 200
curl -si https://vzlettalantov.by/api/v1/public/festivals   # 200
curl -s  https://vzlettalantov.by/ | grep og:title   # the head is rendered server-side
curl -si http://vzlettalantov.by/  | head -1         # 301 to HTTPS
```

That last one matters more than it looks: if it is a `200`, TLS is not actually in front and
nothing is encrypted. If browsing the site instead loops forever, the terminator is not sending
`X-Forwarded-Proto` — §4.

From here on: **push to `main` → approve the deploy → done.**

---

## 7. What a deploy costs

Pushing to `main` takes nothing down. CI and the image build run on GitHub's runners, and the
rollout job then waits for the approval in §5 — production serves the old version throughout, for
as long as the approval takes.

Once approved, the host dumps the database, pulls the new images and runs migrations **while the
old code is still serving**. Only the last step touches the running services. Measured on this
stack by polling the edge five times a second:

| What changed | Failed requests | Why |
|---|---|---|
| Frontend only | **none at all** | the bundle and nginx config are published into volumes by a one-shot job; nginx is never recreated |
| Backend (or both) | **~0.2 s — two requests** | the API container is replaced; nginx stays up, returns 502 for that instant and retries |

For reference, the shape this replaced recreated nginx on every frontend build: ~14 seconds during
which the published port had no listener at all, so clients got a refused connection rather than
even an error page.

Nothing in flight is lost in that window. Each service is stopped with a grace period matched to
what it holds — 45 s for the API, above gunicorn's own 30 s drain — and Celery acknowledges tasks
on completion (`CELERY_TASK_ACKS_LATE`), so a worker stopped mid-print hands the task back instead
of taking it to the grave. A redelivered print run resumes: generation renders only what has no
PDF yet.

**The one thing that can still cost minutes is a migration.** It runs before the rollout, against
the live database, with the old code serving — so a statement that takes a heavy lock stalls
requests for as long as it holds one, and no amount of container choreography helps. Before
approving a release that adds a migration, look at what it does:

- `AddIndex` on a populated table locks writes for the whole build. Use
  `AddIndexConcurrently` with `atomic = False`. (Nothing in the repository does this yet — six
  migrations use plain `AddIndex`, harmless on the empty database they were written against.)
- `AlterField` may rewrite the table.
- `RemoveField` / `DeleteModel` must never ship in the same release as the code that stops using
  the column. Expand first, contract in a later release (ARCH-001 §18.4).

---

## 8. Rollback

Re-deploying an older commit is the rollback, and it is a first-class entry point rather than
something to reconstruct while the site is down:

> Actions → Deploy → **Run workflow** → `sha` = the last good commit → approve.

Its images are still in the registry, and the host prunes only images older than a week.

**A migration is the exception.** Rolling the code back does not roll the schema back, which is
why §18.4 wants migrations to be expand-only: add columns, do not drop them in the same release
that stops using them. When a rollback does need the schema reverted, restore the dump the deploy
took before it — `backups/pre-deploy-<sha>.dump` on the server.

---

## 9. Backups

The deploy takes a dump before every rollout. That is not a backup strategy on its own — OPS-008
§9 is:

| What | How | Where |
|---|---|---|
| Database | `pg_dump -Fc` nightly, and before every deploy (automatic) | **off the machine** |
| Volume | provider snapshot, daily | provider |
| Bucket | object versioning + a lifecycle rule expiring noncurrent versions after 30 days | provider |
| `DJANGO_SECRET_KEY`, S3 credentials | password manager | — |

The pre-deploy dumps in `/srv/vt-platform/backups/` are a safety net for *that rollout* — the
workflow keeps the five most recent and prunes the rest, because a 1–3 GB dump per deploy on a
50 GB disk fills it up months later, during a deploy, which is the worst possible moment.

### The nightly job, to a bucket of its own

[`deploy/backup/`](../../deploy/backup/) holds it: a script, a service and a timer. Install as
root, once:

```bash
cd /srv/vt-platform   # or wherever the repository is checked out on the machine
install -m 0755 deploy/backup/vt-backup.sh /usr/local/bin/vt-backup
install -m 0644 deploy/backup/vt-backup.service deploy/backup/vt-backup.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now vt-backup.timer
```

The database credentials come from `backend/.env`; the bucket's come from `/etc/vt-backup.env`,
which the unit reads and which the application never does (`chmod 600` — these are credentials):

```
BACKUP_S3_BUCKET=vtbackups
BACKUP_S3_ACCESS_KEY_ID=…
BACKUP_S3_SECRET_ACCESS_KEY=…
BACKUP_S3_ENDPOINT_URL=https://…
```

**A bucket of its own is the point, not a detail.** The application's key can delete media, so
everything that key reaches is destroyable by whatever destroys the application — a backup must
not be reachable that way. Give this one a key scoped to `vtbackups` and the two share nothing
but a provider. Set only `BACKUP_S3_BUCKET` and it borrows the application's key, which is better
than nothing and worse than a separate key. Set neither and it falls back to `S3_BUCKET` under a
`backups/db/` prefix, which keeps the single-bucket shape working.

Run it by hand before trusting the timer:

```bash
/usr/local/bin/vt-backup          # writes one dump and reports what it put where
systemctl list-timers vt-backup   # when it next fires
journalctl -u vt-backup -n 50     # what the last run did
```

A failure otherwise reaches only the journal, which is the classic way to lose data: the job
stopped in March and nobody read the log until June. Two more lines in the same
`/etc/vt-backup.env` send it somewhere with a person behind it:

```
BACKUP_TELEGRAM_TOKEN=123456:AA…
BACKUP_TELEGRAM_CHAT_ID=-1001234567890
```

Three things the script does that a plainer one would not, each for a reason worth keeping:

* **It verifies the dump before uploading it.** `pg_dump` exiting 0 means it finished, not that
  the archive is readable; `pg_restore --list` reads the table of contents back, which is the
  cheapest check that would notice a truncated file. The night to find out is not the night you
  need it.
* **It reads the object back after uploading.** `cp` reporting success while the object is absent
  — a wrong endpoint, a key without write permission — is exactly the failure a backup must not
  sleep through, so the size in the listing is compared with the size on disk.
* **It deletes a partial upload on any failure.** An incomplete object is worse than no object:
  in a listing it looks like a backup.

Two notes on the retention, since "keep the last seven" is the obvious instinct:

* **Let the bucket expire them, not the script.** A lifecycle rule on `vtbackups` with an
  expiration of 7 days does it server-side, so a broken timer cannot silently stop pruning while
  still uploading — or worse, prune while failing to upload.
* **Seven daily copies is one week of history.** It restores yesterday, and it cannot restore the
  state before a mistake nobody noticed for ten days. If that matters, add a monthly rule keeping
  one copy for a year; object storage is cheap enough that the decision is about intent, not cost.

### The rehearsal

A dump nobody has restored is a hope, and this is the step that gets skipped. It takes ten
minutes, and it is the only thing that turns the bucket into a backup:

```bash
set -a; . /srv/vt-platform/backend/.env; set +a
KEY=$(aws --endpoint-url "$BACKUP_S3_ENDPOINT_URL" s3 ls s3://vtbackups/ | tail -1 | awk '{print $4}')
aws --endpoint-url "$BACKUP_S3_ENDPOINT_URL" s3 cp "s3://vtbackups/$KEY" /tmp/rehearsal.dump

PG=$(docker ps -q --filter label=com.docker.compose.project=vt-platform-prod \
                  --filter label=com.docker.compose.service=postgres)

# Into a scratch database, never over the live one.
docker exec -i "$PG" psql -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE restore_check;"
docker exec -i "$PG" pg_restore -U "$POSTGRES_USER" -d restore_check --no-owner < /tmp/rehearsal.dump

# What came back: the table count, and a table you can recognise.
docker exec -i "$PG" psql -U "$POSTGRES_USER" -d restore_check -tAc \
  "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';"

docker exec -i "$PG" psql -U "$POSTGRES_USER" -d postgres -c "DROP DATABASE restore_check;"
rm -f /tmp/rehearsal.dump
```

Note that rotating `SECRET_KEY` changes where *future* diploma files are written (OPS-007);
restoring an old dump against a new key is fine for already-issued diplomas, because their
references are in the dump and the objects are untouched.

---

## 10. What is deliberately not here yet

- **No stage environment.** ARCH-001 §18.4 describes one that deploys automatically on merge.
  `deploy.yml` has no `stage` job, because there is no host for it — add both together.
- **E2E tests are not in the pipeline.** Playwright is configured in the repository but needs a
  running stack with seeded data; CI boots the stack and probes it instead.
- **No redundancy.** One machine is one failure domain: a lost disk takes the database with it.
  Media survives if it is in a bucket.
- **Observability is unwritten** (OPS-004). Today the signals are container logs,
  `log_min_duration_statement = 500ms` in PostgreSQL, and the two health endpoints.
