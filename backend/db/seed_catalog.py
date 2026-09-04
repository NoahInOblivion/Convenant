from decimal import Decimal

SEED_CATALOG: dict[str, dict] = {
    "LAPTOP001": {"name": "ProBook Laptop 14", "description": "14-inch laptop", "price": Decimal("75000.00"), "stock": 10},
    "LAPTOP002": {"name": "UltraSlim Laptop 15", "description": "Ultra-thin 15-inch laptop", "price": Decimal("95000.00"), "stock": 5},
    "KB001": {"name": "Mechanical Keyboard", "description": "Cherry MX Brown keyboard", "price": Decimal("4500.00"), "stock": 50},
    "MOUSE001": {"name": "Ergonomic Mouse", "description": "Wireless ergonomic mouse", "price": Decimal("1500.00"), "stock": 100},
    "MONITOR001": {"name": "27-inch Monitor", "description": "4K IPS display", "price": Decimal("32000.00"), "stock": 20},
    "HEADSET001": {"name": "Noise-Cancelling Headset", "description": "Over-ear NC headset", "price": Decimal("8500.00"), "stock": 30},
    "WEBCAM001": {"name": "HD Webcam", "description": "1080p HD webcam", "price": Decimal("3200.00"), "stock": 0},
    "CHAIR001": {"name": "Ergonomic Office Chair", "description": "Lumbar support chair", "price": Decimal("22000.00"), "stock": 15},
}


class InMemoryCatalogRepository:
    def __init__(self, catalog: dict | None = None):
        self._catalog = catalog if catalog is not None else SEED_CATALOG

    def get_price(self, sku: str):
        item = self._catalog.get(sku)
        return item["price"] if item else None

    def check_stock(self, sku: str, quantity: int) -> bool:
        item = self._catalog.get(sku)
        if not item:
            return False
        return item.get("stock", 0) >= quantity
