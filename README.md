# Merchant Agent Gateway

**Merchant Agent Gateway** is a secure payment gateway designed for **AI-powered buyer agents**.

It allows an AI agent to:

* Discover products from a merchant catalog
* Obtain a time-limited, locked quote
* Propose discounts or upsells
* Initiate checkout through an HTTP 402 payment flow
* Complete payment through **Razorpay Test Mode**
* Receive and verify payment webhooks
* Recover from failed payments
* Maintain an append-only audit trail

The key design principle is:

> **The AI can propose actions, but it cannot directly execute money-moving operations.**

All sensitive actions are controlled by deterministic **policy** and **execution** layers.

---

## Architecture

```text
                    ┌─────────────────────┐
                    │    AI Buyer Agent   │
                    │                     │
                    │ Intent / Proposals  │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   Merchant Catalog  │
                    │  Search + JSON-LD    │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │     Quote Engine    │
                    │                     │
                    │ Price + Inventory   │
                    │ 15-min Quote Lock   │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    Policy Engine    │
                    │                     │
                    │ Limits + Validation │
                    │ Human Approval      │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   Execution Engine  │
                    │                     │
                    │ Order + Payment     │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  Razorpay Test Mode │
                    │                     │
                    │ Order / Payment     │
                    └──────────┬──────────┘
                               │
                         Webhook Event
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Webhook Verification│
                    │    HMAC-SHA256      │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   Audit Ledger      │
                    │                     │
                    │ Immutable Events    │
                    │ Recovery History    │
                    └─────────────────────┘
```

### Core flow

```text
AI intent
   ↓
Catalog discovery
   ↓
Locked quote
   ↓
Policy validation
   ↓
Human approval (when required)
   ↓
Checkout
   ↓
Razorpay
   ↓
Verified webhook
   ↓
Order state update
   ↓
Append-only audit ledger
```

---

## Why this architecture?

The gateway separates **decision-making from execution**.

The AI layer can recommend a product, suggest an upsell, or propose a checkout action. However, it does not receive direct access to payment credentials or Razorpay operations.

Before a monetary operation is executed, the request passes through deterministic controls such as:

* Quote validation
* Price validation
* Inventory reservation
* Spending limits
* Nonce/replay protection
* Human approval
* Payment-provider verification

This prevents an AI-generated decision from directly becoming an unauthorized financial transaction.

---

# Features

### AI Buyer Agent

The agent-facing layer accepts structured product constraints and can be implemented using either:

* A deterministic intent parser
* A future LLM provider

The AI can **propose** actions but cannot directly create Razorpay orders or execute payments.

---

### Merchant Catalog

The machine-readable catalog is available through:

```http
GET /catalog.jsonld
```

Catalog search is implemented behind the `CatalogSearch` interface.

The current implementation uses local **NumPy cosine similarity**, while the interface allows the search layer to be replaced later with a vector database without changing the agent-facing API.

The seed catalog contains these eight demo products:

| Product | Category | Price |
| --- | --- | ---: |
| Wireless Headphones | audio | ₹12,999.00 |
| Mechanical Keyboard | electronics | ₹7,499.00 |
| Wireless Mouse | electronics | ₹2,499.00 |
| USB-C Hub | electronics | ₹3,999.00 |
| Laptop Stand | accessory | ₹3,299.00 |
| 1080p Webcam | electronics | ₹5,999.00 |
| Bluetooth Speaker | audio | ₹4,999.00 |
| Carrying Case | accessory | ₹1,499.00 |

Run `python seed.py` before a demo. MCP catalog searches accept structured constraints such as `{"query": "wireless headphones"}`, `{"query": "keyboard"}`, `{"query": "mouse"}`, or `{"query": "electronics"}`.

---

### Quote System

Quotes:

* Use integer paise for monetary values
* Are HMAC signed
* Lock the quoted price for **15 minutes**
* Reserve inventory
* Prevent client-side price manipulation

The client cannot simply modify the amount and submit a different price to the payment layer.

---

### MCP Tools

The project exposes exactly four MCP tools over **stdio**:

| Tool                       | Input                                  |
| -------------------------- | -------------------------------------- |
| `search_catalog`           | `{"constraints": {...}}`               |
| `get_quote`                | `{"product_id": "...", "quantity": 1}` |
| `apply_discount_or_upsell` | `{"quote_id": "..."}`                  |
| `initiate_checkout`        | `{"quote_id": "...", "nonce": "..."}`  |

These tools provide the agent with controlled access to catalog, quote, negotiation, and checkout operations.

---

# Checkout and x402 Flow

The checkout process uses an HTTP **402 Payment Required** flow.

```text
Client
  │
  │ POST /v1/checkout
  ▼
Gateway
  │
  ├── Validate UUID4 nonce
  ├── Validate quote
  ├── Check policy
  └── Create internal order
  │
  ▼
HTTP 402 Payment Required
  │
  └── amount
      currency
      supported settlement methods
```

The client UUID4 nonce is recorded **before other side effects**, providing protection against checkout replay.

Payment execution is intentionally separated from checkout:

```http
POST /v1/orders/{order_id}/pay
```

This separation allows the gateway to distinguish between:

1. Creating and authorizing a checkout
2. Actually executing the payment

---

# Razorpay Integration

The gateway integrates with **Razorpay Test Mode**.

Razorpay credentials are loaded exclusively from environment variables:

```text
.env
```

The integration currently uses Razorpay's order and payment-link capabilities.

### Payment flow

```text
Gateway
   │
   │ Create Razorpay Order
   ▼
Razorpay
   │
   │ Payment Link / Checkout
   ▼
Customer
   │
   │ Test Payment
   ▼
Razorpay
   │
   │ Webhook
   ▼
Gateway
```

Webhook events are received at:

```http
POST /api/v1/webhook/razorpay
```

The webhook signature is verified using **HMAC-SHA256 before the event is allowed to modify application state**.

The mandate payment path is intentionally unsupported and returns:

```http
501 Not Implemented
```

---

# Safety and Security Model

Security is enforced at multiple layers rather than relying on the AI model.

### Monetary safety

All monetary values are represented as **integer paise** to avoid floating-point errors.

### Quote integrity

Quotes are:

* HMAC signed
* Time-limited
* Bound to their price and product information
* Associated with inventory reservations

### Replay protection

Checkout requests require a UUID4 nonce.

Reusing a previously processed nonce does not create another checkout side effect.

### Spending limits

Orders above:

```text
SPEND_LIMIT_PAISE
```

cannot immediately execute payment.

They are moved to:

```text
awaiting_approval
```

and require explicit human approval.

### Prompt-injection protection

The policy layer rejects known recursive prompt-injection patterns before sensitive operations are executed.

---

# Human Approval

High-value transactions require human authorization.

```text
AI proposes checkout
        ↓
Policy Engine
        ↓
Amount > SPEND_LIMIT_PAISE
        ↓
awaiting_approval
        ↓
Human decision
      ↙   ↘
   Approve  Reject
      ↓
Payment     Cancel
```

Approve:

```http
POST /v1/approvals/{id}/approve
```

Reject:

```http
POST /v1/approvals/{id}/reject
```

The important design principle is that **the AI cannot bypass this approval boundary**.

---

# Audit Trail

Every important state transition is recorded in an append-only audit ledger.

View an order's audit history with:

```http
GET /v1/orders/{order_id}/audit
```

The ledger records events such as:

* Agent intent
* Catalog selection
* Quote generation
* Policy evaluation
* Checkout creation
* Razorpay order creation
* Payment settlement
* Human approval
* Payment failure
* Recovery actions

Events are returned in insertion order, providing a chronological view of the transaction lifecycle.

---

# Failure Recovery

The gateway also handles failed payments.

For a `payment.failed` event:

```text
Payment Failed
      ↓
Inventory NOT decremented
      ↓
Quote reservation released
      ↓
Fallback payment link generated
      ↓
Order → recovered_pending_retry
      ↓
Recovery details stored in audit ledger
```

This means a failed payment does not silently consume inventory.

The generated recovery link and failure details are retained in the audit trail so the recovery process remains traceable.

---

# API Overview

### Catalog

```http
GET /catalog.jsonld
```

### Checkout

```http
POST /v1/checkout
```

### Payment

```http
POST /v1/orders/{order_id}/pay
```

### Razorpay Webhook

```http
POST /api/v1/webhook/razorpay
```

### Approval

```http
POST /v1/approvals/{id}/approve
POST /v1/approvals/{id}/reject
```

### Audit

```http
GET /v1/orders/{order_id}/audit
```

---

# Project Setup

## 1. Create a virtual environment

```bash
python -m venv .venv
```

### Linux / macOS

```bash
source .venv/bin/activate
```

### Windows

```powershell
.venv\Scripts\activate
```

---

## 2. Install dependencies

```bash
pip install -r requirements.txt
```

---

## 3. Configure Razorpay

Copy the example environment file:

```bash
cp .env.example .env
```

On Windows, create `.env` manually if required.

Add your **Razorpay Test Mode** credentials to `.env`.

The required variables are `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, and `RAZORPAY_WEBHOOK_SECRET`. Keep `APP_ENV=local` for this demo and set a non-placeholder `QUOTE_SIGNING_SECRET` for signed quotes.

Never commit real credentials to GitHub.

---

## 4. Start the API server

```bash
uvicorn app.main:app --reload
```

---

## 5. Seed the catalog

In another terminal:

```bash
python seed.py
```

---

## 6. Run tests

```bash
pytest -v
```

---

# Demo

The complete demo follows three transaction scenarios.

### 1. Successful payment

```text
Catalog Discovery
      ↓
Quote
      ↓
Upsell Proposal
      ↓
HTTP 402 Checkout
      ↓
Razorpay Payment Link
      ↓
payment.captured Webhook
      ↓
Verified + Audited
```

### 2. Human approval

```text
Create Over-Limit Order
      ↓
Policy Check
      ↓
awaiting_approval
      ↓
Manual Approval
      ↓
Razorpay Payment Link
```

### 3. Failed payment recovery

```text
Payment Attempt
      ↓
payment.failed
      ↓
Release Reservation
      ↓
Generate Fallback Link
      ↓
recovered_pending_retry
      ↓
Recovery Recorded in Audit
```

---

# Exact Demo Sequence

For a short end-to-end demonstration:

**1. Discover the catalog**

Show the JSON-LD catalog and select a product.

**2. Generate a quote**

Create a quote and request an upsell proposal.

**3. Start checkout**

Initiate checkout and demonstrate the HTTP 402 response.

**4. Process payment**

Generate the Razorpay Test Mode payment link.

**5. Demonstrate the webhook**

Send a locally signed `payment.captured` webhook and show the resulting audit trail.

**6. Demonstrate human approval**

Create an order above the spending limit and show it entering `awaiting_approval`. The `demo.py` script then calls the approval endpoint explicitly before creating its payment link.

**7. Demonstrate failure recovery**

Trigger a `payment.failed` event and show the fallback payment link and recovery information in the audit trail.

---

# Technology Stack

| Component             | Technology         |
| --------------------- | ------------------ |
| Language              | Python             |
| API                   | FastAPI            |
| Payment Gateway       | Razorpay Test Mode |
| Agent Interface       | MCP                |
| Catalog Format        | JSON-LD            |
| Similarity Search     | NumPy              |
| Webhook Security      | HMAC-SHA256        |
| Testing               | Pytest             |
| Local Webhook Testing | ngrok              |

---

# Project Goals

This project demonstrates how an AI-powered purchasing system can interact with real payment infrastructure **without giving the AI unrestricted control over financial operations**.

The architecture focuses on:

* **Deterministic policy enforcement**
* **Secure payment execution**
* **Human approval for high-value transactions**
* **Replay protection**
* **Tamper-resistant quote validation**
* **Verified asynchronous webhooks**
* **Failure recovery**
* **Auditable transaction history**

The result is a payment architecture where:

> **AI proposes → Policy authorizes → Execution performs → Webhook confirms → Audit records.**
