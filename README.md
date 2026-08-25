# Merchant Agent Gateway

A hackathon-ready gateway that lets an AI buyer agent discover a merchant, obtain a locked quote, negotiate checkout, and complete payment through Razorpay Test Mode. The AI proposes actions; deterministic policy and execution layers authorize and execute them.

## Setup

```bash
python -m venv .venv
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Windows:

```powershell
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Copy `.env.example` to `.env`, then fill in Razorpay Test Mode credentials.

Start the server:

```bash
uvicorn app.main:app --reload
```

Seed the catalog in a separate terminal:

```bash
python seed.py
```

Run tests:

```bash
pytest -v
```

Run the demo:

```bash
python demo.py
```

## Architecture

```text
AI buyer intent → merchant catalog and quote → policy engine → execution engine
→ Razorpay Test Mode → verified webhook → append-only audit ledger
```

The machine-readable catalog is served at `GET /catalog.jsonld`; catalog search is implemented behind `CatalogSearch`, so its local NumPy cosine ranking can later be replaced by a vector database.

## AI decision layer

The agent-facing interface accepts structured catalog constraints and can be backed by a deterministic intent parser or a future LLM provider. It may propose products and upsells, but never creates orders or invokes Razorpay. Those money actions remain behind the policy and execution layers.

## MCP tools

MCP uses stdio and exposes exactly these four tools:

| Tool | Input |
| --- | --- |
| `search_catalog` | `{"constraints": {...}}` |
| `get_quote` | `{"product_id": "...", "quantity": 1}` |
| `apply_discount_or_upsell` | `{"quote_id": "..."}` |
| `initiate_checkout` | `{"quote_id": "...", "nonce": "..."}` |

## x402 flow

`POST /v1/checkout` records a client UUID4 nonce before all other side effects, preventing replay. It creates an internal order and returns HTTP `402 Payment Required` with the order amount, currency, and supported settlement methods. The actual payment execution is separate: `POST /v1/orders/{order_id}/pay`.

## Razorpay integration

The server uses Razorpay Test Mode credentials from `.env` only. Link checkout creates a Razorpay order and payment link. Razorpay webhooks at `POST /api/v1/webhook/razorpay` are HMAC-SHA256 verified before they alter state. The mandate path is intentionally unsupported and returns `501`.

## Safety model

All monetary amounts use integer paise. Quotes are HMAC signed, lock their price for 15 minutes, and reserve inventory. The policy layer rejects client-supplied amount changes and recursive prompt-injection patterns. Nonces prevent checkout replay.

## Human approval

Orders above `SPEND_LIMIT_PAISE` are moved to `awaiting_approval` and get an approval request instead of making a Razorpay call. Approve with `POST /v1/approvals/{id}/approve`; reject with `POST /v1/approvals/{id}/reject`.

## Audit trail

`GET /v1/orders/{order_id}/audit` returns the append-only ledger in insertion order. It records intent, quote generation, policy results, Razorpay order creation, settlement, and recovery actions.

## Failure recovery

On `payment.failed`, inventory is not decremented, the quote reservation is released, and one fallback payment link is generated. The order moves to `recovered_pending_retry`, with the recovery link and failure details retained in the audit log.

## Exact demo sequence

1. Discover the JSON-LD catalog and select products.
2. Create a quote and request its upsell proposal.
3. Negotiate checkout through HTTP 402 and generate a Razorpay payment link.
4. Send a locally signed `payment.captured` webhook and display the audit trail.
5. Create an over-limit order, then manually approve it using the approval endpoint when the demo pauses once.
6. Generate the post-approval payment link.
7. Run a third order through `payment.failed`, then display its fallback recovery audit trail.
