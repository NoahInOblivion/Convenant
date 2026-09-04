"""
Counter-offer calculator — pure function, no side effects.
"""
from decimal import Decimal, ROUND_HALF_UP


def calculate_counter_offer(
    db_price: Decimal,
    margin_room: Decimal,
    max_discount_pct: Decimal,
) -> Decimal | None:
    """
    Calculate a counter-offer price.

    Args:
        db_price: The current database price of the item.
        margin_room: Available margin as a percentage (e.g., 5.0 = 5%).
        max_discount_pct: Maximum allowed discount percentage (e.g., 10.0 = 10%).

    Returns:
        Counter-offer price (Decimal, 2dp) if discount >= 1%, else None.
    """
    discount_pct = min(margin_room, max_discount_pct)

    if discount_pct < Decimal("1.0"):
        return None

    counter_price = db_price * (1 - discount_pct / Decimal("100"))
    return counter_price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
