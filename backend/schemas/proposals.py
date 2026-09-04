from decimal import Decimal
from datetime import datetime
from typing import Annotated
from pydantic import BaseModel, Field


class CartItem(BaseModel):
    sku: str
    name: str
    quantity: Annotated[int, Field(ge=1)]
    agent_proposed_price: Decimal
    verified_price: Decimal | None = None


class CartProposal(BaseModel):
    proposal_id: str
    session_id: str
    items: Annotated[list[CartItem], Field(min_length=1)]
    total_proposed: Decimal
    reasoning: str
    created_at: datetime
