from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union
from urllib.parse import quote, urlencode

from ..types import PaymentLink

if TYPE_CHECKING:
    from ..client import KutiClient

# Parámetro (snake_case) → campo de la API.
_FIELDS = (
    "slug",
    "title",
    "description",
    "image_url",
    "template",
    "pricing",
    "amount",
    "min_amount",
    "max_amount",
    "suggested_amounts",
    "currency",
    "payment_method_types",
    "category_id",
    "expires_at",
    "customer_field_ids",
    "button_label",
    "success_message",
    "success_button_label",
    "success_button_url",
)


class PaymentLinksResource:
    """Links de pago: un enlace permanente que pagan muchas personas (curso, entrada, donación)."""

    def __init__(self, client: KutiClient) -> None:
        self._client = client

    def create(self, **params: Any) -> PaymentLink:
        """POST /payment-links.

        Obligatorios: ``title``, ``pricing`` ("FIXED" | "CUSTOMER_CHOOSES"),
        ``payment_method_types``; ``amount`` (FIXED) o ``min_amount`` (CUSTOMER_CHOOSES).
        ``customer_field_ids`` sin enviar = los "pedir también al pagar"; [] = ninguno.
        """
        response = self._client.request("POST", "/payment-links", _to_body(params))
        return _from_api(response["data"])

    def retrieve(self, payment_link_id: str) -> PaymentLink:
        """GET /payment-links/:id"""
        response = self._client.request("GET", f"/payment-links/{quote(payment_link_id, safe='')}")
        return _from_api(response["data"])

    def update(self, payment_link_id: str, **params: Any) -> PaymentLink:
        """PUT /payment-links/:id — reemplaza el link completo (los cobros ya creados no cambian)."""
        response = self._client.request(
            "PUT", f"/payment-links/{quote(payment_link_id, safe='')}", _to_body(params)
        )
        return _from_api(response["data"])

    def list(
        self,
        *,
        status: Optional[str] = None,
        q: Optional[str] = None,
        page: Optional[int] = None,
        per_page: Optional[Union[int, str]] = None,
    ) -> Dict[str, Any]:
        """GET /payment-links — returns ``{"data": [...], "pagination": {...}}``."""
        query: Dict[str, str] = {}
        if status is not None:
            query["status"] = status
        if q is not None:
            query["q"] = q
        if page is not None:
            query["page"] = str(page)
        if per_page is not None:
            query["per_page"] = str(per_page)
        path = "/payment-links" + (f"?{urlencode(query)}" if query else "")
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

    def activate(self, payment_link_id: str) -> PaymentLink:
        """POST /payment-links/:id/activate"""
        response = self._client.request(
            "POST", f"/payment-links/{quote(payment_link_id, safe='')}/activate"
        )
        return _from_api(response["data"])

    def deactivate(self, payment_link_id: str) -> PaymentLink:
        """POST /payment-links/:id/deactivate — deja de aceptar pagos."""
        response = self._client.request(
            "POST", f"/payment-links/{quote(payment_link_id, safe='')}/deactivate"
        )
        return _from_api(response["data"])

    def check_slug(self, slug: str, except_id: Optional[str] = None) -> Dict[str, Any]:
        """GET /payment-links/slug-availability — ``{"slug", "available", "suggestion"}``."""
        query = {"slug": slug}
        if except_id is not None:
            query["except_id"] = except_id
        response = self._client.request("GET", f"/payment-links/slug-availability?{urlencode(query)}")
        return response["data"]


def _to_body(params: Dict[str, Any]) -> Dict[str, Any]:
    unknown = set(params) - set(_FIELDS)
    if unknown:
        raise TypeError(f"Parámetros desconocidos: {', '.join(sorted(unknown))}")
    # None se omite; [] viaja (p. ej. customer_field_ids=[] = sin preguntas).
    return {k: (list(v) if isinstance(v, (list, tuple)) else v) for k, v in params.items() if v is not None}


def _from_api(d: Dict[str, Any]) -> PaymentLink:
    return PaymentLink(
        id=d["id"],
        merchant_id=d["merchant_id"],
        livemode=bool(d.get("livemode", False)),
        slug=d["slug"],
        url=d["url"],
        title=d["title"],
        template=d.get("template", "GENERIC"),
        pricing=d["pricing"],
        currency=d.get("currency", "PEN"),
        status=d["status"],
        payment_method_types=list(d.get("payment_method_types") or []),
        created_at=d["created_at"],
        updated_at=d.get("updated_at", d["created_at"]),
        description=d.get("description"),
        image_url=d.get("image_url"),
        amount=d.get("amount"),
        min_amount=d.get("min_amount"),
        max_amount=d.get("max_amount"),
        suggested_amounts=list(d.get("suggested_amounts") or []),
        category_id=d.get("category_id"),
        expires_at=d.get("expires_at"),
        customer_fields=list(d.get("customer_fields") or []),
        button_label=d.get("button_label"),
        success_message=d.get("success_message"),
        success_button_label=d.get("success_button_label"),
        success_button_url=d.get("success_button_url"),
        payments_count=d.get("payments_count"),
        checkouts_count=d.get("checkouts_count"),
        views_count=d.get("views_count"),
        amount_collected=d.get("amount_collected"),
    )
