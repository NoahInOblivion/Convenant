"""
Immutable append-only audit logger.
In production, writes to PostgreSQL with UPDATE/DELETE prevention trigger.
In tests, uses an in-memory list.
"""
import uuid
from datetime import datetime, timezone
from backend.schemas.audit import AuditLogEntry, AuditEventType


class AuditLogger:
    """Abstract base for audit logging."""

    def log(self, session_id: str, event_type: AuditEventType, payload: dict) -> AuditLogEntry:
        raise NotImplementedError


class InMemoryAuditLogger(AuditLogger):
    """In-memory audit logger for testing."""

    def __init__(self):
        self._entries: list[AuditLogEntry] = []

    def log(self, session_id: str, event_type: AuditEventType, payload: dict) -> AuditLogEntry:
        entry = AuditLogEntry(
            entry_id=str(uuid.uuid4()),
            session_id=session_id,
            event_type=event_type,
            payload=payload,
            created_at=datetime.now(timezone.utc),
        )
        self._entries.append(entry)
        return entry

    def get_entries(self, session_id: str | None = None) -> list[AuditLogEntry]:
        if session_id:
            return [e for e in self._entries if e.session_id == session_id]
        return list(self._entries)
