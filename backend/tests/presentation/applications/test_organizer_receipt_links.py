"""The organizer console's receipt links.

A receipt's stored ``file_reference`` is an opaque storage key, and the console turns
one into an "Открыть квитанцию" link. It used to be handed over raw, with the client
prefixing ``/media/`` — which worked only for as long as the files sat on the API
host's own disk. These pin the reference to whatever the storage says its URL is, so
a receipt keeps opening after the uploads move to a bucket.
"""

from __future__ import annotations

from django.test import override_settings

from apps.applications.presentation.api.v1.organizer.views import _receipt_urls


def test_a_stored_key_comes_out_as_something_a_browser_can_open() -> None:
    assert _receipt_urls(["applications/attachments/abc/receipt.pdf"]) == ["/media/applications/attachments/abc/receipt.pdf"]


@override_settings(MEDIA_URL="https://bucket.example/vt/")
def test_the_link_follows_the_storage_rather_than_the_api_host() -> None:
    """The bucket case, and the whole point: no ``/media/`` on the API host is involved."""
    assert _receipt_urls(["applications/attachments/abc/receipt.pdf"]) == ["https://bucket.example/vt/applications/attachments/abc/receipt.pdf"]


def test_a_reference_minted_before_the_move_is_not_nested_inside_a_second_url() -> None:
    absolute = "https://bucket.example/vt/applications/attachments/abc/receipt.pdf"
    assert _receipt_urls([absolute]) == [absolute]


def test_every_receipt_on_the_order_gets_its_own_link_in_order() -> None:
    """An order settled by several transfers has a slip per transfer; one link would
    hide the rest of the payment from whoever is reconciling it."""
    assert _receipt_urls(["a/one.pdf", "a/two.pdf"]) == ["/media/a/one.pdf", "/media/a/two.pdf"]
