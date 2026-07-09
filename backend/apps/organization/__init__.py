"""Organization bounded context (internal back-office).

Owns the platform's single operating organization ("Взлёт талантов") and the
staff privileges granted over it: :class:`StaffMembership` and
:class:`StaffInvitation`. This context is deliberately ignorant of authentication
— it knows a person only by an opaque user id (a UUID). Identity, in turn, knows
nothing about staff. The two communicate only through published read models at
the composition edge (ARCH-001 §14).
"""
