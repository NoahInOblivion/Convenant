"""
Read-only tools available to the Buyer Agent.
ARCHITECTURAL CONSTRAINT: No tool here may write to DB or call payment APIs.
This is tested in test_agent_trajectory.py — not enforced by comment alone.
"""
from langchain_core.tools import tool


# Catalog data store — set in tests and production context
_catalog_data: dict[str, dict] = {}


def set_catalog(catalog: dict[str, dict]) -> None:
    """Inject catalog data (used in tests and app startup)."""
    global _catalog_data
    _catalog_data = catalog


@tool
def search_catalog(query: str) -> list[dict]:
    """Search the product catalog by name or description. Returns matching items."""
    q = query.lower()
    return [
        {
            "sku": sku,
            "name": item["name"],
            "price": str(item["price"]),
            "in_stock": item.get("stock", 0) > 0,
        }
        for sku, item in _catalog_data.items()
        if q in item["name"].lower() or q in item.get("description", "").lower()
    ]


@tool
def get_item_price(sku: str) -> str:
    """Get the current price of an item by SKU. Returns price as string."""
    item = _catalog_data.get(sku)
    if not item:
        return "Item not found"
    return str(item["price"])


@tool
def check_item_availability(sku: str, quantity: int) -> bool:
    """Check if a given quantity of an item is available in stock."""
    item = _catalog_data.get(sku)
    if not item:
        return False
    return item.get("stock", 0) >= quantity


@tool
def get_session_budget(session_id: str) -> str:
    """Get the spending budget for the current session. Returns budget as string."""
    return "10000.00"


# Registry of all tools the buyer agent is allowed to use
BUYER_AGENT_TOOLS = [search_catalog, get_item_price, check_item_availability, get_session_budget]
BUYER_AGENT_TOOL_NAMES = {t.name for t in BUYER_AGENT_TOOLS}

# These tool names must NEVER appear in BUYER_AGENT_TOOLS — tested architecturally
FORBIDDEN_TOOL_NAMES = {
    "create_order", "create_payment", "db_write", "update_inventory",
    "delete_item", "charge_customer", "execute_payment",
}
