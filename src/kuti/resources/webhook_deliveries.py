from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional
from urllib.parse import quote

from ..types import RequestOptions

if TYPE_CHECKING:
    from ..client import KutiClient


class WebhookDeliveriesResource:
    """Entregas de webhook. Devuelve el objeto tal cual la API: ``status``, ``attempts``,
    ``last_http_status`` y ``attempt_history`` (cada intento con ``http_status`` y ``response_body``)."""

    def __init__(self, client: KutiClient) -> None:
        self._client = client

    def retrieve(self, delivery_id: str) -> Dict[str, Any]:
        """GET /webhook-deliveries/:id"""
        return self._client.request("GET", f"/webhook-deliveries/{quote(delivery_id, safe='')}")["data"]

    def retry(self, delivery_id: str, *, idempotency_key: Optional[str] = None) -> Dict[str, Any]:
        """POST /webhook-deliveries/:id/retry — la reencola para envío inmediato."""
        opts = RequestOptions(idempotency_key=idempotency_key) if idempotency_key else None
        return self._client.request(
            "POST", f"/webhook-deliveries/{quote(delivery_id, safe='')}/retry", None, opts
        )["data"]
