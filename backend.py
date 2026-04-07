"""Инициализация схемы БД и CRUD по моделям users, restaurant_tables, bookings."""

from __future__ import annotations

from contextlib import closing
from datetime import datetime
from typing import Any, Optional

from postgres_driver import PostgresDriver

import models.booking as booking_model
import models.tables as tables_model
import models.user as user_model
from models.booking import Booking
from models.tables import RestaurantTable
from models.user import User


def create_tables() -> None:
    with closing(PostgresDriver()) as db:
        db.ensure_table(user_model)
        db.ensure_table(tables_model)
        db.ensure_table(booking_model)


# --- Users ---


def create_user(user: User) -> int:
    with closing(PostgresDriver()) as db:
        new_id = db.create(user_model.TABLE_NAME, user.to_create_payload())
        return int(new_id)


def get_user_by_id(user_id: int) -> Optional[User]:
    with closing(PostgresDriver()) as db:
        row = db.read_one(user_model.TABLE_NAME, {"id": user_id})
        return User.from_row(row) if row else None


def list_users(
    filters: Optional[dict[str, Any]] = None,
    *,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> list[User]:
    with closing(PostgresDriver()) as db:
        rows = db.read_many(
            user_model.TABLE_NAME,
            filters=filters,
            limit=limit,
            offset=offset,
        )
        return [User.from_row(r) for r in rows]


def update_user(user_id: int, user: User) -> int:
    with closing(PostgresDriver()) as db:
        return db.update(
            user_model.TABLE_NAME,
            user.to_update_payload(),
            {"id": user_id},
        )


def delete_user(user_id: int) -> int:
    with closing(PostgresDriver()) as db:
        return db.delete(user_model.TABLE_NAME, {"id": user_id})


# --- Restaurant tables (модель RestaurantTable, таблица restaurant_tables) ---


def create_restaurant_table(table: RestaurantTable) -> int:
    with closing(PostgresDriver()) as db:
        new_id = db.create(tables_model.TABLE_NAME, table.to_create_payload())
        return int(new_id)


def get_restaurant_table_by_id(table_id: int) -> Optional[RestaurantTable]:
    with closing(PostgresDriver()) as db:
        row = db.read_one(tables_model.TABLE_NAME, {"id": table_id})
        return RestaurantTable.from_row(row) if row else None


def list_restaurant_tables(
    filters: Optional[dict[str, Any]] = None,
    *,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> list[RestaurantTable]:
    with closing(PostgresDriver()) as db:
        rows = db.read_many(
            tables_model.TABLE_NAME,
            filters=filters,
            limit=limit,
            offset=offset,
        )
        return [RestaurantTable.from_row(r) for r in rows]


def update_restaurant_table(table_id: int, table: RestaurantTable) -> int:
    with closing(PostgresDriver()) as db:
        return db.update(
            tables_model.TABLE_NAME,
            table.to_update_payload(),
            {"id": table_id},
        )


def delete_restaurant_table(table_id: int) -> int:
    with closing(PostgresDriver()) as db:
        return db.delete(tables_model.TABLE_NAME, {"id": table_id})


# --- Bookings ---


def find_booking_conflicts_for_table(
    restaurant_table_id: int,
    start_at: datetime,
    end_at: datetime,
    *,
    exclude_booking_id: Optional[int] = None,
) -> list[Booking]:
    """
    Брони на том же столе, которые пересекаются по времени с интервалом [start_at, end_at].
    Отменённые (cancelled) не учитываются. exclude_booking_id — при редактировании существующей брони.
    """
    if end_at <= start_at:
        raise ValueError("end_at должен быть позже start_at")

    with closing(PostgresDriver()) as db:
        conn = db.connect()
        params: list[Any] = [restaurant_table_id, end_at, start_at]
        skip = ""
        if exclude_booking_id is not None:
            skip = " AND id <> %s"
            params.append(exclude_booking_id)
        query = f"""
            SELECT id, user_id, restaurant_table_id, start_at, end_at, party_size,
                   status, notes, created_at, updated_at
            FROM {booking_model.TABLE_NAME}
            WHERE restaurant_table_id = %s
              AND status <> 'cancelled'
              AND start_at < %s
              AND end_at > %s
            {skip}
            ORDER BY start_at
        """
        with conn.cursor() as cur:
            cur.execute(query, params)
            columns = [d[0] for d in cur.description]
            return [Booking.from_row(dict(zip(columns, row))) for row in cur.fetchall()]


def is_restaurant_table_available(
    restaurant_table_id: int,
    start_at: datetime,
    end_at: datetime,
    *,
    exclude_booking_id: Optional[int] = None,
) -> tuple[bool, list[Booking]]:
    """Удобная обёртка: (свободен ли слот, список конфликтующих броней)."""
    conflicts = find_booking_conflicts_for_table(
        restaurant_table_id,
        start_at,
        end_at,
        exclude_booking_id=exclude_booking_id,
    )
    return (len(conflicts) == 0, conflicts)


def create_booking(booking: Booking) -> int:
    with closing(PostgresDriver()) as db:
        new_id = db.create(booking_model.TABLE_NAME, booking.to_create_payload())
        return int(new_id)


def get_booking_by_id(booking_id: int) -> Optional[Booking]:
    with closing(PostgresDriver()) as db:
        row = db.read_one(booking_model.TABLE_NAME, {"id": booking_id})
        return Booking.from_row(row) if row else None


def list_bookings(
    filters: Optional[dict[str, Any]] = None,
    *,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> list[Booking]:
    with closing(PostgresDriver()) as db:
        rows = db.read_many(
            booking_model.TABLE_NAME,
            filters=filters,
            limit=limit,
            offset=offset,
        )
        return [Booking.from_row(r) for r in rows]


def update_booking(booking_id: int, booking: Booking) -> int:
    with closing(PostgresDriver()) as db:
        return db.update(
            booking_model.TABLE_NAME,
            booking.to_update_payload(),
            {"id": booking_id},
        )


def delete_booking(booking_id: int) -> int:
    with closing(PostgresDriver()) as db:
        return db.delete(booking_model.TABLE_NAME, {"id": booking_id})


if __name__ == "__main__":
    create_tables()
