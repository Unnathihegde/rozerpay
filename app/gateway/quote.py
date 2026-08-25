from datetime import UTC, datetime, timedelta
import hashlib
import hmac
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.product import Product
from app.models.quote import Quote


def now_utc() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def quote_signature(
    quote_id: str, product_id: str, quantity: int, locked_price_paise: int, expires_at: str
) -> str:
    message = "|".join(
        [quote_id, product_id, str(quantity), str(locked_price_paise), expires_at]
    )
    return hmac.new(
        settings.quote_signing_secret.encode(), message.encode(), hashlib.sha256
    ).hexdigest()


def verify_quote_signature(quote: Quote) -> bool:
    expected = quote_signature(
        quote.id, quote.product_id, quote.quantity, quote.locked_price_paise, quote.expires_at
    )
    return hmac.compare_digest(quote.signature, expected)


def expire_quote_if_needed(db: Session, quote: Quote) -> bool:
    if quote.status == "active" and now_utc() > quote.expires_at:
        quote.status = "expired"
        db.commit()
        return True
    return quote.status == "expired"


def create_quote(db: Session, product_id: str, quantity: int) -> Quote:
    product = db.get(Product, product_id)
    if product is None:
        raise LookupError("product not found")
    if quantity <= 0:
        raise ValueError("quantity must be at least 1")
    if product.stock_qty < quantity:
        raise RuntimeError("insufficient stock")

    current_time = now_utc()
    reserved_quantity = db.scalar(
        select(func.coalesce(func.sum(Quote.quantity), 0)).where(
            Quote.product_id == product_id,
            Quote.status == "active",
            Quote.expires_at > current_time,
        )
    )
    if reserved_quantity + quantity > product.stock_qty:
        raise RuntimeError("insufficient stock")

    quote_id = str(uuid.uuid4())
    expires_at = (
        datetime.fromisoformat(current_time.replace("Z", "+00:00")) + timedelta(minutes=15)
    ).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    locked_price_paise = product.price_paise * quantity
    quote = Quote(
        id=quote_id,
        product_id=product_id,
        quantity=quantity,
        locked_price_paise=locked_price_paise,
        currency="INR",
        created_at=current_time,
        expires_at=expires_at,
        signature=quote_signature(quote_id, product_id, quantity, locked_price_paise, expires_at),
        status="active",
    )
    db.add(quote)
    db.commit()
    db.refresh(quote)
    return quote
