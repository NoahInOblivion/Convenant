from fastapi import APIRouter
from pydantic import BaseModel
from backend.api.deps import audit_logger

router = APIRouter()


class AuditEntryResponse(BaseModel):
    entry_id: str
    session_id: str
    event_type: str
    payload: dict
    created_at: str


@router.get("/audit", response_model=list[AuditEntryResponse])
async def get_audit_log(session_id: str | None = None):
    entries = audit_logger.get_entries(session_id=session_id)
    return [
        AuditEntryResponse(
            entry_id=e.entry_id,
            session_id=e.session_id,
            event_type=e.event_type,
            payload=e.payload,
            created_at=e.created_at.isoformat(),
        )
        for e in entries
    ]
