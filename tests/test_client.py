from __future__ import annotations

import io
import json
from typing import Any, Optional
from unittest.mock import patch
from urllib.error import HTTPError

import pytest

from kuti import (
    KutiAuthenticationError,
    KutiClient,
    KutiNotFoundError,
    KutiRateLimitError,
    KutiValidationError,
)

SECRET_KEY = "kuti_test_abc123"


class FakeHTTPResponse:
    def __init__(self, body: Any) -> None:
        self._raw = json.dumps(body).encode("utf-8")

    def read(self) -> bytes:
        return self._raw

    def __enter__(self) -> "FakeHTTPResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None


def http_error(code: int, body: Any, reason: str = "error") -> HTTPError:
    raw = json.dumps(body).encode("utf-8")
    return HTTPError("https://example.test/", code, reason, hdrs=None, fp=io.BytesIO(raw))  # type: ignore[arg-type]


def error_envelope(code: str, message: str) -> dict:
    return {
        "success": False,
        "message": message,
        "error": {"code": code, "message": message, "request_id": "req_test_1"},
    }


def test_rejects_publishable_key() -> None:
    with pytest.raises(ValueError, match="secret key"):
        KutiClient("kuti_pub_test_abc")


def test_sends_bearer_token() -> None:
    captured: dict = {}

    def fake_urlopen(req: Any, timeout: Optional[float] = None) -> FakeHTTPResponse:
        captured["url"] = req.full_url
        captured["headers"] = {k: v for k, v in req.header_items()}
        return FakeHTTPResponse(
            {
                "data": {
                    "id": "pi_1",
                    "merchant_id": "mer_1",
                    "amount": {"amount": "10.00", "currency": "PEN"},
                    "status": "PENDING",
                    "created_at": "2026-01-01T00:00:00Z",
                }
            },
        )

    with patch("kuti.client.urllib.request.urlopen", side_effect=fake_urlopen):
        client = KutiClient(SECRET_KEY, base_url="https://example.test/v1")
        client.payment_intents.retrieve("pi_1")

    assert captured["url"] == "https://example.test/v1/payment-intents/pi_1"
    assert captured["headers"]["Authorization"] == f"Bearer {SECRET_KEY}"


def test_maps_nested_customer_id() -> None:
    def fake_urlopen(req: Any, timeout: Optional[float] = None) -> FakeHTTPResponse:
        return FakeHTTPResponse(
            {
                "data": {
                    "id": "pi_1",
                    "merchant_id": "mer_1",
                    "customer": {
                        "id": "cus_01ABC",
                        "type": "INDIVIDUAL",
                        "name": "María López",
                    },
                    "amount": {"amount": "50.00", "currency": "PEN"},
                    "status": "SUCCEEDED",
                    "paid_with": {
                        "method_type": "INTEROPERABLE_QR",
                        "paid_at": "2026-01-01T00:01:00Z",
                    },
                    "created_at": "2026-01-01T00:00:00Z",
                }
            },
        )

    with patch("kuti.client.urllib.request.urlopen", side_effect=fake_urlopen):
        intent = KutiClient(SECRET_KEY).payment_intents.retrieve("pi_1")

    assert intent.customer_id == "cus_01ABC"
    assert intent.paid_with is not None
    assert intent.paid_with.method_type == "INTEROPERABLE_QR"


def test_maps_401() -> None:
    with patch(
        "kuti.client.urllib.request.urlopen",
        side_effect=http_error(401, error_envelope("INVALID_API_KEY", "Invalid")),
    ):
        with pytest.raises(KutiAuthenticationError):
            KutiClient(SECRET_KEY).payment_intents.retrieve("pi_1")


def test_maps_404_with_code() -> None:
    with patch(
        "kuti.client.urllib.request.urlopen",
        side_effect=http_error(
            404, error_envelope("PAYMENT_INTENT_NOT_FOUND", "Not found")
        ),
    ):
        with pytest.raises(KutiNotFoundError) as exc:
            KutiClient(SECRET_KEY).payment_intents.retrieve("pi_missing")
    assert exc.value.code == "PAYMENT_INTENT_NOT_FOUND"
    assert exc.value.request_id == "req_test_1"


def test_maps_422() -> None:
    with patch(
        "kuti.client.urllib.request.urlopen",
        side_effect=http_error(
            422, error_envelope("VALIDATION_ERROR", "amount is required")
        ),
    ):
        with pytest.raises(KutiValidationError):
            KutiClient(SECRET_KEY).checkout_sessions.create(
                amount={"amount": "", "currency": "PEN"},
                payment_method_types=[],
            )


def test_create_sends_customer_id_only() -> None:
    captured: dict = {}

    def fake_urlopen(req: Any, timeout: Optional[float] = None) -> FakeHTTPResponse:
        captured["body"] = json.loads(req.data.decode("utf-8"))
        return FakeHTTPResponse(
            {
                "data": {
                    "id": "cs_1",
                    "merchant_id": "mer_1",
                    "payment_intent_id": "pi_1",
                    "amount": {"amount": "50.00", "currency": "PEN"},
                    "status": "OPEN",
                    "created_at": "2026-01-01T00:00:00Z",
                }
            },
        )

    with patch("kuti.client.urllib.request.urlopen", side_effect=fake_urlopen):
        KutiClient(SECRET_KEY).checkout_sessions.create(
            amount={"amount": "50.00", "currency": "PEN"},
            payment_method_types=["INTEROPERABLE_QR"],
            customer={"id": "cus_01ABC"},
            idempotency_key="order-1",
        )

    assert captured["body"]["customer"] == {"id": "cus_01ABC"}

    calls = {"n": 0}

    def fake_urlopen(req: Any, timeout: Optional[float] = None):
        calls["n"] += 1
        if calls["n"] == 1:
            raise http_error(429, error_envelope("RATE_LIMITED", "Too many"))
        return FakeHTTPResponse(
            {
                "data": {
                    "id": "pi_1",
                    "merchant_id": "mer_1",
                    "amount": {"amount": "10.00", "currency": "PEN"},
                    "status": "PENDING",
                    "created_at": "2026-01-01T00:00:00Z",
                }
            },
        )

    with patch("kuti.client.time.sleep"):
        with patch("kuti.client.urllib.request.urlopen", side_effect=fake_urlopen):
            intent = KutiClient(SECRET_KEY).payment_intents.retrieve("pi_1")

    assert intent.id == "pi_1"
    assert calls["n"] == 2


def test_does_not_retry_post_without_idempotency() -> None:
    calls = {"n": 0}

    def fake_urlopen(req: Any, timeout: Optional[float] = None):
        calls["n"] += 1
        raise http_error(429, error_envelope("RATE_LIMITED", "Too many"))

    with patch("kuti.client.urllib.request.urlopen", side_effect=fake_urlopen):
        with pytest.raises(KutiRateLimitError):
            KutiClient(SECRET_KEY).checkout_sessions.create(
                amount={"amount": "10.00", "currency": "PEN"},
                payment_method_types=["INTEROPERABLE_QR"],
            )
    assert calls["n"] == 1


def test_retries_post_with_idempotency_key() -> None:
    calls = {"n": 0}
    captured_headers: dict = {}

    def fake_urlopen(req: Any, timeout: Optional[float] = None):
        calls["n"] += 1
        captured_headers.update({k: v for k, v in req.header_items()})
        if calls["n"] == 1:
            raise http_error(429, error_envelope("RATE_LIMITED", "Too many"))
        return FakeHTTPResponse(
            {
                "data": {
                    "id": "cs_1",
                    "merchant_id": "mer_1",
                    "payment_intent_id": "pi_1",
                    "amount": {"amount": "10.00", "currency": "PEN"},
                    "status": "OPEN",
                    "created_at": "2026-01-01T00:00:00Z",
                }
            },
        )

    with patch("kuti.client.time.sleep"):
        with patch("kuti.client.urllib.request.urlopen", side_effect=fake_urlopen):
            session = KutiClient(SECRET_KEY).checkout_sessions.create(
                amount={"amount": "10.00", "currency": "PEN"},
                payment_method_types=["INTEROPERABLE_QR"],
                idempotency_key="order-42",
            )

    assert session.id == "cs_1"
    assert calls["n"] == 2
    headers_lower = {k.lower(): v for k, v in captured_headers.items()}
    assert headers_lower.get("idempotency-key") == "order-42"
