"""Data models and validation for driver trips and shift summaries."""

from datetime import datetime
from typing import Literal, Optional, List
import uuid
from pydantic import BaseModel, Field, model_validator


PaymentType = Literal["card", "cash"]


class TripBase(BaseModel):
    """Base fields for a trip."""
    start: datetime = Field(..., description="Время начала поездки в формате ISO 8601")
    end: datetime = Field(..., description="Время окончания поездки в формате ISO 8601")
    amount: float = Field(..., gt=0, description="Сумма поездки (должна быть строго > 0)")
    payment: PaymentType = Field(..., description="Способ оплаты: card (карта) или cash (наличные)")
    commission: float = Field(default=0.0, ge=0, description="Комиссия сервиса/парка (>= 0)")

    @model_validator(mode="after")
    def validate_trip_rules(self) -> "TripBase":
        # 1. Validation: end must be strictly after start
        start_dt = self.start
        end_dt = self.end

        # Normalize naive/aware timezone comparisons if needed
        if (start_dt.tzinfo is None and end_dt.tzinfo is not None) or (start_dt.tzinfo is not None and end_dt.tzinfo is None):
            raise ValueError("Время начала и окончания должны оба иметь часовой пояс либо оба быть без него")

        if end_dt <= start_dt:
            raise ValueError("Время окончания поездки (end) должно быть строго позже времени начала (start)")

        # 2. Validation: commission cannot exceed amount
        if self.commission > self.amount:
            raise ValueError(f"Комиссия ({self.commission}) не может превышать сумму поездки ({self.amount})")

        # Round amounts to 2 decimal places to prevent float rounding errors
        self.amount = round(float(self.amount), 2)
        self.commission = round(float(self.commission), 2)

        return self


class TripCreate(TripBase):
    """Payload to create a new trip."""
    id: Optional[str] = Field(None, description="Опциональный уникальный идентификатор поездки")


class Trip(TripBase):
    """Full trip representation with assigned ID."""
    id: str = Field(..., description="Уникальный идентификатор поездки")


class DaySummary(BaseModel):
    """Summary statistics for a selected day."""
    date: str = Field(..., description="Дата смены в формате YYYY-MM-DD")
    total_trips: int = Field(..., description="Общее число поездок за день")
    total_amount: float = Field(..., description="Общая выручка (грязными)")
    total_commission: float = Field(..., description="Общая комиссия сервиса/парка")
    net_income: float = Field(..., description="Сумма «на руки» (выручка минус комиссия)")
    cash_amount: float = Field(..., description="Сумма поездок за наличные")
    card_amount: float = Field(..., description="Сумма поездок по карте")
    cash_trips: int = Field(..., description="Количество поездок за наличные")
    card_trips: int = Field(..., description="Количество поездок по карте")


class DayResponse(BaseModel):
    """Response containing summary and trips list for a day."""
    date: str
    summary: DaySummary
    trips: List[Trip]
    available_dates: List[str] = Field(default_factory=list, description="Список всех дат со сменами")


class TripAddResponse(BaseModel):
    """Response when adding a trip, indicating success or idempotency duplicate."""
    status: Literal["created", "duplicate"] = Field(..., description="Статус операции")
    message: str = Field(..., description="Поясняющее сообщение")
    is_duplicate: bool = Field(..., description="Признак, была ли поездка повторной")
    trip: Trip = Field(..., description="Данные поездки")
