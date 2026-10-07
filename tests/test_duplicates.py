"""Tests for duplicate trip detection and idempotency."""

from datetime import datetime
import tempfile
from pathlib import Path
from app.models import TripCreate
from app.storage import TripStorage


def test_duplicate_protection_by_id():
    """Verify that submitting a trip with an existing ID does NOT create a duplicate."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        storage_file = Path(tmp_dir) / "test_trips.json"
        storage = TripStorage(file_path=str(storage_file), sample_file_path=None)

        # 1. First submission
        trip_in = TripCreate(
            id="trip_dup_1",
            start=datetime.fromisoformat("2026-10-01T10:00:00+05:00"),
            end=datetime.fromisoformat("2026-10-01T10:20:00+05:00"),
            amount=1200.0,
            payment="card",
            commission=180.0
        )
        first_trip, is_new_1 = storage.add_trip(trip_in)
        assert is_new_1 is True
        assert first_trip.id == "trip_dup_1"
        assert len(storage.get_all_trips()) == 1

        # 2. Second submission with identical ID
        dup_trip, is_new_2 = storage.add_trip(trip_in)
        assert is_new_2 is False
        assert dup_trip.id == "trip_dup_1"
        # Total trip count must strictly remain 1!
        assert len(storage.get_all_trips()) == 1


def test_duplicate_protection_by_content_without_id():
    """Verify that re-submitting identical trip data without ID does NOT create a duplicate."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        storage_file = Path(tmp_dir) / "test_trips.json"
        storage = TripStorage(file_path=str(storage_file), sample_file_path=None)

        # 1. First submission without explicit ID
        trip_in_1 = TripCreate(
            start=datetime.fromisoformat("2026-10-01T14:00:00+05:00"),
            end=datetime.fromisoformat("2026-10-01T14:30:00+05:00"),
            amount=850.0,
            payment="cash",
            commission=127.5
        )
        trip1, is_new_1 = storage.add_trip(trip_in_1)
        assert is_new_1 is True
        assert trip1.id is not None
        assert len(storage.get_all_trips()) == 1

        # 2. Repeated submission with the exact same trip data
        trip_in_2 = TripCreate(
            start=datetime.fromisoformat("2026-10-01T14:00:00+05:00"),
            end=datetime.fromisoformat("2026-10-01T14:30:00+05:00"),
            amount=850.0,
            payment="cash",
            commission=127.5
        )
        trip2, is_new_2 = storage.add_trip(trip_in_2)
        assert is_new_2 is False
        assert trip2.id == trip1.id
        # Storage must still have only 1 trip
        assert len(storage.get_all_trips()) == 1


def test_different_trips_are_added():
    """Verify distinct trips are added normally."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        storage_file = Path(tmp_dir) / "test_trips.json"
        storage = TripStorage(file_path=str(storage_file), sample_file_path=None)

        trip_a = TripCreate(
            start=datetime.fromisoformat("2026-10-01T10:00:00+05:00"),
            end=datetime.fromisoformat("2026-10-01T10:20:00+05:00"),
            amount=500.0,
            payment="card",
            commission=75.0
        )
        trip_b = TripCreate(
            start=datetime.fromisoformat("2026-10-01T11:00:00+05:00"),
            end=datetime.fromisoformat("2026-10-01T11:20:00+05:00"),
            amount=700.0,
            payment="cash",
            commission=105.0
        )

        _, is_new_a = storage.add_trip(trip_a)
        _, is_new_b = storage.add_trip(trip_b)

        assert is_new_a is True
        assert is_new_b is True
        assert len(storage.get_all_trips()) == 2
