from decimal import Decimal
from datetime import datetime
from typing import Literal
from pydantic import BaseModel

from backend.schemas.proposals import CartItem


class IntentMandate(BaseModel):
    mandate_id: str
    session_id: str
    user_intent: str
    created_at: datetime
    expires_at: datetime
    signature: str


class CartMandate(BaseModel):
    mandate_id: str
    intent_mandate_id: str
    proposal_id: str
    items: list[CartItem]
    verified_total: Decimal
    created_at: datetime
    expires_at: datetime
    signature: str


class PaymentMandate(BaseModel):
    mandate_id: str
    cart_mandate_id: str
    verified_total: Decimal
    idempotency_key: str
    approval_type: Literal["auto", "human"]
    approver_id: str | None = None
    created_at: datetime
    expires_at: datetime
    consumed: bool = False
    signature: str
