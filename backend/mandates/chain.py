"""
MandateChain: builds and validates the full Intent -> Cart -> Payment chain.
"""
import uuid
from decimal import Decimal
from datetime import datetime, timezone, timedelta

from backend.schemas.proposals import CartProposal, CartItem
from backend.schemas.mandates import IntentMandate, CartMandate, PaymentMandate
from backend.schemas.policy import PolicyDecision
from backend.mandates.signer import sign_mandate, verify_mandate
from backend.mandates.exceptions import ChainIntegrityError


class MandateChain:
    def __init__(self, secret_key: str, intent_ttl: int = 900,
                 cart_ttl: int = 600, payment_ttl: int = 300):
        self._secret = secret_key
        self._intent_ttl = intent_ttl
        self._cart_ttl = cart_ttl
        self._payment_ttl = payment_ttl

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def create_intent_mandate(self, session_id: str, user_intent: str) -> IntentMandate:
        now = self._now()
        m = IntentMandate(
            mandate_id=str(uuid.uuid4()),
            session_id=session_id,
            user_intent=user_intent,
            created_at=now,
            expires_at=now + timedelta(seconds=self._intent_ttl),
            signature="",
        )
        m.signature = sign_mandate(m, self._secret)
        return m

    def create_cart_mandate(
        self, intent_mandate: IntentMandate,
        proposal: CartProposal, decision: PolicyDecision
    ) -> CartMandate:
        # Verify intent mandate first
        if not verify_mandate(intent_mandate, self._secret, raise_on_expired=True):
            raise ChainIntegrityError("Intent mandate signature invalid")

        now = self._now()
        # Use verified prices from policy decision price_mismatches map
        # price_mismatches maps sku -> db_price for items where agent price != db price
        verified_items = []
        for item in proposal.items:
            # Use db price if there was a mismatch, otherwise use agent_proposed_price
            if item.sku in decision.price_mismatches:
                vp = decision.price_mismatches[item.sku]
            else:
                vp = item.agent_proposed_price
            verified_items.append(
                CartItem(**{**item.model_dump(), "verified_price": vp})
            )

        m = CartMandate(
            mandate_id=str(uuid.uuid4()),
            intent_mandate_id=intent_mandate.mandate_id,
            proposal_id=proposal.proposal_id,
            items=verified_items,
            verified_total=decision.verified_total,
            created_at=now,
            expires_at=now + timedelta(seconds=self._cart_ttl),
            signature="",
        )
        m.signature = sign_mandate(m, self._secret)
        return m

    def create_payment_mandate(
        self, cart_mandate: CartMandate, decision: PolicyDecision,
        approval_type: str = "auto", approver_id: str | None = None
    ) -> PaymentMandate:
        if not verify_mandate(cart_mandate, self._secret, raise_on_expired=True):
            raise ChainIntegrityError("Cart mandate signature invalid")

        now = self._now()
        m = PaymentMandate(
            mandate_id=str(uuid.uuid4()),
            cart_mandate_id=cart_mandate.mandate_id,
            verified_total=cart_mandate.verified_total,
            idempotency_key=decision.idempotency_key,
            approval_type=approval_type,
            approver_id=approver_id,
            created_at=now,
            expires_at=now + timedelta(seconds=self._payment_ttl),
            consumed=False,
            signature="",
        )
        m.signature = sign_mandate(m, self._secret)
        return m
