from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional

PaymentMethodType = Literal["INTEROPERABLE_QR", "BANK_TRANSFER"]

CheckoutSessionStatus = Literal["OPEN", "COMPLETED", "EXPIRED", "CANCELLED"]

PaymentIntentStatus = Literal[
    "REQUIRES_PAYMENT_METHOD",
    "PENDING",
    "PROCESSING",
    "SUCCEEDED",
    "FAILED",
    "CANCELLED",
    "EXPIRED",
]


@dataclass(frozen=True)
class Money:
    """Decimal string (never float). Currency: PEN only for now."""

    amount: str
    currency: str = "PEN"


@dataclass(frozen=True)
class CheckoutSessionCustomer:
    """If ``id`` is set, other fields are ignored."""

    id: Optional[str] = None
    external_id: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None  # E.164


@dataclass(frozen=True)
class PaymentIntentCustomer:
    """If ``id`` is set, other fields are ignored."""

    id: Optional[str] = None
    type: Optional[Literal["INDIVIDUAL", "COMPANY"]] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    legal_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    external_id: Optional[str] = None
    document: Optional[Dict[str, str]] = None  # {type, number}


@dataclass(frozen=True)
class PaymentIntentCustomer:
    """Cliente del cobro. Si viene ``id``, se ignora el resto."""

    id: Optional[str] = None
    type: Optional[Literal["INDIVIDUAL", "COMPANY"]] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    legal_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    external_id: Optional[str] = None
    document: Optional[Dict[str, str]] = None  # {type, number}


@dataclass(frozen=True)
class PaymentMethodQr:
    type: Optional[PaymentMethodType] = None
    payload: Optional[str] = None
    image_url: Optional[str] = None
    expires_at: Optional[str] = None


@dataclass(frozen=True)
class PaymentMethodPaymentCode:
    type: Optional[PaymentMethodType] = None
    code: Optional[str] = None
    expires_at: Optional[str] = None


@dataclass(frozen=True)
class PaymentMethod:
    qr: Optional[PaymentMethodQr] = None
    payment_code: Optional[PaymentMethodPaymentCode] = None


@dataclass(frozen=True)
class PaidWith:
    method_type: Optional[PaymentMethodType] = None
    paid_at: Optional[str] = None


@dataclass(frozen=True)
class CheckoutSession:
    id: str
    merchant_id: str
    payment_intent_id: str
    amount: Money
    status: CheckoutSessionStatus
    created_at: str
    customer_id: Optional[str] = None
    description: Optional[str] = None
    success_url: Optional[str] = None
    client_secret: Optional[str] = None
    checkout_url: Optional[str] = None
    payment_method: Optional[PaymentMethod] = None
    expires_at: Optional[str] = None


@dataclass(frozen=True)
class PaymentIntent:
    id: str
    merchant_id: str
    amount: Money
    status: PaymentIntentStatus
    created_at: str
    livemode: Optional[bool] = None
    customer_id: Optional[str] = None
    payment_method_types: Optional[List[PaymentMethodType]] = None
    payment_method: Optional[PaymentMethod] = None
    paid_with: Optional[PaidWith] = None
    checkout_url: Optional[str] = None
    expires_at: Optional[str] = None
    external_reference: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[str] = None
    metadata: Optional[Dict[str, str]] = None
    requires_customer_info: Optional[bool] = None


@dataclass
class CreateCheckoutSessionParams:
    amount: Money
    payment_method_types: List[PaymentMethodType]
    customer: Optional[CheckoutSessionCustomer] = None
    description: Optional[str] = None
    external_reference: Optional[str] = None
    success_url: Optional[str] = None
    expires_at: Optional[str] = None
    metadata: Optional[Dict[str, str]] = None


@dataclass(frozen=True)
class RequestOptions:
    """Evita duplicar la operación si el request se reintenta."""

    idempotency_key: Optional[str] = None


@dataclass(frozen=True)
class ErrorDetail:
    field: Optional[str] = None
    code: Optional[str] = None
    message: Optional[str] = None


def money_from_api(raw: Dict[str, Any]) -> Money:
    return Money(amount=str(raw["amount"]), currency=str(raw["currency"]))


def payment_method_from_api(raw: Optional[Dict[str, Any]]) -> Optional[PaymentMethod]:
    if not raw:
        return None
    qr_raw = raw.get("qr")
    code_raw = raw.get("payment_code")
    return PaymentMethod(
        qr=(
            PaymentMethodQr(
                type=qr_raw.get("type"),
                payload=qr_raw.get("payload"),
                image_url=qr_raw.get("image_url"),
                expires_at=qr_raw.get("expires_at"),
            )
            if qr_raw
            else None
        ),
        payment_code=(
            PaymentMethodPaymentCode(
                type=code_raw.get("type"),
                code=code_raw.get("code"),
                expires_at=code_raw.get("expires_at"),
            )
            if code_raw
            else None
        ),
    )
