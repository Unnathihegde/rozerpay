import json
import uuid
from unittest.mock import Mock

from fastapi.testclient import TestClient

from app.db import Base, SessionLocal, engine
from app.main import app
from app.models.product import Product


def _checkout_for_price(price_paise: int) -> tuple[TestClient, str]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    product_id = str(uuid.uuid4())
    db = SessionLocal()
    try:
        db.add(
            Product(
                id=product_id,
                name="Safety Camera",
                category="camera",
                price_paise=price_paise,
                stock_qty=2,
                attributes_json=json.dumps({"compatibility": "USB-C", "delivery_days": 1}),
                embedding_json=json.dumps([0.0] * 8),
            )
        )
        db.commit()
    finally:
        db.close()
    client = TestClient(app)
    quote = client.post("/v1/quote", json={"product_id": product_id, "quantity": 1}).json()
    checkout = client.post(
        "/v1/checkout", json={"quote_id": quote["quote_id"], "nonce": str(uuid.uuid4())}
    )
    return client, checkout.json()["order_id"]


def _mocked_razorpay_client() -> Mock:
    client = Mock()
    client.order.create.return_value = {"id": "order_rzp_test"}
    client.payment_link.create.return_value = {
        "id": "plink_test",
        "short_url": "https://rzp.io/i/test",
    }
    return client


def test_under_limit_payment_calls_razorpay(monkeypatch) -> None:
    client, order_id = _checkout_for_price(199900)
    mocked_client = _mocked_razorpay_client()
    monkeypatch.setattr("app.gateway.checkout.get_client", lambda: mocked_client)

    response = client.post(f"/v1/orders/{order_id}/pay", json={"mode": "link"})

    assert response.status_code == 200
    mocked_client.order.create.assert_called_once()


def test_over_limit_requires_approval_before_payment(monkeypatch) -> None:
    client, order_id = _checkout_for_price(1000001)
    mocked_client = _mocked_razorpay_client()
    monkeypatch.setattr("app.gateway.checkout.get_client", lambda: mocked_client)

    pending = client.post(f"/v1/orders/{order_id}/pay", json={"mode": "link"})
    repeated = client.post(f"/v1/orders/{order_id}/pay", json={"mode": "link"})
    approval_id = pending.json()["approval_id"]
    approved = client.post(f"/v1/approvals/{approval_id}/approve")
    paid = client.post(f"/v1/orders/{order_id}/pay", json={"mode": "link"})

    assert pending.status_code == 202
    assert repeated.status_code == 202
    assert approved.status_code == 200
    assert paid.status_code == 200
    mocked_client.order.create.assert_called_once()


def test_client_amount_cannot_override_quote() -> None:
    client, order_id = _checkout_for_price(199900)

    response = client.post(
        f"/v1/orders/{order_id}/pay", json={"mode": "link", "amount_paise": 1}
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "price manipulation detected: client-supplied amount does not match locked quote"
    }
