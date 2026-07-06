"""ORM models (adapters) for the Finance bounded context.

Django models live ONLY here, never in the domain (ARCH-001 §7.2, §14).
They carry NO business logic. Each context maps to its own PostgreSQL
schema (ARCH-001 §9.2). No models are defined during bootstrap.
"""
