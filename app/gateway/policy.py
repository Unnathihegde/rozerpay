import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.gateway.quote import now_utc
from app.models import ApprovalRequest, Order, Quote


logger = logging.getLogger(__name__)

PROMPT_INJECTION_PATTERNS = (
    "ignore previous instructions",
    "disregard the above",
    "system prompt",
    "you are now",
)


def _contains_prompt_injection(value: object) -> bool:
    if isinstance(value, str):
        lowered = value.lower()
        return any(pattern in lowered for pattern in PROMPT_INJECTION_PATTERNS)
    if isinstance(value, dict):
        return any(_contains_prompt_injection(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_prompt_injection(item) for item in value)
    return False


def check_for_anomalies(payload: dict, quote: Quote) -> str | None:
    for field in ("price_paise", "amount_paise"):
        if field in payload and payload[field] != quote.locked_price_paise:
            return "price manipulation detected: client-supplied amount does not match locked quote"
    if _contains_prompt_injection(payload):
        return "prompt injection pattern detected"
    return None


def send_approval_webhook(order: Order) -> None:
    logger.info("[APPROVAL WEBHOOK STUB]")


def require_approval_if_needed(db: Session, order: Order) -> ApprovalRequest | None:
    if order.amount_paise <= settings.spend_limit_paise:
        return None

    approvals = list(
        db.scalars(select(ApprovalRequest).where(ApprovalRequest.order_id == order.id))
    )
    approved = next((approval for approval in approvals if approval.status == "approved"), None)
    if approved is not None:
        order.status = "awaiting_payment"
        order.updated_at = now_utc()
        db.commit()
        return None

    if any(approval.status == "rejected" for approval in approvals):
        raise RuntimeError("order state conflict")

    existing = next((approval for approval in approvals if approval.status == "pending"), None)
    if existing is not None:
        return existing

    approval = ApprovalRequest(
        id=str(uuid.uuid4()),
        order_id=order.id,
        amount_paise=order.amount_paise,
        status="pending",
        created_at=now_utc(),
        resolved_at=None,
    )
    order.status = "awaiting_approval"
    order.updated_at = now_utc()
    db.add(approval)
    db.commit()
    db.refresh(approval)
    send_approval_webhook(order)
    return approval


def resolve_approval(db: Session, approval_id: str, approved: bool) -> ApprovalRequest:
    approval = db.get(ApprovalRequest, approval_id)
    if approval is None:
        raise LookupError("approval not found")
    if approval.status != "pending":
        raise RuntimeError("approval is not pending")
    order = db.get(Order, approval.order_id)
    approval.status = "approved" if approved else "rejected"
    approval.resolved_at = now_utc()
    if order is not None:
        order.status = "awaiting_payment" if approved else "failed"
        order.updated_at = now_utc()
    db.commit()
    db.refresh(approval)
    return approval
