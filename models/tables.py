"""Модель стола в ресторане для мини-системы бронирования (одна сущность = один физический стол)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Mapping, Optional


TABLE_NAME = "restaurant_tables"

RESTAURANT_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS restaurant_tables (
    id          SERIAL PRIMARY KEY,
    label       VARCHAR(64) NOT NULL UNIQUE,
    capacity    INT NOT NULL CHECK (capacity > 0),
    zone        VARCHAR(32) NOT NULL DEFAULT 'hall',
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    notes       TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_restaurant_tables_zone ON restaurant_tables (zone);
CREATE INDEX IF NOT EXISTS idx_restaurant_tables_active ON restaurant_tables (is_active);
"""


class TableZone(str, Enum):
    """Зона зала, где стоит стол."""

    HALL = "hall"
    TERRACE = "terrace"
    VIP = "vip"
    BAR = "bar"


@dataclass
class RestaurantTable:
    """
    Один стол: вместимость, зона, метка для гостей и персонала.
    Поля `id`, `created_at`, `updated_at` заполняются БД после вставки.
    """

    label: str
    capacity: int
    zone: TableZone = TableZone.HALL
    is_active: bool = True
    notes: Optional[str] = None
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_create_payload(self) -> dict[str, Any]:
        """Словарь для `PostgresDriver.create(TABLE_NAME, data, ...)`."""
        data: dict[str, Any] = {
            "label": self.label,
            "capacity": self.capacity,
            "zone": self.zone.value,
            "is_active": self.is_active,
        }
        if self.notes is not None:
            data["notes"] = self.notes
        return data

    def to_update_payload(self) -> dict[str, Any]:
        """Словарь для `PostgresDriver.update` (без id и служебных полей)."""
        data: dict[str, Any] = {
            "label": self.label,
            "capacity": self.capacity,
            "zone": self.zone.value,
            "is_active": self.is_active,
        }
        data["notes"] = self.notes
        return data

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> RestaurantTable:
        """Собрать модель из строки `read_one` / `read_many` (ключи = имена колонок)."""
        zone_raw = row["zone"]
        zone = zone_raw if isinstance(zone_raw, TableZone) else TableZone(str(zone_raw))
        return cls(
            id=row["id"],
            label=row["label"],
            capacity=int(row["capacity"]),
            zone=zone,
            is_active=bool(row["is_active"]),
            notes=row.get("notes"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )
