import json

from sqlalchemy.orm import Session

from app.gateway.quote import now_utc
from app.models.ledger import LedgerEntry


def log_audit_trail(db: Session, order_id: str | None, step: str, details: dict) -> None:
    db.add(
        LedgerEntry(
            order_id=order_id,
            step=step,
            timestamp=now_utc(),
            details_json=json.dumps(details),
        )
    )
