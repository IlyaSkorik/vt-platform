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


#: Scheme assumed when the configured base omits one. A public verification page
#: is always served over TLS, so this is the safe completion.
_DEFAULT_SCHEME = "https"


def _with_scheme(base: str) -> str:
    """Complete a scheme-less base URL (``vzlettalantov.by`` → ``https://…``).

    A QR payload without a scheme is not a URL — a phone camera shows it as plain
    text, or linkifies the bare host and silently drops the ``/verify/<token>``
    path, so *every* diploma appears to point at the same place. Printed diplomas
    cannot be recalled, so a misconfigured base is corrected here rather than
    trusted.

    Detected on ``://`` rather than by parsing: ``urlsplit`` reads a bare
    ``localhost:5173`` as scheme ``localhost``, which would defeat the check.
    """
    if not base or "://" in base:
        return base
    return f"{_DEFAULT_SCHEME}://{base}"


def verification_url(token: str) -> str:
    """``https://<configured domain>/verify/<token>`` for a diploma's token."""
    base = _with_scheme(str(settings.DIPLOMA_VERIFICATION_BASE_URL).strip()).rstrip("/")
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
