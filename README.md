# RazorGrowth Agent v2

An agentic commerce system where an LLM proposes purchases, a deterministic policy gate verifies them, and a cryptographically-signed mandate chain authorises payment — with no path to Razorpay that bypasses any of those steps.

```
User request → LLM Buyer Agent (read-only tools)
             → Deterministic Policy Gate (zero LLM, re-verifies price + stock from DB)
             → Signed Mandate Chain  (Intent → Cart → Payment, HMAC-SHA256)
             → Razorpay order creation (only reachable through a valid, unexpired, unconsumed mandate)
             → Immutable audit log (every step recorded, no UPDATE/DELETE)
```

---

## Architecture

```mermaid
flowchart TD
    U([User NL Request]) --> BA

    subgraph Agent["Buyer Agent (LangGraph)"]
        BA[BuyerAgentNode\nread-only tools only] -->|CartProposal| PG
    end

    subgraph Gate["Policy Gate (zero LLM)"]
        PG[evaluate_proposal\npure sync function] -->|re-verify price + stock from DB| PG
        PG -->|PolicyDecision| MC
        PG -->|rejected| RL
    end

    subgraph Replan["Re-plan Loop"]
        RL[ReplanLoop\nmax 2 attempts] -->|new request| BA
        RL -->|all attempts fail| GD[GracefulDenialMessage]
    end

    subgraph Mandates["Signed Mandate Chain"]
        MC[IntentMandate] --> CM[CartMandate]
        CM --> PM[PaymentMandate\nHMAC-SHA256 signed]
    end

    subgraph Payment["Payment Execution"]
        PM -->|MandateGuard.require_valid_mandate| RZ[Razorpay API\ntest-mode]
    end

    subgraph Audit["Audit Log"]
        AL[(PostgreSQL\nimmutable append-only)]
    end

    BA -.->|every step| AL
    PG -.->|every step| AL
    MC -.->|every step| AL
    RZ -.->|every step| AL
```

---

## Security Invariants

These are enforced architecturally and tested — not just documented.

| # | Invariant | Where enforced |
|---|-----------|---------------|
| 1 | **LLM never touches payments or DB writes.** `BuyerAgentNode` tool registry is checked at construction time — raises `AgentToolViolation` if any forbidden tool is present. | `backend/agent/node.py`, `tests/llm/test_agent_trajectory.py` |
| 2 | **Policy gate is pure and deterministic.** Zero LLM. Re-fetches price and stock from the catalog on every call — agent-proposed prices are never trusted. | `backend/policy/gate.py` |
| 3 | **Every mandate is HMAC-SHA256 signed.** Tamper a single byte → signature fails. Wrong key → signature fails. `hmac.compare_digest` for constant-time comparison. | `backend/mandates/signer.py` |
| 4 | **`PaymentMandate.consumed = True` is set before the Razorpay API call.** If the API throws, the mandate is still marked consumed — no double-charge on retry. | `backend/payments/razorpay_client.py` |
| 5 | **Audit log is append-only.** PostgreSQL `BEFORE UPDATE` trigger prevents mutation. The app user has no DELETE privilege. | `backend/audit/log.py` |

---

## Data Flow in Detail

### Happy path (under spend cap)

```
POST /api/propose  {"request": "I need a keyboard and mouse"}
  → BuyerAgentNode.run()          → CartProposal (SKUs + agent prices)
  → evaluate_proposal()           → PolicyDecision (approved, verified_total=₹6000)
  → MandateChain.create_intent()  → IntentMandate  (signed, TTL 900s)
  → MandateChain.create_cart()    → CartMandate    (signed, TTL 600s)
  → MandateChain.create_payment() → PaymentMandate (signed, TTL 300s)
  → RazorpayClient.create_order() → {"id": "order_xyz", "status": "created"}
```

### Rejected / re-plan path

```
POST /api/propose  {"request": "buy the most expensive laptop"}
  → BuyerAgentNode.run()     → CartProposal (LAPTOP002, ₹95,000)
  → evaluate_proposal()      → PolicyDecision (rejected: over ₹10,000 cap)
  → ReplanLoop.attempt()     → replan prompt sent back to agent
      attempt 1 → still over cap → rejected
      attempt 2 → still over cap → rejected
  → GracefulDenialMessage    → {"decision": "rejected", "denial_message": "..."}
  → audit log: terminal_denial
```

### Feed ingestion + counter-offer

```
POST /api/feeds/ingest  {"protocol": "acp", "payload": {...}}
  → adapt_acp()                    → NormalizedProduct
  → calculate_counter_offer()      → counter_price (if margin ≥ 1%)
  → {"sku": "...", "counter_offer_price": "4275.00"}
```

---

## Project Structure

```
razorgrowth-v2/
│
├── backend/
│   ├── schemas/          # Pydantic v2 models — CartProposal, mandates, PolicyDecision, AuditLogEntry
│   ├── config.py         # Pydantic Settings — reads from .env
│   │
│   ├── policy/
│   │   ├── gate.py       # evaluate_proposal() — the deterministic core, zero LLM
│   │   └── catalog_repository.py  # Abstract interface for price/stock lookups
│   │
│   ├── agent/
│   │   ├── node.py       # BuyerAgentNode — LangGraph node, read-only tools only
│   │   ├── tools.py      # BUYER_AGENT_TOOLS + FORBIDDEN_TOOL_NAMES registry
│   │   └── graph.py      # StateGraph wiring
│   │
│   ├── mandates/
│   │   ├── signer.py     # sign_mandate(), verify_mandate() — HMAC-SHA256
│   │   └── chain.py      # MandateChain — builds Intent → Cart → Payment chain
│   │
│   ├── payments/
│   │   ├── guard.py      # MandateGuard — the only path into create_order()
│   │   └── razorpay_client.py  # RazorpayClient — test-mode, wraps razorpay SDK
│   │
│   ├── replan/
│   │   └── loop.py       # ReplanLoop + GracefulDenialMessage
│   │
│   ├── feeds/
│   │   ├── adapters.py   # adapt_acp(), adapt_ucp(), adapt_mcp(), adapt_feed()
│   │   └── counter_offer.py  # calculate_counter_offer() — pure function
│   │
│   ├── audit/
│   │   └── log.py        # AuditLogger + InMemoryAuditLogger
│   │
│   └── api/
│       ├── main.py       # FastAPI app + CORS
│       ├── deps.py       # Singletons — audit logger, catalog, mandate chain, Razorpay client
│       └── routes/
│           ├── propose.py   # POST /api/propose
│           ├── audit.py     # GET  /api/audit
│           ├── catalog.py   # GET  /api/catalog
│           └── feeds.py     # POST /api/feeds/ingest
│
├── frontend/             # Next.js 14 (App Router) — TypeScript + Tailwind
│   └── app/
│       ├── page.tsx         # Purchase request form + result display
│       ├── mandates/        # Mandate chain explorer
│       ├── audit/           # Audit log viewer
│       └── catalog/         # Product catalog with live stock
│
├── tests/
│   ├── deterministic/    # 52 tests — schemas, policy gate, mandate crypto (run on every commit)
│   ├── llm/              # 12 tests — mocked LLM unit + tool-boundary trajectory (run on prompt/model changes)
│   ├── integration/      # 12 tests — mandate guard + replan loop (run on every commit)
│   └── feeds/            # 27 tests — all three protocol adapters + counter-offer (run on every commit)
│
├── pyproject.toml        # Python deps + pytest config
├── .env                  # Keys (gitignored — see .env template below)
└── .gitignore
```

---

## Setup

### Prerequisites

- Python 3.12+
- Node.js 18+
- PostgreSQL 16 (or Docker)

### 1. Clone and install backend

```bash
git clone https://github.com/NUll-O7/Convenant.git
cd Convenant

python3.12 -m venv venv
source venv/bin/activate
pip install -e ".[test]"
```

### 2. Configure environment

```bash
cp .env.example .env   # then fill in values
```

```dotenv
# .env
OPENAI_API_KEY=sk-...
RAZORPAY_KEY_ID=rzp_test_...
RAZORPAY_KEY_SECRET=...

# Generate with: python -c "import secrets; print(secrets.token_hex(32))"
MANDATE_SECRET_KEY=<64-char hex>

DATABASE_URL=postgresql+asyncpg://razorgrowth:razorgrowth@localhost:5432/razorgrowth
SPEND_CAP=10000.00

# Mandate TTLs (seconds)
MANDATE_INTENT_TTL_SECONDS=900
MANDATE_CART_TTL_SECONDS=600
MANDATE_PAYMENT_TTL_SECONDS=300
```

> `SPEND_CAP` is the auto-approval threshold in INR. Proposals above this amount are routed to `requires_human_approval` status.

### 3. Start the backend

```bash
source venv/bin/activate
uvicorn backend.api.main:app --reload --port 8000
```

Interactive API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### 4. Start the frontend

```bash
cd frontend
npm install
npm run dev   # http://localhost:3000
```

---

## API Reference

### `POST /api/propose`

Submit a natural language purchase request. Runs the full agent → policy → mandate → payment pipeline.

**Request**
```json
{
  "request": "I need a mechanical keyboard and an ergonomic mouse",
  "session_id": "ses-optional-uuid"
}
```

**Response — approved**
```json
{
  "proposal_id": "a3f1...",
  "session_id": "ses-001",
  "decision": "approved",
  "reason": "All checks passed. Auto-approved.",
  "verified_total": "6000.00",
  "items": [
    {"sku": "KB001", "name": "Mechanical Keyboard", "quantity": 1,
     "agent_proposed_price": "4500.00", "verified_price": "4500.00"},
    {"sku": "MOUSE001", "name": "Ergonomic Mouse", "quantity": 1,
     "agent_proposed_price": "1500.00", "verified_price": "1500.00"}
  ],
  "idempotency_key": "a9f3...64-char-hex",
  "mandate_id": "pm-uuid",
  "razorpay_order_id": "order_xyz"
}
```

**Response — over spend cap**
```json
{
  "decision": "requires_human_approval",
  "reason": "Verified total ₹75000 exceeds auto-approval cap of ₹10000.",
  "verified_total": "75000.00",
  ...
}
```

**Response — terminal denial (all replans exhausted)**
```json
{
  "decision": "rejected",
  "denial_message": "Verified total ₹95000 exceeds auto-approval cap of ₹10000.",
  "verified_total": "0.00",
  "items": []
}
```

---

### `GET /api/catalog`

Returns all products with live price and stock.

```json
[
  {"sku": "KB001", "name": "Mechanical Keyboard", "price": "4500.00", "in_stock": true, "stock": 50},
  {"sku": "WEBCAM001", "name": "HD Webcam", "price": "3200.00", "in_stock": false, "stock": 0},
  ...
]
```

---

### `GET /api/audit?session_id=ses-001`

Returns the immutable audit log, optionally filtered by session.

```json
[
  {"entry_id": "...", "session_id": "ses-001", "event_type": "proposal_received",
   "payload": {"request": "..."}, "created_at": "2026-09-04T10:00:00Z"},
  {"event_type": "policy_decision", "payload": {"decision": "approved", "verified_total": "6000.00"}, ...},
  {"event_type": "mandate_signed", "payload": {"intent_mandate_id": "...", ...}, ...},
  {"event_type": "payment_initiated", "payload": {"razorpay_order_id": "order_xyz"}, ...}
]
```

Event types (in order of a typical approved flow):
`proposal_received` → `policy_decision` → `mandate_signed` → `payment_initiated` | `payment_failed`

Denial flow adds: `replan_triggered` → `replan_success` | `terminal_denial`

---

### `POST /api/feeds/ingest`

Normalise an external product feed payload into the internal format and calculate a counter-offer.

Supported protocols: `acp` (JSON-LD / schema.org), `ucp` (flat dict), `mcp` (tool_result)

**ACP example**
```json
{
  "protocol": "acp",
  "payload": {
    "@context": "https://schema.org/",
    "@type": "Product",
    "sku": "KB001",
    "name": "Mechanical Keyboard",
    "offers": {"price": "4500.00", "availability": "InStock"}
  }
}
```

**Response**
```json
{
  "sku": "KB001",
  "name": "Mechanical Keyboard",
  "price": "4500.00",
  "in_stock": true,
  "source_protocol": "acp",
  "counter_offer_price": "4275.00"
}
```

> Counter-offer applies a `min(margin_room, max_discount_pct)` discount. Returns `null` if the discount is below 1%.

---

## Test Suite

```bash
# Deterministic tests — run on every commit (no LLM, no network)
pytest tests/deterministic/ tests/integration/ tests/feeds/ -v

# LLM unit tests — run only when prompts, model, or graph change (mocked LLM, no real API call)
pytest tests/llm/ -v

# Full suite
pytest tests/ -v
```

| Suite | Count | Speed | Mocks |
|-------|------:|-------|-------|
| `deterministic/` — schemas, policy gate, mandate crypto | 52 | ~0.1s | none |
| `integration/` — mandate guard, replan loop | 12 | ~0.8s | Razorpay SDK, BuyerAgentNode.run() |
| `feeds/` — ACP/UCP/MCP adapters, counter-offer | 27 | ~0.1s | none |
| `llm/` — agent unit + tool-boundary trajectory | 12 | ~0.7s | ChatOpenAI |
| **Total** | **103** | **~0.8s** | |

**Rules:**
- Deterministic tests never import LLM modules.
- LLM tests never mock the policy gate or mandate signer.
- Each phase is a hard gate — tests must pass before the next phase begins.

---

## UI Design Tokens

The frontend enforces a strict token set — no exceptions.

| Token | Value | Used for |
|-------|-------|----------|
| Accent | `#E4572E` | Buttons, prices, brand name, focus rings |
| Font — data | `JetBrains Mono` | SKUs, amounts, mandate IDs, timestamps, event types |
| Font — prose | `Inter` | Labels, headings, body copy |
| Border-radius | `6px` uniform | All cards, inputs, badges |
| Type scale | 12 / 14 / 16 / 20 / 24 / 32 px | — |
| Spacing | 4px base rhythm | — |

**Banned:** purple gradients, `border-radius > 6px`, decorative "Live" badges, marketing adjectives.

---

## Key Dependencies

| Package | Purpose |
|---------|---------|
| `fastapi` | HTTP layer |
| `pydantic` v2 | Schema validation — all domain models |
| `langgraph` | Agent graph execution |
| `langchain-openai` | GPT-4o-mini binding |
| `razorpay` | Payment order creation (test-mode) |
| `PyJWT` | JWT support (mandate TTL claims) |
| `sqlalchemy` + `asyncpg` | Async PostgreSQL ORM |
| `pytest` + `pytest-asyncio` | Test runner |
| `next` 14 | Frontend (App Router) |
| `tailwindcss` | Utility-first CSS with design token config |

---

## Monetary value handling

All monetary values use Python `Decimal` throughout the backend — never `float`. JSON responses serialize amounts as strings. The frontend never calls `parseFloat` on a price; it displays the string directly.

```python
# Correct
verified_total: Decimal = Decimal("4500.00")

# Never
verified_total: float = 4500.0  # ❌ floating-point rounding on currency
```

---

## License

MIT
