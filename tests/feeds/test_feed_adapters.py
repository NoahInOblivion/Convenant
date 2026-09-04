"""
Feed adapter tests — deterministic, pure functions, no LLM, no DB.
All tests run on every commit.
"""
import pytest
from decimal import Decimal

from backend.feeds.adapters import adapt_acp, adapt_ucp, adapt_mcp, adapt_feed, FeedAdapterError
from backend.feeds.normalized import NormalizedProduct


# ── ACP ──────────────────────────────────────────────────────────────────

ACP_IN_STOCK = {
    "@context": "https://schema.org/",
    "@type": "Product",
    "sku": "KB001",
    "name": "Mechanical Keyboard",
    "offers": {"price": "4500.00", "availability": "InStock"},
}

ACP_OUT_OF_STOCK = {
    "@context": "https://schema.org/",
    "@type": "Product",
    "sku": "WEBCAM001",
    "name": "HD Webcam",
    "offers": {"price": "3200.00", "availability": "OutOfStock"},
}


def test_acp_in_stock_parsed():
    p = adapt_acp(ACP_IN_STOCK)
    assert p.sku == "KB001"
    assert p.name == "Mechanical Keyboard"
    assert p.price == Decimal("4500.00")
    assert p.in_stock is True
    assert p.source_protocol == "acp"


def test_acp_out_of_stock_parsed():
    p = adapt_acp(ACP_OUT_OF_STOCK)
    assert p.sku == "WEBCAM001"
    assert p.in_stock is False


def test_acp_missing_context_raises():
    bad = {**ACP_IN_STOCK}
    del bad["@context"]
    with pytest.raises(FeedAdapterError, match="@context"):
        adapt_acp(bad)


def test_acp_wrong_type_raises():
    bad = {**ACP_IN_STOCK, "@type": "Offer"}
    with pytest.raises(FeedAdapterError, match="Product"):
        adapt_acp(bad)


def test_acp_missing_sku_raises():
    bad = {**ACP_IN_STOCK}
    del bad["sku"]
    with pytest.raises(FeedAdapterError):
        adapt_acp(bad)


def test_acp_invalid_price_raises():
    bad = {**ACP_IN_STOCK, "offers": {"price": "not-a-number", "availability": "InStock"}}
    with pytest.raises(FeedAdapterError):
        adapt_acp(bad)


# ── UCP ──────────────────────────────────────────────────────────────────

UCP_PAYLOAD = {
    "ucp_version": "1.0",
    "sku": "MOUSE001",
    "name": "Ergonomic Mouse",
    "unit_price": "1500.00",
    "in_stock": True,
}


def test_ucp_in_stock_parsed():
    p = adapt_ucp(UCP_PAYLOAD)
    assert p.sku == "MOUSE001"
    assert p.price == Decimal("1500.00")
    assert p.in_stock is True
    assert p.source_protocol == "ucp"


def test_ucp_out_of_stock_parsed():
    bad = {**UCP_PAYLOAD, "in_stock": False}
    p = adapt_ucp(bad)
    assert p.in_stock is False


def test_ucp_missing_version_raises():
    bad = {**UCP_PAYLOAD}
    del bad["ucp_version"]
    with pytest.raises(FeedAdapterError, match="ucp_version"):
        adapt_ucp(bad)


def test_ucp_missing_sku_raises():
    bad = {**UCP_PAYLOAD}
    del bad["sku"]
    with pytest.raises(FeedAdapterError):
        adapt_ucp(bad)


def test_ucp_invalid_price_raises():
    bad = {**UCP_PAYLOAD, "unit_price": "abc"}
    with pytest.raises(FeedAdapterError):
        adapt_ucp(bad)


# ── MCP ──────────────────────────────────────────────────────────────────

MCP_PAYLOAD = {
    "type": "tool_result",
    "tool_name": "get_product_info",
    "schema_version": "mcp/1.0",
    "content": {
        "sku": "HEADSET001",
        "name": "Noise-Cancelling Headset",
        "price": "8500.00",
        "available": True,
    },
}


def test_mcp_available_parsed():
    p = adapt_mcp(MCP_PAYLOAD)
    assert p.sku == "HEADSET001"
    assert p.price == Decimal("8500.00")
    assert p.in_stock is True
    assert p.source_protocol == "mcp"


def test_mcp_unavailable_parsed():
    bad = {**MCP_PAYLOAD, "content": {**MCP_PAYLOAD["content"], "available": False}}
    p = adapt_mcp(bad)
    assert p.in_stock is False


def test_mcp_wrong_type_raises():
    bad = {**MCP_PAYLOAD, "type": "tool_call"}
    with pytest.raises(FeedAdapterError, match="tool_result"):
        adapt_mcp(bad)


def test_mcp_invalid_schema_version_raises():
    bad = {**MCP_PAYLOAD, "schema_version": "v1"}
    with pytest.raises(FeedAdapterError, match="schema_version"):
        adapt_mcp(bad)


def test_mcp_missing_content_raises():
    bad = {**MCP_PAYLOAD}
    del bad["content"]
    with pytest.raises(FeedAdapterError):
        adapt_mcp(bad)


# ── Router ───────────────────────────────────────────────────────────────

def test_adapt_feed_routes_acp():
    p = adapt_feed("acp", ACP_IN_STOCK)
    assert p.source_protocol == "acp"


def test_adapt_feed_routes_ucp():
    p = adapt_feed("ucp", UCP_PAYLOAD)
    assert p.source_protocol == "ucp"


def test_adapt_feed_routes_mcp():
    p = adapt_feed("mcp", MCP_PAYLOAD)
    assert p.source_protocol == "mcp"


def test_adapt_feed_unknown_protocol_raises():
    with pytest.raises(FeedAdapterError, match="Unknown protocol"):
        adapt_feed("grpc", {})
