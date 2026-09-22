from __future__ import annotations

import hashlib
import hmac
import time

import pytest

from kuti import KutiSignatureVerificationError, verify_webhook_signature

SECRET = "whsec_test_1234567890"


def sign(secret: str, timestamp_seconds: int, body: str) -> str:
    digest = hmac.new(
        secret.encode(),
        f"{timestamp_seconds}.{body}".encode(),
        hashlib.sha256,
    ).hexdigest()
    return f"v1={digest}"


def test_accepts_valid_signature() -> None:
    body = '{"type":"payment.succeeded","id":"evt_1"}'
    now = int(time.time())
    verify_webhook_signature(body, sign(SECRET, now, body), str(now), SECRET)


def test_rejects_wrong_secret() -> None:
    body = "{}"
    now = int(time.time())
    with pytest.raises(KutiSignatureVerificationError):
        verify_webhook_signature(body, sign("wrong", now, body), str(now), SECRET)


def test_rejects_tampered_body() -> None:
    now = int(time.time())
    signature = sign(SECRET, now, '{"amount":"10.00"}')
    with pytest.raises(KutiSignatureVerificationError):
        verify_webhook_signature('{"amount":"999.00"}', signature, str(now), SECRET)


def test_rejects_stale_timestamp() -> None:
    body = "{}"
    stale = int(time.time()) - 3600
    with pytest.raises(KutiSignatureVerificationError):
        verify_webhook_signature(body, sign(SECRET, stale, body), str(stale), SECRET)


def test_accepts_stale_with_wide_tolerance() -> None:
    body = "{}"
    stale = int(time.time()) - 3600
    verify_webhook_signature(
        body, sign(SECRET, stale, body), str(stale), SECRET, tolerance_seconds=7200
    )


def test_rejects_malformed_header() -> None:
    with pytest.raises(KutiSignatureVerificationError):
        verify_webhook_signature(
            "{}", "not-a-valid-signature", str(int(time.time())), SECRET
        )
