from __future__ import annotations

import io
import json
from typing import Any, Dict, Optional
from unittest.mock import patch
from urllib.error import HTTPError

import pytest

from kuti import (
    CustomerInput,
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


def test_create_payment_intent_sends_customer_and_idempotency_key() -> None:
    captured: dict[str, Any] = {}

    def fake_urlopen(req: Any, timeout: Optional[float] = None):
        captured["url"] = req.full_url
        captured["body"] = json.loads(req.data.decode("utf-8"))
        captured["headers"] = {k: v for k, v in req.header_items()}
        return FakeHTTPResponse(
            {
                "data": {
                    "id": "pi_created",
                    "merchant_id": "mer_1",
                    "customer": {"id": "cus_1"},
                    "amount": {"amount": "50.00", "currency": "PEN"},
                    "status": "PENDING",
                    "checkout_url": "https://pay.kuti.pe/c/ABC",
                    "created_at": "2026-01-01T00:00:00Z",
                }
            }
        )

    with patch("kuti.client.urllib.request.urlopen", side_effect=fake_urlopen):
        intent = KutiClient(SECRET_KEY, base_url="https://example.test/v1").payment_intents.create(
            amount={"amount": "50.00", "currency": "PEN"},
            payment_method_types=["INTEROPERABLE_QR", "BANK_TRANSFER"],
            customer={
                "type": "INDIVIDUAL",
                "first_name": "María",
                "last_name": "López",
                "email": "maria@example.com",
                "document": {"type": "DNI", "number": "45678912"},
            },
            description="Pedido #1042",
            idempotency_key="order-1042",
        )

    assert intent.id == "pi_created"
    assert intent.customer_id == "cus_1"
    assert captured["url"].endswith("/payment-intents")
    headers_lower = {k.lower(): v for k, v in captured["headers"].items()}
    assert headers_lower.get("idempotency-key") == "order-1042"
    assert captured["body"]["customer"]["first_name"] == "María"
    assert captured["body"]["customer"]["document"] == {"type": "DNI", "number": "45678912"}


def test_create_customer_with_document_and_custom_fields() -> None:
    captured: Dict[str, Any] = {}

    def fake_urlopen(req: Any, timeout: Optional[float] = None) -> FakeHTTPResponse:
        captured["url"] = req.full_url
        captured["method"] = req.get_method()
        captured["body"] = json.loads(req.data.decode("utf-8"))
        return FakeHTTPResponse(
            {
                "data": {
                    "id": "cus_new",
                    "merchant_id": "mer_1",
                    "type": "INDIVIDUAL",
                    "first_name": "María",
                    "document": {"type": "DNI", "number": "45678912", "country": "PE"},
                    "custom_fields": {"grade": "quinto"},
                    "created_at": "2026-01-01T00:00:00Z",
                }
            }
        )

    with patch("kuti.client.urllib.request.urlopen", side_effect=fake_urlopen):
        customer = KutiClient(SECRET_KEY, base_url="https://example.test/v1").customers.create(
            CustomerInput(
                type="INDIVIDUAL",
                first_name="María",
                last_name="López",
                document={"number": "45678912"},
                custom_fields={"grade": "5to grado"},
            )
        )

    assert customer.id == "cus_new"
    assert customer.custom_fields == {"grade": "quinto"}
    assert customer.document == {"type": "DNI", "number": "45678912", "country": "PE"}
    assert captured["url"].endswith("/customers")
    assert captured["method"] == "POST"
    assert captured["body"]["document"] == {"number": "45678912"}
    assert captured["body"]["custom_fields"] == {"grade": "5to grado"}
    assert "id" not in captured["body"]


def test_update_customer_sends_only_given_fields_and_none_removes_a_value() -> None:
    captured: Dict[str, Any] = {}

    def fake_urlopen(req: Any, timeout: Optional[float] = None) -> FakeHTTPResponse:
        captured["method"] = req.get_method()
        captured["body"] = json.loads(req.data.decode("utf-8"))
        return FakeHTTPResponse(
            {
                "data": {
                    "id": "cus_1",
                    "merchant_id": "mer_1",
                    "type": "INDIVIDUAL",
                    "custom_fields": {"grade": "sexto"},
                    "created_at": "2026-01-01T00:00:00Z",
                }
            }
        )

    with patch("kuti.client.urllib.request.urlopen", side_effect=fake_urlopen):
        KutiClient(SECRET_KEY, base_url="https://example.test/v1").customers.update(
            "cus_1", custom_fields={"grade": "sexto", "birth_date": None}
        )

    assert captured["method"] == "PATCH"
    assert captured["body"] == {"custom_fields": {"grade": "sexto", "birth_date": None}}
