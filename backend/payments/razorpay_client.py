import razorpay
from backend.schemas.mandates import PaymentMandate
from backend.payments.guard import MandateGuard
from backend.payments.exceptions import PaymentExecutionError


class RazorpayClient:
    def __init__(self, key_id: str, key_secret: str, secret_key: str):
        self._client = razorpay.Client(auth=(key_id, key_secret))
        self._guard = MandateGuard(secret_key)

    def create_order(self, mandate: PaymentMandate) -> dict:
        # Guard MUST pass before any API call
        self._guard.require_valid_mandate(mandate)

        # Mark consumed BEFORE the API call (idempotency-safe)
        mandate.consumed = True

        amount_paise = int(mandate.verified_total * 100)

        try:
            order = self._client.order.create(
                data={
                    "amount": amount_paise,
                    "currency": "INR",
                    "receipt": mandate.idempotency_key[:40],
                    "notes": {
                        "mandate_id": mandate.mandate_id,
                        "cart_mandate_id": mandate.cart_mandate_id,
                        "session": "covenant",
                    },
                }
            )
            return order
        except Exception as e:
            raise PaymentExecutionError(f"Razorpay order creation failed: {e}") from e
