from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict
from urllib.parse import quote

from ..types import PaidWith, PaymentIntent, money_from_api, payment_method_from_api

if TYPE_CHECKING:
    from ..client import KutiClient


class PaymentIntentsResource:
    def __init__(self, client: KutiClient) -> None:
        self._client = client

    def retrieve(self, payment_intent_id: str) -> PaymentIntent:
        """Consulta el estado real de un cobro.

        Es la fuente de verdad — nunca confíes solo en un callback del frontend
        (``onSuccess`` de Checkout.js). Verifica ``status == "SUCCEEDED"`` aquí
        antes de entregar un producto o servicio.
        """
        response = self._client.request(
            "GET",
            f"/payment-intents/{quote(payment_intent_id, safe='')}",
        )
        return _from_api(response["data"])


def _from_api(dto: Dict[str, Any]) -> PaymentIntent:
    customer = dto.get("customer") or {}
    customer_id = customer.get("id") if isinstance(customer, dict) else None
    if customer_id is None:
        customer_id = dto.get("customer_id")

    paid_raw = dto.get("paid_with")
    paid_with = None
    if paid_raw:
        paid_with = PaidWith(
            method_type=paid_raw.get("method_type"),
            paid_at=paid_raw.get("paid_at"),
        )

    return PaymentIntent(
        id=dto["id"],
        merchant_id=dto["merchant_id"],
        livemode=dto.get("livemode"),
        customer_id=customer_id,
        amount=money_from_api(dto["amount"]),
        status=dto["status"],
        payment_method_types=dto.get("payment_method_types"),
        payment_method=payment_method_from_api(dto.get("payment_method")),
        paid_with=paid_with,
        checkout_url=dto.get("checkout_url"),
        expires_at=dto.get("expires_at"),
        external_reference=dto.get("external_reference"),
        description=dto.get("description"),
        category_id=dto.get("category_id"),
        metadata=dto.get("metadata"),
        requires_customer_info=dto.get("requires_customer_info"),
        created_at=dto["created_at"],
    )
