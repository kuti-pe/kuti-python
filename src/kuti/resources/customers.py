from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union
from urllib.parse import quote, urlencode

from ..types import (
    Customer,
    CustomerInput,
    customer_from_api,
    customer_input_from,
    customer_input_to_api,
)

if TYPE_CHECKING:
    from ..client import KutiClient

_UNSET: Any = object()


class CustomersResource:
    def __init__(self, client: KutiClient) -> None:
        self._client = client

    def create(
        self,
        customer: Union[CustomerInput, Dict[str, Any]],
        *,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Customer:
        """POST /customers — 409 CUSTOMER_ALREADY_EXISTS si el external_id o documento ya existe."""
        body = customer_input_to_api(customer_input_from(customer)) or {}
        body.pop("id", None)
        if metadata is not None:
            body["metadata"] = metadata
        response = self._client.request("POST", "/customers", body)
        return customer_from_api(response["data"])

    def retrieve(self, customer_id: str) -> Customer:
        """GET /customers/{id}"""
        response = self._client.request("GET", f"/customers/{quote(customer_id, safe='')}")
        return customer_from_api(response["data"])

    def update(
        self,
        customer_id: str,
        *,
        first_name: Optional[str] = _UNSET,
        last_name: Optional[str] = _UNSET,
        company_name: Optional[str] = _UNSET,
        email: Optional[str] = _UNSET,
        phone: Optional[str] = _UNSET,
        metadata: Optional[Dict[str, str]] = _UNSET,
        custom_fields: Optional[Dict[str, Any]] = _UNSET,
    ) -> Customer:
        """PATCH /customers/{id} — solo cambian los campos que pasas. En ``custom_fields`` solo
        cambian las keys enviadas; ``None`` borra ese valor. Tipo, documento y external_id no se
        editan."""
        params = {
            "first_name": first_name,
            "last_name": last_name,
            "company_name": company_name,
            "email": email,
            "phone": phone,
            "metadata": metadata,
            "custom_fields": custom_fields,
        }
        body = {k: v for k, v in params.items() if v is not _UNSET}
        response = self._client.request("PATCH", f"/customers/{quote(customer_id, safe='')}", body)
        return customer_from_api(response["data"])

    def list(
        self,
        *,
        q: Optional[str] = None,
        page: Optional[int] = None,
        per_page: Optional[Union[int, str]] = None,
    ) -> Dict[str, Any]:
        """GET /customers → ``{"data": [Customer, ...], "pagination": {...}}``."""
        query = {k: v for k, v in {"q": q, "page": page, "per_page": per_page}.items() if v is not None}
        path = "/customers" + (f"?{urlencode(query)}" if query else "")
        response = self._client.request("GET", path)
        data: List[Customer] = [customer_from_api(c) for c in response.get("data") or []]
        return {"data": data, "pagination": response.get("pagination") or {}}

    def delete(self, customer_id: str) -> Dict[str, Any]:
        """DELETE /customers/{id} — se archiva en vez de borrarse si tiene cobros."""
        response = self._client.request("DELETE", f"/customers/{quote(customer_id, safe='')}")
        return {
            "deleted": bool(response.get("deleted")),
            "archived": bool(response.get("archived")),
            "payment_intents_count": int(response.get("payment_intents_count") or 0),
        }
