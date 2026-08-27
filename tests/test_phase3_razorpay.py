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


def test_webhook_rejects_invalid_signature_without_razorpay_call(monkeypatch) -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        db.add(
            Order(
                id=str(uuid.uuid4()),
                quote_id=str(uuid.uuid4()),
                razorpay_order_id="order_test",
                razorpay_payment_link_id=None,
                razorpay_payment_link_url=None,
                amount_paise=199900,
                currency="INR",
                status="awaiting_payment",
                is_autonomous=False,
                created_at="2026-08-24T00:00:00Z",
                updated_at="2026-08-24T00:00:00Z",
            )
        )
        db.commit()
    finally:
        db.close()

    mocked_client = Mock()
    monkeypatch.setattr("app.gateway.webhook.get_client", lambda: mocked_client)
    payload = json.dumps({"event": "payment.failed", "payload": {"payment": {"entity": {"order_id": "order_test"}}}})
    response = TestClient(app).post(
        "/api/v1/webhook/razorpay",
        content=payload,
        headers={"X-Razorpay-Signature": "invalid"},
    )

    assert response.status_code == 400
    mocked_client.payment_link.create.assert_not_called()


def test_webhook_rejects_malformed_signed_payload() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    payload = b"not-json"
    import hashlib
    import hmac

    signature = hmac.new(settings.razorpay_webhook_secret.encode(), payload, hashlib.sha256).hexdigest()
    response = TestClient(app).post(
        "/api/v1/webhook/razorpay",
        content=payload,
        headers={"X-Razorpay-Signature": signature},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "invalid webhook payload"}
def test_webhook_rejects_signed_payload_with_invalid_event_shape() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    payload = json.dumps({"event": "payment.captured", "payload": {}}).encode()
    signature = hmac.new(settings.razorpay_webhook_secret.encode(), payload, hashlib.sha256).hexdigest()
    response = TestClient(app).post(
        "/api/v1/webhook/razorpay",
        content=payload,
        headers={"X-Razorpay-Signature": signature},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "invalid webhook payload"}


def test_webhook_rejects_signed_unknown_event() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    payload = json.dumps({"event": "payment.refunded", "payload": {"payment": {"entity": {"order_id": "order_test"}}}}).encode()
    signature = hmac.new(settings.razorpay_webhook_secret.encode(), payload, hashlib.sha256).hexdigest()
    response = TestClient(app).post(
        "/api/v1/webhook/razorpay",
        content=payload,
        headers={"X-Razorpay-Signature": signature},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "invalid webhook payload"}
