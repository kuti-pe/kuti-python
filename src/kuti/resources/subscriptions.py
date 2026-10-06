from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union
from urllib.parse import quote, urlencode

from ..types import (
    CustomerInput,
    RequestOptions,
    Subscription,
    customer_input_from,
    customer_input_to_api,
    subscription_cycle_from_api,
    subscription_from_api,
)

if TYPE_CHECKING:
    from ..client import KutiClient

_UNSET: Any = object()


class SubscriptionsResource:
    """Suscripciones: KUTI le cobra solo a tu cliente, cada periodo, sobre su Yape afiliado
    (máximo S/ 2,500 por periodo). Cada periodo es un cobro normal (``payment_intents``)."""

    def __init__(self, client: KutiClient) -> None:
        self._client = client

    def create(
        self,
        *,
        customer: Union[CustomerInput, Dict[str, Any]],
        description: str,
        frequency: str,
        billing_mode: Optional[str] = None,
        amount: Optional[str] = None,
        items: Optional[List[Dict[str, Any]]] = None,
        currency: Optional[str] = None,
        interval: Optional[int] = None,
        day_of_month: Optional[int] = None,
        last_day_of_month: Optional[bool] = None,
        day_of_week: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        charge_time: Optional[str] = None,
        retry_policy: Optional[Dict[str, Any]] = None,
        external_reference: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        send_via: Optional[List[str]] = None,
        idempotency_key: Optional[str] = None,
    ) -> Subscription:
        """POST /subscriptions.

        Monto fijo: cobra el primer periodo al crearla (si el cliente aún no tiene su Yape
        afiliado nace ``INCOMPLETE`` con ``latest_cycle["checkout_url"]``). Monto variable
        (``billing_mode="variable"``): no cobra nada; si falta afiliar, trae ``setup_url``.

        ``items``: ``[{"description", "unit_amount", "quantity"}]``; ``amount`` es el atajo de una
        línea. ``charge_time``: "HH:mm", hora de Perú, nunca entre 01:00 y 03:00.
        ``retry_policy``: ``{"interval_days": [1, 3, 5], "on_exhausted": "past_due" | "cancel"}``;
        ``interval_days: []`` = no reintentar.
        """
        body: Dict[str, Any] = {
            "customer": customer_input_to_api(customer_input_from(customer)),
            "description": description,
            "frequency": frequency,
        }
        optional = {
            "billing_mode": billing_mode,
            "amount": amount,
            "items": items,
            "currency": currency,
            "interval": interval,
            "day_of_month": day_of_month,
            "last_day_of_month": last_day_of_month,
            "day_of_week": day_of_week,
            "start_date": start_date,
            "end_date": end_date,
            "charge_time": charge_time,
            "retry_policy": retry_policy,
            "external_reference": external_reference,
            "metadata": metadata,
            "send_via": send_via,
        }
        body.update({k: v for k, v in optional.items() if v is not None})
        opts = RequestOptions(idempotency_key=idempotency_key) if idempotency_key else None
        response = self._client.request("POST", "/subscriptions", body, opts)
        return subscription_from_api(response["data"])

    def retrieve(self, subscription_id: str) -> Subscription:
        """GET /subscriptions/{id} — la devuelve ya puesta al día con sus cobros."""
        response = self._client.request("GET", _path(subscription_id))
        return subscription_from_api(response["data"])

    def list(
        self,
        *,
        status: Optional[str] = None,
        customer_id: Optional[str] = None,
        page: Optional[int] = None,
        per_page: Optional[Union[int, str]] = None,
    ) -> Dict[str, Any]:
        """GET /subscriptions → ``{"data": [Subscription, ...], "pagination": {...}}``."""
        query = {
            k: v
            for k, v in {"status": status, "customer_id": customer_id, "page": page, "per_page": per_page}.items()
            if v is not None
        }
        response = self._client.request("GET", "/subscriptions" + (f"?{urlencode(query)}" if query else ""))
        return {
            "data": [subscription_from_api(s) for s in response.get("data") or []],
            "pagination": response.get("pagination") or {},
        }

    def update(
        self,
        subscription_id: str,
        *,
        description: Optional[str] = _UNSET,
        amount: Optional[str] = _UNSET,
        items: Optional[List[Dict[str, Any]]] = _UNSET,
        end_date: Optional[str] = _UNSET,
        charge_time: Optional[str] = _UNSET,
        retry_policy: Optional[Dict[str, Any]] = _UNSET,
        metadata: Optional[Dict[str, str]] = _UNSET,
    ) -> Subscription:
        """PATCH /subscriptions/{id} — rige desde el próximo periodo; solo cambia lo que pasas."""
        params = {
            "description": description,
            "amount": amount,
            "items": items,
            "end_date": end_date,
            "charge_time": charge_time,
            "retry_policy": retry_policy,
            "metadata": metadata,
        }
        body = {k: v for k, v in params.items() if v is not _UNSET}
        response = self._client.request("PATCH", _path(subscription_id), body)
        return subscription_from_api(response["data"])

    def pause(self, subscription_id: str, *, idempotency_key: Optional[str] = None) -> Subscription:
        """POST /subscriptions/{id}/pause — deja de cobrar y de reintentar."""
        return self._action(subscription_id, "pause", idempotency_key)

    def resume(self, subscription_id: str, *, idempotency_key: Optional[str] = None) -> Subscription:
        """POST /subscriptions/{id}/resume"""
        return self._action(subscription_id, "resume", idempotency_key)

    def cancel(self, subscription_id: str, *, idempotency_key: Optional[str] = None) -> Subscription:
        """POST /subscriptions/{id}/cancel — final; anula el cobro del periodo que siga sin pagar."""
        return self._action(subscription_id, "cancel", idempotency_key)

    def retry(self, subscription_id: str, *, idempotency_key: Optional[str] = None) -> Subscription:
        """POST /subscriptions/{id}/retry — debita ahora el periodo más antiguo sin pagar."""
        return self._action(subscription_id, "retry", idempotency_key)

    def charge(
        self,
        subscription_id: str,
        *,
        amount: str,
        description: Optional[str] = None,
        period: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> Subscription:
        """POST /subscriptions/{id}/charges — solo monto variable: envía el monto de un periodo y
        KUTI lo debita. Llámalo al recibir ``subscription.amount_required`` o al cerrar tu periodo.
        Un solo cobro por periodo (409 SUBSCRIPTION_PERIOD_ALREADY_CHARGED si lo repites)."""
        body: Dict[str, Any] = {"amount": amount}
        if description is not None:
            body["description"] = description
        if period is not None:
            body["period"] = period
        opts = RequestOptions(idempotency_key=idempotency_key) if idempotency_key else None
        response = self._client.request("POST", f"{_path(subscription_id)}/charges", body, opts)
        return subscription_from_api(response["data"])

    def list_cycles(self, subscription_id: str) -> List[Dict[str, Any]]:
        """GET /subscriptions/{id}/cycles — periodos, del más reciente al más antiguo."""
        response = self._client.request("GET", f"{_path(subscription_id)}/cycles")
        return [subscription_cycle_from_api(c) for c in response.get("data") or []]

    def _action(self, subscription_id: str, action: str, idempotency_key: Optional[str] = None) -> Subscription:
        opts = RequestOptions(idempotency_key=idempotency_key) if idempotency_key else None
        response = self._client.request("POST", f"{_path(subscription_id)}/{action}", None, opts)
        return subscription_from_api(response["data"])


def _path(subscription_id: str) -> str:
    return f"/subscriptions/{quote(subscription_id, safe='')}"
