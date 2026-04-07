# Система бронирования (ресторан)

Мини-приложение: PostgreSQL, Python, графический интерфейс на tkinter.

## Требования

- Python 3.10+ (рекомендуется 3.11+)
- Установленный и запущенный **PostgreSQL**

## Установка

Из корня проекта (Windows PowerShell):

```powershell
cd "C:\путь\к\BOOKING"
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

Короткий вариант (если в корне есть файл-обёртка `requirements`):

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements
```

## Настройка БД

Скопируйте пример окружения и отредактируйте под свой сервер:

```powershell
copy .env.example .env
```

В `.env` должны быть переменные: `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` (см. `postgres_driver.py`).

Создайте пустую базу с именем из `DB_NAME` в PostgreSQL (например через pgAdmin или `createdb`).

## Запуск графического интерфейса

Из корня проекта, с активированным venv или полным путём к Python:

```powershell
.\venv\Scripts\python.exe gui.py
```

При первом запуске откройте вкладку **«Схема БД»** и нажмите **«Создать / обновить таблицы»**.

## Прочие команды

Создать только таблицы из кода (без GUI):

```powershell
.\venv\Scripts\python.exe backend.py
```

Проверка синтаксиса модулей:

```powershell
.\venv\Scripts\python.exe -m py_compile gui.py backend.py postgres_driver.py
```

## Проверка доступности стола при бронировании

На вкладке **«Бронирования»** в подвкладках **«Создать»** и **«Изменить»** есть кнопка **«Проверить доступность стола»**. Она использует поля **ID стола**, **Начало** и **Конец** и проверяет отсутствие пересечений с другими бронями (брони со статусом `cancelled` не блокируют слот). При изменении брони текущая запись исключается из проверки по её **ID брони**.
