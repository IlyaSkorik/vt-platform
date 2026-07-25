"""QR code generation for a diploma's verification link.

Produces a PNG entirely in memory (no temporary files) with the ``qrcode``
library, ready for reportlab's ``drawImage``. Deterministic: the same URL always
yields the same bytes, which is what lets a test compare an embedded QR against a
freshly generated one module by module.

Also builds the verification URL itself. The public domain is **configuration**
(``DIPLOMA_VERIFICATION_BASE_URL``, defaulting to the frontend base URL) — never
hardcoded — because it differs per environment.
"""

from __future__ import annotations

from io import BytesIO

import qrcode
from django.conf import settings

__all__ = ["QR_BORDER", "QR_BOX_SIZE", "qr_png", "verification_url"]

#: Pixels per QR module in the generated PNG. High enough that print output stays
#: crisp, small enough to keep the embedded image a few kilobytes.
QR_BOX_SIZE = 8

#: Quiet-zone width in modules. The QR spec asks for 4; the block already sits in
#: whitespace on the diploma, so 2 keeps the code readable without wasting area.
QR_BORDER = 2

#: Path of the public verification page the QR points at.
_VERIFY_PATH = "verify"


def verification_url(token: str) -> str:
    """``https://<configured domain>/verify/<token>`` for a diploma's token."""
    base = str(settings.DIPLOMA_VERIFICATION_BASE_URL).rstrip("/")
    return f"{base}/{_VERIFY_PATH}/{token}"


def qr_png(data: str) -> bytes:
    """PNG bytes of the QR code encoding ``data``.

    Error correction ``M`` (~15% recoverable) — the usual choice for printed codes
    that may be scuffed or folded.
    """
    code = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=QR_BOX_SIZE,
        border=QR_BORDER,
    )
    code.add_data(data)
    code.make(fit=True)
    buffer = BytesIO()
    code.make_image(fill_color="black", back_color="white").save(buffer, format="PNG")
    return buffer.getvalue()
