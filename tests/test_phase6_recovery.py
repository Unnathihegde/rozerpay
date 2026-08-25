import hashlib
import hmac
import json
import uuid
from unittest.mock import Mock

from fastapi.testclient import TestClient

from app.config import settings
from app.db import Base, SessionLocal, engine
from app.main import app
from app.models import Order
from app.models.product import Product


def test_payment_failure_recovers_with_fallback_link_and_releases_reservation(monkeypatch) -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    product_id = str(uuid.uuid4())
    db = SessionLocal()
    try:
        db.add(
            Product(
                id=product_id,
                name="Recovery Camera",
                category="camera",
                price_paise=199900,
                stock_qty=3,
                attributes_json=json.dumps({"compatibility": "USB-C", "delivery_days": 1}),
                embedding_json=json.dumps([0.0] * 8),
            )
        )
        db.commit()
    finally:
        db.close()

    mocked_client = Mock()
    mocked_client.order.create.return_value = {"id": "order_rzp_recovery"}
    mocked_client.payment_link.create.side_effect = [
        {"id": "plink_initial", "short_url": "https://rzp.io/i/initial"},
        {"id": "plink_fallback", "short_url": "https://rzp.io/i/fallback"},
    ]
    monkeypatch.setattr("app.gateway.checkout.get_client", lambda: mocked_client)
    monkeypatch.setattr("app.gateway.webhook.get_client", lambda: mocked_client)

    client = TestClient(app)
    quote = client.post("/v1/quote", json={"product_id": product_id, "quantity": 1}).json()
    checkout = client.post(
        "/v1/checkout", json={"quote_id": quote["quote_id"], "nonce": str(uuid.uuid4())}
    ).json()
    pay = client.post(f"/v1/orders/{checkout['order_id']}/pay", json={"mode": "link"})
    assert pay.status_code == 200

    payload = json.dumps(
        {
            "event": "payment.failed",
            "payload": {
                "payment": {
                    "entity": {"order_id": "order_rzp_recovery", "error_code": "PAYMENT_FAILED"}
                }
            },
        }
    ).encode()
    signature = hmac.new(settings.razorpay_webhook_secret.encode(), payload, hashlib.sha256).hexdigest()
    webhook = client.post(
        "/api/v1/webhook/razorpay",
        content=payload,
        headers={"X-Razorpay-Signature": signature},
    )

    db = SessionLocal()
    try:
        order = db.get(Order, checkout["order_id"])
        product = db.get(Product, product_id)
    finally:
        db.close()
    audit = client.get(f"/v1/orders/{checkout['order_id']}/audit").json()
    failed_settlement = next(item for item in audit["items"] if item["step"] == "settlement_status")

    assert webhook.status_code == 200
    assert order.status == "recovered_pending_retry"
    assert order.razorpay_payment_link_url == "https://rzp.io/i/fallback"
    assert product.stock_qty == 3
    assert failed_settlement["details"]["status"] == "failed"
    assert failed_settlement["details"]["recovery_link"] is not None
