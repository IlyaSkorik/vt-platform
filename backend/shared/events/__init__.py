"""Shared domain-event infrastructure.

Event base contract, the transactional outbox, and the dispatcher that relays
events to Redis/Celery (ARCH-001 §4.8, §7.4). Business events themselves live
in each context's domain/events.py. Structure only at bootstrap.
"""
