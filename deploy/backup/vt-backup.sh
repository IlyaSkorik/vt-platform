#!/usr/bin/env bash
#
# Nightly database backup to the bucket (OPS-001 §9, OPS-008 §9).
#
# The pre-deploy dumps `deploy.yml` takes are a safety net for *that rollout* and they live on
# the same disk as the database they protect. This is the other thing: one copy per night, off
# the machine, in the bucket that already holds the media.
#
# Three properties the obvious version of this script does not have:
#
# * **The dump is verified before it is uploaded.** `pg_dump` exiting 0 means it finished, not
#   that the archive is readable; `pg_restore --list` reads the table of contents back and is
#   the cheapest thing that would notice a truncated or corrupt file. A backup nobody has read
#   is a hope, and the night to discover that is not the night you need it.
#
# * **A failure is loud.** The classic way to lose data is a backup job that stopped months ago
#   into a log nobody reads. Every exit path here reports, and with `BACKUP_TELEGRAM_*` set it
#   reports where somebody will see it.
#
# * **Retention is the bucket's job, not this script's.** A lifecycle rule on `backups/db/`
#   prunes server-side, so a broken cron cannot silently stop pruning while still uploading —
#   or, worse, prune while failing to upload. See §9 for the rule to set.
#
# Install (as root, once):
#
#   install -m 0755 vt-backup.sh /usr/local/bin/vt-backup
#   install -m 0644 vt-backup.service vt-backup.timer /etc/systemd/system/
#   systemctl daemon-reload && systemctl enable --now vt-backup.timer
#
# Run it by hand the first time — the restore rehearsal is the part that gets skipped:
#
#   /usr/local/bin/vt-backup

set -euo pipefail

STACK_DIR="${STACK_DIR:-/srv/vt-platform}"
ENV_FILE="${ENV_FILE:-$STACK_DIR/backend/.env}"
WORK_DIR="${WORK_DIR:-$STACK_DIR/backups}"

#: The running stack is found by container label rather than through `docker compose -f …`.
#: `docker-compose.prod.yml` is not on this machine in any fixed place — it comes from the
#: Actions runner's workspace, which is recreated on every deploy (OPS-001 §2). A backup that
#: located the database through that file would be a backup that stops working the first time
#: the runner is reinstalled, and would announce it at 03:30 into an empty journal.
COMPOSE_PROJECT="${COMPOSE_PROJECT:-vt-platform-prod}"

#: Anything set in the environment wins over the same name in the env file — systemd's
#: `EnvironmentFile` is how the backup's own bucket and key are supplied without putting them in
#: the application's `.env`, and sourcing that file must not overwrite them.
PRESET_BUCKET="${BACKUP_S3_BUCKET:-}"
PRESET_KEY_ID="${BACKUP_S3_ACCESS_KEY_ID:-}"
PRESET_SECRET="${BACKUP_S3_SECRET_ACCESS_KEY:-}"
PRESET_ENDPOINT="${BACKUP_S3_ENDPOINT_URL:-}"
PRESET_PREFIX="${S3_PREFIX:-}"

log() { printf '%s vt-backup: %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }

# Reported to Telegram when configured, so a silent failure needs both this script and the
# notifier to be broken at once rather than just this script.
notify() {
    [ -n "${BACKUP_TELEGRAM_TOKEN:-}" ] && [ -n "${BACKUP_TELEGRAM_CHAT_ID:-}" ] || return 0
    curl -fsS --max-time 15 \
        -d "chat_id=${BACKUP_TELEGRAM_CHAT_ID}" \
        -d "text=$1" \
        "https://api.telegram.org/bot${BACKUP_TELEGRAM_TOKEN}/sendMessage" >/dev/null 2>&1 || true
}

DUMP=""
REMOTE=""
UPLOADED=false

cleanup() {
    status=$?
    # The local copy goes whatever happened: the whole point is that the backup is not on this
    # machine, and a 1–3 GB file left behind on a failure path fills a 50 GB disk in a season.
    # An `if` and not `[ … ] && rm`: under `set -e` a trailing false test is itself a failure,
    # which would rewrite the exit status this handler exists to report.
    if [ -n "$DUMP" ]; then
        rm -f "$DUMP"
    fi

    if [ "$status" -ne 0 ]; then
        # A partial object is worse than no object — it looks like a backup in the listing.
        if [ "$UPLOADED" = true ] && [ -n "$REMOTE" ]; then
            log "removing the incomplete upload at $REMOTE"
            aws_s3 rm "$REMOTE" >/dev/null 2>&1 || log "could not remove $REMOTE — delete it by hand"
        fi
        log "FAILED (exit $status)"
        notify "❌ Бэкап БД не сделан ($(hostname)). Проверьте: journalctl -u vt-backup"
    fi
    exit "$status"
}
trap cleanup EXIT

# --- Configuration --------------------------------------------------------

[ -f "$ENV_FILE" ] || { log "no env file at $ENV_FILE"; exit 1; }
# shellcheck disable=SC1090  # the path is configuration, not a literal.
set -a; . "$ENV_FILE"; set +a

for required in POSTGRES_USER POSTGRES_DB; do
    [ -n "${!required:-}" ] || { log "$required is unset in $ENV_FILE"; exit 1; }
done

# Which bucket the dumps go to, and with whose credentials.
#
# A bucket of its own is the shape worth having, and the reason is the application's key: it can
# delete media, so everything it can reach is destroyable by whatever destroys the application. A
# backup must not be reachable that way. Each part of the connection overrides independently —
# give it only a bucket and it borrows the application's key; give it a key too and the two share
# nothing but a provider.
#
# Falling back to `S3_BUCKET` keeps the single-bucket shape working, and there the dumps take a
# prefix of their own so a lifecycle rule can expire them without touching media. A dedicated
# bucket needs no such namespacing, so the prefix defaults away.
if [ -n "${PRESET_BUCKET:-${BACKUP_S3_BUCKET:-}}" ]; then
    BACKUP_BUCKET="${PRESET_BUCKET:-$BACKUP_S3_BUCKET}"
    S3_PREFIX="${PRESET_PREFIX-}"
else
    BACKUP_BUCKET="${S3_BUCKET:-}"
    S3_PREFIX="${PRESET_PREFIX:-backups/db}"
fi
[ -n "$BACKUP_BUCKET" ] || {
    log "no bucket to write to: set BACKUP_S3_BUCKET (preferred) or S3_BUCKET in $ENV_FILE"
    exit 1
}

# The bucket's own credentials, named as the AWS CLI expects them. Set explicitly rather than
# left to the environment so the CLI cannot silently pick up an instance profile or a stray
# ~/.aws/credentials and write the backup somewhere nobody is looking.
export AWS_ACCESS_KEY_ID="${PRESET_KEY_ID:-${BACKUP_S3_ACCESS_KEY_ID:-${S3_ACCESS_KEY_ID:-}}}"
export AWS_SECRET_ACCESS_KEY="${PRESET_SECRET:-${BACKUP_S3_SECRET_ACCESS_KEY:-${S3_SECRET_ACCESS_KEY:-}}}"
export AWS_DEFAULT_REGION="${BACKUP_S3_REGION:-${S3_REGION:-us-east-1}}"
S3_ENDPOINT_URL="${PRESET_ENDPOINT:-${BACKUP_S3_ENDPOINT_URL:-${S3_ENDPOINT_URL:-}}}"

[ -n "$AWS_ACCESS_KEY_ID" ] && [ -n "$AWS_SECRET_ACCESS_KEY" ] || {
    log "no credentials for the bucket: set BACKUP_S3_ACCESS_KEY_ID/BACKUP_S3_SECRET_ACCESS_KEY"
    exit 1
}

# `aws` if the host has it, otherwise the official image — Docker is already a requirement here
# and an image is one less thing to keep updated on the host. Same command either way.
if command -v aws >/dev/null 2>&1; then
    # shellcheck disable=SC2086  # Unquoted on purpose: `${x:+…}` must expand to two words or none.
    aws_s3() { aws ${S3_ENDPOINT_URL:+--endpoint-url "$S3_ENDPOINT_URL"} s3 "$@"; }
else
    # `BACKUP_DOCKER_ARGS` for the case the endpoint is not reachable from a default bridge
    # network — a MinIO in the stack's own network, say, which then needs `--network`. Empty for
    # a provider's public endpoint, which is the usual shape.
    # shellcheck disable=SC2086  # As above, plus the args are deliberately word-split.
    aws_s3() {
        docker run --rm -i \
            -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY -e AWS_DEFAULT_REGION \
            -v "$WORK_DIR:$WORK_DIR:ro" \
            ${BACKUP_DOCKER_ARGS:-} \
            amazon/aws-cli:latest \
            ${S3_ENDPOINT_URL:+--endpoint-url "$S3_ENDPOINT_URL"} s3 "$@"
    }
fi

# --- The database container ------------------------------------------------

PG_CONTAINER="${POSTGRES_CONTAINER:-}"
if [ -z "$PG_CONTAINER" ]; then
    PG_CONTAINER="$(docker ps -q \
        --filter "label=com.docker.compose.project=$COMPOSE_PROJECT" \
        --filter "label=com.docker.compose.service=postgres" | head -1)"
fi
[ -n "$PG_CONTAINER" ] || {
    log "no running postgres container for project '$COMPOSE_PROJECT'"
    log "set COMPOSE_PROJECT, or name the container with POSTGRES_CONTAINER"
    exit 1
}

pg() { docker exec -i "$PG_CONTAINER" "$@"; }

# --- Dump -----------------------------------------------------------------

mkdir -p "$WORK_DIR"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DUMP="$WORK_DIR/nightly-$STAMP.dump"
# Built in two pieces rather than interpolated in one: an empty prefix in `s3://b/$p/name` leaves
# a double slash, and S3 does not collapse it — the key would literally begin with `/`, and the
# lifecycle rule written against `db/` would never match it.
KEY="vt-$STAMP.dump"
if [ -n "$S3_PREFIX" ]; then
    KEY="${S3_PREFIX%/}/$KEY"
fi
REMOTE="s3://$BACKUP_BUCKET/$KEY"

log "dumping $POSTGRES_DB"
# `-Fc`: the custom format, which is what `pg_restore` wants and what the pre-deploy dumps
# already use. Compressed, and restorable table by table rather than all or nothing.
pg pg_dump -Fc -U "$POSTGRES_USER" "$POSTGRES_DB" >"$DUMP"

SIZE_BYTES="$(stat -c %s "$DUMP")"
# An empty or near-empty archive is a `pg_dump` that failed in a way that still exited 0 —
# no such thing as a 1 KB dump of this database.
[ "$SIZE_BYTES" -gt 4096 ] || { log "dump is only $SIZE_BYTES bytes — refusing to upload it"; exit 1; }
log "dumped $(du -h "$DUMP" | cut -f1)"

# --- Verify ---------------------------------------------------------------

log "verifying the archive is readable"
# Read the table of contents back through the same PostgreSQL that wrote it. Cheap — it reads
# the header, not the data — and it is what separates "the file exists" from "the file restores".
pg pg_restore --list >/dev/null <"$DUMP"

# --- Upload ---------------------------------------------------------------

log "uploading to $REMOTE"
UPLOADED=true
aws_s3 cp "$DUMP" "$REMOTE" --only-show-errors

# The listing is read back rather than trusted: `cp` reporting success and the object being
# absent is exactly the failure a backup script must not sleep through.
REMOTE_BYTES="$(aws_s3 ls "$REMOTE" | awk '{print $3}' | head -1)"
[ -n "$REMOTE_BYTES" ] || { log "uploaded object is not in the listing"; exit 1; }
[ "$REMOTE_BYTES" = "$SIZE_BYTES" ] || {
    log "size mismatch: local $SIZE_BYTES, remote $REMOTE_BYTES"
    exit 1
}

log "OK — $(du -h "$DUMP" | cut -f1) at $REMOTE"
