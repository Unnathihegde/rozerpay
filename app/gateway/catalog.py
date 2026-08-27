import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.product import Product


class CatalogSearch:
    def __init__(self, db: Session):
        self.db = db

    def query(self, constraints: dict, top_k: int = 10) -> list[Product]:
        statement = select(Product)
        if "max_price_paise" in constraints:
            statement = statement.where(Product.price_paise <= constraints["max_price_paise"])
        if "category" in constraints:
            statement = statement.where(Product.category == constraints["category"])

        products = list(self.db.scalars(statement))
        if "compatibility" in constraints:
            products = [
                product
                for product in products
                if product.attributes.get("compatibility") == constraints["compatibility"]
            ]
        if "max_delivery_days" in constraints:
            products = [
                product
                for product in products
                if product.attributes.get("delivery_days", 0)
                <= constraints["max_delivery_days"]
            ]

        query_embedding = constraints.get("query_embedding")
        if query_embedding is not None:
            query_vector = np.asarray(query_embedding, dtype=float)
            query_norm = np.linalg.norm(query_vector)

            def similarity(product: Product) -> float:
                product_vector = np.asarray(product.embedding, dtype=float)
                denominator = query_norm * np.linalg.norm(product_vector)
                return float(np.dot(query_vector, product_vector) / denominator) if denominator else 0.0

            products.sort(key=similarity, reverse=True)
        else:
            products.sort(key=lambda product: product.price_paise)
        return products[:top_k]


UPSELL_RULES = {
    "camera": {"add": "lens_cleaner_kit", "margin_delta_pct": 12},
    "audio": {"add": "carrying_case", "margin_delta_pct": 8},
    "accessory": {"add": None, "margin_delta_pct": 0},
}


def suggest_upsell(product: Product) -> dict | None:
    rule = UPSELL_RULES.get(product.category)
    if rule is None:
        return None
    if rule["add"] is None:
        return None
    return {
        "suggested_item": rule["add"],
        "reason": f"item_category == {product.category} -> add {rule['add']}",
        "margin_delta": f"+{rule['margin_delta_pct']}%",
    }
