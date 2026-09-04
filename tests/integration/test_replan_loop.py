"""
Phase 5 integration tests: Re-plan loop + graceful denial.
- BuyerAgentNode.run() is mocked (no real OpenAI API)
- Policy gate and mandate signer are NEVER mocked
- InMemoryCatalogRepository used for real price/stock checks
"""
import pytest
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from backend.schemas.proposals import CartItem, CartProposal
from backend.schemas.policy import PolicyDecision
from backend.policy.gate import evaluate_proposal
from backend.audit.log import InMemoryAuditLogger
from backend.replan.loop import ReplanLoop, GracefulDenialMessage
from backend.db.seed_catalog import InMemoryCatalogRepository, SEED_CATALOG


SPEND_CAP = Decimal("10000.00")


def utcnow():
    return datetime.now(timezone.utc)


def make_proposal(items, proposal_id="prop-test", session_id="ses-test"):
    total = sum(i.agent_proposed_price * i.quantity for i in items)
    return CartProposal(
        proposal_id=proposal_id,
        session_id=session_id,
        items=items,
        total_proposed=total,
        reasoning="Test proposal",
        created_at=utcnow(),
    )


def make_item(sku, name, qty, price):
    return CartItem(sku=sku, name=name, quantity=qty, agent_proposed_price=price)


# Catalog: KB001=4500 (in stock), LAPTOP001=75000 (in stock), WEBCAM001=0 stock
catalog = InMemoryCatalogRepository()


# ---- Scenario 1: Over-cap -> replan -> approved ----

def test_replan_from_over_cap_to_approved():
    """
    First proposal is over cap (LAPTOP001 at 75000 > 10000).
    Replan proposes an affordable item (KB001 at 4500).
    Expect: replan succeeds, returns (CartProposal, PolicyDecision) with decision=approved.
    """
    audit = InMemoryAuditLogger()

    # First proposal: over cap
    over_cap_proposal = make_proposal(
        [make_item("LAPTOP001", "ProBook Laptop 14", 1, Decimal("75000.00"))],
        proposal_id="prop-over-cap",
    )
    initial_decision = evaluate_proposal(over_cap_proposal, catalog, SPEND_CAP, set())
    assert initial_decision.decision == "requires_human_approval"

    # Replan proposal: within cap
    affordable_proposal = make_proposal(
        [make_item("KB001", "Mechanical Keyboard", 1, Decimal("4500.00"))],
        proposal_id="prop-affordable",
    )

    mock_agent = MagicMock()
    mock_agent.run.return_value = affordable_proposal

    loop = ReplanLoop(
        buyer_agent=mock_agent,
        catalog=catalog,
        spend_cap=SPEND_CAP,
        audit_logger=audit,
        max_attempts=2,
    )

    result = loop.attempt(
        original_request="Buy me a laptop",
        session_id="ses-test",
        initial_decision=initial_decision,
    )

    assert isinstance(result, tuple), f"Expected (proposal, decision) tuple, got {type(result)}"
    proposal, decision = result
    assert decision.decision == "approved"
    assert decision.verified_total == Decimal("4500.00")

    # Audit check
    entries = audit.get_entries("ses-test")
    event_types = [e.event_type for e in entries]
    assert "replan_triggered" in event_types
    assert "replan_success" in event_types
    assert "terminal_denial" not in event_types


# ---- Scenario 2: All replans rejected -> terminal denial ----

def test_terminal_denial_after_all_replans_fail():
    """
    All replan proposals are over cap.
    After max_attempts (2) exhausted, returns GracefulDenialMessage.
    terminal_denial audit entry must be logged.
    """
    audit = InMemoryAuditLogger()

    # Both proposals are laptops (over cap)
    over_cap_proposal = make_proposal(
        [make_item("LAPTOP001", "ProBook Laptop 14", 1, Decimal("75000.00"))],
        proposal_id="prop-over-cap-initial",
    )
    initial_decision = evaluate_proposal(over_cap_proposal, catalog, SPEND_CAP, set())

    replan_proposal_1 = make_proposal(
        [make_item("LAPTOP001", "ProBook Laptop 14", 1, Decimal("75000.00"))],
        proposal_id="prop-replan-1",
    )
    replan_proposal_2 = make_proposal(
        [make_item("LAPTOP002", "UltraSlim Laptop 15", 1, Decimal("95000.00"))],
        proposal_id="prop-replan-2",
    )

    mock_agent = MagicMock()
    mock_agent.run.side_effect = [replan_proposal_1, replan_proposal_2]

    loop = ReplanLoop(
        buyer_agent=mock_agent,
        catalog=catalog,
        spend_cap=SPEND_CAP,
        audit_logger=audit,
        max_attempts=2,
    )

    result = loop.attempt(
        original_request="Buy me the most expensive laptop",
        session_id="ses-test-2",
        initial_decision=initial_decision,
    )

    assert isinstance(result, GracefulDenialMessage)
    assert result.session_id == "ses-test-2"
    assert result.attempts == 2

    # Audit: terminal_denial must be logged
    entries = audit.get_entries("ses-test-2")
    event_types = [e.event_type for e in entries]
    assert "terminal_denial" in event_types
    assert "replan_success" not in event_types
    # 2 replan_triggered events (one per attempt)
    triggered_count = sum(1 for e in entries if e.event_type == "replan_triggered")
    assert triggered_count == 2


# ---- Scenario 3: Out-of-stock -> replan -> approved with in-stock item ----

def test_replan_from_out_of_stock_to_approved():
    """
    First proposal has WEBCAM001 (out of stock stock=0).
    Replan proposes MOUSE001 (in stock, 1500 < 10000 cap).
    """
    audit = InMemoryAuditLogger()

    oos_proposal = make_proposal(
        [make_item("WEBCAM001", "HD Webcam", 1, Decimal("3200.00"))],
        proposal_id="prop-oos",
    )
    initial_decision = evaluate_proposal(oos_proposal, catalog, SPEND_CAP, set())
    assert initial_decision.decision == "rejected"
    assert "WEBCAM001" in initial_decision.out_of_stock_skus

    in_stock_proposal = make_proposal(
        [make_item("MOUSE001", "Ergonomic Mouse", 1, Decimal("1500.00"))],
        proposal_id="prop-in-stock",
    )
    mock_agent = MagicMock()
    mock_agent.run.return_value = in_stock_proposal

    loop = ReplanLoop(
        buyer_agent=mock_agent, catalog=catalog,
        spend_cap=SPEND_CAP, audit_logger=audit, max_attempts=2,
    )
    result = loop.attempt(
        original_request="Buy me a webcam",
        session_id="ses-oos",
        initial_decision=initial_decision,
    )

    assert isinstance(result, tuple)
    _, decision = result
    assert decision.decision == "approved"
