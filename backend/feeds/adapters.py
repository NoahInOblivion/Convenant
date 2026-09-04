"""
Multi-protocol feed adapters.
Pure functions — no LLM, no DB, no side effects.

Protocols supported:
  - ACP (Agent Commerce Protocol): JSON-LD with @context schema.org
  - UCP (Universal Commerce Protocol): flat dict with ucp_version
  - MCP (Model Context Protocol): tool_result with schema_version mcp/1.0
"""
from decimal import Decimal, InvalidOperation
from backend.feeds.normalized import NormalizedProduct


class FeedAdapterError(Exception):
    """Raised when a feed payload cannot be parsed."""


def adapt_acp(payload: dict) -> NormalizedProduct:
    """
    Parse ACP (Agent Commerce Protocol) JSON-LD payload.
    Expected shape:
      {
        "@context": "https://schema.org/",
        "@type": "Product",
        "sku": "...",
        "name": "...",
        "offers": {"price": "...", "availability": "InStock|OutOfStock"}
      }
    """
    try:
        ctx = payload.get("@context", "")
        if "schema.org" not in ctx:
            raise FeedAdapterError(f"ACP: invalid @context: {ctx!r}")
        if payload.get("@type") != "Product":
            raise FeedAdapterError(f"ACP: expected @type=Product, got {payload.get('@type')!r}")

        sku = payload["sku"]
        name = payload["name"]
        offers = payload["offers"]
        price = Decimal(str(offers["price"]))
        availability = offers.get("availability", "")
        in_stock = availability == "InStock"

        return NormalizedProduct(
            sku=sku, name=name, price=price,
            in_stock=in_stock, source_protocol="acp",
        )
    except FeedAdapterError:
        raise
    except (KeyError, InvalidOperation, TypeError) as e:
        raise FeedAdapterError(f"ACP parse error: {e}") from e


def adapt_ucp(payload: dict) -> NormalizedProduct:
    """
    Parse UCP (Universal Commerce Protocol) flat dict.
    Expected shape:
      {"ucp_version": "1.0", "sku": "...", "name": "...", "unit_price": "...", "in_stock": bool}
    """
    try:
        version = payload.get("ucp_version", "")
        if not version:
            raise FeedAdapterError("UCP: missing ucp_version")

        sku = payload["sku"]
        name = payload["name"]
        price = Decimal(str(payload["unit_price"]))
        in_stock = bool(payload["in_stock"])

        return NormalizedProduct(
            sku=sku, name=name, price=price,
            in_stock=in_stock, source_protocol="ucp",
        )
    except FeedAdapterError:
        raise
    except (KeyError, InvalidOperation, TypeError) as e:
        raise FeedAdapterError(f"UCP parse error: {e}") from e


def adapt_mcp(payload: dict) -> NormalizedProduct:
    """
    Parse MCP (Model Context Protocol) tool result.
    Expected shape:
      {
        "type": "tool_result",
        "tool_name": "get_product_info",
        "schema_version": "mcp/1.0",
        "content": {"sku": "...", "name": "...", "price": "...", "available": bool}
      }
    """
    try:
        if payload.get("type") != "tool_result":
            raise FeedAdapterError(f"MCP: expected type=tool_result, got {payload.get('type')!r}")
        schema_version = payload.get("schema_version", "")
        if not schema_version.startswith("mcp/"):
            raise FeedAdapterError(f"MCP: invalid schema_version: {schema_version!r}")

        content = payload["content"]
        sku = content["sku"]
        name = content["name"]
        price = Decimal(str(content["price"]))
        in_stock = bool(content["available"])

        return NormalizedProduct(
            sku=sku, name=name, price=price,
            in_stock=in_stock, source_protocol="mcp",
        )
    except FeedAdapterError:
        raise
    except (KeyError, InvalidOperation, TypeError) as e:
        raise FeedAdapterError(f"MCP parse error: {e}") from e


PROTOCOL_ADAPTERS = {
    "acp": adapt_acp,
    "ucp": adapt_ucp,
    "mcp": adapt_mcp,
}


def adapt_feed(protocol: str, payload: dict) -> NormalizedProduct:
    """Route to the correct adapter by protocol name."""
    adapter = PROTOCOL_ADAPTERS.get(protocol.lower())
    if not adapter:
        raise FeedAdapterError(f"Unknown protocol: {protocol!r}. Supported: {list(PROTOCOL_ADAPTERS)}")
    return adapter(payload)
