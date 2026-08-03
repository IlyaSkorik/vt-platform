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

# Only the real .env and the pre-deploy dumps live here. The application files come from the
# runner's own workspace, so there is no second checkout to keep in step.
install -d -o deploy -g deploy /srv/vt-platform/backend /srv/vt-platform/backups
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

**C — inside the stack's nginx.** Put a server block in `deploy/nginx/tls/` (the container
includes `/etc/nginx/tls/*.conf`), mount the certificates, and publish 443 in the compose file.
Certificate renewal then becomes this container's problem, which is why it is not the default.

Whichever you choose, HTTPS is not optional: `SECURE_SSL_REDIRECT` answers plain HTTP with a 301,
and `SECURE_HSTS_SECONDS` is a year with preload.

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

## 7. Rollback

Re-deploying an older commit is the rollback, and it is a first-class entry point rather than
something to reconstruct while the site is down:

> Actions → Deploy → **Run workflow** → `sha` = the last good commit → approve.

Its images are still in the registry, and the host prunes only images older than a week.

**A migration is the exception.** Rolling the code back does not roll the schema back, which is
why §18.4 wants migrations to be expand-only: add columns, do not drop them in the same release
that stops using them. When a rollback does need the schema reverted, restore the dump the deploy
took before it — `backups/pre-deploy-<sha>.dump` on the server.

---

## 8. Backups

The deploy takes a dump before every rollout. That is not a backup strategy on its own — OPS-008
§9 is:

| What | How | Where |
|---|---|---|
| Database | `pg_dump -Fc` nightly, and before every deploy (automatic) | **off the machine** |
| Volume | provider snapshot, daily | provider |
| Bucket | object versioning + a lifecycle rule expiring noncurrent versions after 30 days | provider |
| `DJANGO_SECRET_KEY`, S3 credentials | password manager | — |

The part that gets skipped is the restore rehearsal. A dump nobody has restored is a hope.

Note that rotating `SECRET_KEY` changes where *future* diploma files are written (OPS-007);
restoring an old dump against a new key is fine for already-issued diplomas, because their
references are in the dump and the objects are untouched.

---

## 9. What is deliberately not here yet

- **No stage environment.** ARCH-001 §18.4 describes one that deploys automatically on merge.
  `deploy.yml` has no `stage` job, because there is no host for it — add both together.
- **E2E tests are not in the pipeline.** Playwright is configured in the repository but needs a
  running stack with seeded data; CI boots the stack and probes it instead.
- **No redundancy.** One machine is one failure domain: a lost disk takes the database with it.
  Media survives if it is in a bucket.
- **Observability is unwritten** (OPS-004). Today the signals are container logs,
  `log_min_duration_statement = 500ms` in PostgreSQL, and the two health endpoints.
