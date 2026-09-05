import json
import uuid

import numpy as np

from app.db import Base, SessionLocal, engine
from app.models.product import Product


CATALOG = [
    ("Wireless Headphones", "audio", 1299900),
    ("Mechanical Keyboard", "electronics", 749900),
    ("Wireless Mouse", "electronics", 249900),
    ("USB-C Hub", "electronics", 399900),
    ("Laptop Stand", "accessory", 329900),
    ("1080p Webcam", "electronics", 599900),
    ("Bluetooth Speaker", "audio", 499900),
    ("Carrying Case", "accessory", 149900),
]
COMPATIBILITY = ["USB-C", "Lightning", "Bluetooth", "N/A"]


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    rng = np.random.default_rng(42)
    db = SessionLocal()
    try:
        db.query(Product).delete()
        for index, (name, category, price_paise) in enumerate(CATALOG):
            db.add(
                Product(
                    id=str(uuid.uuid4()),
                    name=name,
                    category=category,
                    price_paise=price_paise,
                    stock_qty=10,
                    attributes_json=json.dumps(
                        {
                            "compatibility": COMPATIBILITY[index % len(COMPATIBILITY)],
                            "delivery_days": (index % 5) + 1,
                        }
                    ),
                    embedding_json=json.dumps(rng.random(8).tolist()),
                )
            )
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed()
