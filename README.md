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

session = kuti.checkout_sessions.create(
    amount={"amount": "249.90", "currency": "PEN"},
    payment_method_types=["INTEROPERABLE_QR", "BANK_TRANSFER"],
    description="Zapatillas running talla 42",
    customer={"id": "cus_01ABC"},
    # customer={"first_name": "María", "last_name": "López", "email": "maria@example.com"},
    idempotency_key=f"order-{order_id}",
)

# window.Kuti.open({ checkoutUrl: session.checkout_url, onSuccess, onFailure })
```

## Clientes y campos personalizados

El cliente tiene la **misma forma** en `customers.create`, en el `customer` de un cobro y en el de
una checkout session. `custom_fields` son los campos que el negocio definió en
**Ajustes → Clientes → Campos** (la key de cada campo):

```python
from kuti import CustomerInput

customer = kuti.customers.create(
    CustomerInput(
        type="INDIVIDUAL",
        first_name="María",
        last_name="López",
        document={"type": "DNI", "number": "45678912"},  # type opcional: se deduce del número
        email="maria@example.com",
        custom_fields={"grade": "quinto", "student_code": "2026-00781"},
    )
)

# En un cobro: se reutiliza el cliente por id → external_id → documento, o se crea.
kuti.payment_intents.create(
    amount={"amount": "250.00", "currency": "PEN"},
    payment_method_types=["INTEROPERABLE_QR"],
    description="Pensión marzo",
    customer={"document": {"number": "45678912"}, "custom_fields": {"grade": "sexto"}},
    idempotency_key="pension-2026-03-45678912",
)

# Editar: solo cambian las keys enviadas; None borra el valor.
kuti.customers.update(customer.id, custom_fields={"birth_date": None})
```

## Confirmar un pago

```python
intent = kuti.payment_intents.retrieve(payment_intent_id)
if intent.status == "SUCCEEDED":
    # fulfill order
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
- `kuti.customers.create(customer, metadata=None)` / `retrieve(id)` / `update(id, ...)` / `list(...)` / `delete(id)`
- `kuti.checkout_sessions.create(...)` — Checkout.js
- `kuti.payment_intents.create(...)` — cobro directo
- `kuti.payment_intents.list(...)`
- `kuti.payment_intents.retrieve(id)`
- `kuti.payment_intents.cancel(id)`
- `kuti.payment_intents.send_whatsapp(id, ...)`
- `verify_webhook_signature(...)`
- `verify_webhook_signature(payload, signature_header, timestamp_header, secret, tolerance_seconds=300)`

## Requisitos

Python 3.9+ · sin dependencias de runtime.
