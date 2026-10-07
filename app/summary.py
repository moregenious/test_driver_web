"""Pure functions for shift summary calculation and trip date grouping."""

from typing import List
from decimal import Decimal, ROUND_HALF_UP
from .models import Trip, DaySummary


def get_trip_date(trip: Trip) -> str:
    """Extract local date (YYYY-MM-DD) from trip start datetime."""
    return trip.start.strftime("%Y-%m-%d")


def filter_trips_by_date(trips: List[Trip], target_date: str) -> List[Trip]:
    """Filter trips that started on the target date."""
    return [trip for trip in trips if get_trip_date(trip) == target_date]


def calculate_day_summary(trips: List[Trip], date_str: str) -> DaySummary:
    """
    Calculate summary statistics for a given day and list of trips.
    Uses precise decimal arithmetic to avoid floating-point inaccuracies.
    """
    if not trips:
        return DaySummary(
            date=date_str,
            total_trips=0,
            total_amount=0.0,
            total_commission=0.0,
            net_income=0.0,
            cash_amount=0.0,
            card_amount=0.0,
            cash_trips=0,
            card_trips=0
        )

    # Calculate using Decimal for financial precision
    total_amount_dec = Decimal("0.00")
    total_commission_dec = Decimal("0.00")
    cash_amount_dec = Decimal("0.00")
    card_amount_dec = Decimal("0.00")

    cash_trips = 0
    card_trips = 0

    for trip in trips:
        amt = Decimal(str(round(trip.amount, 2)))
        comm = Decimal(str(round(trip.commission, 2)))

        total_amount_dec += amt
        total_commission_dec += comm

        if trip.payment == "cash":
            cash_amount_dec += amt
            cash_trips += 1
        elif trip.payment == "card":
            card_amount_dec += amt
            card_trips += 1

    net_income_dec = total_amount_dec - total_commission_dec

    return DaySummary(
        date=date_str,
        total_trips=len(trips),
        total_amount=float(total_amount_dec.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        total_commission=float(total_commission_dec.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        net_income=float(net_income_dec.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        cash_amount=float(cash_amount_dec.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        card_amount=float(card_amount_dec.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        cash_trips=cash_trips,
        card_trips=card_trips
    )


def format_currency_amount(val: float) -> str:
    """Format number with thousands space, e.g. 2400 -> '2 400', 585.5 -> '585.50'."""
    if val % 1 == 0:
        return f"{int(val):,}".replace(",", " ")
    return f"{val:,.2f}".replace(",", " ")


def format_receipt_text(summary: DaySummary, trips: List[Trip], currency: str = "₸") -> str:
    """
    Format day summary and trips into an authentic thermal receipt string,
    matching the test task reference layout.
    """
    # Convert YYYY-MM-DD to DD.MM.YYYY
    try:
        parts = summary.date.split("-")
        formatted_date = f"{parts[2]}.{parts[1]}.{parts[0]}"
    except Exception:
        formatted_date = summary.date

    lines = [
        "       Дневник смен       ",
        f"        {formatted_date}        ",
        ""
    ]

    for t in trips:
        start_str = t.start.strftime("%H:%M")
        end_str = t.end.strftime("%H:%M")
        pay_str = "карта" if t.payment == "card" else "нал."
        time_part = f"{start_str}–{end_str} {pay_str}"
        amt_str = f"{format_currency_amount(t.amount)} {currency}"
        # Align left and right inside ~34 chars
        dots_or_spaces = 34 - len(time_part) - len(amt_str)
        spaces = " " * max(1, dots_or_spaces)
        lines.append(f"{time_part}{spaces}{amt_str}")

    divider = "-" * 34
    lines.append(divider)

    # Summary rows
    trips_val = str(summary.total_trips)
    lines.append(f"Поездок{' ' * (34 - len('Поездок') - len(trips_val))}{trips_val}")

    gross_val = f"{format_currency_amount(summary.total_amount)} {currency}"
    lines.append(f"Выручка{' ' * (34 - len('Выручка') - len(gross_val))}{gross_val}")

    comm_val = f"-{format_currency_amount(summary.total_commission)} {currency}"
    lines.append(f"Комиссия{' ' * (34 - len('Комиссия') - len(comm_val))}{comm_val}")

    cash_card_val = f"{format_currency_amount(summary.cash_amount)} / {format_currency_amount(summary.card_amount)}"
    lines.append(f"Наличные / карта{' ' * (34 - len('Наличные / карта') - len(cash_card_val))}{cash_card_val}")

    lines.append(divider)

    net_val = f"{format_currency_amount(summary.net_income)} {currency}"
    lines.append(f"На руки{' ' * (34 - len('На руки') - len(net_val))}{net_val}")

    return "\n".join(lines)

