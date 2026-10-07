"""Integration tests for FastAPI endpoints, validation, and idempotency."""

import pytest
from fastapi.testclient import TestClient
from app.main import app, storage


@pytest.fixture(autouse=True)
def reset_storage_before_each():
    """Reset storage to original sample data before each test."""
    storage.reset_to_sample()
    yield


client = TestClient(app)


def test_get_trips_for_day():
    """Test retrieving trips for a specific date (2026-10-01)."""
    response = client.get("/api/trips?date=2026-10-01")
    assert response.status_code == 200
    data = response.json()

    assert data["date"] == "2026-10-01"
    assert "summary" in data
    assert "trips" in data
    assert len(data["trips"]) == 2

    summary = data["summary"]
    assert summary["total_trips"] == 2
    assert summary["total_amount"] == 3900.0
    assert summary["total_commission"] == 585.0
    assert summary["net_income"] == 3315.0
    assert summary["card_trips"] == 1
    assert summary["cash_trips"] == 1


def test_get_trips_default_date():
    """Test retrieving trips when date query parameter is omitted."""
    response = client.get("/api/trips")
    assert response.status_code == 200
    data = response.json()
    assert "date" in data
    assert "summary" in data
    assert "trips" in data


def test_get_day_summary_endpoint():
    """Test dedicated summary endpoint."""
    response = client.get("/api/summary?date=2026-10-01")
    assert response.status_code == 200
    summary = response.json()
    assert summary["total_trips"] == 2
    assert summary["net_income"] == 3315.0


def test_get_day_receipt_text_endpoint():
    """Test receipt formatted text endpoint matches the task mockup."""
    response = client.get("/api/receipt?date=2026-10-01&currency=₸")
    assert response.status_code == 200
    text = response.text
    assert "Дневник смен" in text
    assert "01.10.2026" in text
    assert "08:10–08:32 карта" in text
    assert "2 400 ₸" in text
    assert "09:05–09:20 нал." in text
    assert "1 500 ₸" in text
    assert "Поездок" in text
    assert "Выручка" in text
    assert "3 900 ₸" in text
    assert "Комиссия" in text
    assert "-585 ₸" in text
    assert "Наличные / карта" in text
    assert "1 500 / 2 400" in text
    assert "На руки" in text
    assert "3 315 ₸" in text


def test_add_trip_success():
    """Test adding a valid new trip."""
    payload = {
        "id": "new_trip_100",
        "start": "2026-10-05T12:00:00+05:00",
        "end": "2026-10-05T12:30:00+05:00",
        "amount": 2000.0,
        "payment": "card",
        "commission": 300.0
    }
    response = client.post("/api/trips", json=payload)
    assert response.status_code == 201
    result = response.json()
    assert result["status"] == "created"
    assert result["is_duplicate"] is False
    assert result["trip"]["id"] == "new_trip_100"


def test_add_trip_duplicate_idempotent():
    """Test duplicate submission returns 200 OK without creating duplicate in storage."""
    payload = {
        "id": "t1",  # Already in sample data!
        "start": "2026-10-01T08:10:00+05:00",
        "end": "2026-10-01T08:32:00+05:00",
        "amount": 2400.0,
        "payment": "card",
        "commission": 360.0
    }
    # Initial count for this date
    initial_count = len(client.get("/api/trips?date=2026-10-01").json()["trips"])

    response = client.post("/api/trips", json=payload)
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "duplicate"
    assert result["is_duplicate"] is True
    assert result["trip"]["id"] == "t1"

    # Count must remain unchanged!
    new_count = len(client.get("/api/trips?date=2026-10-01").json()["trips"])
    assert new_count == initial_count


def test_add_trip_duplicate_strict_conflict():
    """Test duplicate submission with strict_conflict=true returns 409."""
    payload = {
        "id": "t1",
        "start": "2026-10-01T08:10:00+05:00",
        "end": "2026-10-01T08:32:00+05:00",
        "amount": 2400.0,
        "payment": "card",
        "commission": 360.0
    }
    response = client.post("/api/trips?strict_conflict=true", json=payload)
    assert response.status_code == 409
    assert "уже существует" in response.json()["detail"]


def test_validation_amount_must_be_positive():
    """Test amount <= 0 is rejected."""
    # Amount = 0
    payload = {
        "start": "2026-10-05T12:00:00+05:00",
        "end": "2026-10-05T12:30:00+05:00",
        "amount": 0.0,
        "payment": "card",
        "commission": 0.0
    }
    response = client.post("/api/trips", json=payload)
    assert response.status_code == 422

    # Amount < 0
    payload["amount"] = -500.0
    response = client.post("/api/trips", json=payload)
    assert response.status_code == 422


def test_validation_end_must_be_after_start():
    """Test end <= start is rejected."""
    # End before start
    payload = {
        "start": "2026-10-05T12:30:00+05:00",
        "end": "2026-10-05T12:00:00+05:00",
        "amount": 1000.0,
        "payment": "cash",
        "commission": 150.0
    }
    response = client.post("/api/trips", json=payload)
    assert response.status_code == 422

    # End equals start
    payload["end"] = payload["start"]
    response = client.post("/api/trips", json=payload)
    assert response.status_code == 422


def test_validation_commission_cannot_exceed_amount():
    """Test commission > amount is rejected."""
    payload = {
        "start": "2026-10-05T12:00:00+05:00",
        "end": "2026-10-05T12:30:00+05:00",
        "amount": 500.0,
        "payment": "cash",
        "commission": 600.0
    }
    response = client.post("/api/trips", json=payload)
    assert response.status_code == 422


def test_validation_invalid_payment():
    """Test payment method other than card or cash is rejected."""
    payload = {
        "start": "2026-10-05T12:00:00+05:00",
        "end": "2026-10-05T12:30:00+05:00",
        "amount": 500.0,
        "payment": "crypto",
        "commission": 50.0
    }
    response = client.post("/api/trips", json=payload)
    assert response.status_code == 422


def test_delete_trip():
    """Test deleting trip endpoint."""
    response = client.delete("/api/trips/t2")
    assert response.status_code == 200
    assert response.json()["status"] == "deleted"

    # Second delete returns 404
    response_404 = client.delete("/api/trips/t2")
    assert response_404.status_code == 404
