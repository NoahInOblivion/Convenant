import pytest
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

from backend.schemas.mandates import PaymentMandate
from backend.mandates.signer import sign_mandate
from backend.payments.guard import MandateGuard
from backend.payments.exceptions import MandateGuardException
from backend.payments.razorpay_client import RazorpayClient


SECRET = "a" * 64


def utcnow():
    return datetime.now(timezone.utc)


def make_payment_mandate(consumed=False, expires_delta=timedelta(seconds=300), sign=True, secret=SECRET):
    expires_at = utcnow() + expires_delta
    mandate = PaymentMandate(
        mandate_id="pm-test-001",
        cart_mandate_id="cm-test-001",
        verified_total=Decimal("5000.00"),
        idempotency_key="abc123def456abc123def456abc123def456abc123def456abc123def456abc1",
        approval_type="auto",
        created_at=utcnow(),
        expires_at=expires_at,
        consumed=consumed,
        signature="",
    )
    if sign:
        mandate.signature = sign_mandate(mandate, secret)
    return mandate


# --- MandateGuard unit tests ---

def test_valid_mandate_passes_guard():
    guard = MandateGuard(SECRET)
    mandate = make_payment_mandate()
    guard.require_valid_mandate(mandate)  # must not raise


def test_none_mandate_raises_guard_exception():
    guard = MandateGuard(SECRET)
    with pytest.raises(MandateGuardException, match="None"):
        guard.require_valid_mandate(None)


def test_tampered_mandate_raises_guard_exception():
    guard = MandateGuard(SECRET)
    mandate = make_payment_mandate()
    mandate.verified_total = Decimal("1.00")  # tamper after signing
    with pytest.raises(MandateGuardException, match="invalid signature"):
        guard.require_valid_mandate(mandate)


def test_expired_mandate_raises_guard_exception():
    guard = MandateGuard(SECRET)
    mandate = make_payment_mandate(expires_delta=timedelta(seconds=-10))
    with pytest.raises(MandateGuardException):
        guard.require_valid_mandate(mandate)


def test_consumed_mandate_raises_guard_exception():
    guard = MandateGuard(SECRET)
    mandate = make_payment_mandate(consumed=True)  # signed with consumed=True
    with pytest.raises(MandateGuardException):
        guard.require_valid_mandate(mandate)


def test_wrong_secret_raises_guard_exception():
    guard = MandateGuard("c" * 64)
    mandate = make_payment_mandate(secret=SECRET)  # signed with different secret
    with pytest.raises(MandateGuardException, match="invalid signature"):
        guard.require_valid_mandate(mandate)


# --- RazorpayClient guard integration ---

def test_create_order_with_valid_mandate_calls_razorpay():
    mandate = make_payment_mandate()
    with patch("backend.payments.razorpay_client.razorpay.Client") as mock_razorpay:
        mock_client = MagicMock()
        mock_razorpay.return_value = mock_client
        mock_client.order.create.return_value = {"id": "order_test123", "status": "created"}
        client = RazorpayClient("key_id", "key_secret", SECRET)
        result = client.create_order(mandate)
        assert result["id"] == "order_test123"
        assert mandate.consumed is True
        mock_client.order.create.assert_called_once()


def test_create_order_tampered_mandate_raises_and_sdk_not_called():
    mandate = make_payment_mandate()
    mandate.verified_total = Decimal("1.00")  # tamper
    with patch("backend.payments.razorpay_client.razorpay.Client") as mock_razorpay:
        mock_client = MagicMock()
        mock_razorpay.return_value = mock_client
        client = RazorpayClient("key_id", "key_secret", SECRET)
        with pytest.raises(MandateGuardException):
            client.create_order(mandate)
        mock_client.order.create.assert_not_called()


def test_consumed_is_true_before_api_call():
    mandate = make_payment_mandate()
    consumed_before = []
    original_create = None

    with patch("backend.payments.razorpay_client.razorpay.Client") as mock_razorpay:
        mock_client = MagicMock()
        mock_razorpay.return_value = mock_client

        def capture_and_return(data):
            consumed_before.append(mandate.consumed)
            return {"id": "order_captured"}

        mock_client.order.create.side_effect = capture_and_return
        client = RazorpayClient("key_id", "key_secret", SECRET)
        client.create_order(mandate)

    assert consumed_before == [True]  # consumed=True was set before the API call
