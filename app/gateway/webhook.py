import hashlib
import hmac
import json
import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.config import settings
from app.gateway.quote import now_utc
from app.ledger.writer import log_audit_trail
from app.models import Order, Product, Quote, WebhookEvent
from app.razorpay_client.client import get_client


VALID_WEBHOOK_EVENTS = {"payment.captured", "payment.failed"}


def verify_webhook_signature(payload: bytes, received_signature: str | None) -> bool:
    if not received_signature:
        return False
    expected = hmac.new(
        settings.razorpay_webhook_secret.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(received_signature, expected)


def _read_event_id(event: dict, entity: dict) -> str | None:
    for value in (
        event.get("event_id"),
        event.get("id"),
        entity.get("id"),
        entity.get("payment_id"),
        entity.get("order_id"),
    ):
        if value:
            return str(value)
    return None


def _read_order_id(entity: dict) -> str | None:
    if not isinstance(entity, dict):
        return None
    value = entity.get("order_id")
    return str(value) if value else None


def _read_payment_timestamp(entity: dict) -> str | None:
    timestamp = entity.get("created_at")
    if timestamp is None:
        return None
    try:
        dt = datetime.fromtimestamp(int(timestamp), UTC)
        return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    except (TypeError, ValueError, OSError):
        return None


def _get_or_create_webhook_record(db: Session, event_name: str, order: Order | None, payload: bytes, event: dict) -> WebhookEvent | None:
    entity = event.get("payload", {}).get("payment", {}).get("entity", {})
    event_key = _read_event_id(event, entity) or f"{event_name}:{_read_order_id(entity) or 'unknown'}"
    digest = hashlib.sha256(payload).hexdigest()
    record = db.query(WebhookEvent).filter(WebhookEvent.event_key == event_key).one_or_none()
    if record is None:
        record = WebhookEvent(
            event_key=event_key,
            event_type=event_name,
            order_id=order.id if order is not None else _read_order_id(entity),
            payment_id=str(entity.get("id")) if isinstance(entity, dict) and entity.get("id") else None,
            processed_at=now_utc(),
            payload_sha256=digest,
            raw_payload=json.dumps(event, separators=(",", ":"), sort_keys=True),
        )
        db.add(record)
        db.commit()
    return record


def process_webhook(db: Session, payload: bytes) -> dict:
    event = json.loads(payload)
    if not isinstance(event, dict):
        raise ValueError("invalid webhook payload")
    event_name = event.get("event")
    if event_name not in VALID_WEBHOOK_EVENTS:
        raise ValueError("unsupported webhook event")
    entity = event.get("payload", {}).get("payment", {}).get("entity", {})
    if not isinstance(entity, dict) or not _read_order_id(entity):
        raise ValueError("webhook payment order_id is required")
    razorpay_order_id = _read_order_id(entity)
    order = db.query(Order).filter(Order.razorpay_order_id == razorpay_order_id).one_or_none()
    record = _get_or_create_webhook_record(db, event_name, order, payload, event)
    if record is not None and order is not None and order.webhook_event_id == record.event_key and order.webhook_processing_status == "processed":
        return {"status": "duplicate", "event_id": record.event_key, "event_type": event_name, "order_id": order.id}

    if order is None:
        return {"status": "ignored", "event_id": record.event_key if record else None, "event_type": event_name, "reason": "order_not_found"}

    order.webhook_received_at = now_utc()
    order.webhook_event_id = record.event_key
    order.webhook_event_type = event_name
    order.webhook_verified = True
    order.webhook_processing_status = "received"

    if event_name == "payment.captured":
        order.payment_id = str(entity.get("id") or order.payment_id)
        order.payment_status = "captured"
        order.payment_method = entity.get("method") or order.payment_method
        order.payment_amount_paise = int(entity.get("amount") or order.amount_paise)
        order.payment_currency = entity.get("currency") or order.currency
        order.payment_timestamp = _read_payment_timestamp(entity) or order.payment_timestamp or now_utc()
        quote = db.get(Quote, order.quote_id)
        product = db.get(Product, quote.product_id) if quote else None
        if quote and product and order.status != "paid":
            product.stock_qty = max(0, product.stock_qty - quote.quantity)
            quote.status = "consumed"
            order.status = "paid"
            order.updated_at = now_utc()
            log_audit_trail(db, order.id, "settlement_status", {"status": "paid", "payment_id": order.payment_id})
        order.webhook_processing_status = "processed"
        db.commit()
        return {"status": "ok", "event_id": record.event_key, "event_type": event_name, "order_id": order.id}

    if event_name == "payment.failed":
        if order.status == "recovered_pending_retry" and order.webhook_event_id == record.event_key:
            order.webhook_processing_status = "processed"
            db.commit()
            return {"status": "duplicate", "event_id": record.event_key, "event_type": event_name, "order_id": order.id}
        order.payment_id = str(entity.get("id") or order.payment_id)
        order.payment_status = "failed"
        order.payment_method = entity.get("method") or order.payment_method
        order.payment_amount_paise = int(entity.get("amount") or order.amount_paise)
        order.payment_currency = entity.get("currency") or order.currency
        order.payment_timestamp = _read_payment_timestamp(entity) or order.payment_timestamp or now_utc()
        quote = db.get(Quote, order.quote_id)
        if quote and quote.status == "active":
            quote.status = "expired"
        fallback_link = get_client().payment_link.create(
            {
                "amount": order.amount_paise,
                "currency": "INR",
                "reference_id": f"{order.id}-retry-{uuid.uuid4().hex[:8]}",
                "description": f"Payment retry for order {order.id}",
                "notify": {"sms": False, "email": False},
            }
        )
        order.razorpay_payment_link_id = fallback_link["id"]
        order.razorpay_payment_link_url = fallback_link["short_url"]
        order.status = "recovered_pending_retry"
        order.updated_at = now_utc()
        order.webhook_processing_status = "processed"
        log_audit_trail(
            db,
            order.id,
            "settlement_status",
            {
                "status": "failed",
                "error_code": entity.get("error_code"),
                "recovery_link": order.razorpay_payment_link_url,
                "inventory_status": "RELEASED",
            },
        )
        log_audit_trail(
            db,
            order.id,
            "PAYMENT_FAILURE_RECOVERY",
            {"recovery_link": order.razorpay_payment_link_url},
        )
        db.commit()
        return {"status": "ok", "event_id": record.event_key, "event_type": event_name, "order_id": order.id}

    raise ValueError("unsupported webhook event")
