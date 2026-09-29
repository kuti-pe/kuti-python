from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional
from urllib.parse import quote, urlencode

from ..types import PaymentException, payment_exception_from_api

if TYPE_CHECKING:
    from ..client import KutiClient


class PaymentExceptionsResource:
    """Pagos para revisar. Aviso por webhook: ``payment.exception_created``."""

    def __init__(self, client: KutiClient) -> None:
        self._client = client

    def list(
        self,
        *,
        status: Optional[str] = None,
        payment_intent_id: Optional[str] = None,
        page: Optional[int] = None,
        per_page: Optional[int] = None,
    ) -> Dict[str, Any]:
        """GET /payment-exceptions → ``{"data": [PaymentException, ...], "pagination": {...}}``."""
        query = {
            k: v
            for k, v in {
                "status": status,
                "payment_intent_id": payment_intent_id,
                "page": page,
                "per_page": per_page,
            }.items()
            if v is not None
        }
        path = "/payment-exceptions" + (f"?{urlencode(query)}" if query else "")
        response = self._client.request("GET", path)
        data: List[PaymentException] = [payment_exception_from_api(r) for r in response.get("data") or []]
        return {"data": data, "pagination": response.get("pagination") or {}}

    def resolve(self, exception_id: str, *, status: str, note: Optional[str] = None) -> PaymentException:
        """POST /payment-exceptions/:id/resolve — deja constancia de qué hiciste (no mueve dinero).

        ``status``: "REFUNDED" (lo devolviste), "APPLIED" (lo aplicaste) o "DISMISSED".
        """
        body: Dict[str, Any] = {"status": status}
        if note is not None:
            body["note"] = note
        response = self._client.request(
            "POST", f"/payment-exceptions/{quote(exception_id, safe='')}/resolve", body
        )
        return payment_exception_from_api(response["data"])
