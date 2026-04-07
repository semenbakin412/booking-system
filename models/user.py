"""Модель пользователя для мини-системы бронирования (соответствие будущей таблице `users`)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Mapping, Optional


TABLE_NAME = "users"

# SQL для создания таблицы под эту модель (выполнить при миграции / инициализации БД).
USERS_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    email           VARCHAR(255) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    full_name       VARCHAR(255) NOT NULL,
    phone           VARCHAR(32),
    role            VARCHAR(32) NOT NULL DEFAULT 'client',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users (role);
"""


class UserRole(str, Enum):
    """Роль в системе бронирования."""

    CLIENT = "client"
    ADMIN = "admin"


@dataclass
class User:
    """
    Пользователь: вход в систему, контакт для напоминаний о бронировании.
    Поля `id`, `created_at`, `updated_at` заполняются БД после вставки.
    """

    email: str
    password_hash: str
    full_name: str
    phone: Optional[str] = None
    role: UserRole = UserRole.CLIENT
    is_active: bool = True
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_create_payload(self) -> dict[str, Any]:
        """Словарь для `PostgresDriver.create(TABLE_NAME, data, ...)`."""
        data: dict[str, Any] = {
            "email": self.email,
            "password_hash": self.password_hash,
            "full_name": self.full_name,
            "role": self.role.value,
            "is_active": self.is_active,
        }
        if self.phone is not None:
            data["phone"] = self.phone
        return data

    def to_update_payload(self) -> dict[str, Any]:
        """Словарь для `PostgresDriver.update` (без id и служебных полей)."""
        data: dict[str, Any] = {
            "email": self.email,
            "password_hash": self.password_hash,
            "full_name": self.full_name,
            "role": self.role.value,
            "is_active": self.is_active,
        }
        data["phone"] = self.phone
        return data

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> User:
        """Собрать модель из строки `read_one` / `read_many` (ключи = имена колонок)."""
        role_raw = row["role"]
        role = role_raw if isinstance(role_raw, UserRole) else UserRole(str(role_raw))
        return cls(
            id=row["id"],
            email=row["email"],
            password_hash=row["password_hash"],
            full_name=row["full_name"],
            phone=row.get("phone"),
            role=role,
            is_active=bool(row["is_active"]),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )
