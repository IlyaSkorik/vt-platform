"""Repository implementations for the Analytics bounded context.

ORM-backed adapters implementing the ports in application/interfaces.py and
domain/interfaces.py (ARCH-001 §7.2) — the only gateway between aggregates and
persistence. A package so repositories can be split per aggregate. Structure only.
"""
