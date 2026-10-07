"""FastAPI server for Driver Shift Diary."""

from datetime import datetime
from pathlib import Path
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, PlainTextResponse

from .models import Trip, TripCreate, DaySummary, DayResponse, TripAddResponse
from .storage import TripStorage
from .summary import calculate_day_summary, get_trip_date, format_receipt_text


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = BASE_DIR / "data" / "trips.json"
SAMPLE_FILE = BASE_DIR / "data" / "trips_sample.json"
STATIC_DIR = BASE_DIR / "app" / "static"

storage = TripStorage(file_path=str(DATA_FILE), sample_file_path=str(SAMPLE_FILE))

app = FastAPI(
    title="Дневник смен водителя API",
    description="API для учета поездок водителя, расчета смен, комиссии и выручки на руки.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/dates", response_model=List[str], tags=["Смены"])
def get_available_dates():
    """Получить список всех дат, в которых есть зафиксированные поездки."""
    return storage.get_available_dates()


@app.get("/api/trips", response_model=DayResponse, tags=["Поездки"])
def get_trips_for_day(date: Optional[str] = Query(None, description="Дата в формате YYYY-MM-DD")):
    """
    Получить список поездок и сводку за выбранный день.
    Если дата не указана, выбирается самая свежая дата с поездками или текущий день.
    """
    available_dates = storage.get_available_dates()

    if not date:
        if available_dates:
            target_date = available_dates[0]
        else:
            target_date = datetime.now().strftime("%Y-%m-%d")
    else:
        # Validate date format YYYY-MM-DD
        try:
            datetime.strptime(date, "%Y-%m-%d")
            target_date = date
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Некорректный формат даты. Используйте YYYY-MM-DD."
            )

    trips = storage.get_trips_by_date(target_date)
    summary = calculate_day_summary(trips, target_date)

    return DayResponse(
        date=target_date,
        summary=summary,
        trips=trips,
        available_dates=available_dates
    )


@app.get("/api/summary", response_model=DaySummary, tags=["Смены"])
def get_day_summary(date: str = Query(..., description="Дата в формате YYYY-MM-DD")):
    """Получить сводку за день: поездки, выручка, комиссия, на руки, наличные/карта."""
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Некорректный формат даты. Используйте YYYY-MM-DD."
        )

    trips = storage.get_trips_by_date(date)
    return calculate_day_summary(trips, date)


@app.get("/api/receipt", response_class=PlainTextResponse, tags=["Смены"])
def get_day_receipt(
    date: Optional[str] = Query(None, description="Дата в формате YYYY-MM-DD"),
    currency: str = Query("₸", description="Символ валюты (по умолчанию ₸)")
):
    """
    Получить чек смены в точном текстовом формате как на образце:
    время, способ оплаты, суммы, комиссия и жирный итог «На руки».
    """
    available_dates = storage.get_available_dates()
    if not date:
        target_date = available_dates[0] if available_dates else datetime.now().strftime("%Y-%m-%d")
    else:
        try:
            datetime.strptime(date, "%Y-%m-%d")
            target_date = date
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Некорректный формат даты. Используйте YYYY-MM-DD."
            )

    trips = storage.get_trips_by_date(target_date)
    summary = calculate_day_summary(trips, target_date)
    return format_receipt_text(summary, trips, currency=currency)



@app.post(
    "/api/trips",
    response_model=TripAddResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Поездки"]
)
def add_trip(
    trip_in: TripCreate,
    response: Response,
    strict_conflict: bool = Query(
        False,
        description="Если True, при дубликате возвращать HTTP 409 Conflict вместо HTTP 200"
    )
):
    """
    Добавить поездку с валидацией данных.
    Защита от дублей: повторная отправка той же поездки (по id или по совпадению полей) не создает дубль.
    """
    trip, is_new = storage.add_trip(trip_in)

    if not is_new:
        if strict_conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Поездка с ID {trip.id} или аналогичными параметрами уже существует."
            )
        # Idempotent response with 200 OK
        response.status_code = status.HTTP_200_OK
        return TripAddResponse(
            status="duplicate",
            message=f"Поездка уже зарегистрирована (ID: {trip.id}). Дубль не создан.",
            is_duplicate=True,
            trip=trip
        )

    return TripAddResponse(
        status="created",
        message="Поездка успешно зарегистрирована",
        is_duplicate=False,
        trip=trip
    )


@app.delete("/api/trips/{trip_id}", tags=["Поездки"])
def delete_trip(trip_id: str):
    """Удалить поездку по ID."""
    success = storage.delete_trip(trip_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Поездка с ID {trip_id} не найдена"
        )
    return {"status": "deleted", "id": trip_id, "message": "Поездка успешно удалена"}


@app.post("/api/reset", tags=["Служебные"])
def reset_sample_data():
    """Сбросить данные к исходному демонстрационному набору поездок."""
    storage.reset_to_sample()
    return {"status": "ok", "message": "Данные сброшены к исходному состоянию"}


# Serve static web files
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/", include_in_schema=False)
    def serve_frontend():
        index_file = STATIC_DIR / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"message": "Дневник смен водителя API. Посетите /docs для Swagger документации."}
