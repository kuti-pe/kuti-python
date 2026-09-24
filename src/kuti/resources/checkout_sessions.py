from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from ..types import (
    CheckoutSession,
    CheckoutSessionCustomer,
    Money,
    customer_input_from,
    customer_input_to_api,
    PaymentMethodType,
    RequestOptions,
    money_from_api,
    payment_method_from_api,
)

if TYPE_CHECKING:
    from ..client import KutiClient


class CheckoutSessionsResource:
    def __init__(self, client: KutiClient) -> None:
        self._client = client

    def create(
        self,
        *,
        amount: Union[Money, Dict[str, str]],
        payment_method_types: List[PaymentMethodType],
        customer: Optional[Union[CheckoutSessionCustomer, Dict[str, Any]]] = None,
        description: Optional[str] = None,
        external_reference: Optional[str] = None,
        success_url: Optional[str] = None,
        expires_at: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        idempotency_key: Optional[str] = None,
    ) -> CheckoutSession:
        """POST /checkout-sessions. Pass ``idempotency_key`` to safely retry."""
        money = (
            amount
            if isinstance(amount, Money)
            else Money(amount=str(amount["amount"]), currency=str(amount["currency"]))
        )
        body: Dict[str, Any] = {
            "amount": {"amount": money.amount, "currency": money.currency},
            "payment_method_types": list(payment_method_types),
        }
        cust = customer_input_to_api(customer_input_from(customer))
        if cust is not None:
            body["customer"] = cust
        if description is not None:
            body["description"] = description
        if external_reference is not None:
            body["external_reference"] = external_reference
        if success_url is not None:
            body["success_url"] = success_url
        if expires_at is not None:
            body["expires_at"] = expires_at
        if metadata is not None:
            body["metadata"] = metadata

        opts = RequestOptions(idempotency_key=idempotency_key) if idempotency_key else None
        response = self._client.request("POST", "/checkout-sessions", body, opts)
        return _from_api(response["data"])


def _from_api(dto: Dict[str, Any]) -> CheckoutSession:
    return CheckoutSession(
        id=dto["id"],
        merchant_id=dto["merchant_id"],
        customer_id=dto.get("customer_id"),
        payment_intent_id=dto["payment_intent_id"],
        amount=money_from_api(dto["amount"]),
        status=dto["status"],
        description=dto.get("description"),
        success_url=dto.get("success_url"),
        client_secret=dto.get("client_secret"),
        checkout_url=dto.get("checkout_url"),
        payment_method=payment_method_from_api(dto.get("payment_method")),
        expires_at=dto.get("expires_at"),
        created_at=dto["created_at"],
    )
