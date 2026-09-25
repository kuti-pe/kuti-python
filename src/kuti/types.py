from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Union

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


CustomerType = Literal["INDIVIDUAL", "COMPANY"]


@dataclass(frozen=True)
class CustomerInput:
    """Datos de un cliente enviados "inline" (cobro, checkout session) — misma forma que
    ``customers.create``. Se reutiliza un cliente existente por id → external_id → documento;
    si no existe, se crea. Si viene ``id``, se ignora el resto (salvo ``custom_fields``).

    ``document``: ``{"type": "DNI", "number": "45678912", "country": "PE"}`` — ``type`` es
    opcional (se deduce del número) y ``country`` por defecto PE.
    ``custom_fields``: campos definidos por el negocio (Ajustes → Clientes → Campos), por key.
    """

    id: Optional[str] = None
    type: Optional[CustomerType] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company_name: Optional[str] = None  # razón social, solo COMPANY
    email: Optional[str] = None
    phone: Optional[str] = None  # E.164
    external_id: Optional[str] = None
    document: Optional[Dict[str, str]] = None
    custom_fields: Optional[Dict[str, Any]] = None


# Mismos datos en todos los recursos: se mantienen los nombres por legibilidad.
CheckoutSessionCustomer = CustomerInput
PaymentIntentCustomer = CustomerInput


@dataclass(frozen=True)
class Customer:
    id: str
    merchant_id: str
    type: CustomerType
    created_at: str
    external_id: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company_name: Optional[str] = None
    document: Optional[Dict[str, str]] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    metadata: Optional[Dict[str, str]] = None
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    payment_intents_count: Optional[int] = None  # solo en customers.retrieve


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
    # Cliente congelado en el cobro: id, type, first_name, last_name, company_name, name,
    # document {type, number, country}, email, custom_fields.
    customer: Optional[Dict[str, Any]] = None
    # Link de pago del que salió este cobro (plink_…), si aplica.
    payment_link_id: Optional[str] = None
    # Canales por los que se envió el cobro al crearlo ("EMAIL", "WHATSAPP").
    send_via: Optional[List[str]] = None


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


def customer_input_from(value: Union[CustomerInput, Dict[str, Any], None]) -> Optional[CustomerInput]:
    if value is None or isinstance(value, CustomerInput):
        return value
    return CustomerInput(
        id=value.get("id"),
        type=value.get("type"),
        first_name=value.get("first_name"),
        last_name=value.get("last_name"),
        company_name=value.get("company_name"),
        email=value.get("email"),
        phone=value.get("phone"),
        external_id=value.get("external_id"),
        document=value.get("document"),
        custom_fields=value.get("custom_fields"),
    )


def customer_input_to_api(customer: Optional[CustomerInput]) -> Optional[Dict[str, Any]]:
    """Cuerpo del cliente (snake_case); omite los vacíos. ``custom_fields`` viaja tal cual
    (un ``None`` dentro significa "borrar ese valor" en una edición)."""
    if customer is None:
        return None
    out: Dict[str, Any] = {}
    for key in ("id", "type", "first_name", "last_name", "company_name", "email", "phone", "external_id"):
        value = getattr(customer, key)
        if value is not None and value != "":
            out[key] = value
    if customer.document:
        out["document"] = {k: v for k, v in customer.document.items() if v not in (None, "")}
    if customer.custom_fields:
        out["custom_fields"] = customer.custom_fields
    return out


def customer_from_api(dto: Dict[str, Any]) -> Customer:
    return Customer(
        id=dto["id"],
        merchant_id=dto["merchant_id"],
        type=dto["type"],
        created_at=dto["created_at"],
        external_id=dto.get("external_id"),
        first_name=dto.get("first_name"),
        last_name=dto.get("last_name"),
        company_name=dto.get("company_name"),
        document=dto.get("document"),
        email=dto.get("email"),
        phone=dto.get("phone"),
        metadata=dto.get("metadata"),
        custom_fields=dto.get("custom_fields") or {},
        payment_intents_count=dto.get("payment_intents_count"),
    )


@dataclass
class PaymentLink:
    """Link de pago: un enlace permanente que pagan muchas personas. Cada pago es un cobro con
    ``payment_link_id``."""

    id: str
    merchant_id: str
    livemode: bool
    slug: str
    url: str  # pay.kuti.pe/l/{slug}: la URL para compartir
    title: str
    template: str
    pricing: str
    currency: str
    status: str
    payment_method_types: List[str]
    created_at: str
    updated_at: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    amount: Optional[str] = None
    min_amount: Optional[str] = None
    max_amount: Optional[str] = None
    suggested_amounts: List[str] = field(default_factory=list)
    category_id: Optional[str] = None
    expires_at: Optional[str] = None
    # Preguntas a quien paga (copia): id, key, label, type, options, required, help_text.
    customer_fields: List[Dict[str, Any]] = field(default_factory=list)
    button_label: Optional[str] = None
    success_message: Optional[str] = None
    success_button_label: Optional[str] = None
    success_button_url: Optional[str] = None
    payments_count: Optional[int] = None  # pagos confirmados
    checkouts_count: Optional[int] = None  # llenaron sus datos
    views_count: Optional[int] = None  # visitas a la página
    amount_collected: Optional[str] = None

    @property
    def is_active(self) -> bool:
        return self.status == "ACTIVE"
