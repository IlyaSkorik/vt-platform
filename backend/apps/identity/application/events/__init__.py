"""Application-layer event handling for the Identity & Access bounded context.

Consumers of the domain events that command handlers return: side-effect handlers
(:mod:`apps.identity.application.events.handlers`) and their public surface. These
are framework-free orchestrators over the application ports — the outbound half of
the use-case pipeline (ARCH-001 §4.8).
"""

from apps.identity.application.events.handlers import SendVerificationEmailOnUserRegistered

__all__ = ["SendVerificationEmailOnUserRegistered"]
