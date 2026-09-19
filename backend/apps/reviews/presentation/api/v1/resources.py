"""Projecting Reviews DTOs onto the wire.

One place where a view's JSON shape is decided, so the organizer's payload, the
operator's and the public one cannot drift apart field by field as each view is
edited.

Photographs are rendered as addresses here rather than as stored keys: a key is
this context's private business, and a client that had to assemble a URL from one
would be a client that breaks when the storage moves.
"""

from __future__ import annotations

from typing import Any

from apps.reviews.application.dto import PublicPageView, ReviewPageView, ReviewView
from apps.reviews.presentation.api.v1.files import photo_url

__all__ = ["public_page", "review", "review_page"]


def review_page(view: ReviewPageView) -> dict[str, Any]:
    return {
        "id": view.id,
        "slug": view.slug,
        "title": view.title,
        "intro": view.intro,
        "accepting": view.accepting,
        "reviewCount": view.review_count,
        "createdAt": view.created_at,
        "updatedAt": view.updated_at,
    }


def public_page(view: PublicPageView) -> dict[str, Any]:
    return {
        "slug": view.slug,
        "title": view.title,
        "intro": view.intro,
        "organizationName": view.organization_name,
        "accepting": view.accepting,
        "festivals": [{"id": option.id, "title": option.title} for option in view.festivals],
    }


def review(view: ReviewView) -> dict[str, Any]:
    return {
        "id": view.id,
        "authorName": view.author_name,
        "text": view.text,
        "photos": [url for reference in view.photos if (url := photo_url(reference))],
        "competitionId": view.competition_id,
        "competitionTitle": view.competition_title,
        "submittedAt": view.submitted_at,
        # The consent is shown, not merely stored: an organizer looking at a note
        # that named somebody should be able to see on what basis it is held
        # without opening a database (LEGAL-001 §13.3).
        "consentType": view.consent_code,
        "consentVersion": view.consent_version,
        "consentAcceptedAt": view.consent_accepted_at,
        "organizationId": view.organization_id,
        "organizationName": view.organization_name,
    }
