import json
import uuid

from fastapi.testclient import TestClient

from app.db import Base, SessionLocal, engine
from app.main import app
from app.models.product import Product


def test_quote_reservation_prevents_overcommitment() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    product_id = str(uuid.uuid4())
    db = SessionLocal()
    try:
        db.add(
            Product(
                id=product_id,
                name="Only One Camera",
                category="camera",
                price_paise=199900,
                stock_qty=1,
                attributes_json=json.dumps({"compatibility": "USB-C", "delivery_days": 1}),
                embedding_json=json.dumps([0.0] * 8),
            )
        )
        db.commit()
    finally:
        db.close()

    client = TestClient(app)
    first = client.post("/v1/quote", json={"product_id": product_id, "quantity": 1})
    second = client.post("/v1/quote", json={"product_id": product_id, "quantity": 1})

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json() == {"detail": "insufficient stock"}
