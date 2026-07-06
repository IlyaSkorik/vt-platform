"""Application ports (contracts) required by Finance use cases.

Abstractions the application layer depends on — repositories and gateways such
as UserRepository, EmailGateway, NotificationGateway, Clock, EventBus. Concrete
adapters live in infrastructure/ and are injected at composition time
(ARCH-001 §7.3, Dependency Inversion). Structure only at bootstrap.
"""
