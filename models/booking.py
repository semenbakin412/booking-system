"""Модель бронирования: связь пользователя, стола и интервала времени."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Mapping, Optional


TABLE_NAME = "bookings"

BOOKINGS_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS bookings (
    id                   SERIAL PRIMARY KEY,
    user_id              INT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    restaurant_table_id  INT NOT NULL REFERENCES restaurant_tables (id) ON DELETE RESTRICT,
    start_at             TIMESTAMPTZ NOT NULL,
    end_at               TIMESTAMPTZ NOT NULL,
    party_size           INT NOT NULL CHECK (party_size > 0),
    status               VARCHAR(32) NOT NULL DEFAULT 'pending',
    notes                TEXT,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_bookings_time_range CHECK (end_at > start_at)
);
CREATE INDEX IF NOT EXISTS idx_bookings_user_id ON bookings (user_id);
CREATE INDEX IF NOT EXISTS idx_bookings_restaurant_table_id ON bookings (restaurant_table_id);
CREATE INDEX IF NOT EXISTS idx_bookings_start_at ON bookings (start_at);
CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings (status);
"""


class BookingStatus(str, Enum):
    """Статус бронирования в жизненном цикле."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


@dataclass
class Booking:
    """
    Одно бронирование: кто (`user_id`), какой стол (`restaurant_table_id`), когда и сколько гостей.
    Поля `id`, `created_at`, `updated_at` заполняются БД после вставки.
    """

    user_id: int
    restaurant_table_id: int
    start_at: datetime
    end_at: datetime
    party_size: int
    status: BookingStatus = BookingStatus.PENDING
    notes: Optional[str] = None
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_create_payload(self) -> dict[str, Any]:
        """Словарь для `PostgresDriver.create(TABLE_NAME, data, ...)`."""
        data: dict[str, Any] = {
            "user_id": self.user_id,
            "restaurant_table_id": self.restaurant_table_id,
            "start_at": self.start_at,
            "end_at": self.end_at,
            "party_size": self.party_size,
            "status": self.status.value,
        }
        if self.notes is not None:
            data["notes"] = self.notes
        return data

    def to_update_payload(self) -> dict[str, Any]:
        """Словарь для `PostgresDriver.update` (без id и служебных полей)."""
        data: dict[str, Any] = {
            "user_id": self.user_id,
            "restaurant_table_id": self.restaurant_table_id,
            "start_at": self.start_at,
            "end_at": self.end_at,
            "party_size": self.party_size,
            "status": self.status.value,
        }
        data["notes"] = self.notes
        return data

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> Booking:
        """Собрать модель из строки `read_one` / `read_many` (ключи = имена колонок)."""
        status_raw = row["status"]
        status = (
            status_raw
            if isinstance(status_raw, BookingStatus)
            else BookingStatus(str(status_raw))
        )
        return cls(
            id=row["id"],
            user_id=int(row["user_id"]),
            restaurant_table_id=int(row["restaurant_table_id"]),
            start_at=row["start_at"],
            end_at=row["end_at"],
            party_size=int(row["party_size"]),
            status=status,
            notes=row.get("notes"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )
