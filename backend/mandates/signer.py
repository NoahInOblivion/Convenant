"""
Mandate signing and verification.
Independent of the agent graph — pure crypto functions.
"""
import hmac
import hashlib
import json
from datetime import datetime, timezone

from backend.schemas.mandates import IntentMandate, CartMandate, PaymentMandate
from backend.mandates.exceptions import (
    MandateExpiredError,
    MandateReplayError,
)

Mandate = IntentMandate | CartMandate | PaymentMandate


def _canonical_payload(mandate: Mandate) -> bytes:
    """
    Produce a canonical, deterministic JSON bytes representation of the mandate,
    excluding the 'signature' field itself.
    """
    data = mandate.model_dump(mode="json")
    data.pop("signature", None)
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sign_mandate(mandate: Mandate, secret_key: str) -> str:
    """
    Compute HMAC-SHA256 of the canonical mandate payload.
    Returns hex digest string.
    """
    key = secret_key.encode("utf-8")
    payload = _canonical_payload(mandate)
    return hmac.new(key, payload, hashlib.sha256).hexdigest()


def verify_mandate(
    mandate: Mandate,
    secret_key: str,
    raise_on_expired: bool = False,
    raise_on_replay: bool = False,
) -> bool:
    """
    Verify a mandate's signature and optionally check expiry and consumed state.

    Returns True if signature is valid (and expiry/replay checks pass if requested).
    Returns False if signature is invalid.
    Raises MandateExpiredError if expired and raise_on_expired=True.
    Raises MandateReplayError if consumed and raise_on_replay=True (PaymentMandate only).
    """
    # Compute expected signature
    key = secret_key.encode("utf-8")
    payload = _canonical_payload(mandate)
    expected = hmac.new(key, payload, hashlib.sha256).hexdigest()

    # Constant-time comparison
    if not hmac.compare_digest(expected, mandate.signature):
        return False

    # Expiry check
    if raise_on_expired:
        if mandate.expires_at < datetime.now(timezone.utc):
            raise MandateExpiredError(
                f"Mandate {mandate.mandate_id} expired at {mandate.expires_at.isoformat()}"
            )

    # Replay check (PaymentMandate only)
    if raise_on_replay and isinstance(mandate, PaymentMandate):
        if mandate.consumed:
            raise MandateReplayError(
                f"PaymentMandate {mandate.mandate_id} has already been consumed."
            )

    return True
