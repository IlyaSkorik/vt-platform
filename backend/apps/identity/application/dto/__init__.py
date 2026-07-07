"""Data-transfer objects for the Identity & Access application layer.

Plain, serialization-agnostic input/output shapes for use cases. Result DTOs
(:class:`UserDto`, :class:`OperationResultDto`) are re-exported here as the
package's public surface; see :mod:`apps.identity.application.dto.results`.
"""

from apps.identity.application.dto.results import OperationResultDto, UserDto

__all__ = ["OperationResultDto", "UserDto"]
