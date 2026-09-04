"""LangGraph graph wiring for the agentic commerce flow."""
from typing import TypedDict

from langgraph.graph import StateGraph, END

from backend.schemas.proposals import CartProposal
from backend.schemas.policy import PolicyDecision
from backend.agent.node import BuyerAgentNode


class AgentState(TypedDict):
    session_id: str
    user_request: str
    cart_proposal: CartProposal | None
    policy_decision: PolicyDecision | None
    error: str | None


def build_graph(buyer_node: BuyerAgentNode) -> StateGraph:
    graph = StateGraph(AgentState)

    def buyer_step(state: AgentState) -> AgentState:
        try:
            proposal = buyer_node.run(state["user_request"], state["session_id"])
            return {**state, "cart_proposal": proposal, "error": None}
        except Exception as e:
            return {**state, "cart_proposal": None, "error": str(e)}

    graph.add_node("buyer", buyer_step)
    graph.set_entry_point("buyer")
    graph.add_edge("buyer", END)
    return graph.compile()
