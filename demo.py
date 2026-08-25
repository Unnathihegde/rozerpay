"""End-to-end Merchant Agent Gateway demo.

Razorpay Test Mode credentials are required in .env before running this script.
Start the local server first with: uvicorn app.main:app --reload
"""

import hashlib
import hmac
import json
import os
import uuid
from decimal import Decimal

import httpx
from dotenv import load_dotenv


BASE_URL = "http://localhost:8000"


def pretty(value: object) -> None:
    print(json.dumps(value, indent=2))


def create_quote(client: httpx.Client, product_id: str) -> dict:
    response = client.post("/v1/quote", json={"product_id": product_id, "quantity": 1})
    response.raise_for_status()
    quote = response.json()
    print("Quote:")
    pretty(quote)
    return quote


def checkout(client: httpx.Client, quote_id: str) -> dict:
    response = client.post("/v1/checkout", json={"quote_id": quote_id, "nonce": str(uuid.uuid4())})
    if response.status_code != 402:
        response.raise_for_status()
        raise RuntimeError("checkout did not return HTTP 402")
    negotiation = response.json()
    print("HTTP 402 payment negotiation:")
    pretty(negotiation)
    return negotiation


def pay(client: httpx.Client, order_id: str) -> dict:
    response = client.post(f"/v1/orders/{order_id}/pay", json={"mode": "link"})
    response.raise_for_status()
    payment = response.json()
    print("Razorpay payment link:")
    pretty(payment)
    return payment


def send_webhook(client: httpx.Client, event: str, razorpay_order_id: str, **fields: str) -> dict:
    payload = {
        "event": event,
        "payload": {"payment": {"entity": {"order_id": razorpay_order_id, **fields}}},
    }
    body = json.dumps(payload).encode()
    signature = hmac.new(
        os.environ["RAZORPAY_WEBHOOK_SECRET"].encode(), body, hashlib.sha256
    ).hexdigest()
    response = client.post(
        "/api/v1/webhook/razorpay",
        content=body,
        headers={"X-Razorpay-Signature": signature},
    )
    response.raise_for_status()
    return response.json()


def show_audit(client: httpx.Client, order_id: str) -> None:
    response = client.get(f"/v1/orders/{order_id}/audit")
    response.raise_for_status()
    print("Audit trail:")
    pretty(response.json())


def product_price_paise(product: dict) -> int:
    return int(Decimal(product["offers"]["price"]) * 100)


def main() -> None:
    load_dotenv()
    if not os.environ.get("RAZORPAY_WEBHOOK_SECRET"):
        raise RuntimeError("RAZORPAY_WEBHOOK_SECRET must be set in .env")

    print("Razorpay Test Mode credentials are required for this demo.")
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        catalog_response = client.get("/catalog.jsonld")
        catalog_response.raise_for_status()
        catalog = catalog_response.json()
        products = catalog["itemListElement"]
        print(f"Catalog count: {len(products)}")

        cheap_product = min(products, key=product_price_paise)
        expensive_product = max(products, key=product_price_paise)

        print("\nScenario A — Normal autonomous transaction")
        quote_a = create_quote(client, cheap_product["@id"])
        upsell = client.post(f"/v1/quote/{quote_a['quote_id']}/upsell")
        upsell.raise_for_status()
        print("Upsell:")
        pretty(upsell.json())
        order_a = checkout(client, quote_a["quote_id"])
        payment_a = pay(client, order_a["order_id"])
        settlement_a = send_webhook(client, "payment.captured", payment_a["razorpay_order_id"])
        print("Successful settlement:")
        pretty(settlement_a)
        show_audit(client, order_a["order_id"])

        print("\nScenario B — Human approval")
        quote_b = create_quote(client, expensive_product["@id"])
        order_b = checkout(client, quote_b["quote_id"])
        pending = client.post(f"/v1/orders/{order_b['order_id']}/pay", json={"mode": "link"})
        if pending.status_code != 202:
            pending.raise_for_status()
            raise RuntimeError("expected over-limit transaction to require approval")
        print("Approval requested:")
        pretty(pending.json())
        input("Press Enter after approving the transaction using the approval endpoint...")
        print("Human approval received")
        pay(client, order_b["order_id"])
        print("Payment link generated")

        print("\nScenario C — Payment failure recovery")
        quote_c = create_quote(client, cheap_product["@id"])
        order_c = checkout(client, quote_c["quote_id"])
        payment_c = pay(client, order_c["order_id"])
        send_webhook(
            client,
            "payment.failed",
            payment_c["razorpay_order_id"],
            error_code="PAYMENT_FAILED",
        )
        print("Payment failed")
        print("Inventory reservation released")
        print("Fallback payment link generated")
        show_audit(client, order_c["order_id"])


if __name__ == "__main__":
    main()
