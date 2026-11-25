"""
Counter-offer calculator tests — deterministic, pure function.
"""
from decimal import Decimal

from backend.feeds.counter_offer import calculate_counter_offer


def test_standard_discount_applies():
    """5% margin, 10% max -> 5% discount applied."""
    result = calculate_counter_offer(
        db_price=Decimal("10000.00"),
        margin_room=Decimal("5.0"),
        max_discount_pct=Decimal("10.0"),
    )
    assert result == Decimal("9500.00")


def test_max_discount_caps_at_max():
    """Margin 15%, max 10% -> discount capped at 10%."""
    result = calculate_counter_offer(
        db_price=Decimal("10000.00"),
        margin_room=Decimal("15.0"),
        max_discount_pct=Decimal("10.0"),
    )
    assert result == Decimal("9000.00")


def test_discount_below_one_percent_returns_none():
    """discount_pct = 0.5% < 1% -> return None."""
    result = calculate_counter_offer(
        db_price=Decimal("10000.00"),
        margin_room=Decimal("0.5"),
        max_discount_pct=Decimal("10.0"),
    )
    assert result is None


def test_exactly_one_percent_applies():
    """discount_pct = exactly 1% -> counter-offer generated."""
    result = calculate_counter_offer(
        db_price=Decimal("10000.00"),
        margin_room=Decimal("1.0"),
        max_discount_pct=Decimal("10.0"),
    )
    assert result == Decimal("9900.00")


def test_zero_margin_returns_none():
    result = calculate_counter_offer(
        db_price=Decimal("5000.00"),
        margin_room=Decimal("0.0"),
        max_discount_pct=Decimal("10.0"),
    )
    assert result is None


def test_result_rounded_to_2dp():
    """Price * discount may produce many decimal places — must round to 2dp."""
    result = calculate_counter_offer(
        db_price=Decimal("9999.00"),
        margin_room=Decimal("3.0"),
        max_discount_pct=Decimal("10.0"),
    )
    # 9999.00 * 0.97 = 9699.03
    assert result == Decimal("9699.03")
    assert result == result.quantize(Decimal("0.01"))


def test_counter_price_less_than_db_price():
    """Counter-offer must always be strictly less than db_price when discount >= 1%."""
    db_price = Decimal("45000.00")
    result = calculate_counter_offer(db_price, Decimal("5.0"), Decimal("10.0"))
    assert result < db_price
