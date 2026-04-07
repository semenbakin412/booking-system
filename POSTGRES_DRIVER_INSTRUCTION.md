# PostgresDriver - инструкция по использованию

## 1) Что это

`PostgresDriver` - это простой модуль для работы с PostgreSQL через универсальные CRUD-методы:
- `create(...)`
- `read_one(...)`
- `read_many(...)`
- `update(...)`
- `delete(...)`

Модуль читает параметры подключения из `.env` тем же способом, что и проектный `main.py`.

## 2) Требования

Установите зависимости:

```bash
pip install -r requirements.txt
```

Та же установка сработает и с `pip install -r requirements` (в корне есть файл-обёртка).

## 3) Настройка переменных окружения

Создайте файл `.env` в корне проекта:

```env
HOST=localhost
PORT=5432
NAME=postgres
USER=postgres
PASSWORD=your_password
```

## 4) Базовое использование

```python
from postgres_driver import PostgresDriver

db = PostgresDriver()
new_id = db.create("users", {"name": "Ivan", "email": "ivan@example.com"})
user = db.read_one("users", {"id": new_id})
users = db.read_many("users", {"name": "Ivan"}, columns=["id", "name", "email"])
updated = db.update("users", {"name": "Ivan Petrov"}, {"id": new_id})
deleted = db.delete("users", {"id": new_id})
db.close()
```

## 5) Сигнатуры методов

- `create(table: str, data: dict, returning: str = "id") -> Any`
  - вставляет запись и возвращает значение поля `returning`.
- `read_one(table: str, filters: dict, columns: list[str] | None = None) -> dict | None`
  - возвращает одну запись или `None`.
- `read_many(table: str, filters: dict | None = None, columns: list[str] | None = None, limit: int | None = None, offset: int | None = None) -> list[dict]`
  - возвращает список записей.
- `update(table: str, data: dict, filters: dict) -> int`
  - обновляет записи, возвращает количество измененных строк.
- `delete(table: str, filters: dict) -> int`
  - удаляет записи, возвращает количество удаленных строк.

## 6) Важные ограничения

- В `update(...)` и `delete(...)` фильтры обязательны.
- Пустые `data` в `create(...)` и `update(...)` запрещены.
- Метод `create(...)` по умолчанию ожидает, что в таблице есть поле `id` (или передайте другой `returning`).

