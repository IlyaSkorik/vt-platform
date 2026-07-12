"""Data-transfer objects for the Teacher Directory application layer.

Plain, serialization-agnostic output shapes for use cases. See
:mod:`apps.teachers.application.dto.results`.
"""

from apps.teachers.application.dto.results import OperationResultDto, TeacherDto

__all__ = ["OperationResultDto", "TeacherDto"]
