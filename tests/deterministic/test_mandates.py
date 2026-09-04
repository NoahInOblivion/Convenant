"""Mandate signing/verification tests — deterministic, no LLM, fast. Run on every commit."""
import pytest
from decimal import Decimal
from datetime import datetime, timezone, timedelta

from backend.schemas.proposals import CartItem
from backend.schemas.mandates import IntentMandate, CartMandate, PaymentMandate
from backend.mandates.signer import sign_mandate, verify_mandate
from backend.mandates.exceptions import (
    MandateExpiredError,
    MandateTamperedError,
    MandateReplayError,
)

SECRET = "a" * 64
OTHER_SECRET = "b" * 64


def utcnow():
    return datetime.now(timezone.utc)


def future(seconds=600):
    return utcnow() + timedelta(seconds=seconds)


def past(seconds=10):
    return utcnow() - timedelta(seconds=seconds)


def make_intent(expires_at=None):
    return IntentMandate(
        mandate_id="im-001", session_id="ses-001",
        user_intent="Buy a laptop",
        created_at=utcnow(),
        expires_at=expires_at or future(),
        signature="",
    )


def make_cart(expires_at=None):
    item = CartItem(sku="SKU001", name="Laptop", quantity=1,
                    agent_proposed_price=Decimal("45000.00"),
                    verified_price=Decimal("45000.00"))
    return CartMandate(
        mandate_id="cm-001", intent_mandate_id="im-001", proposal_id="p-001",
        items=[item], verified_total=Decimal("45000.00"),
        created_at=utcnow(), expires_at=expires_at or future(), signature="",
    )


def make_payment(expires_at=None, consumed=False):
    return PaymentMandate(
        mandate_id="pm-001", cart_mandate_id="cm-001",
        verified_total=Decimal("45000.00"),
        idempotency_key="abc123", approval_type="auto",
        created_at=utcnow(), expires_at=expires_at or future(),
        consumed=consumed, signature="",
    )


# ── Signing and valid verification ────────────────────────────────────────────

def test_sign_and_verify_intent_mandate():
    mandate = make_intent()
    sig = sign_mandate(mandate, SECRET)
    mandate.signature = sig
    assert verify_mandate(mandate, SECRET) is True


def test_sign_and_verify_cart_mandate():
    mandate = make_cart()
    sig = sign_mandate(mandate, SECRET)
    mandate.signature = sig
    assert verify_mandate(mandate, SECRET) is True


def test_sign_and_verify_payment_mandate():
    mandate = make_payment()
    sig = sign_mandate(mandate, SECRET)
    mandate.signature = sig
    assert verify_mandate(mandate, SECRET) is True


def test_wrong_secret_fails_verification():
    mandate = make_intent()
    mandate.signature = sign_mandate(mandate, SECRET)
    assert verify_mandate(mandate, OTHER_SECRET) is False


# ── Tamper detection ──────────────────────────────────────────────────────

def test_single_byte_tamper_in_intent_fails():
    """Change one character in user_intent -> signature must not verify."""
    mandate = make_intent()
    mandate.signature = sign_mandate(mandate, SECRET)
    # Flip the last character
    last = mandate.user_intent[-1]
    mandate.user_intent = mandate.user_intent[:-1] + ("X" if last != "X" else "Y")
    assert verify_mandate(mandate, SECRET) is False


def test_single_byte_tamper_in_cart_total_fails():
    mandate = make_cart()
    mandate.signature = sign_mandate(mandate, SECRET)
    mandate.verified_total = Decimal("45000.01")  # 1 paisa change
    assert verify_mandate(mandate, SECRET) is False


def test_single_byte_tamper_in_payment_amount_fails():
    mandate = make_payment()
    mandate.signature = sign_mandate(mandate, SECRET)
    mandate.verified_total = Decimal("45000.01")
    assert verify_mandate(mandate, SECRET) is False


def test_tamper_consumed_flag_fails():
    """Flipping consumed from False to True must fail verification."""
    mandate = make_payment(consumed=False)
    mandate.signature = sign_mandate(mandate, SECRET)
    mandate.consumed = True
    assert verify_mandate(mandate, SECRET) is False


# ── Expiry ───────────────────────────────────────────────────────────────────

def test_expired_mandate_raises_expired_error():
    mandate = make_intent(expires_at=past(seconds=1))
    mandate.signature = sign_mandate(mandate, SECRET)
    with pytest.raises(MandateExpiredError):
        verify_mandate(mandate, SECRET, raise_on_expired=True)


def test_future_mandate_does_not_raise():
    mandate = make_intent(expires_at=future(seconds=600))
    mandate.signature = sign_mandate(mandate, SECRET)
    assert verify_mandate(mandate, SECRET, raise_on_expired=True) is True


# ── Replay (consumed) ──────────────────────────────────────────────────────────

def test_consumed_payment_mandate_raises_replay_error():
    """A PaymentMandate signed with consumed=True must raise MandateReplayError."""
    mandate = make_payment(consumed=True)
    # Sign it with consumed=True so the signature is valid for this state
    mandate.signature = sign_mandate(mandate, SECRET)
    with pytest.raises(MandateReplayError):
        verify_mandate(mandate, SECRET, raise_on_replay=True)


def test_unconsumed_payment_mandate_does_not_raise_replay():
    mandate = make_payment(consumed=False)
    mandate.signature = sign_mandate(mandate, SECRET)
    assert verify_mandate(mandate, SECRET, raise_on_replay=True) is True
