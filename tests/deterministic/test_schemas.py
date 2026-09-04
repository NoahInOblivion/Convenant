"""Schema validation tests — deterministic, no LLM. Run on every commit."""
import pytest
from decimal import Decimal
from datetime import datetime, timezone
from pydantic import ValidationError

from backend.schemas.proposals import CartItem, CartProposal
from backend.schemas.mandates import IntentMandate, CartMandate, PaymentMandate
from backend.schemas.policy import PolicyDecision
from backend.schemas.audit import AuditLogEntry


def utcnow():
    return datetime.now(timezone.utc)


# ── CartItem ──────────────────────────────────────────────────────────────────

def test_cart_item_valid():
    item = CartItem(sku="SKU001", name="Laptop", quantity=1, agent_proposed_price=Decimal("45000.00"))
    assert item.sku == "SKU001"
    assert item.verified_price is None

def test_cart_item_missing_sku():
    with pytest.raises(ValidationError, match="sku"):
        CartItem(name="Laptop", quantity=1, agent_proposed_price=Decimal("45000.00"))

def test_cart_item_missing_name():
    with pytest.raises(ValidationError, match="name"):
        CartItem(sku="SKU001", quantity=1, agent_proposed_price=Decimal("45000.00"))

def test_cart_item_missing_quantity():
    with pytest.raises(ValidationError, match="quantity"):
        CartItem(sku="SKU001", name="Laptop", agent_proposed_price=Decimal("45000.00"))

def test_cart_item_missing_agent_proposed_price():
    with pytest.raises(ValidationError, match="agent_proposed_price"):
        CartItem(sku="SKU001", name="Laptop", quantity=1)

def test_cart_item_quantity_zero_rejected():
    with pytest.raises(ValidationError, match="quantity"):
        CartItem(sku="SKU001", name="Laptop", quantity=0, agent_proposed_price=Decimal("45000.00"))

def test_cart_item_quantity_negative_rejected():
    with pytest.raises(ValidationError, match="quantity"):
        CartItem(sku="SKU001", name="Laptop", quantity=-1, agent_proposed_price=Decimal("45000.00"))


# ── CartProposal ──────────────────────────────────────────────────────────────

def _make_item():
    return CartItem(sku="SKU001", name="Laptop", quantity=1, agent_proposed_price=Decimal("45000.00"))

def test_cart_proposal_valid():
    p = CartProposal(
        proposal_id="abc-123",
        session_id="ses-001",
        items=[_make_item()],
        total_proposed=Decimal("45000.00"),
        reasoning="User wants a laptop for work.",
        created_at=utcnow(),
    )
    assert p.proposal_id == "abc-123"

def test_cart_proposal_missing_proposal_id():
    with pytest.raises(ValidationError, match="proposal_id"):
        CartProposal(session_id="ses-001", items=[_make_item()], total_proposed=Decimal("45000.00"),
                     reasoning="r", created_at=utcnow())

def test_cart_proposal_missing_session_id():
    with pytest.raises(ValidationError, match="session_id"):
        CartProposal(proposal_id="abc", items=[_make_item()], total_proposed=Decimal("45000.00"),
                     reasoning="r", created_at=utcnow())

def test_cart_proposal_empty_items_rejected():
    with pytest.raises(ValidationError, match="items"):
        CartProposal(proposal_id="abc", session_id="ses", items=[],
                     total_proposed=Decimal("0"), reasoning="r", created_at=utcnow())

def test_cart_proposal_missing_reasoning():
    with pytest.raises(ValidationError, match="reasoning"):
        CartProposal(proposal_id="abc", session_id="ses", items=[_make_item()],
                     total_proposed=Decimal("45000.00"), created_at=utcnow())


# ── IntentMandate ─────────────────────────────────────────────────────────────

def test_intent_mandate_valid():
    m = IntentMandate(
        mandate_id="m-001", session_id="ses-001",
        user_intent="Buy me a laptop under 50k",
        created_at=utcnow(), expires_at=utcnow(),
        signature="abc123",
    )
    assert m.mandate_id == "m-001"

def test_intent_mandate_missing_signature():
    with pytest.raises(ValidationError, match="signature"):
        IntentMandate(mandate_id="m-001", session_id="ses-001",
                      user_intent="Buy laptop", created_at=utcnow(), expires_at=utcnow())


# ── CartMandate ───────────────────────────────────────────────────────────────

def test_cart_mandate_valid():
    m = CartMandate(
        mandate_id="cm-001", intent_mandate_id="im-001", proposal_id="p-001",
        items=[_make_item()], verified_total=Decimal("45000.00"),
        created_at=utcnow(), expires_at=utcnow(), signature="sig",
    )
    assert m.mandate_id == "cm-001"

def test_cart_mandate_missing_intent_mandate_id():
    with pytest.raises(ValidationError, match="intent_mandate_id"):
        CartMandate(mandate_id="cm-001", proposal_id="p-001", items=[_make_item()],
                    verified_total=Decimal("45000.00"), created_at=utcnow(),
                    expires_at=utcnow(), signature="sig")


# ── PaymentMandate ────────────────────────────────────────────────────────────

def test_payment_mandate_valid():
    m = PaymentMandate(
        mandate_id="pm-001", cart_mandate_id="cm-001",
        verified_total=Decimal("45000.00"), idempotency_key="abc",
        approval_type="auto", created_at=utcnow(), expires_at=utcnow(), signature="sig",
    )
    assert m.consumed is False

def test_payment_mandate_invalid_approval_type():
    with pytest.raises(ValidationError, match="approval_type"):
        PaymentMandate(mandate_id="pm-001", cart_mandate_id="cm-001",
                       verified_total=Decimal("45000.00"), idempotency_key="abc",
                       approval_type="robot", created_at=utcnow(), expires_at=utcnow(), signature="sig")

def test_payment_mandate_missing_idempotency_key():
    with pytest.raises(ValidationError, match="idempotency_key"):
        PaymentMandate(mandate_id="pm-001", cart_mandate_id="cm-001",
                       verified_total=Decimal("45000.00"), approval_type="auto",
                       created_at=utcnow(), expires_at=utcnow(), signature="sig")


# ── PolicyDecision ────────────────────────────────────────────────────────────

def test_policy_decision_valid():
    d = PolicyDecision(
        proposal_id="p-001", decision="approved", reason="All checks passed.",
        verified_total=Decimal("5000.00"), spend_cap=Decimal("10000.00"),
        idempotency_key="key123", out_of_stock_skus=[], price_mismatches={},
        created_at=utcnow(),
    )
    assert d.decision == "approved"

def test_policy_decision_invalid_decision_value():
    with pytest.raises(ValidationError, match="decision"):
        PolicyDecision(proposal_id="p-001", decision="maybe", reason="r",
                       verified_total=Decimal("5000.00"), spend_cap=Decimal("10000.00"),
                       idempotency_key=None, out_of_stock_skus=[], price_mismatches={},
                       created_at=utcnow())


# ── AuditLogEntry ─────────────────────────────────────────────────────────────

def test_audit_log_entry_valid():
    e = AuditLogEntry(
        entry_id="e-001", session_id="ses-001",
        event_type="proposal_received", payload={"proposal_id": "p-001"},
        created_at=utcnow(),
    )
    assert e.immutable is True

def test_audit_log_entry_invalid_event_type():
    with pytest.raises(ValidationError, match="event_type"):
        AuditLogEntry(entry_id="e-001", session_id="ses-001",
                      event_type="unknown_event", payload={}, created_at=utcnow())

def test_audit_log_entry_missing_session_id():
    with pytest.raises(ValidationError, match="session_id"):
        AuditLogEntry(entry_id="e-001", event_type="proposal_received",
                      payload={}, created_at=utcnow())
