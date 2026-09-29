from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List
from urllib.parse import quote, urlencode

if TYPE_CHECKING:
    from ..client import KutiClient


class DiagnosticsResource:
    """Diagnóstico (permiso ``diagnostics:read``): qué pasó con una petición, un cobro o un webhook.
    Ideal con una key de Solo lectura en un asistente de IA. Nunca expone al proveedor de pago.
    Devuelve el objeto tal cual la API (snake_case)."""

    def __init__(self, client: KutiClient) -> None:
        self._client = client

    def get_request(self, request_id: str) -> Dict[str, Any]:
        """GET /diagnostics/requests/:id — usa ``err.request_id`` o el header X-Request-Id.

        → ``{"request": {...}, "events": [{..., "webhook_deliveries": [...]}]}``
        """
        return self._client.request("GET", f"/diagnostics/requests/{quote(request_id, safe='')}")["data"]

    def list_by_correlation_id(self, correlation_id: str) -> List[Dict[str, Any]]:
        """GET /diagnostics/requests?correlation_id= — tus llamadas con el mismo X-Request-Id."""
        path = "/diagnostics/requests?" + urlencode({"correlation_id": correlation_id})
        return self._client.request("GET", path)["data"]

    def trace_payment_intent(self, payment_intent_id: str) -> Dict[str, Any]:
        """GET /diagnostics/payment-intents/:id/trace — la historia completa de un cobro."""
        return self._client.request(
            "GET", f"/diagnostics/payment-intents/{quote(payment_intent_id, safe='')}/trace"
        )["data"]
