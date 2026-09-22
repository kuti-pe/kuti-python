# kuti-pe

SDK oficial de KUTI para Python. Crea sesiones de checkout, consulta el estado de un pago y verifica webhooks — sin reimplementar auth, manejo de errores ni firma HMAC a mano.

> **Solo servidor.** Este paquete usa tu secret key (`kuti_live_...` / `kuti_test_...`). Nunca lo importes en código que se sirva al navegador.

## Instalación

```bash
pip install kuti-pe
```

## Quickstart

```python
import os
from kuti import KutiClient

kuti = KutiClient(os.environ["KUTI_SECRET_KEY"])

# El monto SIEMPRE se resuelve en tu backend — nunca confíes en un monto
# que te mande el navegador del comprador.
session = kuti.checkout_sessions.create(
    amount={"amount": "249.90", "currency": "PEN"},
    payment_method_types=["INTEROPERABLE_QR", "BANK_TRANSFER"],
    description="Zapatillas running talla 42",
    # Cliente existente: solo el id. Para uno nuevo: name/email/phone/external_id.
    customer={"id": "cus_01ABC"},
    # customer={"name": "María López", "email": "maria@example.com"},
    idempotency_key=f"order-{order_id}",  # evita duplicar el cobro si reintentas
)

# Envía session.checkout_url al frontend y ábrelo con Checkout.js:
#   window.Kuti.open({ checkoutUrl: session.checkout_url, onSuccess, onFailure })
```

## Confirmar un pago (sin necesitar webhooks)

`onSuccess` de Checkout.js corre en el navegador del comprador — no es confiable por sí solo. Vuelve a preguntarle a la API:

```python
intent = kuti.payment_intents.retrieve(payment_intent_id)
if intent.status == "SUCCEEDED":
    # entrega el producto / activa el servicio
    pass
```

## Verificar un webhook

```python
from flask import Flask, request
from kuti import verify_webhook_signature, KutiSignatureVerificationError
import os

app = Flask(__name__)

@app.post("/webhooks/kuti")
def kuti_webhook():
    payload = request.get_data(as_text=True)  # body CRUDO, sin json.loads antes
    try:
        verify_webhook_signature(
            payload,
            request.headers["X-Kuti-Signature"],
            request.headers["X-Kuti-Timestamp"],
            os.environ["KUTI_WEBHOOK_SECRET"],
        )
    except KutiSignatureVerificationError:
        return "Invalid signature", 400

    event = request.get_json(force=True)
    # payment.succeeded, checkout.session.completed, …
    return "", 200
```

## Manejo de errores

Todas las excepciones de la API extienden `KutiApiError` (`status`, `code`, `request_id`, `doc_url`, `details`):

```python
from kuti import KutiValidationError, KutiNotFoundError, KutiApiError

try:
    kuti.checkout_sessions.create(...)
except KutiValidationError as err:
    print(err.details)  # [ErrorDetail(field="amount.amount", ...)]
except KutiNotFoundError:
    pass
except KutiApiError as err:
    print(err.code, err.request_id)  # úsalo al reportar un bug a soporte
```

Los `GET` y los `POST` con `idempotency_key` se reintentan automáticamente en errores de red o `429`/`503`. Un `POST` sin `idempotency_key` nunca se reintenta, para no duplicar un cobro.

## API

- `KutiClient(secret_key, base_url=None)`
- `kuti.checkout_sessions.create(*, amount, payment_method_types, …, idempotency_key=None)`
- `kuti.payment_intents.retrieve(id)`
- `verify_webhook_signature(payload, signature_header, timestamp_header, secret, tolerance_seconds=300)`

## Requisitos

Python 3.9+ · sin dependencias de runtime.
