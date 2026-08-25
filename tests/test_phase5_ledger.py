import hashlib
import hmac
import json
import uuid
from unittest.mock import Mock

from fastapi.testclient import TestClient


from app.config import settings
from app.db import Base, SessionLocal, engine
from app.main import app
from app.models.product import Product


def test_happy_path_audit_sequence(monkeypatch) -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    product_id = str(uuid.uuid4())
    db = SessionLocal()
    try:
        db.add(
            Product(
                id=product_id,
                name="Ledger Camera",
                category="camera",
                price_paise=199900,
                stock_qty=2,
                attributes_json=json.dumps({"compatibility": "USB-C", "delivery_days": 1}),
                embedding_json=json.dumps([0.0] * 8),
            )
        )
        db.commit()
    finally:
        db.close()

    mocked_client = Mock()
    mocked_client.order.create.return_value = {"id": "order_rzp_ledger"}
    mocked_client.payment_link.create.return_value = {
        "id": "plink_ledger",
        "short_url": "https://rzp.io/i/ledger",
    }
    monkeypatch.setattr("app.gateway.checkout.get_client", lambda: mocked_client)

    client = TestClient(app)
    quote = client.post("/v1/quote", json={"product_id": product_id, "quantity": 1}).json()
    checkout = client.post(
        "/v1/checkout", json={"quote_id": quote["quote_id"], "nonce": str(uuid.uuid4())}
    ).json()
    client.post(f"/v1/orders/{checkout['order_id']}/pay", json={"mode": "link"})

    payload = json.dumps(
        {
            "event": "payment.captured",
            "payload": {"payment": {"entity": {"order_id": "order_rzp_ledger"}}},
        }
    ).encode()
    signature = hmac.new(settings.razorpay_webhook_secret.encode(), payload, hashlib.sha256).hexdigest()
    response = client.post(
        "/api/v1/webhook/razorpay",
        content=payload,
        headers={"X-Razorpay-Signature": signature},
    )
    audit = client.get(f"/v1/orders/{checkout['order_id']}/audit")

    assert response.status_code == 200
    assert [item["step"] for item in audit.json()["items"]] == [
        "intent_received",
        "quote_generated",
        "policy_check_passed",
        "razorpay_order_created",
        "settlement_status",
    ]
