"""ORM models (adapters) for the Notifications bounded context.

Django models live ONLY here, never in the domain (ARCH-001 §7.2, §14), and
carry NO business logic. A package (not a single module) so models can be split
per aggregate as the context grows. Each context maps to its own PostgreSQL
schema (ARCH-001 §9.2). No models are defined during bootstrap.
"""
