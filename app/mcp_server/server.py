from __future__ import annotations

from types import SimpleNamespace

from app.db import SessionLocal
from app.gateway.catalog import CatalogSearch, suggest_upsell
from app.gateway.checkout import initiate_checkout
from app.gateway.quote import create_quote
from app.models import Product, Quote


class _ToolManager:
    def __init__(self) -> None:
        self._tools: list[SimpleNamespace] = []

    def register(self, func, *, name: str | None = None) -> None:
        tool_name = name or func.__name__
        self._tools.append(SimpleNamespace(name=tool_name, func=func))

    def list_tools(self) -> list[SimpleNamespace]:
        return list(self._tools)


class FastMCP:
    def __init__(self, name: str) -> None:
        self.name = name
        self._tool_manager = _ToolManager()

    def tool(self, name: str | None = None):
        def decorator(func):
            self._tool_manager.register(func, name=name)
            return func

        return decorator


mcp = FastMCP("Merchant Agent Gateway")


@mcp.tool()
def search_catalog(constraints: dict) -> dict:
    """Search the merchant catalog using structured buyer constraints."""
    db = SessionLocal()
    try:
        products = CatalogSearch(db).query(constraints)
        return {
            "items": [
                {
                    "id": product.id,
                    "name": product.name,
                    "category": product.category,
                    "price_paise": product.price_paise,
                    "stock_qty": product.stock_qty,
                }
                for product in products
            ],
            "count": len(products),
        }
    finally:
        db.close()


@mcp.tool()
def get_quote(product_id: str, quantity: int) -> dict:
    """Create a signed, time-limited quote."""
    if not product_id:
        raise ValueError("product_id is required")
    if quantity < 1:
        raise ValueError("quantity must be at least 1")
    db = SessionLocal()
    try:
        quote = create_quote(db, product_id, quantity)
        return {
            "quote_id": quote.id,
            "product_id": quote.product_id,
            "quantity": quote.quantity,
            "locked_price_paise": quote.locked_price_paise,
            "currency": quote.currency,
            "expires_at": quote.expires_at,
            "signature": quote.signature,
        }
    finally:
        db.close()


@mcp.tool()
def apply_discount_or_upsell(quote_id: str) -> dict | None:
    """Return the deterministic upsell proposal for a quote."""
    db = SessionLocal()
    try:
        quote = db.get(Quote, quote_id)
        if quote is None:
            raise ValueError("quote not found")
        product = db.get(Product, quote.product_id)
        if product is None:
            raise ValueError("product not found")
        return suggest_upsell(product)
    finally:
        db.close()


@mcp.tool(name="initiate_checkout")
def initiate_checkout_tool(quote_id: str, nonce: str) -> dict:
    """Begin x402 payment negotiation for a quote."""
    if not quote_id:
        raise ValueError("quote_id is required")
    if not nonce:
        raise ValueError("nonce is required")
    db = SessionLocal()
    try:
        order = initiate_checkout(db, quote_id, nonce)
        return {
            "order_id": order.id,
            "amount_paise": order.amount_paise,
            "currency": order.currency,
            "settlement_methods": ["razorpay_link", "razorpay_mandate"],
        }
    finally:
        db.close()
