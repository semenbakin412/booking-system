import os
import time
from pathlib import Path
from typing import Any, Optional

import psycopg2
from dotenv import load_dotenv
from psycopg2 import sql
from psycopg2.extensions import connection as PgConnection

_ENV_PATH = Path(__file__).resolve().parent / ".env"
try:
    # Primary mode: standard UTF-8 .env in project root.
    load_dotenv(dotenv_path=_ENV_PATH, encoding="utf-8")
except UnicodeDecodeError:
    # Fallback for Windows-created files in legacy ANSI/CP1251 encoding.
    load_dotenv(dotenv_path=_ENV_PATH, encoding="cp1251")


class PostgresDriver:
    """Simple PostgreSQL driver with generic CRUD operations."""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        dbname: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        connect_timeout: int = 5,
    ) -> None:
        self.host = host or os.getenv("DB_HOST", "localhost")
        self.port = int(port or os.getenv("DB_PORT", "5432"))
        self.dbname = dbname or os.getenv("DB_NAME", "test")
        self.user = user or os.getenv("DB_USER", "postgres")
        self.password = password or os.getenv("DB_PASSWORD", "")
        self.connect_timeout = connect_timeout
        self._conn: Optional[PgConnection] = None

    def connect(self) -> PgConnection:
        if self._conn is None or self._conn.closed:
            try:
                self._conn = psycopg2.connect(
                    host=self.host,
                    port=self.port,
                    dbname=self.dbname,
                    user=self.user,
                    password=self.password,
                    connect_timeout=self.connect_timeout,
                )
            except UnicodeDecodeError as e:
                raise RuntimeError(
                    "Не удалось декодировать ответ PostgreSQL при подключении. "
                    "Проверьте DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD в .env "
                    "и убедитесь, что учетные данные верные."
                ) from e
        return self._conn

    def close(self) -> None:
        if self._conn is not None and not self._conn.closed:
            self._conn.close()

    def create(
        self,
        table: str,
        data: dict[str, Any],
        returning: str = "id",
    ) -> Any:
        if not data:
            raise ValueError("data for create() must not be empty")

        conn = self.connect()
        columns = list(data.keys())
        values = list(data.values())

        query = sql.SQL(
            "INSERT INTO {table} ({fields}) VALUES ({values}) RETURNING {returning}"
        ).format(
            table=sql.Identifier(table),
            fields=sql.SQL(", ").join(sql.Identifier(c) for c in columns),
            values=sql.SQL(", ").join(sql.Placeholder() for _ in values),
            returning=sql.Identifier(returning),
        )

        with conn:
            with conn.cursor() as cur:
                cur.execute(query, values)
                row = cur.fetchone()
                return row[0] if row else None

    def read_one(
        self,
        table: str,
        filters: dict[str, Any],
        columns: Optional[list[str]] = None,
    ) -> Optional[dict[str, Any]]:
        rows = self.read_many(table=table, filters=filters, columns=columns, limit=1)
        return rows[0] if rows else None

    def read_many(
        self,
        table: str,
        filters: Optional[dict[str, Any]] = None,
        columns: Optional[list[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        conn = self.connect()
        selected_cols = (
            sql.SQL(", ").join(sql.Identifier(c) for c in columns)
            if columns
            else sql.SQL("*")
        )

        where_clause, where_values = self._build_where_clause(filters or {})
        query = sql.SQL("SELECT {cols} FROM {table}{where}").format(
            cols=selected_cols,
            table=sql.Identifier(table),
            where=where_clause,
        )

        params = list(where_values)
        if limit is not None:
            query += sql.SQL(" LIMIT %s")
            params.append(limit)
        if offset is not None:
            query += sql.SQL(" OFFSET %s")
            params.append(offset)

        with conn.cursor() as cur:
            cur.execute(query, params)
            records = cur.fetchall()
            column_names = [desc[0] for desc in cur.description]
            return [dict(zip(column_names, row)) for row in records]

    def update(self, table: str, data: dict[str, Any], filters: dict[str, Any]) -> int:
        if not data:
            raise ValueError("data for update() must not be empty")
        if not filters:
            raise ValueError("filters for update() must not be empty")

        conn = self.connect()
        set_columns = list(data.keys())
        set_values = list(data.values())
        where_clause, where_values = self._build_where_clause(filters)

        set_expr = sql.SQL(", ").join(
            sql.SQL("{} = {}").format(sql.Identifier(col), sql.Placeholder())
            for col in set_columns
        )

        query = sql.SQL("UPDATE {table} SET {set_expr}{where}").format(
            table=sql.Identifier(table),
            set_expr=set_expr,
            where=where_clause,
        )

        with conn:
            with conn.cursor() as cur:
                cur.execute(query, set_values + where_values)
                return cur.rowcount

    def delete(self, table: str, filters: dict[str, Any]) -> int:
        if not filters:
            raise ValueError("filters for delete() must not be empty")

        conn = self.connect()
        where_clause, where_values = self._build_where_clause(filters)
        query = sql.SQL("DELETE FROM {table}{where}").format(
            table=sql.Identifier(table),
            where=where_clause,
        )

        with conn:
            with conn.cursor() as cur:
                cur.execute(query, where_values)
                return cur.rowcount

    def ensure_table(self, model: Any) -> None:
        """
        Создать таблицу (и индексы из DDL), если их ещё нет.

        Ожидается модуль в духе ``models.user``: атрибут ``TABLE_NAME`` и строка DDL
        в ``TABLE_DDL`` или в единственном атрибуте вида ``*_TABLE_DDL``
        (например ``USERS_TABLE_DDL``).
        """
        table_name = getattr(model, "TABLE_NAME", None)
        if not isinstance(table_name, str) or not table_name.strip():
            raise TypeError("model должен задавать непустую строку TABLE_NAME")

        ddl = self._ddl_string_from_model(model)
        conn = self.connect()
        with conn:
            with conn.cursor() as cur:
                for statement in self._split_sql_statements(ddl):
                    cur.execute(statement)

    @staticmethod
    def _ddl_string_from_model(model: Any) -> str:
        direct = getattr(model, "TABLE_DDL", None)
        if isinstance(direct, str) and direct.strip():
            return direct.strip()

        chunks: list[str] = []
        for key in dir(model):
            if not key.endswith("_TABLE_DDL"):
                continue
            val = getattr(model, key, None)
            if isinstance(val, str) and val.strip():
                chunks.append(val.strip())
        if not chunks:
            raise TypeError(
                "model должен задавать TABLE_DDL или один строковый атрибут *_TABLE_DDL "
                "(как USERS_TABLE_DDL в models.user)."
            )
        if len(chunks) > 1:
            raise TypeError(
                "в model несколько строк *_TABLE_DDL; задайте один TABLE_DDL или оставьте один DDL."
            )
        return chunks[0]

    @staticmethod
    def _split_sql_statements(script: str) -> list[str]:
        """Разбить DDL на отдельные команды (psycopg2 выполняет одну за раз)."""
        parts: list[str] = []
        for raw in script.split(";"):
            stmt = raw.strip()
            if stmt:
                parts.append(stmt)
        return parts

    def create_tables(self) -> None:
        conn = self.connect()
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                      id   SERIAL PRIMARY KEY,
                      name TEXT NOT NULL,
                      age  INT CHECK (age >= 0)
                    );
                    """
                )
                # Backward-compatible migration: if users table exists from
                # previous steps (without age), add missing column.
                cur.execute(
                    """
                    ALTER TABLE users
                    ADD COLUMN IF NOT EXISTS age INT CHECK (age >= 0);
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS orders (
                      id         SERIAL PRIMARY KEY,
                      user_id    INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                      amount     NUMERIC(10,2) NOT NULL,
                      created_at TIMESTAMP DEFAULT NOW()
                    );
                    """
                )

    def add_user(self, name: str, age: int) -> int:
        data: dict[str, Any] = {"name": name, "age": age}
        if self._users_email_is_required():
            safe_name = "".join(ch.lower() for ch in name if ch.isalnum()) or "user"
            data["email"] = f"{safe_name}_{int(time.time() * 1000)}@example.local"

        return int(self.create(table="users", data=data, returning="id"))

    def add_order(self, user_id: int, amount: float) -> int:
        return int(
            self.create(
                table="orders",
                data={"user_id": user_id, "amount": amount},
                returning="id",
            )
        )

    def get_user_totals(self) -> list[dict[str, Any]]:
        conn = self.connect()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT u.id,
                       u.name,
                       COALESCE(SUM(o.amount), 0) AS total_amount
                FROM users u
                LEFT JOIN orders o ON o.user_id = u.id
                GROUP BY u.id, u.name
                ORDER BY total_amount DESC;
                """
            )
            rows = cur.fetchall()
            return [
                {"id": row[0], "name": row[1], "total_amount": float(row[2])}
                for row in rows
            ]

    @staticmethod
    def _build_where_clause(filters: dict[str, Any]) -> tuple[sql.SQL, list[Any]]:
        if not filters:
            return sql.SQL(""), []

        conditions = []
        values: list[Any] = []
        for column, value in filters.items():
            conditions.append(
                sql.SQL("{} = {}").format(sql.Identifier(column), sql.Placeholder())
            )
            values.append(value)

        where_clause = sql.SQL(" WHERE ") + sql.SQL(" AND ").join(conditions)
        return where_clause, values

    def _users_email_is_required(self) -> bool:
        conn = self.connect()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'users'
                  AND column_name = 'email';
                """
            )
            row = cur.fetchone()
            return bool(row and row[0] == "NO")

