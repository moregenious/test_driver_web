"""File-based storage for trips with atomic persistence, thread-safety, and duplicate protection."""

import json
import os
import threading
import uuid
from pathlib import Path
from typing import List, Optional, Tuple
from datetime import datetime

from .models import Trip, TripCreate
from .summary import get_trip_date


class TripStorage:
    def __init__(self, file_path: str = "data/trips.json", sample_file_path: Optional[str] = "data/trips_sample.json"):
        self.file_path = Path(file_path)
        self.sample_file_path = Path(sample_file_path) if sample_file_path else None
        self._lock = threading.Lock()
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        """Ensure storage directory and trips.json file exist."""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            if self.sample_file_path and self.sample_file_path.exists():
                # Copy from sample data
                content = self.sample_file_path.read_text(encoding="utf-8")
                self.file_path.write_text(content, encoding="utf-8")
            else:
                # Initialize empty list
                self._save_raw([])

    def _load_raw(self) -> List[dict]:
        """Read raw trip dictionaries from JSON file."""
        if not self.file_path.exists():
            return []
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []

    def _save_raw(self, data: List[dict]) -> None:
        """Atomically write raw trip dictionaries to JSON file."""
        temp_path = self.file_path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        # Atomic replace
        os.replace(temp_path, self.file_path)

    def get_all_trips(self) -> List[Trip]:
        """Return all trips parsed as Trip models, sorted by start time."""
        with self._lock:
            raw_items = self._load_raw()
            trips = [Trip(**item) for item in raw_items]
            trips.sort(key=lambda t: t.start)
            return trips

    def get_trips_by_date(self, target_date: str) -> List[Trip]:
        """Return trips filtered by start date (YYYY-MM-DD)."""
        all_trips = self.get_all_trips()
        return [t for t in all_trips if get_trip_date(t) == target_date]

    def get_available_dates(self) -> List[str]:
        """Return unique sorted list of dates (YYYY-MM-DD) that have trips."""
        all_trips = self.get_all_trips()
        dates = sorted({get_trip_date(t) for t in all_trips}, reverse=True)
        return dates

    def get_trip_by_id(self, trip_id: str) -> Optional[Trip]:
        """Find a trip by ID."""
        for trip in self.get_all_trips():
            if trip.id == trip_id:
                return trip
        return None

    def _generate_id(self, existing_trips: List[Trip]) -> str:
        """Generate a user-friendly or unique ID like t10 or uuid short."""
        existing_ids = {t.id for t in existing_trips}
        idx = 1
        while f"t{idx}" in existing_ids:
            idx += 1
        return f"t{idx}"

    def add_trip(self, trip_in: TripCreate) -> Tuple[Trip, bool]:
        """
        Add a new trip with duplicate protection.
        Returns: (Trip, is_created)
        - If duplicate is found (by id OR by identical trip data), returns (existing_trip, False)
        - If new, saves to storage and returns (new_trip, True)
        """
        with self._lock:
            raw_items = self._load_raw()
            existing_trips = [Trip(**item) for item in raw_items]

            # 1. Duplicate check by ID if provided
            if trip_in.id:
                for existing in existing_trips:
                    if existing.id == trip_in.id:
                        return existing, False

            # 2. Duplicate check by content fingerprint (start, end, amount, payment, commission)
            for existing in existing_trips:
                if (
                    existing.start == trip_in.start
                    and existing.end == trip_in.end
                    and abs(existing.amount - trip_in.amount) < 0.001
                    and existing.payment == trip_in.payment
                    and abs(existing.commission - trip_in.commission) < 0.001
                ):
                    return existing, False

            # 3. Create new Trip instance
            new_id = trip_in.id if trip_in.id else self._generate_id(existing_trips)
            new_trip = Trip(
                id=new_id,
                start=trip_in.start,
                end=trip_in.end,
                amount=trip_in.amount,
                payment=trip_in.payment,
                commission=trip_in.commission,
            )

            # 4. Append and persist atomically
            serialized_trip = {
                "id": new_trip.id,
                "start": new_trip.start.isoformat(),
                "end": new_trip.end.isoformat(),
                "amount": new_trip.amount,
                "payment": new_trip.payment,
                "commission": new_trip.commission,
            }
            raw_items.append(serialized_trip)
            self._save_raw(raw_items)

            return new_trip, True

    def delete_trip(self, trip_id: str) -> bool:
        """Delete a trip by ID. Returns True if deleted, False if not found."""
        with self._lock:
            raw_items = self._load_raw()
            initial_count = len(raw_items)
            filtered = [item for item in raw_items if item.get("id") != trip_id]
            if len(filtered) < initial_count:
                self._save_raw(filtered)
                return True
            return False

    def reset_to_sample(self) -> None:
        """Reset storage to original sample data."""
        with self._lock:
            if self.sample_file_path and self.sample_file_path.exists():
                content = self.sample_file_path.read_text(encoding="utf-8")
                self.file_path.write_text(content, encoding="utf-8")
            else:
                self._save_raw([])
