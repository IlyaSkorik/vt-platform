"""Data-transfer objects for the Participants application layer.

Plain, serialization-agnostic input/output shapes for use cases. Result DTOs
(:class:`ParticipantDto`, :class:`GuardianLinkDto`, :class:`OperationResultDto`)
are re-exported here as the package's public surface; see
:mod:`apps.participants.application.dto.results`.
"""

from apps.participants.application.dto.results import (
    GuardianLinkDto,
    OperationResultDto,
    ParticipantDto,
)

__all__ = ["GuardianLinkDto", "OperationResultDto", "ParticipantDto"]
