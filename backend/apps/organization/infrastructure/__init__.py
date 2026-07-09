"""Infrastructure layer for the Organization bounded context.

Concrete adapters for the application ports (ARCH-001 §7.3): Django ORM models,
mappers (anti-corruption layer between aggregates and rows), repositories,
system adapters (clock, uuid), and messaging (token hasher, event dispatch).
Only this layer touches Django/DRF/the ORM.
"""
