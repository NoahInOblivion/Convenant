from backend.schemas.mandates import PaymentMandate
from backend.mandates.signer import verify_mandate
from backend.mandates.exceptions import MandateExpiredError, MandateReplayError
from backend.payments.exceptions import MandateGuardException


class MandateGuard:
    def __init__(self, secret_key: str):
        self._secret = secret_key

    def require_valid_mandate(self, mandate: PaymentMandate) -> None:
        if mandate is None:
            raise MandateGuardException("PaymentMandate is None")

        if not verify_mandate(mandate, self._secret):
            raise MandateGuardException(
                f"PaymentMandate {mandate.mandate_id} has invalid signature — tampered or wrong key"
            )

        try:
            verify_mandate(mandate, self._secret, raise_on_expired=True)
        except MandateExpiredError as e:
            raise MandateGuardException(str(e)) from e

        try:
            verify_mandate(mandate, self._secret, raise_on_replay=True)
        except MandateReplayError as e:
            raise MandateGuardException(str(e)) from e
