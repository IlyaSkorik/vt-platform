"""Gunicorn configuration (OPS-008 §4).

The numbers here are the ones that document measured — they are not a template. The image's
``CMD`` points at this file rather than passing flags inline so the sizing lives in one place,
which is what OPS-008 §4 asks for.

Two values are read from the environment because OPS-008 §2 gives a different figure for the
smaller box (2 vCPU / 6 GB) than for the comfortable one (4 vCPU / 8 GB), and a single image
has to serve both.
"""

from __future__ import annotations

import os

bind = "0.0.0.0:8000"

# ASGI: Django's sync views run in a thread pool inside each worker, so processes are for CPU
# parallelism and the pool absorbs concurrency. Three workers on 4 vCPU leaves a core for
# PostgreSQL; nine would only take RAM away from it. Drop to 2 on the 2 vCPU box.
worker_class = "uvicorn.workers.UvicornWorker"
workers = int(os.environ.get("GUNICORN_WORKERS", "3"))

# reportlab and pypdf hold on to memory across a big print run. Recycling workers keeps a
# long-lived process from growing indefinitely; the jitter avoids all of them restarting at once.
#
# Configurable because the number is sized for ordinary traffic, and a live programme is not
# that: every open screen in the hall polls the public endpoint every few seconds, so a few
# hundred viewers spend this budget in under a minute and the workers spend the event
# recycling instead of answering. Raise it for the day (`GUNICORN_MAX_REQUESTS=50000`) and
# the leak this guards against — a print run, which nobody starts mid-festival — is simply
# not happening meanwhile.
max_requests = int(os.environ.get("GUNICORN_MAX_REQUESTS", "1000"))
max_requests_jitter = int(os.environ.get("GUNICORN_MAX_REQUESTS_JITTER", "100"))

timeout = 120  # a large synchronous PDF export must not be killed mid-render
graceful_timeout = 30
keepalive = 5

accesslog = "-"
errorlog = "-"

# nginx terminates TLS, so the real scheme arrives in a header — and gunicorn only honours
# that header from an address it trusts. OPS-008 §7 assumes nginx on the same host
# (127.0.0.1); under Compose it is a separate container with an address the bridge network
# assigns, so the trusted set has to be configurable.
#
# This is load-bearing, not hygiene: `production.py` sets both `SECURE_PROXY_SSL_HEADER` and
# `SECURE_SSL_REDIRECT`, so if `X-Forwarded-Proto` is dropped, Django concludes every request
# is plain HTTP and redirects it to HTTPS — forever. Widening the trust is safe only because
# the backend port is never published; nginx is the only thing that can reach it.
forwarded_allow_ips = os.environ.get("GUNICORN_FORWARDED_ALLOW_IPS", "127.0.0.1")
