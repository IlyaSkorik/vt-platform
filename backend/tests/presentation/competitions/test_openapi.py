"""OpenAPI schema-generation guard for the Competitions API.

drf-spectacular must be able to build the schema without errors, and every
organizer operation must appear with its stable ``operationId``. This catches
undocumented/undecorated actions and serializer regressions before they reach the
generated frontend client.
"""

from __future__ import annotations

from typing import Any

from drf_spectacular.generators import SchemaGenerator


def _schema() -> Any:
    generator: Any = SchemaGenerator()  # type: ignore[no-untyped-call]
    return generator.get_schema(request=None, public=True)


def test_schema_generates_and_covers_competition_operations() -> None:
    schema = _schema()
    paths = schema["paths"]
    assert isinstance(paths, dict)

    operation_ids = {
        operation["operationId"]
        for path, methods in paths.items()
        if "/competitions" in path
        for method, operation in methods.items()
        if isinstance(operation, dict) and "operationId" in operation
    }

    # A representative slice of each area: CRUD, lifecycle, configuration.
    expected = {
        "createCompetition",
        "listCompetitions",
        "getCompetition",
        "updateCompetition",
        "publishCompetition",
        "openRegistration",
        "archiveCompetition",
        "markCompetitionReady",
        "addCategory",
        "renameCategory",
        "removeCategory",
        "addPricingRule",
        "changePrice",
        "addRegulation",
    }
    missing = expected - operation_ids
    assert not missing, f"OpenAPI is missing operations: {sorted(missing)}"
