"""
POST /api/propose — submit a natural language purchase request.
Full flow: BuyerAgent → PolicyGate → MandateChain → (optionally) RazorpayClient
"""
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.policy.gate import evaluate_proposal
from backend.replan.loop import ReplanLoop, GracefulDenialMessage
from backend.api.deps import (
    audit_logger, catalog, seen_idempotency_keys,
    mandate_chain, razorpay_client, get_buyer_agent,
)

router = APIRouter()


class ProposeRequest(BaseModel):
    request: str
    session_id: str = ""


class CartItemResponse(BaseModel):
    sku: str
    name: str
    quantity: int
    agent_proposed_price: str
    verified_price: str | None


class ProposeResponse(BaseModel):
    proposal_id: str
    session_id: str
    decision: str
    reason: str
    verified_total: str
    items: list[CartItemResponse]
    idempotency_key: str | None
    mandate_id: str | None = None
    razorpay_order_id: str | None = None
    denial_message: str | None = None


@router.post("/propose", response_model=ProposeResponse)
async def propose(body: ProposeRequest):
    from backend.config import settings

    session_id = body.session_id or str(uuid.uuid4())
    buyer_agent = get_buyer_agent()

    # Log request received
    audit_logger.log(
        session_id=session_id,
        event_type="proposal_received",
        payload={"request": body.request},
    )

    # Step 1: Buyer agent proposes a cart
    try:
        proposal = buyer_agent.run(body.request, session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {e}")

    # Step 2: Policy gate evaluation
    decision = evaluate_proposal(
        proposal, catalog, settings.spend_cap, seen_idempotency_keys
    )
    audit_logger.log(
        session_id=session_id,
        event_type="policy_decision",
        payload=decision.model_dump(mode="json"),
    )

    # Step 3: If rejected, try replan
    if decision.decision == "rejected":
        replan_loop = ReplanLoop(
            buyer_agent=buyer_agent,
            catalog=catalog,
            spend_cap=settings.spend_cap,
            audit_logger=audit_logger,
            max_attempts=2,
        )
        result = replan_loop.attempt(body.request, session_id, decision)
        if isinstance(result, GracefulDenialMessage):
            return ProposeResponse(
                proposal_id=proposal.proposal_id,
                session_id=session_id,
                decision="rejected",
                reason=result.reason,
                verified_total="0.00",
                items=[],
                idempotency_key=None,
                denial_message=result.reason,
            )
        proposal, decision = result

    # Step 4: Build mandate chain for approved/human-approval proposals
    items_response = [
        CartItemResponse(
            sku=item.sku,
            name=item.name,
            quantity=item.quantity,
            agent_proposed_price=str(item.agent_proposed_price),
            verified_price=str(item.verified_price) if item.verified_price else None,
        )
        for item in proposal.items
    ]

    if decision.decision == "requires_human_approval":
        return ProposeResponse(
            proposal_id=proposal.proposal_id,
            session_id=session_id,
            decision="requires_human_approval",
            reason=decision.reason,
            verified_total=str(decision.verified_total),
            items=items_response,
            idempotency_key=decision.idempotency_key,
        )

    # Approved: build mandate chain
    if decision.idempotency_key:
        seen_idempotency_keys.add(decision.idempotency_key)

    intent_mandate = mandate_chain.create_intent_mandate(session_id, body.request)
    cart_mandate = mandate_chain.create_cart_mandate(intent_mandate, proposal, decision)
    payment_mandate = mandate_chain.create_payment_mandate(
        cart_mandate, decision, approval_type="auto"
    )

    audit_logger.log(
        session_id=session_id,
        event_type="mandate_signed",
        payload={
            "intent_mandate_id": intent_mandate.mandate_id,
            "cart_mandate_id": cart_mandate.mandate_id,
            "payment_mandate_id": payment_mandate.mandate_id,
        },
    )

    # Create Razorpay order
    try:
        order = razorpay_client.create_order(payment_mandate)
        audit_logger.log(
            session_id=session_id,
            event_type="payment_initiated",
            payload={"razorpay_order_id": order.get("id"), "amount": str(decision.verified_total)},
        )
        return ProposeResponse(
            proposal_id=proposal.proposal_id,
            session_id=session_id,
            decision="approved",
            reason=decision.reason,
            verified_total=str(decision.verified_total),
            items=items_response,
            idempotency_key=decision.idempotency_key,
            mandate_id=payment_mandate.mandate_id,
            razorpay_order_id=order.get("id"),
        )
    except Exception as e:
        audit_logger.log(
            session_id=session_id,
            event_type="payment_failed",
            payload={"error": str(e)},
        )
        raise HTTPException(status_code=502, detail=f"Payment error: {e}")
