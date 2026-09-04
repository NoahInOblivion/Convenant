# RazorGrowth Agent v2 — Design Specification

**Date:** 2026-09-04  
**Track:** Razorpay AI Buildathon — Track 01: AI Growth & Agentic Commerce  
**Status:** Approved

---

## 1. System Purpose

RazorGrowth Agent v2 is an agentic commerce system where an LLM-powered Buyer Agent proposes purchases in natural language, but all financial decisions flow through a deterministic, cryptographically-signed chain of mandates before any Razorpay API call is made. The system is designed for auditability, tamper-evidence, and graceful failure — not just the happy path.

The pitch narrative centers on the **rejection → re-plan → approval** scenario (Phase 5), showing the signed mandate chain viewer and immutable audit log as first-class UI elements.

---

## 2. Non-Negotiable Architectural Invariants

1. LLM Buyer Agent produces CartProposal only. No DB writes. No payment calls. Enforced architecturally.
2. Deterministic Policy Gate: pure sync function, re-verifies price/stock from DB, never trusts agent price.
3. Signed Mandate Chain: IntentMandate → CartMandate → PaymentMandate — HMAC-SHA256, tamper-evident, single-use.
4. Razorpay gated behind verified PaymentMandate. create_order() without valid mandate raises MandateGuardException.
5. Immutable Audit Log: every event recorded, no UPDATE/DELETE possible.

---

## 3. Tech Stack

- Language: Python 3.12
- Web Framework: FastAPI 0.115+
- Agent Graph: LangGraph 0.2+
- LLM: OpenAI GPT-4o-mini
- Schemas: Pydantic v2
- Database: PostgreSQL 16 (SQLAlchemy 2.0 async + asyncpg)
- Signing: HMAC-SHA256 (hashlib) + JWT (PyJWT 2.x)
- Payments: razorpay Python SDK (test-mode)
- Testing: pytest 8+, pytest-asyncio, pytest-mock
- Frontend: Next.js 14 (App Router), TypeScript, Tailwind CSS
- Infrastructure: Docker Compose

---

## 4. Configuration (env vars)

- DATABASE_URL=postgresql+asyncpg://...
- OPENAI_API_KEY=sk-...
- RAZORPAY_KEY_ID=rzp_test_...
- RAZORPAY_KEY_SECRET=...
- MANDATE_SECRET_KEY=<32-byte hex>
- SPEND_CAP=10000.00
- MANDATE_INTENT_TTL_SECONDS=900
- MANDATE_CART_TTL_SECONDS=600
- MANDATE_PAYMENT_TTL_SECONDS=300

---

## 5. Design Tokens (Phase 7)

- Accent: #E4572E (Razorpay orange-red)
- Accent Hover: #C73E1D
- Surface: #0F1117
- Surface Elevated: #1A1D26
- Border: #2A2D3A
- Text Primary: #F0F2F5
- Text Secondary: #8B8FA8
- Type scale: 12/14/16/20/24/32px
- Spacing: 4px base rhythm
- Border-radius: 6px uniform
- Fonts: JetBrains Mono (data) + Inter (prose)
