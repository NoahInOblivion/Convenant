"""
Deterministic Policy Gate — zero LLM, pure synchronous function.
Never trusts agent-proposed prices. Always re-verifies from catalog.
"""
import hashlib
import json
from decimal import Decimal
from datetime import datetime, timezone

from backend.schemas.proposals import CartProposal
from backend.schemas.policy import PolicyDecision
from backend.policy.catalog_repository import CatalogRepository


def _generate_idempotency_key(proposal: CartProposal, verified_total: Decimal) -> str:
    """SHA-256(proposal_id + verified_total + sorted_skus)."""
    sorted_skus = sorted(f"{item.sku}x{item.quantity}" for item in proposal.items)
    payload = json.dumps({
        "proposal_id": proposal.proposal_id,
        "verified_total": str(verified_total),
        "skus": sorted_skus,
    }, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def evaluate_proposal(
    proposal: CartProposal,
    catalog: CatalogRepository,
    spend_cap: Decimal,
    seen_idempotency_keys: set[str],
) -> PolicyDecision:
    """
    Evaluate a CartProposal deterministically.

    Rules applied in order:
    1. Price re-verification (DB price wins, always)
    2. Stock check (collect all out-of-stock SKUs)
    3. Reject if any out-of-stock
    4. Calculate verified_total from DB prices
    5. Idempotency key generation
    6. Duplicate key check -> reject if seen
    7. Spend cap check -> requires_human_approval if over
    8. Auto-approve if all checks pass
    """
    out_of_stock_skus: list[str] = []
    price_mismatches: dict[str, Decimal] = {}
    verified_items: list[tuple] = []  # (item, db_price)

    for item in proposal.items:
        db_price = catalog.get_price(item.sku)

        # Unknown SKU -> treat as out of stock
        if db_price is None:
            out_of_stock_skus.append(item.sku)
            continue

        # Record price mismatch (for audit) but always use DB price
        if db_price != item.agent_proposed_price:
            price_mismatches[item.sku] = db_price

        # Stock check
        if not catalog.check_stock(item.sku, item.quantity):
            out_of_stock_skus.append(item.sku)
            continue

        verified_items.append((item, db_price))

    # Rule 3: reject if any out-of-stock
    if out_of_stock_skus:
        return PolicyDecision(
            proposal_id=proposal.proposal_id,
            decision="rejected",
            reason=f"Out of stock or unknown SKUs: {', '.join(out_of_stock_skus)}",
            verified_total=Decimal("0"),
            spend_cap=spend_cap,
            idempotency_key=None,
            out_of_stock_skus=out_of_stock_skus,
            price_mismatches=price_mismatches,
            created_at=datetime.now(timezone.utc),
        )

    # Rule 4: verified total uses DB prices
    verified_total = sum(db_price * item.quantity for item, db_price in verified_items)

    # Rule 5: generate idempotency key
    idempotency_key = _generate_idempotency_key(proposal, verified_total)

    # Rule 6: duplicate check
    if idempotency_key in seen_idempotency_keys:
        return PolicyDecision(
            proposal_id=proposal.proposal_id,
            decision="rejected",
            reason="Duplicate idempotency key detected — this proposal has already been processed.",
            verified_total=verified_total,
            spend_cap=spend_cap,
            idempotency_key=idempotency_key,
            out_of_stock_skus=[],
            price_mismatches=price_mismatches,
            created_at=datetime.now(timezone.utc),
        )

    # Rule 7: spend cap check
    if verified_total > spend_cap:
        return PolicyDecision(
            proposal_id=proposal.proposal_id,
            decision="requires_human_approval",
            reason=f"Verified total \u20b9{verified_total} exceeds auto-approval cap of \u20b9{spend_cap}.",
            verified_total=verified_total,
            spend_cap=spend_cap,
            idempotency_key=idempotency_key,
            out_of_stock_skus=[],
            price_mismatches=price_mismatches,
            created_at=datetime.now(timezone.utc),
        )

    # Rule 8: auto-approve
    return PolicyDecision(
        proposal_id=proposal.proposal_id,
        decision="approved",
        reason="All checks passed. Auto-approved.",
        verified_total=verified_total,
        spend_cap=spend_cap,
        idempotency_key=idempotency_key,
        out_of_stock_skus=[],
        price_mismatches=price_mismatches,
        created_at=datetime.now(timezone.utc),
    )
