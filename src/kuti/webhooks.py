from __future__ import annotations

import hashlib
import hmac
import time

from .errors import KutiSignatureVerificationError

_SIGNATURE_PREFIX = "v1="
_DEFAULT_TOLERANCE_SECONDS = 300


def verify_webhook_signature(
    payload: str | bytes,
    signature_header: str,
    timestamp_header: str,
    secret: str,
    tolerance_seconds: int = _DEFAULT_TOLERANCE_SECONDS,
) -> None:
    """Verifica la firma de un webhook de KUTI.

    Recomputa ``HMAC_SHA256(secret, "<timestamp>.<body>")`` con el *payload* crudo
    (el string exacto del body, SIN parsear a JSON primero) y lo compara en tiempo
    constante contra el header ``X-Kuti-Signature``. También rechaza timestamps
    viejos para evitar ataques de replay.

    :raises KutiSignatureVerificationError: si la firma no coincide o el timestamp
        está fuera de tolerancia.
    """
    if not signature_header.startswith(_SIGNATURE_PREFIX):
        raise KutiSignatureVerificationError(
            "Unexpected signature format (expected v1=<hex>)."
        )

    try:
        timestamp_seconds = int(timestamp_header)
    except (TypeError, ValueError) as exc:
        raise KutiSignatureVerificationError("Invalid timestamp header.") from exc

    now = int(time.time())
    if abs(now - timestamp_seconds) > tolerance_seconds:
        raise KutiSignatureVerificationError(
            "Timestamp outside of tolerance — possible replay attack, "
            "or your clock is out of sync."
        )

    body = payload if isinstance(payload, str) else payload.decode("utf-8")
    expected = _compute_signature(secret, timestamp_seconds, body)
    received = signature_header[len(_SIGNATURE_PREFIX) :]

    if not hmac.compare_digest(expected, received):
        raise KutiSignatureVerificationError("Signature mismatch.")


def _compute_signature(secret: str, timestamp_seconds: int, body: str) -> str:
    signed = f"{timestamp_seconds}.{body}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
