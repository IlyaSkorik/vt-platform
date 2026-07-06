"""Domain <-> persistence mappers for the Judging bounded context.

Translate between framework-free domain objects and Django ORM models, keeping
the domain ignorant of persistence (ARCH-001 §4.1, §7.2). Structure only at bootstrap.
"""
