# OPS-009 — Mail provider quotas and how the platform stays inside them

**Status:** Active · **Applies to:** every environment with a real SMTP provider

The hosting agreement caps what one mailbox may do (§5 of the contract). Every cap fails the
same way: the provider throttles, refuses, or files the message as bulk mail, and the
platform hears nothing useful — a participant simply never receives their letter. So the
limits are enforced on the way out, in `apps/notifications`, rather than trusted to be
comfortably far away.

## The contract, and what the platform does about it

| § | Limit | Enforcement |
|---|---|---|
| 5.3.6 | **30 outgoing messages per minute per mailbox** | Counted in the shared cache per envelope sender. Over the allowance, the delivery task comes back when the window resets. |
| 5.3.4 | **50 recipients per message** (To + Cc + Bcc) | Checked before queueing; refused synchronously so the caller sees it. |
| 5.3.1 | **100 MB per message** | Checked on the assembled MIME payload, not on the attachment bytes — encoding inflates them by about a third. |
| 5.7 | 10 failed logins per minute, after which only the last successful IP may connect | Authentication failures are **never retried**. A worker hammering a wrong password would lock the platform out of its own mailbox. |
| 5.4, 5.6 | 10 simultaneous sessions per mailbox | One worker at `--concurrency 1` (OPS-008) uses one. Nothing to configure. |
| 5.3.2, 5.3.3 | 100 GB and 1 000 000 messages per mailbox | Nothing to enforce: the platform sends and does not keep a copy. Worth watching if a mailbox is ever used to receive. |
| 5.8 | The provider filters outbound bulk mail | The reason the rate limiter exists at all rather than only a retry-on-failure. |

Settings, all with the contract's numbers as defaults:

```
EMAIL_RATE_LIMIT_PER_MINUTE=30    # 0 disables the limiter (what the test suite runs on)
EMAIL_MAX_RECIPIENTS=50
EMAIL_MAX_BYTES=104857600
```

## Two mailboxes

The allowance is counted **per mailbox**, so a second address is the cheapest headroom there
is. The platform sends on two channels:

```
EMAIL_DEFAULT_FROM=no-reply@vzlettalantov.by   # priority
EMAIL_BULK_FROM=news@vzlettalantov.by          # bulk; empty = use the one above
```

**The split is about what happens under load, not about importance.** The question for each
letter is: *is somebody waiting to proceed?*

| Channel | Letters | Why |
|---|---|---|
| `send_priority` → `EMAIL_DEFAULT_FROM` | email verification, password reset, staff invitation, "оплатите до …" | Each carries a link or a deadline somebody is blocked on. Late is as good as never. |
| `send_bulk` → `EMAIL_BULK_FROM` | submission receipts, an organizer's review outcomes (accepted / rejected / returned), auto-cancellation notices | Arrive by the hundred, predictable, nobody is watching their inbox for one. |

The two-part reasoning matters, because either half alone leaves the problem in place:

1. **Two mailboxes double the send rate.** A registration rush spends the bulk mailbox's 30
   a minute and the priority one is still untouched — there is a test for exactly that.
2. **A priority on the task reorders the queue.** Two mailboxes do nothing about ordering: one
   queue means a password reset still waits behind five hundred receipts. Redis has no native
   priorities, so Celery emulates them with one list per step, which is why
   `CELERY_BROKER_TRANSPORT_OPTIONS` declares `priority_steps` — without that declaration a
   priority is silently ignored.

Both mailboxes must exist at the provider and both must be able to send. Nothing checks that
at boot: a `EMAIL_BULK_FROM` the provider does not know will authenticate fine (the SMTP login
is one account) and then bounce, or be rejected as a forged sender under SPF/DKIM. Send one
test message through each channel after configuring them.

## Why delivery is queued

Sending used to happen in the request. That is fine for one verification letter and wrong for
everything else: an organizer returning eighty applications for correction is one click and
eighty messages in a few seconds — three times the minute's allowance, and exactly the shape
the provider's bulk filter looks for. It also made the organizer wait for eighty SMTP
round-trips.

Now every context composes its message and hands it to `send_transactional`, which validates
it and queues one Celery task per message. The queue is where the allowance is counted, and
where a refusal is something to come back from rather than an error in somebody's request.

The trade is honest and worth stating: if Redis or the worker is down, mail stops going out
silently, where before a failure surfaced in the request. That is what makes the worker part
of the monitored surface, not an optional extra.

## Things that will bite

- **The window is fixed, not sliding.** A burst that straddles a minute boundary can in
  principle exceed 30 in a rolling 60 seconds. Deliberate: the recovery is the same retry
  that covers any refusal, and real traffic does not sit at the cap. If the provider ever
  starts rejecting on that, lower `EMAIL_RATE_LIMIT_PER_MINUTE` to 25 rather than building a
  sliding window.
- **Attachments are refused, not dropped.** Nothing in the platform emails attachments —
  documents are linked so they stay behind their own access rules and out of a 100 MB limit.
  Queueing one would also put megabytes in Redis. If that has to change, put the bytes in
  storage and the link in the body.
- **A wrong password is a hard stop.** `SMTPAuthenticationError` is logged at exception level
  and the task gives up. If mail stops entirely after a credentials change, that log line is
  the first place to look — and check whether §5.7 has already pinned the mailbox to another
  IP.
- **Two mailboxes are the limit of what this buys for free.** The quota is per envelope
  sender and the tariff allows 10 domains × 1 000 mailboxes, so a third channel is possible
  — but each one needs its own SPF/DKIM story and its own reputation, and a platform sending
  from five addresses looks worse to a receiving spam filter than one sending from two.
- **Both channels share one worker.** The priority reorders the queue; it does not add
  capacity. If bulk volume ever grows enough to keep the worker permanently busy, the answer
  is a second worker on its own queue (OPS-008 §5), not a third mailbox.
