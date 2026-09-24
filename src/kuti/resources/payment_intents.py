from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union
from urllib.parse import quote, urlencode

from ..types import (
    Money,
    PaidWith,
    PaymentIntent,
    PaymentIntentCustomer,
    PaymentMethodType,
    customer_input_from,
    customer_input_to_api,
    RequestOptions,
    money_from_api,
    payment_method_from_api,
)

if TYPE_CHECKING:
    from ..client import KutiClient


class PaymentIntentsResource:
    def __init__(self, client: KutiClient) -> None:
        self._client = client

    def create(
        self,
        *,
        amount: Union[Money, Dict[str, str]],
        payment_method_types: List[PaymentMethodType],
        customer: Optional[Union[PaymentIntentCustomer, Dict[str, Any]]] = None,
        receivable_id: Optional[str] = None,
        category_id: Optional[str] = None,
        requires_customer_info: Optional[bool] = None,
        description: Optional[str] = None,
        external_reference: Optional[str] = None,
        expires_at: Optional[str] = None,
        merchant_id: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        idempotency_key: Optional[str] = None,
    ) -> PaymentIntent:
        """POST /payment-intents — QR, bank code, checkout_url."""
        money = (
            amount
            if isinstance(amount, Money)
            else Money(amount=str(amount["amount"]), currency=str(amount["currency"]))
        )
        cust = customer_input_to_api(customer_input_from(customer))

        body: Dict[str, Any] = {
            "amount": {"amount": money.amount, "currency": money.currency},
            "payment_method_types": list(payment_method_types),
        }
        if cust is not None:
            body["customer"] = cust
        if receivable_id is not None:
            body["receivable_id"] = receivable_id
        if category_id is not None:
            body["category_id"] = category_id
        if requires_customer_info is not None:
            body["requires_customer_info"] = requires_customer_info
        if description is not None:
            body["description"] = description
        if external_reference is not None:
            body["external_reference"] = external_reference
        if expires_at is not None:
            body["expires_at"] = expires_at
        if merchant_id is not None:
            body["merchant_id"] = merchant_id
        if metadata is not None:
            body["metadata"] = metadata

        opts = RequestOptions(idempotency_key=idempotency_key) if idempotency_key else None
        response = self._client.request("POST", "/payment-intents", body, opts)
        return _from_api(response["data"])

    def list(
        self,
        *,
        status: Optional[str] = None,
        q: Optional[str] = None,
        customer_id: Optional[str] = None,
        created_from: Optional[str] = None,
        created_to: Optional[str] = None,
        page: Optional[int] = None,
        per_page: Optional[Union[int, str]] = None,
    ) -> Dict[str, Any]:
        """GET /payment-intents — returns ``{"data": [...], "pagination": {...}}``."""
        query: Dict[str, str] = {}
        if status is not None:
            query["status"] = status
        if q is not None:
            query["q"] = q
        if customer_id is not None:
            query["customer_id"] = customer_id
        if created_from is not None:
            query["created_from"] = created_from
        if created_to is not None:
            query["created_to"] = created_to
        if page is not None:
            query["page"] = str(page)
        if per_page is not None:
            query["per_page"] = str(per_page)
        path = "/payment-intents"
        if query:
            path = f"{path}?{urlencode(query)}"
        response = self._client.request("GET", path)
        rows = [_from_api(row) for row in (response.get("data") or [])]
        p = response.get("pagination") or {}
        return {
            "data": rows,
            "pagination": {
                "page": p.get("page", 1),
                "per_page": p.get("per_page", len(rows)),
                "total": p.get("total", len(rows)),
                "total_pages": p.get("total_pages", 1),
                "has_more": p.get("has_more", False),
            },
        }

    def retrieve(self, payment_intent_id: str) -> PaymentIntent:
        """GET /payment-intents/:id"""
        response = self._client.request(
            "GET",
            f"/payment-intents/{quote(payment_intent_id, safe='')}",
        )
        return _from_api(response["data"])

    def cancel(self, payment_intent_id: str) -> PaymentIntent:
        """POST /payment-intents/:id/cancel"""
        response = self._client.request(
            "POST",
            f"/payment-intents/{quote(payment_intent_id, safe='')}/cancel",
        )
        return _from_api(response["data"])

    def send_whatsapp(
        self,
        payment_intent_id: str,
        *,
        phone: Optional[str] = None,
        customer_name: Optional[str] = None,
    ) -> None:
        """POST /payment-intents/:id/send-whatsapp — 204 on success."""
        body: Dict[str, Any] = {}
        if phone is not None:
            body["phone"] = phone
        if customer_name is not None:
            body["customer_name"] = customer_name
        self._client.request(
            "POST",
            f"/payment-intents/{quote(payment_intent_id, safe='')}/send-whatsapp",
            body,
        )


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
        customer=customer if isinstance(customer, dict) and customer else None,
    )
