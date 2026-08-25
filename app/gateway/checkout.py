import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.gateway.quote import expire_quote_if_needed, now_utc
from app.models import Order, Quote, UsedNonce
from app.razorpay_client.client import get_client
from app.ledger.writer import log_audit_trail


def initiate_checkout(db: Session, quote_id: str, nonce: str) -> Order:
    try:
        db.add(UsedNonce(nonce=nonce, used_at=now_utc()))
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise RuntimeError("nonce already used (replay detected)") from error

    quote = db.get(Quote, quote_id)
    if quote is None:
        raise LookupError("quote not found")
    if expire_quote_if_needed(db, quote):
        raise TimeoutError("quote expired")
    if quote.status != "active":
        raise RuntimeError("quote is not active")

    current_time = now_utc()
    order = Order(
        id=str(uuid.uuid4()),
        quote_id=quote.id,
        razorpay_order_id=None,
        razorpay_payment_link_id=None,
        razorpay_payment_link_url=None,
        amount_paise=quote.locked_price_paise,
        currency=quote.currency,
        status="awaiting_payment",
        is_autonomous=False,
        created_at=current_time,
        updated_at=current_time,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def create_payment_link(db: Session, order_id: str) -> Order:
    order = db.get(Order, order_id)
    if order is None:
        raise LookupError("order not found")
    if order.status != "awaiting_payment" or order.razorpay_order_id is not None:
        raise RuntimeError("order state conflict")

    client = get_client()
    razorpay_order = client.order.create(
        {
            "amount": order.amount_paise,
            "currency": "INR",
            "receipt": order.id,
            "payment_capture": 1,
        }
    )
    payment_link = client.payment_link.create(
        {
            "amount": order.amount_paise,
            "currency": "INR",
            "reference_id": order.id,
            "description": f"Payment for order {order.id}",
            "notify": {"sms": False, "email": False},
        }
    )
    order.razorpay_order_id = razorpay_order["id"]
    order.razorpay_payment_link_id = payment_link["id"]
    order.razorpay_payment_link_url = payment_link["short_url"]
    order.updated_at = now_utc()
    log_audit_trail(db, order.id, "razorpay_order_created", {})
    db.commit()
    db.refresh(order)
    return order
