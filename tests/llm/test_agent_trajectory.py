"""
Trajectory test — architectural assertion that BuyerAgentNode NEVER
has forbidden tools in its registry. Runs fast with no LLM call.
"""
import pytest
from unittest.mock import patch, MagicMock

from backend.agent.tools import BUYER_AGENT_TOOL_NAMES, FORBIDDEN_TOOL_NAMES
from backend.agent.node import BuyerAgentNode


def test_buyer_agent_has_no_forbidden_tools():
    """The BuyerAgentNode tool registry must contain ZERO forbidden tools."""
    with patch("backend.agent.node.ChatOpenAI") as mock_cls:
        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value = mock_llm
        mock_cls.return_value = mock_llm
        # Construction itself raises AgentToolViolation if forbidden tools present
        node = BuyerAgentNode()

    violations = BUYER_AGENT_TOOL_NAMES & FORBIDDEN_TOOL_NAMES
    assert not violations, (
        f"Forbidden tools found in BuyerAgentNode registry: {violations}. "
        "The buyer agent must never have direct DB write or payment tools."
    )


def test_forbidden_tool_names_are_defined():
    """Sanity check: the FORBIDDEN_TOOL_NAMES set is non-empty."""
    assert len(FORBIDDEN_TOOL_NAMES) >= 4


def test_allowed_tools_are_read_only():
    """All allowed tool names must be read-only operations."""
    read_only_prefixes = ("search_", "get_", "check_", "list_", "find_")
    for name in BUYER_AGENT_TOOL_NAMES:
        assert any(name.startswith(p) for p in read_only_prefixes), (
            f"Tool '{name}' does not look like a read-only tool. "
            "Buyer agent tools must be read-only (search_, get_, check_, list_, find_)."
        )


def test_construction_raises_on_forbidden_tool():
    """If a forbidden tool is somehow added to BUYER_AGENT_TOOLS, construction must raise."""
    from backend.agent.exceptions import AgentToolViolation
    from backend.agent import tools as agent_tools
    from langchain_core.tools import tool as lc_tool

    @lc_tool
    def create_payment(amount: str) -> str:
        """Forbidden tool that should never be in the agent."""
        return "paid"

    original_tools = agent_tools.BUYER_AGENT_TOOLS[:]
    original_names = agent_tools.BUYER_AGENT_TOOL_NAMES.copy()

    try:
        # Temporarily inject the forbidden tool
        agent_tools.BUYER_AGENT_TOOLS.append(create_payment)
        agent_tools.BUYER_AGENT_TOOL_NAMES.add("create_payment")

        with patch("backend.agent.node.ChatOpenAI") as mock_cls:
            mock_llm = MagicMock()
            mock_llm.bind_tools.return_value = mock_llm
            mock_cls.return_value = mock_llm
            with pytest.raises(AgentToolViolation, match="forbidden tools"):
                BuyerAgentNode()
    finally:
        # Restore original state
        agent_tools.BUYER_AGENT_TOOLS.clear()
        agent_tools.BUYER_AGENT_TOOLS.extend(original_tools)
        agent_tools.BUYER_AGENT_TOOL_NAMES.clear()
        agent_tools.BUYER_AGENT_TOOL_NAMES.update(original_names)
