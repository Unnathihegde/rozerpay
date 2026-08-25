# Agentic Commerce Gateway — Project Checkpoint

## 1. Project Goal

This project makes a traditional merchant transactable by an AI buyer agent. It provides machine-readable discovery, price-locked quotes, policy-gated checkout, Razorpay Test Mode settlement, recovery handling, and an explainable audit trail. The core safety boundary is: AI proposes; policy authorizes; execution performs payment actions.

## 2. Current Status

- Phase 0: COMPLETE
- Phase 1: COMPLETE
- Phase 2: COMPLETE
- Phase 3: COMPLETE
- Phase 4: COMPLETE
- Phase 5: COMPLETE
- Phase 6: COMPLETE
- Phase 7: COMPLETE
- Phase 8: NOT STARTED — Frontend

## 3. Architecture

```text
AI Buyer Agent
       |
       v
MCP (stdio) / x402 HTTP 402
       |
       v
FastAPI Gateway ----> SQLite / SQLAlchemy Database
       |
       v
Policy Engine (anomalies, spend limit, approvals)
       |
       v
Razorpay Test Mode (order + payment link)
       |
       v
Verified Razorpay Webhooks
       |
       v
Append-only Ledger / Database
```

## 4. Implemented Features

- Catalog discovery through `GET /catalog.jsonld`.
- JSON-LD/schema.org `ItemList`, `Product`, and `Offer` responses.
- Product search and hard filtering with optional NumPy cosine ranking.
- Quote generation with integer-paise prices.
- 15-minute quote locking using UTC ISO-8601 timestamps.
- HMAC-SHA256 quote signing and constant-time verification helper.
- Inventory reservation protection against over-commitment.
- MCP server using stdio.
- Exactly four MCP tools.
- x402-compatible HTTP 402 checkout negotiation.
- Persisted nonce replay protection before checkout side effects.
- Deterministic category-based upsell engine.
- Razorpay Test Mode client integration.
- Razorpay payment-link creation.
- Intentional mandate/recurring payment `501` stub.
- HMAC webhook signature verification.
- `payment.captured` settlement handling, including stock decrement and quote consumption.
- `payment.failed` recovery with released reservation and one fallback payment link.
- Configurable autonomous spend limit.
- Human approval workflow for over-limit orders.
- Client price/amount manipulation detection.
- Recursive prompt-injection pattern detection.
- Append-only audit ledger.
- Audit retrieval endpoint.
- End-to-end `demo.py` flow for success, approval, and failure recovery.

## 5. Database Models

| Model / table | Purpose |
| --- | --- |
| `Product` / `products` | Catalog item, stock, attributes, and embedding data. |
| `Quote` / `quotes` | Signed, price-locked, time-limited inventory reservation. |
| `UsedNonce` / `used_nonces` | Persistent checkout replay protection. |
| `Order` / `orders` | Internal payment state and Razorpay identifiers/links. |
| `ApprovalRequest` / `approval_requests` | Human decision state for orders above the spending limit. |
| `LedgerEntry` / `ledger_entries` | Append-only audit records for money-related actions. |

## 6. API Endpoints

| HTTP method | Endpoint | Purpose | Current status |
| --- | --- | --- | --- |
| GET | `/catalog.jsonld` | Discover catalog as JSON-LD/schema.org. | Implemented |
| POST | `/v1/quote` | Create a signed, stock-reserved quote. | Implemented |
| POST | `/v1/quote/{quote_id}/upsell` | Retrieve deterministic upsell proposal. | Implemented |
| POST | `/v1/checkout` | Negotiate x402 checkout and return HTTP 402. | Implemented |
| POST | `/v1/orders/{order_id}/pay` | Create Razorpay link payment after policy checks. | Implemented |
| GET | `/v1/orders/{order_id}/audit` | Retrieve ordered append-only audit entries. | Implemented |
| POST | `/v1/approvals/{approval_id}/approve` | Approve a pending over-limit transaction. | Implemented |
| POST | `/v1/approvals/{approval_id}/reject` | Reject a pending over-limit transaction. | Implemented |
| POST | `/api/v1/webhook/razorpay` | Verify and process Razorpay payment webhooks. | Implemented |

## 7. MCP Tools

| Tool | Purpose |
| --- | --- |
| `search_catalog` | Search catalog products using structured constraints. |
| `get_quote` | Create and return a signed, time-limited quote. |
| `apply_discount_or_upsell` | Return the deterministic upsell proposal for a quote. |
| `initiate_checkout` | Begin x402 checkout using a quote and UUID4 nonce. |

## 8. Safety Controls

- **Overspending:** `SPEND_LIMIT_PAISE` blocks Razorpay execution above the limit until a human approves the related `ApprovalRequest`.
- **Replay attacks:** a nonce is persisted before other checkout side effects; reusing it returns `409`.
- **Price manipulation:** supplied `price_paise` or `amount_paise` values must exactly match the locked quote or the request returns `400`.
- **Prompt injection:** recursive string inspection rejects specified case-insensitive injection phrases before payment execution.
- **Payment failures:** failed webhooks leave product stock unchanged, release the quote reservation, create one fallback payment link, and record recovery details in the ledger.

## 9. Testing Status

The repository contains one test module for each backend verification phase. The most recent recorded results are:

| Test | Actual result |
| --- | --- |
| Phase 1 — `tests/test_phase1_catalog.py` | `1 passed` |
| Phase 2 — `tests/test_phase2_mcp.py` | `1 passed` |
| Phase 3 — `tests/test_phase3_razorpay.py` | `1 passed` |
| Phase 4 — `tests/test_phase4_safety.py` | `3 passed` |
| Phase 5 — `tests/test_phase5_ledger.py` | `1 passed` |
| Phase 6 — `tests/test_phase6_recovery.py` | `1 passed` |
| Full suite — `pytest -v` | `8 passed` |

All pytest Razorpay interactions are mocked; the test suite does not call Razorpay.

## 10. Razorpay Status

The application uses Razorpay Test Mode credentials loaded from `.env` for real link-payment execution. `POST /v1/orders/{order_id}/pay` creates a Razorpay order and payment link; `payment.captured` and `payment.failed` are handled through the verified webhook endpoint.

Pytest mocks Razorpay SDK calls, including payment-link creation and order creation. `demo.py` requires a locally running server configured with real Razorpay TEST credentials and a valid `RAZORPAY_WEBHOOK_SECRET` to sign its locally generated webhook payloads. Recurring/mandate flow is intentionally not implemented and returns `501`.

## 11. Demo Status

`demo.py` uses `httpx.Client()` against `http://localhost:8000`. It demonstrates catalog discovery, quote creation, upsell, HTTP 402 checkout, Razorpay payment link creation, a signed successful-capture webhook, and audit retrieval. It then demonstrates an over-limit order and pauses exactly once for the user to approve it through the approval endpoint. Finally, it demonstrates a signed failed-payment webhook, fallback link generation, released reservation, and recovery audit trail.

## 12. Important Files

| File | Purpose |
| --- | --- |
| `app/main.py` | FastAPI app and all implemented REST endpoints. |
| `app/config.py` | `.env` loading and validated application settings. |
| `app/db.py` | SQLAlchemy base, engine, sessions, and database dependency. |
| `app/models/` | SQLAlchemy models for catalog, checkout, approval, and ledger state. |
| `app/gateway/catalog.py` | Catalog search and deterministic upsell rules. |
| `app/gateway/quote.py` | UTC helper, quote signing, expiry, and reservation logic. |
| `app/gateway/checkout.py` | Nonce-protected checkout and Razorpay link execution. |
| `app/gateway/policy.py` | Anomaly checks, spend limits, and approval workflow. |
| `app/gateway/webhook.py` | Webhook signature verification and settlement/recovery handling. |
| `app/mcp_server/server.py` | The four stdio MCP tools. |
| `app/razorpay_client/client.py` | Sole Razorpay client factory. |
| `app/ledger/writer.py` | Append-only audit insertion helper. |
| `seed.py` | Seeds the deterministic 15-product catalog. |
| `demo.py` | Local end-to-end Razorpay Test Mode demonstration. |
| `tests/` | Phase-specific automated backend verification. |
| `README.md` | Setup, architecture, demo, and operational documentation. |

## 13. Security / Secrets

Never commit `.env`, `gateway.db`, Razorpay key IDs/secrets, webhook secrets, or quote-signing secrets to GitHub. Commit `.env.example` with placeholders instead. Keep `requirements.txt`, source code, tests, README, and this checkpoint report under version control.

## 14. Tomorrow's Next Step

NEXT STEP: Build Phase 8 — Frontend Dashboard

The frontend should visualize only existing functionality: JSON-LD/catalog products and stock, product filtering, quote creation/countdown/signature, upsell proposals, x402 checkout state, payment-link status, approval status/actions, settlement/recovery status, and ordered audit entries.

## 15. Resume Instructions

Backend Phases 0–7 are complete. Do not rebuild the backend. Start by reviewing the existing API endpoints and then build the Phase 8 frontend on top of them. Use the endpoint table above and `app/main.py` as the backend contract; preserve the existing policy, webhook, and ledger safety boundaries.
