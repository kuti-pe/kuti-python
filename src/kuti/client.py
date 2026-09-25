from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional
from .errors import KutiConnectionError, error_for_status
from .resources.checkout_sessions import CheckoutSessionsResource
from .resources.customers import CustomersResource
from .resources.payment_intents import PaymentIntentsResource
from .resources.payment_links import PaymentLinksResource
from .types import RequestOptions

DEFAULT_BASE_URL = "https://api.kuti.pe/v1"
_SECRET_KEY_PREFIXES = ("kuti_live_", "kuti_test_")
_MAX_RETRIES = 2
_RETRYABLE_STATUS = {429, 503}


class KutiClient:
    """Cliente HTTP central de KUTI.

    Cuelgan de aquí los recursos (``checkout_sessions``, ``customers``, ``payment_intents``);
    esta clase solo resuelve auth, reintentos y mapeo de errores.
    """

    def __init__(self, secret_key: str, *, base_url: Optional[str] = None) -> None:
        if not any(secret_key.startswith(p) for p in _SECRET_KEY_PREFIXES):
            raise ValueError(
                "KutiClient expects a secret key (kuti_live_... / kuti_test_...), "
                "not a publishable key."
            )
        self._secret_key = secret_key
        self._base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self.checkout_sessions = CheckoutSessionsResource(self)
        self.customers = CustomersResource(self)
        self.payment_intents = PaymentIntentsResource(self)
        self.payment_links = PaymentLinksResource(self)

    def request(
        self,
        method: str,
        path: str,
        body: Optional[Dict[str, Any]] = None,
        opts: Optional[RequestOptions] = None,
    ) -> Dict[str, Any]:
        """Uso interno de los recursos — no lo llames directo."""
        headers = {
            "Authorization": f"Bearer {self._secret_key}",
            "Accept": "application/json",
            "User-Agent": "kuti-pe/1.0.0 (python)",
        }
        data: Optional[bytes] = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        if opts and opts.idempotency_key:
            headers["Idempotency-Key"] = opts.idempotency_key

        # Solo se reintenta si el request es idempotente por diseño (GET) o el caller
        # ya proveyó una Idempotency-Key — nunca un POST "a ciegas".
        can_retry = method == "GET" or bool(opts and opts.idempotency_key)
        max_attempts = _MAX_RETRIES + 1 if can_retry else 1

        last_error: Optional[BaseException] = None
        for attempt in range(max_attempts):
            if attempt > 0:
                time.sleep((2**attempt) * 0.2)
            try:
                req = urllib.request.Request(
                    f"{self._base_url}{path}",
                    data=data,
                    headers=headers,
                    method=method,
                )
                with urllib.request.urlopen(req, timeout=30) as resp:
                    raw = resp.read().decode("utf-8")
                    return json.loads(raw) if raw else {}
            except urllib.error.HTTPError as exc:
                envelope = _safe_parse_error(exc)
                err_body = envelope.get("error") or {}
                api_error = error_for_status(
                    exc.code,
                    code=err_body.get("code") or "UNKNOWN_ERROR",
                    message=err_body.get("message")
                    or envelope.get("message")
                    or exc.reason,
                    request_id=err_body.get("request_id"),
                    doc_url=err_body.get("doc_url"),
                    details=err_body.get("details"),
                )
                if can_retry and exc.code in _RETRYABLE_STATUS and attempt < _MAX_RETRIES:
                    last_error = api_error
                    continue
                raise api_error from None
            except urllib.error.URLError as exc:
                last_error = KutiConnectionError("Could not reach the KUTI API.", exc)
                if not can_retry:
                    raise last_error from exc
            except TimeoutError as exc:
                last_error = KutiConnectionError("Could not reach the KUTI API.", exc)
                if not can_retry:
                    raise last_error from exc

        assert last_error is not None
        raise last_error


def _safe_parse_error(exc: urllib.error.HTTPError) -> Dict[str, Any]:
    try:
        raw = exc.read().decode("utf-8")
        parsed = json.loads(raw) if raw else {}
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}
