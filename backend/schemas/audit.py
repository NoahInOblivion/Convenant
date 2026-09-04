from datetime import datetime
from typing import Literal
from pydantic import BaseModel


AuditEventType = Literal[
    "proposal_received", "policy_decision", "mandate_signed",
    "human_approval_requested", "human_approved", "human_rejected",
    "payment_initiated", "payment_success", "payment_failed",
    "replan_triggered", "replan_success", "replan_failed",
    "terminal_denial",
]


class AuditLogEntry(BaseModel):
    entry_id: str
    session_id: str
    event_type: AuditEventType
    payload: dict
    created_at: datetime
    immutable: bool = True
