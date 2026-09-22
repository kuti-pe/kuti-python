from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union
from urllib.parse import quote

from ..types import (
    Money,
    PaidWith,
    PaymentIntent,
    PaymentIntentCustomer,
    PaymentMethodType,
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
        customer_id: Optional[str] = None,
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
        """Crea un payment intent (cobro).

        Devuelve QR, código de pago de servicios y ``checkout_url``.
        El monto SIEMPRE debe resolverse en tu backend. Pasa ``idempotency_key``
        para no duplicar el cobro al reintentar.
        """
        money = (
            amount
            if isinstance(amount, Money)
            else Money(amount=str(amount["amount"]), currency=str(amount["currency"]))
        )
        cust_obj = _normalize_customer(customer)

        body: Dict[str, Any] = {
            "amount": {"amount": money.amount, "currency": money.currency},
            "payment_method_types": list(payment_method_types),
        }
        if cust_obj is not None:
            body["customer"] = _customer_to_api(cust_obj)
        if customer_id is not None:
            body["customer_id"] = customer_id
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


def _normalize_customer(
    customer: Optional[Union[PaymentIntentCustomer, Dict[str, Any]]],
) -> Optional[PaymentIntentCustomer]:
    if customer is None:
        return None
    if isinstance(customer, PaymentIntentCustomer):
        return customer
    return PaymentIntentCustomer(
        id=customer.get("id"),
        type=customer.get("type"),
        given_name=customer.get("given_name"),
        family_name=customer.get("family_name"),
        legal_name=customer.get("legal_name"),
        email=customer.get("email"),
        phone=customer.get("phone"),
        external_id=customer.get("external_id"),
        document=customer.get("document"),
    )


def _customer_to_api(cust: PaymentIntentCustomer) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    if cust.id is not None:
        out["id"] = cust.id
    if cust.type is not None:
        out["type"] = cust.type
    if cust.given_name is not None:
        out["given_name"] = cust.given_name
    if cust.family_name is not None:
        out["family_name"] = cust.family_name
    if cust.legal_name is not None:
        out["legal_name"] = cust.legal_name
    if cust.email is not None:
        out["email"] = cust.email
    if cust.phone is not None:
        out["phone"] = cust.phone
    if cust.external_id is not None:
        out["external_id"] = cust.external_id
    if cust.document is not None:
        out["document"] = cust.document
    return out


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
