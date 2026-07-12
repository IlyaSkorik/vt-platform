"""Query use cases for the Teacher Directory bounded context.

The **read side**: side-effect-free operations returning DTOs. See
:mod:`apps.teachers.application.queries.teacher_queries`.
"""

from apps.teachers.application.queries.teacher_queries import GetTeacherDirectoryQuery, GetTeacherQuery

__all__ = ["GetTeacherDirectoryQuery", "GetTeacherQuery"]
