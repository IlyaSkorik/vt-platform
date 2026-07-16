"""URL routes for the Teacher Directory API endpoints.

Noun-resource paths only (API-000 §3.3): archiving *creates* an archival
sub-resource, reactivating *creates* a reactivation. Mounted under ``/api/v1/`` by
:mod:`apps.teachers.presentation.urls`.
"""

from __future__ import annotations

from django.urls import path

from apps.teachers.presentation.api.v1.teachers.views import (
    TeacherArchivalView,
    TeacherCollectionView,
    TeacherDetailView,
    TeacherReactivationView,
)

app_name = "teachers"

urlpatterns = [
    path("teachers", TeacherCollectionView.as_view(), name="collection"),
    path("teachers/<str:teacher_id>", TeacherDetailView.as_view(), name="detail"),
    path("teachers/<str:teacher_id>/archival", TeacherArchivalView.as_view(), name="archival"),
    path("teachers/<str:teacher_id>/reactivation", TeacherReactivationView.as_view(), name="reactivation"),
]
