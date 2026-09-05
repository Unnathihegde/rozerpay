import json
import uuid

import numpy as np

from app.db import Base, SessionLocal, engine, ensure_schema_compatibility
from app.models.product import Product


CATALOG = [
    ("Wireless Headphones", "audio", 1299900, "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=1200&q=85"),
    ("Mechanical Keyboard", "electronics", 749900, "https://images.unsplash.com/photo-1587829741301-dc798b83add3?auto=format&fit=crop&w=1200&q=85"),
    ("Wireless Mouse", "electronics", 249900, "https://images.unsplash.com/photo-1527814050087-3793815479db?auto=format&fit=crop&w=1200&q=85"),
    ("USB-C Hub", "electronics", 399900, "https://images.unsplash.com/photo-1625842268584-8f3296236761?auto=format&fit=crop&w=1200&q=85"),
    ("Laptop Stand", "accessory", 329900, "https://images.unsplash.com/photo-1618424181497-157f25b6ddd5?auto=format&fit=crop&w=1200&q=85"),
    ("1080p Webcam", "electronics", 599900, "https://images.unsplash.com/photo-1587825140708-dfaf72ae4b04?auto=format&fit=crop&w=1200&q=85"),
    ("Bluetooth Speaker", "audio", 499900, "https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?auto=format&fit=crop&w=1200&q=85"),
    ("Carrying Case", "accessory", 149900, "https://images.unsplash.com/photo-1548036328-c9fa89d128fa?auto=format&fit=crop&w=1200&q=85"),
]
COMPATIBILITY = ["USB-C", "Lightning", "Bluetooth", "N/A"]


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_schema_compatibility()
    rng = np.random.default_rng(42)
    db = SessionLocal()
    try:
        db.query(Product).delete()
        for index, (name, category, price_paise, image_url) in enumerate(CATALOG):
            db.add(
                Product(
                    id=str(uuid.uuid4()),
                    name=name,
                    category=category,
                    price_paise=price_paise,
                    stock_qty=10,
                    image_url=image_url,
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
