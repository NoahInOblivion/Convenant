class MandateError(Exception):
    """Base class for mandate errors."""

class MandateExpiredError(MandateError):
    """Mandate has passed its expires_at timestamp."""

class MandateTamperedError(MandateError):
    """Mandate signature does not match payload — tamper detected."""

class MandateReplayError(MandateError):
    """PaymentMandate has already been consumed — replay attack blocked."""

class ChainIntegrityError(MandateError):
    """Mandate chain linkage is broken."""
