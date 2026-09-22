"""Request/response serializers for the Finance REST API v1.

Request serializers validate shape only — types and lengths the domain would
otherwise have to re-derive from a raw payload. Every *rule* (a sum that is not
positive, a missing purpose, an article that is not on the list) stays in the
domain, so it holds no matter which edge asks.

Response serializers exist so drf-spectacular renders an accurate OpenAPI 3.1
contract (API-000 §25); the views build their bodies from DTOs.
"""

from __future__ import annotations

from drf_spectacular.utils import inline_serializer
from rest_framework import serializers

from apps.finance.domain.value_objects import EXPENSE_NOTE_MAX, EXPENSE_PURPOSE_MAX, ExpenseCategory

__all__ = [
    "EXPENSE_CATEGORIES",
    "AmendExpenseRequestSerializer",
    "ExpenseLedgerResponseSerializer",
    "ExpenseResponseSerializer",
    "FinanceProblemDetailSerializer",
    "RecordExpenseRequestSerializer",
]

#: Every article of spending, read off the domain enum so the console's choice
#: list cannot drift from what the aggregate will actually accept.
EXPENSE_CATEGORIES = tuple(category.value for category in ExpenseCategory)


#: RFC 9457 problem document (API-000 §8).
#:
#: Assembled inline rather than declared as a ``Serializer`` subclass, exactly as
#: Reviews does it: a problem document has a field called ``instance``, and that
#: name already belongs to ``BaseSerializer`` — declaring it as a class attribute
#: is a type error before it is anything else.
FinanceProblemDetailSerializer = inline_serializer(
    name="FinanceProblemDetail",
    fields={
        "type": serializers.URLField(),
        "title": serializers.CharField(),
        "status": serializers.IntegerField(),
        "detail": serializers.CharField(),
        "instance": serializers.CharField(),
        "requestId": serializers.CharField(),
    },
)


class RecordExpenseRequestSerializer(serializers.Serializer[dict[str, object]]):
    """One cost being entered into the platform's books.

    ``amount`` is a string and not a number on purpose: it is money, and a JSON
    number would be parsed as a float somewhere between the form and the column.
    The domain parses it, which is also where "1 200,50" becomes a decimal.

    ``organizationId`` omitted means the platform carried this cost itself. That is
    the ordinary case for infrastructure and is not a missing field.
    """

    amount = serializers.CharField(max_length=32)
    category = serializers.ChoiceField(choices=list(EXPENSE_CATEGORIES))
    purpose = serializers.CharField(max_length=EXPENSE_PURPOSE_MAX)
    spentAt = serializers.DateField()
    organizationId = serializers.UUIDField(required=False, allow_null=True)
    note = serializers.CharField(max_length=EXPENSE_NOTE_MAX, required=False, allow_blank=True)


class AmendExpenseRequestSerializer(serializers.Serializer[dict[str, object]]):
    """A correction. Every field optional; an omitted one is left as it was.

    ``organizationId`` present and ``null`` is the one payload that means something
    rather than nothing: move this cost off the client and onto the platform. The
    view tells the two apart by whether the key was sent at all.
    """

    amount = serializers.CharField(max_length=32, required=False)
    category = serializers.ChoiceField(choices=list(EXPENSE_CATEGORIES), required=False)
    purpose = serializers.CharField(max_length=EXPENSE_PURPOSE_MAX, required=False)
    spentAt = serializers.DateField(required=False)
    organizationId = serializers.UUIDField(required=False, allow_null=True)
    note = serializers.CharField(max_length=EXPENSE_NOTE_MAX, required=False, allow_blank=True)


class _ExpenseSerializer(serializers.Serializer[dict[str, object]]):
    id = serializers.UUIDField()
    # A decimal string, like every other money figure on this console.
    amount = serializers.CharField()
    category = serializers.ChoiceField(choices=list(EXPENSE_CATEGORIES))
    purpose = serializers.CharField()
    spentAt = serializers.DateField()
    note = serializers.CharField(allow_blank=True)
    organizationId = serializers.UUIDField(allow_null=True)
    organizationName = serializers.CharField(allow_null=True)
    createdAt = serializers.DateTimeField()
    updatedAt = serializers.DateTimeField()


class _CategoryTotalSerializer(serializers.Serializer[dict[str, object]]):
    category = serializers.ChoiceField(choices=list(EXPENSE_CATEGORIES))
    amount = serializers.CharField()
    count = serializers.IntegerField()


_meta = inline_serializer(name="FinanceMeta", fields={"requestId": serializers.CharField()})

ExpenseResponseSerializer = inline_serializer(
    name="PlatformExpenseResponse",
    fields={"data": _ExpenseSerializer(), "meta": _meta},
)

ExpenseLedgerResponseSerializer = inline_serializer(
    name="PlatformExpenseLedgerResponse",
    fields={
        "data": inline_serializer(
            name="PlatformExpenseLedger",
            fields={
                "expenses": _ExpenseSerializer(many=True),
                "total": serializers.CharField(),
                "byCategory": _CategoryTotalSerializer(many=True),
                "truncated": serializers.BooleanField(),
            },
        ),
        "meta": _meta,
    },
)
