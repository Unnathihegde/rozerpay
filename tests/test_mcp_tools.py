import json
import uuid

import pytest

from app.db import Base, SessionLocal, engine
from app.mcp_server.server import (
    apply_discount_or_upsell,
    get_quote,
    initiate_checkout_tool,
    mcp,
    search_catalog,
)
from app.models.product import Product


def test_mcp_registers_expected_tools() -> None:
    assert [tool.name for tool in mcp._tool_manager.list_tools()] == [
        "search_catalog",
        "get_quote",
        "apply_discount_or_upsell",
        "initiate_checkout",
    ]


def test_mcp_tools_use_gateway_state_and_validate_inputs() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    product_id = str(uuid.uuid4())
    db = SessionLocal()
    try:
        db.add(
            Product(
                id=product_id,
                name="MCP Product",
                category="custom",
                price_paise=1000,
                stock_qty=2,
                attributes_json=json.dumps({}),
                embedding_json=json.dumps([1.0] * 8),
            )
        )
        db.commit()
    finally:
        db.close()

    results = search_catalog({})
    quote = get_quote(product_id, 1)
    order = initiate_checkout_tool(quote["quote_id"], str(uuid.uuid4()))

    assert results["count"] == 1
    assert quote["product_id"] == product_id
    assert apply_discount_or_upsell(quote["quote_id"]) is None
    assert order["amount_paise"] == 1000
    with pytest.raises(ValueError, match="quantity must be at least 1"):
        get_quote(product_id, 0)
    with pytest.raises(ValueError, match="nonce is required"):
        initiate_checkout_tool(quote["quote_id"], "")
