# OPS-007 — Object storage for uploads and generated documents

**Status:** Active · **Applies to:** every deployed environment

Uploads (posters, landing images, regulations, competition documents, application
attachments, payment receipts) and generated documents (diplomas, thank-you letters and
their ZIP archives) live in an S3 bucket. Locally and in the test suite they stay on the
filesystem under `backend/media/` — nothing else differs, and no code branches on it.

## How the switch works

Everything is written through Django's `default_storage`, and every stored reference is
whatever that storage says the file's URL is. So the whole platform moves on one setting:

```
S3_BUCKET=vt-platform-media          # set this and the platform is on S3
S3_REGION=ru-central1
S3_ENDPOINT_URL=https://storage.yandexcloud.net   # required for anything that is not AWS
S3_ACCESS_KEY_ID=…
S3_SECRET_ACCESS_KEY=…
S3_CUSTOM_DOMAIN=cdn.example.com     # optional: a CDN or vanity host, no scheme
S3_LOCATION=prod                     # optional: key prefix, so one bucket can hold several envs
```

Leave `S3_BUCKET` empty and the filesystem backend stays in place. There is no third mode
and no per-file choice.

References already in the database keep the shape they were stored with. Switching does
**not** migrate anything: files written before the switch stay where they were written, and
their `/media/…` references keep resolving as long as that path is still served.

## Bucket configuration

### 1. Public read (required)

The bucket is **public-read** by policy. Objects carry no ACL, because several providers
disable object ACLs outright.

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": "*",
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::vt-platform-media/*"
  }]
}
```

Confidentiality rests on the **key**, not on the bucket. A diploma's natural key is public
on both halves — the competition id appears in public URLs, the diploma number increments —
so diploma and document keys carry an unguessable segment derived from `SECRET_KEY`
(`apps/diplomas/infrastructure/pdf/workspace.py`). Without it the whole registry could be
walked by counting numbers up from one.

Two consequences worth stating plainly:

- A leaked URL stays valid forever. There is no expiry to save you.
- Rotating `SECRET_KEY` changes where *future* documents are written. Already-issued ones
  keep working: their reference is stored in the database and the object is untouched.

### 2. CORS (required — the diploma constructor breaks without it)

The template constructor renders the backing PDF with `react-pdf`, which **fetches the file
from JavaScript**. A bucket without CORS fails that fetch, and the constructor shows "Не
удалось загрузить PDF" while every other part of the platform looks fine.

```json
[{
  "AllowedOrigins": ["https://app.example.com"],
  "AllowedMethods": ["GET", "HEAD"],
  "AllowedHeaders": ["*"],
  "MaxAgeSeconds": 3600
}]
```

### 3. Versioning (recommended)

The database is backed up with `pg_dump`; the bucket is not covered by that. Object
versioning is what makes an accidental delete or an overwritten template recoverable.

## Caching

Objects are written with `Cache-Control: public, max-age=31536000, immutable`. That is safe
because a key's content never changes meaning: a replaced poster is written under a new
key, and a regenerated diploma lands on the same key with the same content for the same
inputs. It is also what makes a CDN in front of the bucket worth having — set
`S3_CUSTOM_DOMAIN` to it.

## What the server no longer needs

With media in a bucket, a single-server deployment needs roughly **40–60 GB** of disk
rather than 100–160: only the database, WAL and temporary files. Backups simplify to
`pg_dump` off the box plus bucket versioning — and losing the server's disk no longer
loses the diplomas.

Celery is the one place to watch: the print-package job now uploads over the network
instead of writing to disk. Keep `--max-tasks-per-child` and the task time limits generous,
and rely on boto3's retries for the occasional `503` from the provider.
