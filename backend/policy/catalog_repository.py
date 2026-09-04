from decimal import Decimal
from abc import ABC, abstractmethod


class CatalogRepository(ABC):
    @abstractmethod
    def get_price(self, sku: str) -> Decimal | None: ...
    
    @abstractmethod
    def check_stock(self, sku: str, quantity: int) -> bool: ...
