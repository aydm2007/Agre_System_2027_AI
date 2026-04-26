import hmac, hashlib

import threading, json, httpx
from django.utils import timezone
from .models import WebhookEndpoint, OutboundDelivery

def dispatch_event(event:str, payload:dict):
    endpoints = WebhookEndpoint.objects.filter(is_active=True, event__in=[event,"audit"])
    for ep in endpoints:
        delivery = OutboundDelivery.objects.create(endpoint=ep, payload=payload, status="pending", attempts=0)
        threading.Thread(target=_send, args=(delivery.id,), daemon=True).start()

def _send(delivery_id:int):
    from .models import OutboundDelivery
    d = OutboundDelivery.objects.get(id=delivery_id)
    try:
        d.attempts += 1
        d.last_attempt = timezone.now()
        headers = {"Content-Type": "application/json"}
        if d.endpoint.secret:
            sig = hmac.new(d.endpoint.secret.encode('utf-8'), json.dumps(d.payload, ensure_ascii=False).encode('utf-8'), hashlib.sha256).hexdigest()
            headers["X-Webhook-Secret"] = d.endpoint.secret
            headers["X-Webhook-Signature"] = sig
        r = httpx.post(d.endpoint.url, json=d.payload, headers=headers, timeout=10)
        d.response_code = r.status_code
        d.response_text = r.text[:1000]
        d.status = "sent" if r.status_code < 400 else "failed"
    except (ConnectionError, TimeoutError, ValueError, OSError) as e:
        d.status = "failed"; d.response_text = str(e)[:1000]
    d.save(update_fields=["attempts","last_attempt","response_code","response_text","status"])
