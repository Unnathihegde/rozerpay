from decimal import Decimal

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import Base, engine, get_db
from app.gateway.catalog import suggest_upsell
from app.gateway.checkout import create_payment_link, initiate_checkout
from app.gateway.policy import check_for_anomalies, require_approval_if_needed, resolve_approval
from app.gateway.quote import create_quote, expire_quote_if_needed
from app.gateway.webhook import process_webhook, verify_webhook_signature
from app.ledger.writer import log_audit_trail
from app.models import ApprovalRequest, LedgerEntry, Order, Product, Quote


app = FastAPI(title="Merchant Agent Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)


class QuoteRequest(BaseModel):
    product_id: str
    quantity: int = Field(ge=1)


class CheckoutRequest(BaseModel):
    quote_id: str
    nonce: str


class PayRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    mode: str
    price_paise: int | None = None
    amount_paise: int | None = None


@app.get("/catalog.jsonld")
def catalog_jsonld(db: Session = Depends(get_db)) -> JSONResponse:
    products = list(db.scalars(select(Product).order_by(Product.price_paise)))
    items = []
    for product in products:
        price_inr = Decimal(product.price_paise) / Decimal(100)
        availability = "InStock" if product.stock_qty > 0 else "OutOfStock"
        items.append(
            {
                "@type": "Product",
                "@id": product.id,
                "name": product.name,
                "category": product.category,
                "offers": {
                    "@type": "Offer",
                    "priceCurrency": "INR",
                    "price": f"{price_inr:.2f}",
                    "availability": f"https://schema.org/{availability}",
                },
            }
        )
    return JSONResponse(
        content={
            "@context": "https://schema.org",
            "@type": "ItemList",
            "itemListElement": items,
        },
        media_type="application/ld+json",
    )


@app.post("/v1/quote")
def quote(request: QuoteRequest, db: Session = Depends(get_db)) -> dict:
    try:
        created_quote = create_quote(db, request.product_id, request.quantity)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {
        "quote_id": created_quote.id,
        "product_id": created_quote.product_id,
        "quantity": created_quote.quantity,
        "locked_price_paise": created_quote.locked_price_paise,
        "currency": created_quote.currency,
        "expires_at": created_quote.expires_at,
        "signature": created_quote.signature,
    }


@app.post("/v1/quote/{quote_id}/upsell")
def upsell(quote_id: str, db: Session = Depends(get_db)) -> dict | None:
    stored_quote = db.get(Quote, quote_id)
    if stored_quote is None:
        raise HTTPException(status_code=404, detail="quote not found")
    if expire_quote_if_needed(db, stored_quote):
        raise HTTPException(status_code=410, detail="quote expired")
    product = db.get(Product, stored_quote.product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="product not found")
    proposal = suggest_upsell(product)
    order = db.query(Order).filter(Order.quote_id == quote_id).order_by(Order.created_at).first()
    if order is not None:
        log_audit_trail(db, order.id, "upsell_offered", {"upsell": proposal})
        db.commit()
    return proposal


@app.post("/v1/checkout")
def checkout(request: CheckoutRequest, db: Session = Depends(get_db)) -> JSONResponse:
    try:
        order = initiate_checkout(db, request.quote_id, request.nonce)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except TimeoutError as error:
        raise HTTPException(status_code=410, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    log_audit_trail(db, order.id, "intent_received", {})
    log_audit_trail(db, order.id, "quote_generated", {})
    db.commit()
    return JSONResponse(
        status_code=402,
        content={
            "order_id": order.id,
            "amount_paise": order.amount_paise,
            "currency": order.currency,
            "settlement_methods": ["razorpay_link", "razorpay_mandate"],
        },
    )


@app.post("/v1/orders/{order_id}/pay")
def pay(order_id: str, request: PayRequest, db: Session = Depends(get_db)) -> dict:
    if request.mode == "mandate":
        raise HTTPException(status_code=501, detail="mandate flow not implemented in this build")
    if request.mode != "link":
        raise HTTPException(status_code=400, detail="unsupported payment mode")
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    stored_quote = db.get(Quote, order.quote_id)
    if stored_quote is None:
        raise HTTPException(status_code=404, detail="quote not found")
    anomaly = check_for_anomalies(request.model_dump(exclude_none=True), stored_quote)
    if anomaly is not None:
        log_audit_trail(db, order.id, "policy_check_failed", {"reason": anomaly})
        db.commit()
        raise HTTPException(status_code=400, detail=anomaly)
    try:
        approval = require_approval_if_needed(db, order)
    except RuntimeError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if approval is not None:
        return JSONResponse(
            status_code=202,
            content={
                "detail": "amount exceeds spend limit, pending human approval",
                "approval_id": approval.id,
            },
        )
    log_audit_trail(db, order.id, "policy_check_passed", {})
    db.commit()
    try:
        order = create_payment_link(db, order_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return {
        "order_id": order.id,
        "razorpay_order_id": order.razorpay_order_id,
        "payment_link_url": order.razorpay_payment_link_url,
        "status": order.status,
    }


@app.get("/v1/orders/{order_id}/audit")
def audit(order_id: str, db: Session = Depends(get_db)) -> dict:
    if db.get(Order, order_id) is None:
        raise HTTPException(status_code=404, detail="order not found")
    entries = list(
        db.query(LedgerEntry)
        .filter(LedgerEntry.order_id == order_id)
        .order_by(LedgerEntry.id)
    )
    items = [
        {"step": entry.step, "timestamp": entry.timestamp, "details": entry.details}
        for entry in entries
    ]
    return {"order_id": order_id, "items": items, "count": len(items)}


@app.get("/v1/approvals")
def pending_approvals(db: Session = Depends(get_db)) -> dict:
    approvals = list(
        db.scalars(
            select(ApprovalRequest)
            .where(ApprovalRequest.status == "pending")
            .order_by(ApprovalRequest.created_at)
        )
    )
    return {
        "items": [
            {
                "approval_id": approval.id,
                "order_id": approval.order_id,
                "amount_paise": approval.amount_paise,
                "status": approval.status,
                "created_at": approval.created_at,
            }
            for approval in approvals
        ],
        "count": len(approvals),
    }


@app.post("/v1/approvals/{approval_id}/approve")
def approve(approval_id: str, db: Session = Depends(get_db)) -> dict:
    try:
        approval = resolve_approval(db, approval_id, approved=True)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return {"approval_id": approval.id, "status": approval.status}


@app.post("/v1/approvals/{approval_id}/reject")
def reject(approval_id: str, db: Session = Depends(get_db)) -> dict:
    try:
        approval = resolve_approval(db, approval_id, approved=False)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return {"approval_id": approval.id, "status": approval.status}


def _serialize_order(order: Order, product: Product | None, quote: Quote | None) -> dict:
    return {
        "order_id": order.id,
        "quote_id": order.quote_id,
        "product_id": quote.product_id if quote is not None else None,
        "product_name": product.name if product is not None else None,
        "category": product.category if product is not None else None,
        "quantity": quote.quantity if quote is not None else None,
        "amount_paise": order.amount_paise,
        "currency": order.currency,
        "status": order.status,
        "source": "agent" if order.is_autonomous else "storefront",
        "is_autonomous": order.is_autonomous,
        "razorpay_order_id": order.razorpay_order_id,
        "razorpay_payment_link_url": order.razorpay_payment_link_url,
        "created_at": order.created_at,
        "updated_at": order.updated_at,
    }


@app.get("/v1/orders")
def list_orders(db: Session = Depends(get_db)) -> dict:
    orders = list(db.scalars(select(Order).order_by(Order.created_at.desc())))
    quote_ids = {order.quote_id for order in orders}
    quotes = {q.id: q for q in db.scalars(select(Quote).where(Quote.id.in_(quote_ids)))} if quote_ids else {}
    product_ids = {q.product_id for q in quotes.values()}
    products = {p.id: p for p in db.scalars(select(Product).where(Product.id.in_(product_ids)))} if product_ids else {}
    items = []
    for order in orders:
        quote = quotes.get(order.quote_id)
        product = products.get(quote.product_id) if quote is not None else None
        items.append(_serialize_order(order, product, quote))
    return {"items": items, "count": len(items)}


@app.get("/v1/inventory")
def list_inventory(db: Session = Depends(get_db)) -> dict:
    products = list(db.scalars(select(Product).order_by(Product.category, Product.name)))
    items = [
        {
            "product_id": product.id,
            "name": product.name,
            "category": product.category,
            "price_paise": product.price_paise,
            "stock_qty": product.stock_qty,
            "attributes": product.attributes,
        }
        for product in products
    ]
    return {"items": items, "count": len(items)}


@app.get("/v1/ledger")
def list_ledger(limit: int = 100, db: Session = Depends(get_db)) -> dict:
    limit = max(1, min(limit, 500))
    entries = list(
        db.query(LedgerEntry).order_by(LedgerEntry.id.desc()).limit(limit)
    )
    items = [
        {
            "id": entry.id,
            "order_id": entry.order_id,
            "step": entry.step,
            "timestamp": entry.timestamp,
            "details": entry.details,
        }
        for entry in entries
    ]
    return {"items": items, "count": len(items)}


@app.get("/v1/metrics")
def metrics(db: Session = Depends(get_db)) -> dict:
    total_orders = db.scalar(select(func.count()).select_from(Order)) or 0
    paid_orders = (
        db.scalar(select(func.count()).select_from(Order).where(Order.status == "paid")) or 0
    )
    autonomous_orders = (
        db.scalar(select(func.count()).select_from(Order).where(Order.is_autonomous.is_(True))) or 0
    )
    gmv_paise = db.scalar(select(func.coalesce(func.sum(Order.amount_paise), 0))) or 0
    settled_paise = (
        db.scalar(
            select(func.coalesce(func.sum(Order.amount_paise), 0)).where(Order.status == "paid")
        )
        or 0
    )
    pending_approvals = (
        db.scalar(
            select(func.count())
            .select_from(ApprovalRequest)
            .where(ApprovalRequest.status == "pending")
        )
        or 0
    )
    total_stock = db.scalar(select(func.coalesce(func.sum(Product.stock_qty), 0))) or 0
    product_count = db.scalar(select(func.count()).select_from(Product)) or 0
    out_of_stock = (
        db.scalar(select(func.count()).select_from(Product).where(Product.stock_qty == 0)) or 0
    )

    status_rows = db.execute(
        select(Order.status, func.count()).group_by(Order.status)
    ).all()
    status_breakdown = {status: count for status, count in status_rows}

    return {
        "total_orders": total_orders,
        "paid_orders": paid_orders,
        "autonomous_orders": autonomous_orders,
        "storefront_orders": total_orders - autonomous_orders,
        "gmv_paise": int(gmv_paise),
        "settled_paise": int(settled_paise),
        "pending_approvals": pending_approvals,
        "product_count": product_count,
        "total_stock": int(total_stock),
        "out_of_stock": out_of_stock,
        "status_breakdown": status_breakdown,
        "spend_limit_paise": settings.spend_limit_paise,
    }


@app.get("/v1/status")
def system_status(db: Session = Depends(get_db)) -> dict:
    razorpay_configured = not settings.razorpay_key_id.startswith("rzp_test_xxxx")
    webhook_configured = not settings.razorpay_webhook_secret.startswith("whsec_xxxx")
    last_entry = db.query(LedgerEntry).order_by(LedgerEntry.id.desc()).first()
    return {
        "services": [
            {"name": "Gateway API", "status": "operational"},
            {"name": "Ledger", "status": "operational"},
            {
                "name": "Razorpay Keys",
                "status": "operational" if razorpay_configured else "test_mode",
            },
            {
                "name": "Webhook Signing",
                "status": "operational" if webhook_configured else "test_mode",
            },
        ],
        "spend_limit_paise": settings.spend_limit_paise,
        "quote_signing": "enabled",
        "last_event_at": last_entry.timestamp if last_entry is not None else None,
    }


@app.post("/api/v1/webhook/razorpay")
async def razorpay_webhook(request: Request, db: Session = Depends(get_db)) -> dict:
    payload = await request.body()
    signature = request.headers.get("X-Razorpay-Signature")
    if not verify_webhook_signature(payload, signature):
        raise HTTPException(status_code=400, detail="invalid webhook signature")
    process_webhook(db, payload)
    return {"status": "ok"}
