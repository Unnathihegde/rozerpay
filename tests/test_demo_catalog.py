import hashlib
import hmac
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.mcp_server.server import apply_discount_or_upsell, search_catalog
from seed import seed


def test_seeded_catalog_supports_demo_discovery_and_quote() -> None:
    seed()
    client = TestClient(app)

    response = client.get("/catalog.jsonld")
    assert response.status_code == 200
    products = {item["name"]: item for item in response.json()["itemListElement"]}
    assert len(products) == 8
    assert {"Wireless Headphones", "Mechanical Keyboard", "Wireless Mouse"} <= products.keys()

    assert search_catalog({"query": "wireless headphones"})["count"] == 1
    assert search_catalog({"query": "keyboard"})["count"] == 1
    assert search_catalog({"query": "mouse"})["count"] == 1
    assert search_catalog({"query": "electronics"})["count"] == 4

    product_id = products["Wireless Headphones"]["@id"]
    quote = client.post("/v1/quote", json={"product_id": product_id, "quantity": 1}).json()
    signing_message = "|".join(
        [
            quote["quote_id"],
            quote["product_id"],
            str(quote["quantity"]),
            str(quote["locked_price_paise"]),
            quote["expires_at"],
        ]
    )
    expires_at = datetime.fromisoformat(quote["expires_at"].replace("Z", "+00:00"))
    remaining_seconds = (expires_at - datetime.now(UTC)).total_seconds()

    assert isinstance(quote["locked_price_paise"], int)
    assert hmac.compare_digest(
        quote["signature"],
        hmac.new(settings.quote_signing_secret.encode(), signing_message.encode(), hashlib.sha256).hexdigest(),
    )
    assert 14 * 60 < remaining_seconds <= 15 * 60
    assert apply_discount_or_upsell(quote["quote_id"])["suggested_item"] == "Carrying Case"