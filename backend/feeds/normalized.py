from dataclasses import dataclass
from decimal import Decimal


@dataclass
class NormalizedProduct:
    sku: str
    name: str
    price: Decimal
    in_stock: bool
    source_protocol: str  # "acp", "ucp", or "mcp"
