import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.db import Base, SessionLocal, engine
from app.main import app
from app.models.approval import ApprovalRequest


def test_lists_only_pending_approval_requests() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    pending_id = str(uuid.uuid4())
    resolved_id = str(uuid.uuid4())
    db = SessionLocal()
    try:
        db.add_all(
            [
                ApprovalRequest(
                    id=pending_id,
                    order_id=str(uuid.uuid4()),
                    amount_paise=1_500_000,
                    status="pending",
                    created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
                    resolved_at=None,
                ),
                ApprovalRequest(
                    id=resolved_id,
                    order_id=str(uuid.uuid4()),
                    amount_paise=2_500_000,
                    status="approved",
                    created_at="2025-01-01T00:01:00Z",
                    resolved_at="2025-01-01T00:02:00Z",
                ),
            ]
        )
        db.commit()
    finally:
        db.close()

    response = TestClient(app).get("/v1/approvals")

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "approval_id": pending_id,
                "order_id": response.json()["items"][0]["order_id"],
                "amount_paise": 1_500_000,
                "status": "pending",
                "created_at": "2025-01-01T00:00:00Z",
            }
        ],
        "count": 1,
    }
    assert resolved_id not in response.text
