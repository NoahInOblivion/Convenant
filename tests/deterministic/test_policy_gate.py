"""Policy gate tests — deterministic, zero LLM. 17 cases. Run on every commit."""
import pytest
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import MagicMock

from backend.schemas.proposals import CartItem, CartProposal
from backend.schemas.policy import PolicyDecision
from backend.policy.gate import evaluate_proposal
from backend.policy.catalog_repository import CatalogRepository


def utcnow():
    return datetime.now(timezone.utc)


def make_item(sku="SKU001", name="Laptop", qty=1, price=Decimal("45000.00")):
    return CartItem(sku=sku, name=name, quantity=qty, agent_proposed_price=price)


def make_proposal(items=None, total=Decimal("45000.00"), session="ses-001", proposal_id="prop-001"):
    if items is None:
        items = [make_item()]
    return CartProposal(
        proposal_id=proposal_id, session_id=session,
        items=items, total_proposed=total,
        reasoning="Test proposal", created_at=utcnow(),
    )


def make_catalog(prices=None, stock=None):
    cat = MagicMock(spec=CatalogRepository)
    prices = prices or {"SKU001": Decimal("45000.00")}
    stock = stock or {"SKU001": 100}
    cat.get_price.side_effect = lambda sku: prices.get(sku)
    cat.check_stock.side_effect = lambda sku, qty: stock.get(sku, 0) >= qty
    return cat


SPEND_CAP = Decimal("10000.00")


# ── Happy path ────────────────────────────────────────────────────────────────

def test_under_cap_approved():
    proposal = make_proposal(
        items=[make_item(price=Decimal("5000.00"))],
        total=Decimal("5000.00"),
    )
    catalog = make_catalog(prices={"SKU001": Decimal("5000.00")}, stock={"SKU001": 10})
    decision = evaluate_proposal(proposal, catalog, SPEND_CAP, set())
    assert decision.decision == "approved"
    assert decision.verified_total == Decimal("5000.00")
    assert decision.idempotency_key is not None


def test_exact_boundary_approved():
    """Verified total exactly equals spend cap -> approved (not over)."""
    proposal = make_proposal(
        items=[make_item(price=Decimal("10000.00"))],
        total=Decimal("10000.00"),
    )
    catalog = make_catalog(prices={"SKU001": Decimal("10000.00")}, stock={"SKU001": 5})
    decision = evaluate_proposal(proposal, catalog, SPEND_CAP, set())
    assert decision.decision == "approved"


def test_one_rupee_over_cap_requires_human():
    """One rupee over -> requires_human_approval, not approved."""
    proposal = make_proposal(
        items=[make_item(price=Decimal("10001.00"))],
        total=Decimal("10001.00"),
    )
    catalog = make_catalog(prices={"SKU001": Decimal("10001.00")}, stock={"SKU001": 5})
    decision = evaluate_proposal(proposal, catalog, SPEND_CAP, set())
    assert decision.decision == "requires_human_approval"
    assert decision.verified_total == Decimal("10001.00")


def test_over_cap_requires_human_approval():
    proposal = make_proposal(
        items=[make_item(price=Decimal("50000.00"))],
        total=Decimal("50000.00"),
    )
    catalog = make_catalog(prices={"SKU001": Decimal("50000.00")}, stock={"SKU001": 5})
    decision = evaluate_proposal(proposal, catalog, SPEND_CAP, set())
    assert decision.decision == "requires_human_approval"


# ── Stock checks ──────────────────────────────────────────────────────────────

def test_out_of_stock_rejected():
    proposal = make_proposal(items=[make_item(qty=5)], total=Decimal("225000.00"))
    catalog = make_catalog(prices={"SKU001": Decimal("45000.00")}, stock={"SKU001": 2})
    decision = evaluate_proposal(proposal, catalog, SPEND_CAP, set())
    assert decision.decision == "rejected"
    assert "SKU001" in decision.out_of_stock_skus


def test_zero_stock_rejected():
    proposal = make_proposal()
    catalog = make_catalog(prices={"SKU001": Decimal("5000.00")}, stock={"SKU001": 0})
    decision = evaluate_proposal(proposal, catalog, SPEND_CAP, set())
    assert decision.decision == "rejected"
    assert "SKU001" in decision.out_of_stock_skus


def test_unknown_sku_rejected():
    proposal = make_proposal(items=[make_item(sku="GHOST_SKU")])
    catalog = make_catalog(prices={}, stock={})
    decision = evaluate_proposal(proposal, catalog, SPEND_CAP, set())
    assert decision.decision == "rejected"
    assert "GHOST_SKU" in decision.out_of_stock_skus


def test_multi_item_one_out_of_stock_rejected():
    items = [
        make_item(sku="SKU001", qty=1, price=Decimal("2000.00")),
        make_item(sku="SKU002", name="Mouse", qty=10, price=Decimal("500.00")),
    ]
    catalog = make_catalog(
        prices={"SKU001": Decimal("2000.00"), "SKU002": Decimal("500.00")},
        stock={"SKU001": 5, "SKU002": 3},
    )
    decision = evaluate_proposal(make_proposal(items=items), catalog, SPEND_CAP, set())
    assert decision.decision == "rejected"
    assert "SKU002" in decision.out_of_stock_skus


# ── Price re-verification ─────────────────────────────────────────────────────

def test_price_mismatch_uses_db_price():
    item = make_item(price=Decimal("40000.00"))  # agent says 40k
    proposal = make_proposal(items=[item], total=Decimal("40000.00"))
    catalog = make_catalog(prices={"SKU001": Decimal("45000.00")}, stock={"SKU001": 5})
    decision = evaluate_proposal(proposal, catalog, SPEND_CAP, set())
    assert decision.verified_total == Decimal("45000.00")
    assert "SKU001" in decision.price_mismatches
    assert decision.price_mismatches["SKU001"] == Decimal("45000.00")


def test_agent_inflated_price_uses_db_price():
    item = make_item(price=Decimal("9999.00"))  # agent over-reports
    proposal = make_proposal(items=[item], total=Decimal("9999.00"))
    catalog = make_catalog(prices={"SKU001": Decimal("5000.00")}, stock={"SKU001": 5})
    decision = evaluate_proposal(proposal, catalog, SPEND_CAP, set())
    assert decision.verified_total == Decimal("5000.00")
    assert decision.decision == "approved"


# ── Idempotency key ───────────────────────────────────────────────────────────

def test_idempotency_key_generated_on_approval():
    proposal = make_proposal(items=[make_item(price=Decimal("5000.00"))], total=Decimal("5000.00"))
    catalog = make_catalog(prices={"SKU001": Decimal("5000.00")}, stock={"SKU001": 10})
    decision = evaluate_proposal(proposal, catalog, SPEND_CAP, set())
    assert decision.idempotency_key is not None
    assert len(decision.idempotency_key) == 64  # SHA-256 hex digest


def test_duplicate_idempotency_key_rejected():
    proposal = make_proposal(items=[make_item(price=Decimal("5000.00"))], total=Decimal("5000.00"))
    catalog = make_catalog(prices={"SKU001": Decimal("5000.00")}, stock={"SKU001": 10})
    first = evaluate_proposal(proposal, catalog, SPEND_CAP, set())
    seen = {first.idempotency_key}
    second = evaluate_proposal(proposal, catalog, SPEND_CAP, seen)
    assert second.decision == "rejected"
    assert "duplicate" in second.reason.lower() or "idempotency" in second.reason.lower()


def test_different_proposals_get_different_keys():
    p1 = make_proposal(items=[make_item(sku="SKU001", price=Decimal("5000.00"))],
                       total=Decimal("5000.00"), proposal_id="prop-A")
    p2 = make_proposal(items=[make_item(sku="SKU001", qty=2, price=Decimal("5000.00"))],
                       total=Decimal("10000.00"), proposal_id="prop-B")
    cat = make_catalog(prices={"SKU001": Decimal("5000.00")}, stock={"SKU001": 10})
    d1 = evaluate_proposal(p1, cat, SPEND_CAP, set())
    d2 = evaluate_proposal(p2, cat, SPEND_CAP, set())
    assert d1.idempotency_key != d2.idempotency_key


# ── Multi-item + combined checks ──────────────────────────────────────────────

def test_multi_item_under_cap_approved():
    items = [
        make_item(sku="SKU001", name="Keyboard", qty=1, price=Decimal("2000.00")),
        make_item(sku="SKU002", name="Mouse", qty=1, price=Decimal("1500.00")),
        make_item(sku="SKU003", name="Pad", qty=1, price=Decimal("500.00")),
    ]
    catalog = make_catalog(
        prices={"SKU001": Decimal("2000.00"), "SKU002": Decimal("1500.00"), "SKU003": Decimal("500.00")},
        stock={"SKU001": 5, "SKU002": 5, "SKU003": 5},
    )
    proposal = make_proposal(items=items, total=Decimal("4000.00"))
    decision = evaluate_proposal(proposal, catalog, SPEND_CAP, set())
    assert decision.decision == "approved"
    assert decision.verified_total == Decimal("4000.00")


def test_policy_decision_has_timestamp():
    proposal = make_proposal(items=[make_item(price=Decimal("5000.00"))], total=Decimal("5000.00"))
    catalog = make_catalog(prices={"SKU001": Decimal("5000.00")}, stock={"SKU001": 10})
    decision = evaluate_proposal(proposal, catalog, SPEND_CAP, set())
    assert decision.created_at is not None


def test_idempotency_key_generated_for_human_approval():
    """Over-cap proposals still get an idempotency key (for human approval flow)."""
    proposal = make_proposal(
        items=[make_item(price=Decimal("15000.00"))],
        total=Decimal("15000.00"),
    )
    catalog = make_catalog(prices={"SKU001": Decimal("15000.00")}, stock={"SKU001": 5})
    decision = evaluate_proposal(proposal, catalog, SPEND_CAP, set())
    assert decision.decision == "requires_human_approval"
    assert decision.idempotency_key is not None
    assert len(decision.idempotency_key) == 64
