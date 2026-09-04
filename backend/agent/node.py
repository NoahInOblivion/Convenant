"""
BuyerAgentNode — LangGraph node.
INVARIANT: This node only produces CartProposal. No DB writes. No payment calls.
"""
import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI

from backend.schemas.proposals import CartItem, CartProposal
from backend.agent.tools import BUYER_AGENT_TOOLS, BUYER_AGENT_TOOL_NAMES, FORBIDDEN_TOOL_NAMES
from backend.agent.exceptions import AgentOutputError, AgentToolViolation

SYSTEM_PROMPT = """You are a shopping assistant. Your job is to propose a cart of items
based on the user's request.

RULES:
- Use the tools provided to search the catalog and check prices/availability.
- NEVER attempt to make payments, write to databases, or execute orders.
- After gathering information, respond with a valid JSON CartProposal containing:
  proposal_id, session_id, items (list of CartItem), total_proposed, reasoning, created_at.
- Each CartItem must have: sku, name, quantity, agent_proposed_price.
- If an item is not in the catalog, say so in reasoning and exclude it.
- total_proposed is the sum of (agent_proposed_price × quantity) for all items.
- created_at must be an ISO 8601 UTC datetime string.

Your FINAL response MUST be a JSON object only — no markdown fences, no extra text.
"""


class BuyerAgentNode:
    def __init__(self, model_name: str = "gpt-4o-mini", temperature: float = 0.3):
        # Architectural assertion at construction time — not just a comment
        violations = BUYER_AGENT_TOOL_NAMES & FORBIDDEN_TOOL_NAMES
        if violations:
            raise AgentToolViolation(
                f"BuyerAgentNode tool registry contains forbidden tools: {violations}"
            )

        self._llm = ChatOpenAI(model=model_name, temperature=temperature)
        self._llm_with_tools = self._llm.bind_tools(BUYER_AGENT_TOOLS)
        # Tool lookup map for the execution loop
        self._tool_map = {t.name: t for t in BUYER_AGENT_TOOLS}

    def _parse_proposal(self, raw: str, session_id: str) -> CartProposal:
        """Parse LLM output into CartProposal. Raises AgentOutputError on failure."""
        try:
            raw = raw.strip()
            # Strip markdown fences if present
            if raw.startswith("```"):
                lines = raw.split("\n")
                inner_lines = lines[1:]
                if inner_lines and inner_lines[-1].strip() == "```":
                    inner_lines = inner_lines[:-1]
                raw = "\n".join(inner_lines)
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise AgentOutputError(f"Agent produced invalid JSON: {e}\nRaw: {raw[:500]}")

        # Ensure required fields
        required = {"items", "total_proposed", "reasoning"}
        missing = required - set(data.keys())
        if missing:
            raise AgentOutputError(f"Agent CartProposal missing fields: {missing}")

        if not data.get("items"):
            raise AgentOutputError("Agent CartProposal has empty items list")

        # Build CartProposal (Pydantic validates further)
        try:
            return CartProposal(
                proposal_id=data.get("proposal_id", str(uuid.uuid4())),
                session_id=data.get("session_id", session_id),
                items=[CartItem(**item) for item in data["items"]],
                total_proposed=Decimal(str(data["total_proposed"])),
                reasoning=data["reasoning"],
                created_at=datetime.now(timezone.utc),
            )
        except Exception as e:
            raise AgentOutputError(f"CartProposal construction failed: {e}")

    def run(self, user_request: str, session_id: str) -> CartProposal:
        """
        Run the buyer agent with a proper tool-calling loop.

        When the LLM makes tool calls (response.tool_calls non-empty),
        response.content is '' — we must execute each tool and feed results
        back before the LLM can produce its final JSON answer.
        """
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_request),
        ]

        max_iterations = 8  # safety ceiling on tool-call rounds
        for iteration in range(max_iterations):
            response = self._llm_with_tools.invoke(messages)
            messages.append(response)

            # No tool calls → this is the final text answer
            if not getattr(response, "tool_calls", None):
                if not response.content:
                    raise AgentOutputError(
                        "Agent returned empty content with no tool calls — "
                        "likely a model refusal or max-token issue."
                    )
                return self._parse_proposal(response.content, session_id)

            # Process each tool call and collect results
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_id = tool_call["id"]

                tool_fn = self._tool_map.get(tool_name)
                if tool_fn is None:
                    result = f"Unknown tool: {tool_name}"
                else:
                    try:
                        result = tool_fn.invoke(tool_args)
                    except Exception as exc:
                        result = f"Tool error: {exc}"

                messages.append(
                    ToolMessage(content=str(result), tool_call_id=tool_id)
                )

        raise AgentOutputError(
            f"Agent did not produce a final JSON response within {max_iterations} iterations."
        )
