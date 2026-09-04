"""Agent unit tests — mocked LLM output. No real API calls."""
import pytest
from decimal import Decimal
from unittest.mock import MagicMock, patch

from backend.agent.node import BuyerAgentNode
from backend.agent.exceptions import AgentOutputError


VALID_PROPOSAL_JSON = '''{
  "proposal_id": "prop-001",
  "session_id": "ses-001",
  "items": [
    {"sku": "SKU001", "name": "Laptop", "quantity": 1, "agent_proposed_price": "45000.00"}
  ],
  "total_proposed": "45000.00",
  "reasoning": "User wants a laptop for work.",
  "created_at": "2026-09-04T05:00:00Z"
}'''


def make_mock_response(content: str):
    mock = MagicMock()
    mock.content = content
    return mock


@pytest.fixture
def agent():
    with patch("backend.agent.node.ChatOpenAI") as mock_llm_cls:
        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value = mock_llm
        mock_llm_cls.return_value = mock_llm
        node = BuyerAgentNode()
        node._llm_with_tools = mock_llm
        yield node, mock_llm


def test_valid_proposal_parsed(agent):
    node, mock_llm = agent
    mock_llm.invoke.return_value = make_mock_response(VALID_PROPOSAL_JSON)
    proposal = node.run("Buy me a laptop", "ses-001")
    assert proposal.items[0].sku == "SKU001"
    assert proposal.total_proposed == Decimal("45000.00")


def test_malformed_json_raises_agent_output_error(agent):
    node, mock_llm = agent
    mock_llm.invoke.return_value = make_mock_response("this is not json {{{")
    with pytest.raises(AgentOutputError, match="invalid JSON"):
        node.run("Buy me something", "ses-001")


def test_missing_items_field_raises(agent):
    node, mock_llm = agent
    mock_llm.invoke.return_value = make_mock_response(
        '{"total_proposed": "5000", "reasoning": "r"}'
    )
    with pytest.raises(AgentOutputError, match="missing fields"):
        node.run("Buy something", "ses-001")


def test_empty_items_list_raises(agent):
    node, mock_llm = agent
    mock_llm.invoke.return_value = make_mock_response(
        '{"items": [], "total_proposed": "0", "reasoning": "nothing"}'
    )
    with pytest.raises(AgentOutputError, match="empty items"):
        node.run("Buy nothing", "ses-001")


def test_markdown_fenced_json_parsed(agent):
    node, mock_llm = agent
    fenced = f"```json\n{VALID_PROPOSAL_JSON}\n```"
    mock_llm.invoke.return_value = make_mock_response(fenced)
    proposal = node.run("Buy me a laptop", "ses-001")
    assert proposal.items[0].sku == "SKU001"


def test_missing_reasoning_raises(agent):
    node, mock_llm = agent
    mock_llm.invoke.return_value = make_mock_response(
        '{"items": [{"sku":"S","name":"X","quantity":1,"agent_proposed_price":"100"}], "total_proposed": "100"}'
    )
    with pytest.raises(AgentOutputError, match="missing fields"):
        node.run("Buy something", "ses-001")


def test_missing_total_proposed_raises(agent):
    node, mock_llm = agent
    mock_llm.invoke.return_value = make_mock_response(
        '{"items": [{"sku":"S","name":"X","quantity":1,"agent_proposed_price":"100"}], "reasoning": "ok"}'
    )
    with pytest.raises(AgentOutputError, match="missing fields"):
        node.run("Buy something", "ses-001")


def test_invalid_item_structure_raises(agent):
    """Item missing required field 'sku' -> AgentOutputError."""
    node, mock_llm = agent
    mock_llm.invoke.return_value = make_mock_response(
        '{"items": [{"name":"X","quantity":1,"agent_proposed_price":"100"}], '
        '"total_proposed": "100", "reasoning": "ok"}'
    )
    with pytest.raises(AgentOutputError, match="construction failed"):
        node.run("Buy something", "ses-001")
