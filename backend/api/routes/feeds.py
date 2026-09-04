from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.feeds.adapters import adapt_feed, FeedAdapterError
from backend.feeds.counter_offer import calculate_counter_offer
from decimal import Decimal

router = APIRouter()


class FeedIngestRequest(BaseModel):
    protocol: str  # "acp", "ucp", or "mcp"
    payload: dict


class NormalizedProductResponse(BaseModel):
    sku: str
    name: str
    price: str
    in_stock: bool
    source_protocol: str
    counter_offer_price: str | None = None


@router.post("/feeds/ingest", response_model=NormalizedProductResponse)
async def ingest_feed(body: FeedIngestRequest):
    try:
        product = adapt_feed(body.protocol, body.payload)
    except FeedAdapterError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # Calculate counter-offer with 5% margin room, 10% max
    counter = calculate_counter_offer(
        db_price=product.price,
        margin_room=Decimal("5.0"),
        max_discount_pct=Decimal("10.0"),
    )

    return NormalizedProductResponse(
        sku=product.sku,
        name=product.name,
        price=str(product.price),
        in_stock=product.in_stock,
        source_protocol=product.source_protocol,
        counter_offer_price=str(counter) if counter else None,
    )
