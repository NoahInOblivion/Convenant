"""
Replan loop — graceful denial when the policy gate rejects.
Max 2 replan attempts before terminal denial.
"""
from dataclasses import dataclass
from decimal import Decimal

from backend.schemas.proposals import CartProposal
from backend.schemas.policy import PolicyDecision
from backend.agent.node import BuyerAgentNode
from backend.policy.gate import evaluate_proposal
from backend.policy.catalog_repository import CatalogRepository
from backend.audit.log import AuditLogger


@dataclass
class GracefulDenialMessage:
    session_id: str
    reason: str
    original_request: str
    attempts: int


class ReplanLoop:
    def __init__(
        self,
        buyer_agent: BuyerAgentNode,
        catalog: CatalogRepository,
        spend_cap: Decimal,
        audit_logger: AuditLogger,
        max_attempts: int = 2,
    ):
        self._agent = buyer_agent
        self._catalog = catalog
        self._spend_cap = spend_cap
        self._audit = audit_logger
        self._max_attempts = max_attempts
        self._seen_keys: set[str] = set()

    def _build_replan_prompt(self, original_request: str, decision: PolicyDecision) -> str:
        parts = [f"Original request: {original_request}"]
        parts.append(f"Previous proposal was rejected: {decision.reason}")
        if decision.out_of_stock_skus:
            parts.append(f"Out of stock: {', '.join(decision.out_of_stock_skus)}. Please exclude these.")
        if decision.price_mismatches:
            parts.append("Note: prices were corrected to database values.")
        if decision.decision == "requires_human_approval":
            parts.append(
                f"The total exceeded the auto-approval limit of ₹{self._spend_cap}. "
                f"Please propose a cart that stays within ₹{self._spend_cap}."
            )
        parts.append("Please propose a revised cart that satisfies all constraints.")
        return "\n".join(parts)

    def attempt(
        self,
        original_request: str,
        session_id: str,
        initial_decision: PolicyDecision,
    ) -> tuple[CartProposal, PolicyDecision] | GracefulDenialMessage:
        """
        Try up to max_attempts times to get an approved proposal.
        Returns (CartProposal, PolicyDecision) on approval, or GracefulDenialMessage on failure.
        """
        decision = initial_decision

        for attempt_num in range(1, self._max_attempts + 1):
            replan_prompt = self._build_replan_prompt(original_request, decision)

            self._audit.log(
                session_id=session_id,
                event_type="replan_triggered",
                payload={
                    "attempt": attempt_num,
                    "max_attempts": self._max_attempts,
                    "previous_decision": decision.model_dump(mode="json"),
                    "replan_prompt": replan_prompt,
                },
            )

            try:
                new_proposal = self._agent.run(replan_prompt, session_id)
            except Exception as e:
                self._audit.log(
                    session_id=session_id,
                    event_type="replan_failed",
                    payload={"attempt": attempt_num, "error": str(e)},
                )
                continue

            new_decision = evaluate_proposal(
                new_proposal, self._catalog, self._spend_cap, self._seen_keys
            )

            self._audit.log(
                session_id=session_id,
                event_type="policy_decision",
                payload={"attempt": attempt_num, "decision": new_decision.model_dump(mode="json")},
            )

            if new_decision.decision == "approved":
                if new_decision.idempotency_key:
                    self._seen_keys.add(new_decision.idempotency_key)
                self._audit.log(
                    session_id=session_id,
                    event_type="replan_success",
                    payload={"attempt": attempt_num, "proposal_id": new_proposal.proposal_id},
                )
                return new_proposal, new_decision

            decision = new_decision

        # All attempts exhausted
        self._audit.log(
            session_id=session_id,
            event_type="terminal_denial",
            payload={
                "attempts": self._max_attempts,
                "final_reason": decision.reason,
                "original_request": original_request,
            },
        )
        return GracefulDenialMessage(
            session_id=session_id,
            reason=decision.reason,
            original_request=original_request,
            attempts=self._max_attempts,
        )
