from fastapi import APIRouter
from pydantic import BaseModel
from backend.db.seed_catalog import SEED_CATALOG

router = APIRouter()


class CatalogItemResponse(BaseModel):
    sku: str
    name: str
    price: str
    in_stock: bool
    stock: int


@router.get("/catalog", response_model=list[CatalogItemResponse])
async def get_catalog():
    return [
        CatalogItemResponse(
            sku=sku,
            name=item["name"],
            price=str(item["price"]),
            in_stock=item["stock"] > 0,
            stock=item["stock"],
        )
        for sku, item in SEED_CATALOG.items()
    ]
