class MandateGuardException(Exception):
    """Raised when create_order() is called without a valid, unexpired, unconsumed PaymentMandate."""

class PaymentExecutionError(Exception):
    """Raised when the Razorpay API returns an error."""
