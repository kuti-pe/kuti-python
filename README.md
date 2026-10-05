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

Todas las excepciones de la API extienden `KutiApiError` (`status`, `code`, `request_id`, `correlation_id`, `doc_url`, `details`):

```python
from kuti import KutiValidationError, KutiNotFoundError, KutiPermissionError, KutiApiError

try:
    kuti.checkout_sessions.create(...)
except KutiValidationError as err:
    print(err.details)  # [ErrorDetail(field="amount.amount", ...)]
except KutiNotFoundError:
    pass
except KutiPermissionError as err:
    if err.is_insufficient_scope:
        ...  # a la API key le falta el permiso de este endpoint (edítala en el panel o usa otra)
    elif err.is_dashboard_only:
        ...  # endpoint solo del panel de KUTI (p. ej. cambiar la cuenta bancaria)
except KutiApiError as err:
    print(err.code, err.request_id)  # úsalo al reportar un bug a soporte
    diagnosis = kuti.diagnostics.get_request(err.request_id)  # qué pasó con esa llamada
```

Los `GET` y los `POST` con `idempotency_key` se reintentan automáticamente en errores de red o `429`/`503`. Un `POST` sin `idempotency_key` nunca se reintenta, para no duplicar un cobro.


## Links de pago

Un enlace permanente que pagan muchas personas (curso, entrada, donación). Cada pago es un cobro
normal con `payment_link_id`.

```python
link = kuti.payment_links.create(
    title="Taller de Excel — sábado 10am",
    template="COURSE",
    pricing="FIXED",
    amount="120.00",
    payment_method_types=["INTEROPERABLE_QR", "BANK_TRANSFER"],
    customer_field_ids=["cfd_…"],  # [] = solo nombre, apellido y correo
    button_label="Inscribirme",
    success_message="¡Listo! Te esperamos el sábado.",
    success_button_label="Unirme al grupo",
    success_button_url="https://chat.whatsapp.com/…",
)
print(link.url)  # https://pay.kuti.pe/l/taller-de-excel

# Quienes pagaron el link
paid = kuti.payment_intents.list(payment_link_id=link.id, status="SUCCEEDED", per_page="all")
```

## Enviar el cobro al crearlo

```python
kuti.payment_intents.create(
    amount={"amount": "250.00", "currency": "PEN"},
    payment_method_types=["INTEROPERABLE_QR"],
    customer={"id": "cus_…"},
    send_via=["EMAIL", "WHATSAPP"],  # None = ["EMAIL"]; [] = no enviar
)
```

## Yape afiliado y suscripciones

> Por ahora solo en **modo prueba** (claves `kuti_test_…`). En producción estará disponible
> cuando Yape afiliado quede habilitado para tu negocio.

Con `"YAPE"` en `payment_method_types`, tu cliente aprueba una sola vez desde su app y su Yape
queda afiliado a tu negocio. Desde ahí puedes cobrarle sin que vuelva a aprobar.

```python
# Qué tiene guardado el cliente
methods = kuti.customers.list_payment_methods("cus_…")

# Cobrarle ahora, sin que esté presente
pi = kuti.payment_intents.create(
    amount={"amount": "80.00", "currency": "PEN"},
    payment_method_types=["YAPE"],
    customer={"id": "cus_…"},
    description="Pedido #1042",
    send_via=[],
    payment_method=methods[0]["id"],
    confirm=True,
    idempotency_key="pedido-1042",
)
# pi.status == "SUCCEEDED", o pi.last_saved_method_payment["failure_code"] (p. ej.
# "insufficient_funds") y el cobro queda abierto: su enlace (pi.checkout_url) sigue sirviendo.

# Enviarle un enlace donde vea su Yape guardado y pague con un toque (vale 30 minutos)
kuti.payment_intents.create(
    amount={"amount": "120.00", "currency": "PEN"},
    payment_method_types=["YAPE", "INTEROPERABLE_QR"],
    customer={"id": "cus_…"},
    saved_payment_methods="enabled",
)

# Tienda con login propio que incrusta el checkout: la llave se la pasas a KUTI.js
session = kuti.payment_intents.create_customer_session(pi.id)
```

**Suscripción de monto fijo.** KUTI cobra solo cada periodo (máximo S/ 2,500).

```python
sub = kuti.subscriptions.create(
    customer={"id": "cus_…"},
    description="Plan Pro",
    amount="99.00",
    frequency="MONTHLY",
    charge_time="09:00",  # hora de Perú; nunca entre 01:00 y 03:00
    retry_policy={"interval_days": [1, 3, 5], "on_exhausted": "past_due"},  # opcional
    metadata={"workspace_id": "ws_4821"},
)

if sub.status == "INCOMPLETE":
    # El cliente aún no tiene su Yape afiliado: debe afiliarlo y pagar el primer periodo aquí.
    print(sub.latest_cycle["checkout_url"])
```

**Suscripción de monto variable** (por consumo). Al crearla no se cobra nada; se cobra a periodo
vencido y tú envías el monto de cada periodo.

```python
sub = kuti.subscriptions.create(
    customer={"id": "cus_…"},
    description="LIA por consumo",
    billing_mode="variable",
    frequency="MONTHLY",
)
# Si falta afiliar: sub.setup_url (también se lo enviamos por correo).

# Al recibir el webhook subscription.amount_required (o al cerrar tu periodo):
kuti.subscriptions.charge(
    sub.id,
    amount="184.00",
    description="92 alumnos en octubre",
    period="2026-10",
    idempotency_key=f"consumo-{sub.id}-2026-10",
)
```

Eventos: `subscription.created`, `.activated`, `.payment_succeeded`, `.payment_failed`,
`.amount_required`, `.period_skipped`, `.updated`, `.paused`, `.resumed`, `.cancelled`,
`.completed`. El `data` es la suscripción completa; `latest_cycle` trae el motivo del fallo, el
intento y cuándo se reintenta. KUTI no corta tu servicio: tú decides qué hacer con cada aviso.

## API

- `KutiClient(secret_key, base_url=None)`
- `kuti.customers.create(customer, metadata=None)` / `retrieve(id)` / `update(id, ...)` / `list(...)` / `delete(id)`
- `kuti.checkout_sessions.create(...)` — Checkout.js
- `kuti.payment_intents.create(...)` — cobro directo
- `kuti.payment_intents.list(...)` — filtros `status`, `q`, `customer_id`, `source` (single | link | subscription), `payment_link_id`
- `kuti.payment_intents.retrieve(id)`
- `kuti.payment_intents.cancel(id)`
- `kuti.payment_intents.send_whatsapp(id, ...)`
- `kuti.payment_intents.enable_saved_payment_methods(id)` / `create_customer_session(id)` — mostrar el Yape guardado en el checkout
- `kuti.customers.list_payment_methods(id)` / `detach_payment_method(id, payment_method_id)` — Yape afiliado del cliente
- `kuti.subscriptions.create(...)` / `retrieve(id)` / `list(...)` / `update(id, ...)` / `pause(id)` / `resume(id)` / `cancel(id)` / `retry(id)` / `charge(id, amount=..., description=None, period=None)` / `list_cycles(id)`
- `kuti.payment_links.create(...)` / `retrieve(id)` / `update(id, ...)` / `list(...)` / `activate(id)` / `deactivate(id)` / `check_slug(slug, except_id=None)`
- `kuti.payment_exceptions.list(...)` / `resolve(id, status=..., note=None)` — pagos para revisar
- `kuti.webhook_deliveries.retrieve(id)` / `retry(id)` — cada intento con el status HTTP y lo que respondió tu servidor
- `kuti.diagnostics.get_request(request_id)` / `list_by_correlation_id(id)` / `trace_payment_intent(id)` — permiso `diagnostics:read`
- `verify_webhook_signature(payload, signature_header, timestamp_header, secret, tolerance_seconds=300)`

## Requisitos

Python 3.9+ · sin dependencias de runtime.
