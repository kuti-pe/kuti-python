from __future__ import annotations

from typing import Any, List, Optional

from .types import ErrorDetail


class KutiApiError(Exception):
    """Error base de la API — cualquier respuesta HTTP != 2xx."""

    def __init__(
        self,
        *,
        status: int,
        code: str,
        message: str,
        request_id: Optional[str] = None,
        doc_url: Optional[str] = None,
        details: Optional[List[Any]] = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.request_id = request_id
        self.doc_url = doc_url
        self.details: List[ErrorDetail] = []
        for d in details or []:
            if isinstance(d, dict):
                self.details.append(
                    ErrorDetail(
                        field=d.get("field"),
                        code=d.get("code"),
                        message=d.get("message"),
                    )
                )


class KutiAuthenticationError(KutiApiError):
    """401 — secret key inválida, revocada o ausente."""


class KutiPermissionError(KutiApiError):
    """403 — key válida pero sin permiso."""


class KutiNotFoundError(KutiApiError):
    """404 — recurso inexistente o de otro merchant."""


class KutiValidationError(KutiApiError):
    """400 / 422 — request inválido. Revisa `.details`."""


class KutiConflictError(KutiApiError):
    """409 — conflicto de estado."""


class KutiRateLimitError(KutiApiError):
    """429 — demasiadas requests."""


class KutiConnectionError(Exception):
    """Fallo de red o timeout — no hubo respuesta HTTP de KUTI."""

    def __init__(self, message: str, cause: Optional[BaseException] = None) -> None:
        super().__init__(message)
        self.__cause__ = cause


class KutiSignatureVerificationError(Exception):
    """Firma de webhook inválida o timestamp fuera de tolerancia."""


def error_for_status(
    status: int,
    *,
    code: str,
    message: str,
    request_id: Optional[str] = None,
    doc_url: Optional[str] = None,
    details: Optional[List[Any]] = None,
) -> KutiApiError:
    kwargs = dict(
        status=status,
        code=code,
        message=message,
        request_id=request_id,
        doc_url=doc_url,
        details=details,
    )
    if status == 401:
        return KutiAuthenticationError(**kwargs)
    if status == 403:
        return KutiPermissionError(**kwargs)
    if status == 404:
        return KutiNotFoundError(**kwargs)
    if status in (400, 422):
        return KutiValidationError(**kwargs)
    if status == 409:
        return KutiConflictError(**kwargs)
    if status == 429:
        return KutiRateLimitError(**kwargs)
    return KutiApiError(**kwargs)
