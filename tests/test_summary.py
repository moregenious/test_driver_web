"""Unit tests for daily summary calculations."""

from datetime import datetime
from app.models import Trip
from app.summary import calculate_day_summary, filter_trips_by_date


def test_calculate_day_summary_sample_data():
    """Test calculation on user prompt example trips."""
    trips = [
        Trip(
            id="t1",
            start=datetime.fromisoformat("2026-10-01T08:10:00+05:00"),
            end=datetime.fromisoformat("2026-10-01T08:32:00+05:00"),
            amount=2400.0,
            payment="card",
            commission=360.0
        ),
        Trip(
            id="t2",
            start=datetime.fromisoformat("2026-10-01T09:05:00+05:00"),
            end=datetime.fromisoformat("2026-10-01T09:20:00+05:00"),
            amount=1500.0,
            payment="cash",
            commission=225.0
        ),
    ]

    summary = calculate_day_summary(trips, "2026-10-01")

    assert summary.date == "2026-10-01"
    assert summary.total_trips == 2
    assert summary.total_amount == 3900.0
    assert summary.total_commission == 585.0
    # "На руки" = 3900 - 585 = 3315
    assert summary.net_income == 3315.0

    # Payment breakdown
    assert summary.card_amount == 2400.0
    assert summary.card_trips == 1
    assert summary.cash_amount == 1500.0
    assert summary.cash_trips == 1
    assert summary.card_amount + summary.cash_amount == summary.total_amount


def test_calculate_day_summary_empty():
    """Test calculation when there are no trips for the day."""
    summary = calculate_day_summary([], "2026-10-05")

    assert summary.date == "2026-10-05"
    assert summary.total_trips == 0
    assert summary.total_amount == 0.0
    assert summary.total_commission == 0.0
    assert summary.net_income == 0.0
    assert summary.cash_amount == 0.0
    assert summary.card_amount == 0.0
    assert summary.cash_trips == 0
    assert summary.card_trips == 0


def test_calculate_day_summary_decimal_precision():
    """Verify precision with fractional kopecks/cents without float drift."""
    trips = [
        Trip(
            id="frac1",
            start=datetime.fromisoformat("2026-10-01T10:00:00+05:00"),
            end=datetime.fromisoformat("2026-10-01T10:15:00+05:00"),
            amount=100.10,
            payment="card",
            commission=15.01
        ),
        Trip(
            id="frac2",
            start=datetime.fromisoformat("2026-10-01T10:30:00+05:00"),
            end=datetime.fromisoformat("2026-10-01T10:45:00+05:00"),
            amount=200.20,
            payment="cash",
            commission=30.03
        ),
    ]

    summary = calculate_day_summary(trips, "2026-10-01")

    assert summary.total_amount == 300.30
    assert summary.total_commission == 45.04
    assert summary.net_income == 255.26
    assert summary.card_amount == 100.10
    assert summary.cash_amount == 200.20


def test_filter_trips_by_date():
    """Verify filtering only selects trips on that specific calendar day."""
    trips = [
        Trip(
            id="day1",
            start=datetime.fromisoformat("2026-10-01T08:00:00+05:00"),
            end=datetime.fromisoformat("2026-10-01T08:30:00+05:00"),
            amount=1000.0,
            payment="card",
            commission=100.0
        ),
        Trip(
            id="day2",
            start=datetime.fromisoformat("2026-10-02T08:00:00+05:00"),
            end=datetime.fromisoformat("2026-10-02T08:30:00+05:00"),
            amount=1200.0,
            payment="cash",
            commission=120.0
        ),
    ]

    filtered_day1 = filter_trips_by_date(trips, "2026-10-01")
    assert len(filtered_day1) == 1
    assert filtered_day1[0].id == "day1"

    filtered_day2 = filter_trips_by_date(trips, "2026-10-02")
    assert len(filtered_day2) == 1
    assert filtered_day2[0].id == "day2"

    filtered_day3 = filter_trips_by_date(trips, "2026-10-03")
    assert len(filtered_day3) == 0
