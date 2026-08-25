import json
import uuid

import numpy as np

from app.db import Base, SessionLocal, engine
from app.models.product import Product


CATALOG = [
    ("Travel Camera", "camera", 4599900),
    ("Compact Camera", "camera", 2999900),
    ("Mirrorless Camera", "camera", 6999900),
    ("Action Camera", "camera", 2499900),
    ("Studio Camera", "camera", 8999900),
    ("Wireless Headphones", "audio", 1599900),
    ("Bluetooth Speaker", "audio", 899900),
    ("Noise Cancelling Earbuds", "audio", 1199900),
    ("Podcast Microphone", "audio", 749900),
    ("Portable DAC", "audio", 999900),
    ("USB-C Cable", "accessory", 99900),
    ("Lightning Cable", "accessory", 129900),
    ("Bluetooth Tracker", "accessory", 199900),
    ("Camera Strap", "accessory", 149900),
    ("Lens Cleaner Kit", "accessory", 79900),
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
