import json
import uuid

from fastapi.testclient import TestClient

from app.db import Base, SessionLocal, engine
from app.main import app
from app.models import Order
from app.models.product import Product


def test_checkout_nonce_cannot_be_replayed() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    product_id = str(uuid.uuid4())
    db = SessionLocal()
    try:
        db.add(
            Product(
                id=product_id,
                name="Camera",
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

    client = TestClient(app)
    quote_response = client.post("/v1/quote", json={"product_id": product_id, "quantity": 1})
    quote_id = quote_response.json()["quote_id"]
    nonce = str(uuid.uuid4())

    first = client.post("/v1/checkout", json={"quote_id": quote_id, "nonce": nonce})
    second = client.post("/v1/checkout", json={"quote_id": quote_id, "nonce": nonce})

    assert first.status_code == 402
    assert second.status_code == 409
    assert second.json() == {"detail": "nonce already used (replay detected)"}
    db = SessionLocal()
    try:
        assert db.query(Order).count() == 1
    finally:
        db.close()
