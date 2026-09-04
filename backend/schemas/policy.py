from decimal import Decimal
from datetime import datetime
from typing import Literal
from pydantic import BaseModel


class PolicyDecision(BaseModel):
    proposal_id: str
    decision: Literal["approved", "rejected", "requires_human_approval"]
    reason: str
    verified_total: Decimal
    spend_cap: Decimal
    idempotency_key: str | None
    out_of_stock_skus: list[str]
    price_mismatches: dict[str, Decimal]
    created_at: datetime
