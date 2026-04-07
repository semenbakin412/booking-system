# Система бронирования столиков ресторана

Приложение для управления бронированиями столиков в ресторане с PostgreSQL базой данных и графическим интерфейсом.

## Возможности

- **Управление пользователями** — создание, просмотр, редактирование, удаление пользователей с ролями (клиент, администратор, менеджер)
- **Управление столами** — добавление столов с указанием номера, вместимости и зоны (зал, терраса, VIP)
- **Бронирования** — создание броней с проверкой доступности стола по времени
- **Валидация** — автоматическая проверка пересекающихся броней для избежания конфликтов

## Технологии

- Python 3.10+
- PostgreSQL
- psycopg2-binary
- python-dotenv
- tkinter (встроен в Python)

## Установка

1. Клонируйте репозиторий
2. Установите зависимости:

```bash
pip install -r requirements.txt
```

3. Настройте подключение к базе данных в `.env`:

```
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=restaurant_booking
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password
```

## Запуск

### GUI-приложение

```bash
python gui.py
```

### Backend (только API/логика)

```bash
python -c "import backend; backend.create_tables()"
```

## Структура проекта

```
├── backend.py          # Логика работы с БД (CRUD)
├── gui.py              # Графический интерфейс (tkinter)
├── main.py             # Точка входа с функциями backend
├── postgres_driver.py  # Драйвер для работы с PostgreSQL
├── models/             # Модели данных
│   ├── user.py
│   ├── tables.py
│   └── booking.py
└── requirements.txt    # Зависимости
```

## Модели данных

### Users (Пользователи)
- email, password_hash, full_name, phone
- role: CLIENT / ADMIN / MANAGER
- is_active, created_at, updated_at

### RestaurantTables (Столы)
- label (номер/название), capacity (вместимость)
- zone: HALL / TERRACE / VIP
- is_active, notes, created_at, updated_at

### Bookings (Бронирования)
- user_id, restaurant_table_id
- start_at, end_at (время брони)
- party_size (количество гостей)
- status: PENDING / CONFIRMED / CANCELLED / COMPLETED
- notes, created_at, updated_at
