import hashlib
import hmac
import json

from sqlalchemy.orm import Session

from app.config import settings
from app.gateway.quote import now_utc
from app.models import Order, Product, Quote
from app.razorpay_client.client import get_client
from app.ledger.writer import log_audit_trail


def verify_webhook_signature(payload: bytes, received_signature: str | None) -> bool:
    if not received_signature:
        return False
    expected = hmac.new(
        settings.razorpay_webhook_secret.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(received_signature, expected)


def process_webhook(db: Session, payload: bytes) -> None:
    event = json.loads(payload)
    if not isinstance(event, dict):
        raise ValueError("invalid webhook payload")
    event_name = event.get("event")
    if event_name not in {"payment.captured", "payment.failed"}:
        raise ValueError("unsupported webhook event")
    entity = event.get("payload", {}).get("payment", {}).get("entity", {})
    if not isinstance(entity, dict) or not entity.get("order_id"):
        raise ValueError("webhook payment order_id is required")
    razorpay_order_id = entity.get("order_id")
    order = db.query(Order).filter(Order.razorpay_order_id == razorpay_order_id).one_or_none()
    if order is None:
        return

    if event_name == "payment.captured":
        quote = db.get(Quote, order.quote_id)
        product = db.get(Product, quote.product_id) if quote else None
        if quote and product and order.status != "paid":
            product.stock_qty -= quote.quantity
            quote.status = "consumed"
            order.status = "paid"
            order.updated_at = now_utc()
            log_audit_trail(db, order.id, "settlement_status", {"status": "paid"})
            db.commit()
        return

    if event_name == "payment.failed":
        if order.status == "recovered_pending_retry":
            return
        quote = db.get(Quote, order.quote_id)
        if quote and quote.status == "active":
            quote.status = "expired"
        fallback_link = get_client().payment_link.create(
            {
                "amount": order.amount_paise,
                "currency": "INR",
                "reference_id": order.id,
                "description": f"Payment retry for order {order.id}",
                "notify": {"sms": False, "email": False},
            }
        )
        order.razorpay_payment_link_id = fallback_link["id"]
        order.razorpay_payment_link_url = fallback_link["short_url"]
        order.status = "recovered_pending_retry"
        order.updated_at = now_utc()
        log_audit_trail(
            db,
            order.id,
            "settlement_status",
            {
                "status": "failed",
                "error_code": entity.get("error_code"),
                "recovery_link": fallback_link["short_url"],
                "inventory_status": "RELEASED",
            },
        )
        log_audit_trail(
            db,
            order.id,
            "PAYMENT_FAILURE_RECOVERY",
            {"recovery_link": fallback_link["short_url"]},
        )
        db.commit()
