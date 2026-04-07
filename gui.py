"""Графический интерфейс системы бронирования (tkinter + backend)."""

from __future__ import annotations

import hashlib
import sys
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk
from typing import Any, Callable, Optional

import backend
from models.booking import Booking, BookingStatus
from models.tables import RestaurantTable, TableZone
from models.user import User, UserRole


def _hash_password(plain: str) -> str:
    """Демо-хеш для поля password_hash (не для продакшена)."""
    return hashlib.sha256(plain.encode("utf-8")).hexdigest()


def _parse_dt(s: str) -> datetime:
    s = s.strip()
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%d.%m.%Y %H:%M"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    raise ValueError(
        "Дата/время: используйте ГГГГ-ММ-ДД ЧЧ:ММ или ДД.ММ.ГГГГ ЧЧ:ММ"
    )


def _optional_int(entry: str) -> Optional[int]:
    s = entry.strip()
    if not s:
        return None
    return int(s)


def _run_safe(action: Callable[[], None]) -> None:
    try:
        action()
    except Exception as e:  # noqa: BLE001 — показать любую ошибку БД в GUI
        messagebox.showerror("Ошибка", str(e))


class BookingApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Бронирование ресторана")
        self.root.geometry("960x720")
        self.root.minsize(800, 560)

        style = ttk.Style()
        if sys.platform == "win32":
            style.theme_use("vista")

        nb = ttk.Notebook(self.root)
        nb.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self._tab_schema(nb)
        self._tab_users(nb)
        self._tab_tables(nb)
        self._tab_bookings(nb)

    def _tab_schema(self, parent: ttk.Notebook) -> None:
        f = ttk.Frame(parent, padding=12)
        parent.add(f, text="Схема БД")

        ttk.Label(
            f,
            text="Создать таблицы users, restaurant_tables, bookings (IF NOT EXISTS).",
            wraplength=520,
        ).pack(anchor=tk.W)

        def do_create() -> None:
            backend.create_tables()
            messagebox.showinfo("Готово", "Таблицы созданы или уже существуют.")

        ttk.Button(f, text="Создать / обновить таблицы", command=lambda: _run_safe(do_create)).pack(
            anchor=tk.W, pady=(12, 0)
        )

    def _tab_users(self, parent: ttk.Notebook) -> None:
        outer = ttk.Frame(parent, padding=4)
        parent.add(outer, text="Пользователи")
        snb = ttk.Notebook(outer)
        snb.pack(fill=tk.BOTH, expand=True)

        # --- Создать ---
        t_create = ttk.Frame(snb, padding=10)
        snb.add(t_create, text="Создать")
        self.u_c_email = self._entry_row(t_create, "Email", 0)
        self.u_c_password = self._entry_row(t_create, "Пароль", 1, show="*")
        self.u_c_full_name = self._entry_row(t_create, "ФИО", 2)
        self.u_c_phone = self._entry_row(t_create, "Телефон (необяз.)", 3)
        self.u_c_role = self._combo_row(
            t_create, "Роль", 4, [r.value for r in UserRole], UserRole.CLIENT.value
        )
        self.u_c_active = tk.BooleanVar(value=True)
        ttk.Checkbutton(t_create, text="Активен", variable=self.u_c_active).grid(
            row=5, column=0, columnspan=2, sticky=tk.W, pady=4
        )
        ttk.Button(
            t_create,
            text="Создать пользователя",
            command=lambda: _run_safe(self._user_create),
        ).grid(row=6, column=0, columnspan=2, pady=12, sticky=tk.W)

        # --- Найти ---
        t_get = ttk.Frame(snb, padding=10)
        snb.add(t_get, text="Найти")
        self.u_g_id = self._entry_row(t_get, "ID", 0)
        self.u_g_out = tk.Text(t_get, height=8, width=70, state=tk.DISABLED, wrap=tk.WORD)
        self.u_g_out.grid(row=1, column=0, columnspan=2, sticky=tk.NSEW, pady=8)
        t_get.rowconfigure(1, weight=1)
        t_get.columnconfigure(0, weight=1)
        ttk.Button(t_get, text="Загрузить", command=lambda: _run_safe(self._user_get)).grid(
            row=2, column=0, sticky=tk.W
        )

        # --- Список ---
        t_list = ttk.Frame(snb, padding=10)
        snb.add(t_list, text="Список")
        self.u_l_email = self._entry_row(t_list, "Фильтр email", 0)
        self.u_l_role = self._combo_row(
            t_list, "Фильтр роль", 1, ["", *[r.value for r in UserRole]], ""
        )
        self.u_l_limit = self._entry_row(t_list, "Лимит (пусто = все)", 2)
        self.u_l_offset = self._entry_row(t_list, "Смещение", 3)
        cols = ("id", "email", "full_name", "phone", "role", "is_active")
        self.u_tree = ttk.Treeview(t_list, columns=cols, show="headings", height=12)
        for c, w in zip(cols, (50, 180, 160, 100, 80, 70)):
            self.u_tree.heading(c, text=c)
            self.u_tree.column(c, width=w)
        ys = ttk.Scrollbar(t_list, orient=tk.VERTICAL, command=self.u_tree.yview)
        self.u_tree.configure(yscrollcommand=ys.set)
        self.u_tree.grid(row=4, column=0, sticky=tk.NSEW)
        ys.grid(row=4, column=1, sticky=tk.NS)
        t_list.rowconfigure(4, weight=1)
        t_list.columnconfigure(0, weight=1)
        ttk.Button(t_list, text="Обновить список", command=lambda: _run_safe(self._user_list)).grid(
            row=5, column=0, pady=8, sticky=tk.W
        )

        # --- Изменить ---
        t_up = ttk.Frame(snb, padding=10)
        snb.add(t_up, text="Изменить")
        self.u_u_id = self._entry_row(t_up, "ID", 0)
        ttk.Button(t_up, text="Загрузить в форму", command=lambda: _run_safe(self._user_load_for_update)).grid(
            row=1, column=0, columnspan=2, sticky=tk.W, pady=4
        )
        self.u_u_email = self._entry_row(t_up, "Email", 2)
        self.u_u_password = self._entry_row(t_up, "Новый пароль", 3, show="*")
        self.u_u_full_name = self._entry_row(t_up, "ФИО", 4)
        self.u_u_phone = self._entry_row(t_up, "Телефон", 5)
        self.u_u_role = self._combo_row(
            t_up, "Роль", 6, [r.value for r in UserRole], UserRole.CLIENT.value
        )
        self.u_u_active = tk.BooleanVar(value=True)
        ttk.Checkbutton(t_up, text="Активен", variable=self.u_u_active).grid(
            row=7, column=0, columnspan=2, sticky=tk.W, pady=4
        )
        ttk.Button(t_up, text="Сохранить изменения", command=lambda: _run_safe(self._user_update)).grid(
            row=8, column=0, pady=12, sticky=tk.W
        )

        # --- Удалить ---
        t_del = ttk.Frame(snb, padding=10)
        snb.add(t_del, text="Удалить")
        self.u_d_id = self._entry_row(t_del, "ID пользователя", 0)
        ttk.Button(t_del, text="Удалить", command=lambda: _run_safe(self._user_delete)).grid(
            row=1, column=0, pady=12, sticky=tk.W
        )

    def _tab_tables(self, parent: ttk.Notebook) -> None:
        outer = ttk.Frame(parent, padding=4)
        parent.add(outer, text="Столы")
        snb = ttk.Notebook(outer)
        snb.pack(fill=tk.BOTH, expand=True)

        t_create = ttk.Frame(snb, padding=10)
        snb.add(t_create, text="Создать")
        self.t_c_label = self._entry_row(t_create, "Метка (номер)", 0)
        self.t_c_capacity = self._entry_row(t_create, "Вместимость", 1)
        self.t_c_zone = self._combo_row(
            t_create, "Зона", 2, [z.value for z in TableZone], TableZone.HALL.value
        )
        self.t_c_active = tk.BooleanVar(value=True)
        ttk.Checkbutton(t_create, text="Активен", variable=self.t_c_active).grid(
            row=3, column=0, columnspan=2, sticky=tk.W, pady=4
        )
        self.t_c_notes = self._entry_row(t_create, "Заметки", 4)
        ttk.Button(
            t_create, text="Создать стол", command=lambda: _run_safe(self._table_create)
        ).grid(row=5, column=0, pady=12, sticky=tk.W)

        t_get = ttk.Frame(snb, padding=10)
        snb.add(t_get, text="Найти")
        self.t_g_id = self._entry_row(t_get, "ID", 0)
        self.t_g_out = tk.Text(t_get, height=8, width=70, state=tk.DISABLED, wrap=tk.WORD)
        self.t_g_out.grid(row=1, column=0, columnspan=2, sticky=tk.NSEW, pady=8)
        t_get.rowconfigure(1, weight=1)
        t_get.columnconfigure(0, weight=1)
        ttk.Button(t_get, text="Загрузить", command=lambda: _run_safe(self._table_get)).grid(
            row=2, column=0, sticky=tk.W
        )

        t_list = ttk.Frame(snb, padding=10)
        snb.add(t_list, text="Список")
        self.t_l_zone = self._combo_row(
            t_list, "Фильтр зона", 0, ["", *[z.value for z in TableZone]], ""
        )
        self.t_l_limit = self._entry_row(t_list, "Лимит", 1)
        self.t_l_offset = self._entry_row(t_list, "Смещение", 2)
        cols = ("id", "label", "capacity", "zone", "is_active", "notes")
        self.t_tree = ttk.Treeview(t_list, columns=cols, show="headings", height=12)
        for c, w in zip(cols, (40, 80, 70, 80, 70, 200)):
            self.t_tree.heading(c, text=c)
            self.t_tree.column(c, width=w)
        ys = ttk.Scrollbar(t_list, orient=tk.VERTICAL, command=self.t_tree.yview)
        self.t_tree.configure(yscrollcommand=ys.set)
        self.t_tree.grid(row=3, column=0, sticky=tk.NSEW)
        ys.grid(row=3, column=1, sticky=tk.NS)
        t_list.rowconfigure(3, weight=1)
        t_list.columnconfigure(0, weight=1)
        ttk.Button(t_list, text="Обновить список", command=lambda: _run_safe(self._table_list)).grid(
            row=4, column=0, pady=8, sticky=tk.W
        )

        t_up = ttk.Frame(snb, padding=10)
        snb.add(t_up, text="Изменить")
        self.t_u_id = self._entry_row(t_up, "ID", 0)
        ttk.Button(t_up, text="Загрузить в форму", command=lambda: _run_safe(self._table_load_for_update)).grid(
            row=1, column=0, columnspan=2, sticky=tk.W, pady=4
        )
        self.t_u_label = self._entry_row(t_up, "Метка", 2)
        self.t_u_capacity = self._entry_row(t_up, "Вместимость", 3)
        self.t_u_zone = self._combo_row(
            t_up, "Зона", 4, [z.value for z in TableZone], TableZone.HALL.value
        )
        self.t_u_active = tk.BooleanVar(value=True)
        ttk.Checkbutton(t_up, text="Активен", variable=self.t_u_active).grid(
            row=5, column=0, columnspan=2, sticky=tk.W, pady=4
        )
        self.t_u_notes = self._entry_row(t_up, "Заметки", 6)
        ttk.Button(t_up, text="Сохранить", command=lambda: _run_safe(self._table_update)).grid(
            row=7, column=0, pady=12, sticky=tk.W
        )

        t_del = ttk.Frame(snb, padding=10)
        snb.add(t_del, text="Удалить")
        self.t_d_id = self._entry_row(t_del, "ID стола", 0)
        ttk.Button(t_del, text="Удалить", command=lambda: _run_safe(self._table_delete)).grid(
            row=1, column=0, pady=12, sticky=tk.W
        )

    def _tab_bookings(self, parent: ttk.Notebook) -> None:
        outer = ttk.Frame(parent, padding=4)
        parent.add(outer, text="Бронирования")
        snb = ttk.Notebook(outer)
        snb.pack(fill=tk.BOTH, expand=True)

        hint = (
            "Дата/время: ГГГГ-ММ-ДД ЧЧ:ММ или ДД.ММ.ГГГГ ЧЧ:ММ"
        )

        t_create = ttk.Frame(snb, padding=10)
        snb.add(t_create, text="Создать")
        ttk.Label(t_create, text=hint, foreground="gray").grid(row=0, column=0, columnspan=2, sticky=tk.W)
        self.b_c_user = self._entry_row(t_create, "ID пользователя", 1)
        self.b_c_table = self._entry_row(t_create, "ID стола", 2)
        self.b_c_start = self._entry_row(t_create, "Начало", 3)
        self.b_c_end = self._entry_row(t_create, "Конец", 4)
        self.b_c_party = self._entry_row(t_create, "Гостей", 5)
        self.b_c_status = self._combo_row(
            t_create,
            "Статус",
            6,
            [s.value for s in BookingStatus],
            BookingStatus.PENDING.value,
        )
        self.b_c_notes = self._entry_row(t_create, "Заметки", 7)
        ttk.Button(
            t_create,
            text="Проверить доступность стола",
            command=lambda: _run_safe(self._booking_check_availability_create),
        ).grid(row=8, column=0, pady=(8, 0), sticky=tk.W)
        ttk.Button(
            t_create, text="Создать бронирование", command=lambda: _run_safe(self._booking_create)
        ).grid(row=9, column=0, pady=12, sticky=tk.W)

        t_get = ttk.Frame(snb, padding=10)
        snb.add(t_get, text="Найти")
        self.b_g_id = self._entry_row(t_get, "ID брони", 0)
        self.b_g_out = tk.Text(t_get, height=10, width=72, state=tk.DISABLED, wrap=tk.WORD)
        self.b_g_out.grid(row=1, column=0, columnspan=2, sticky=tk.NSEW, pady=8)
        t_get.rowconfigure(1, weight=1)
        t_get.columnconfigure(0, weight=1)
        ttk.Button(t_get, text="Загрузить", command=lambda: _run_safe(self._booking_get)).grid(
            row=2, column=0, sticky=tk.W
        )

        t_list = ttk.Frame(snb, padding=10)
        snb.add(t_list, text="Список")
        self.b_l_user = self._entry_row(t_list, "Фильтр user_id", 0)
        self.b_l_table = self._entry_row(t_list, "Фильтр restaurant_table_id", 1)
        self.b_l_status = self._combo_row(
            t_list,
            "Фильтр статус",
            2,
            ["", *[s.value for s in BookingStatus]],
            "",
        )
        self.b_l_limit = self._entry_row(t_list, "Лимит", 3)
        self.b_l_offset = self._entry_row(t_list, "Смещение", 4)
        cols = ("id", "user_id", "table_id", "start", "end", "party", "status")
        self.b_tree = ttk.Treeview(t_list, columns=cols, show="headings", height=11)
        for c, w in zip(cols, (36, 60, 60, 130, 130, 50, 90)):
            self.b_tree.heading(c, text=c)
            self.b_tree.column(c, width=w)
        ys = ttk.Scrollbar(t_list, orient=tk.VERTICAL, command=self.b_tree.yview)
        self.b_tree.configure(yscrollcommand=ys.set)
        self.b_tree.grid(row=5, column=0, sticky=tk.NSEW)
        ys.grid(row=5, column=1, sticky=tk.NS)
        t_list.rowconfigure(5, weight=1)
        t_list.columnconfigure(0, weight=1)
        ttk.Button(t_list, text="Обновить список", command=lambda: _run_safe(self._booking_list)).grid(
            row=6, column=0, pady=8, sticky=tk.W
        )

        t_up = ttk.Frame(snb, padding=10)
        snb.add(t_up, text="Изменить")
        ttk.Label(t_up, text=hint, foreground="gray").grid(row=0, column=0, columnspan=2, sticky=tk.W)
        self.b_u_id = self._entry_row(t_up, "ID брони", 1)
        ttk.Button(t_up, text="Загрузить в форму", command=lambda: _run_safe(self._booking_load_for_update)).grid(
            row=2, column=0, columnspan=2, sticky=tk.W, pady=4
        )
        self.b_u_user = self._entry_row(t_up, "ID пользователя", 3)
        self.b_u_table = self._entry_row(t_up, "ID стола", 4)
        self.b_u_start = self._entry_row(t_up, "Начало", 5)
        self.b_u_end = self._entry_row(t_up, "Конец", 6)
        self.b_u_party = self._entry_row(t_up, "Гостей", 7)
        self.b_u_status = self._combo_row(
            t_up, "Статус", 8, [s.value for s in BookingStatus], BookingStatus.PENDING.value
        )
        self.b_u_notes = self._entry_row(t_up, "Заметки", 9)
        ttk.Button(
            t_up,
            text="Проверить доступность стола",
            command=lambda: _run_safe(self._booking_check_availability_update),
        ).grid(row=10, column=0, pady=(8, 0), sticky=tk.W)
        ttk.Button(t_up, text="Сохранить", command=lambda: _run_safe(self._booking_update)).grid(
            row=11, column=0, pady=12, sticky=tk.W
        )

        t_del = ttk.Frame(snb, padding=10)
        snb.add(t_del, text="Удалить")
        self.b_d_id = self._entry_row(t_del, "ID брони", 0)
        ttk.Button(t_del, text="Удалить", command=lambda: _run_safe(self._booking_delete)).grid(
            row=1, column=0, pady=12, sticky=tk.W
        )

    @staticmethod
    def _entry_row(parent: ttk.Frame, label: str, row: int, show: str = "") -> ttk.Entry:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W, pady=2)
        e = ttk.Entry(parent, width=48, show=show)
        e.grid(row=row, column=1, sticky=tk.EW, pady=2)
        parent.columnconfigure(1, weight=1)
        return e

    @staticmethod
    def _combo_row(
        parent: ttk.Frame, label: str, row: int, values: list[str], default: str
    ) -> ttk.Combobox:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W, pady=2)
        cb = ttk.Combobox(parent, width=45, values=values, state="readonly")
        cb.set(default)
        cb.grid(row=row, column=1, sticky=tk.EW, pady=2)
        parent.columnconfigure(1, weight=1)
        return cb

    @staticmethod
    def _set_text(widget: tk.Text, content: str) -> None:
        widget.configure(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, content)
        widget.configure(state=tk.DISABLED)

    # --- User handlers ---

    def _user_create(self) -> None:
        phone = self.u_c_phone.get().strip() or None
        u = User(
            email=self.u_c_email.get().strip(),
            password_hash=_hash_password(self.u_c_password.get()),
            full_name=self.u_c_full_name.get().strip(),
            phone=phone,
            role=UserRole(self.u_c_role.get()),
            is_active=self.u_c_active.get(),
        )
        new_id = backend.create_user(u)
        messagebox.showinfo("Создано", f"ID пользователя: {new_id}")

    def _user_get(self) -> None:
        uid = int(self.u_g_id.get().strip())
        u = backend.get_user_by_id(uid)
        if not u:
            self._set_text(self.u_g_out, "Не найдено.")
            return
        text = (
            f"id: {u.id}\nemail: {u.email}\nfull_name: {u.full_name}\n"
            f"phone: {u.phone}\nrole: {u.role.value}\nis_active: {u.is_active}\n"
            f"created_at: {u.created_at}\nupdated_at: {u.updated_at}"
        )
        self._set_text(self.u_g_out, text)

    def _user_list(self) -> None:
        filters: dict[str, Any] = {}
        em = self.u_l_email.get().strip()
        if em:
            filters["email"] = em
        role = self.u_l_role.get().strip()
        if role:
            filters["role"] = role
        fl = filters or None
        limit = _optional_int(self.u_l_limit.get())
        offset = _optional_int(self.u_l_offset.get())
        rows = backend.list_users(filters=fl, limit=limit, offset=offset)
        for i in self.u_tree.get_children():
            self.u_tree.delete(i)
        for u in rows:
            self.u_tree.insert(
                "",
                tk.END,
                values=(
                    u.id,
                    u.email,
                    u.full_name,
                    u.phone or "",
                    u.role.value,
                    u.is_active,
                ),
            )

    def _user_load_for_update(self) -> None:
        uid = int(self.u_u_id.get().strip())
        u = backend.get_user_by_id(uid)
        if not u:
            messagebox.showwarning("Нет данных", "Пользователь не найден.")
            return
        self.u_u_email.delete(0, tk.END)
        self.u_u_email.insert(0, u.email)
        self.u_u_password.delete(0, tk.END)
        self.u_u_full_name.delete(0, tk.END)
        self.u_u_full_name.insert(0, u.full_name)
        self.u_u_phone.delete(0, tk.END)
        if u.phone:
            self.u_u_phone.insert(0, u.phone)
        self.u_u_role.set(u.role.value)
        self.u_u_active.set(u.is_active)

    def _user_update(self) -> None:
        uid = int(self.u_u_id.get().strip())
        pwd = self.u_u_password.get()
        if not pwd.strip():
            old = backend.get_user_by_id(uid)
            if not old:
                raise ValueError("Пользователь не найден.")
            password_hash = old.password_hash
        else:
            password_hash = _hash_password(pwd)
        phone = self.u_u_phone.get().strip() or None
        u = User(
            email=self.u_u_email.get().strip(),
            password_hash=password_hash,
            full_name=self.u_u_full_name.get().strip(),
            phone=phone,
            role=UserRole(self.u_u_role.get()),
            is_active=self.u_u_active.get(),
        )
        n = backend.update_user(uid, u)
        messagebox.showinfo("Готово", f"Обновлено строк: {n}")

    def _user_delete(self) -> None:
        uid = int(self.u_d_id.get().strip())
        if not messagebox.askyesno("Подтверждение", f"Удалить пользователя id={uid}?"):
            return
        n = backend.delete_user(uid)
        messagebox.showinfo("Готово", f"Удалено строк: {n}")

    # --- Table handlers ---

    def _table_create(self) -> None:
        notes = self.t_c_notes.get().strip() or None
        t = RestaurantTable(
            label=self.t_c_label.get().strip(),
            capacity=int(self.t_c_capacity.get().strip()),
            zone=TableZone(self.t_c_zone.get()),
            is_active=self.t_c_active.get(),
            notes=notes,
        )
        new_id = backend.create_restaurant_table(t)
        messagebox.showinfo("Создано", f"ID стола: {new_id}")

    def _table_get(self) -> None:
        tid = int(self.t_g_id.get().strip())
        t = backend.get_restaurant_table_by_id(tid)
        if not t:
            self._set_text(self.t_g_out, "Не найдено.")
            return
        text = (
            f"id: {t.id}\nlabel: {t.label}\ncapacity: {t.capacity}\nzone: {t.zone.value}\n"
            f"is_active: {t.is_active}\nnotes: {t.notes}\n"
            f"created_at: {t.created_at}\nupdated_at: {t.updated_at}"
        )
        self._set_text(self.t_g_out, text)

    def _table_list(self) -> None:
        filters: dict[str, Any] = {}
        z = self.t_l_zone.get().strip()
        if z:
            filters["zone"] = z
        fl = filters or None
        limit = _optional_int(self.t_l_limit.get())
        offset = _optional_int(self.t_l_offset.get())
        rows = backend.list_restaurant_tables(filters=fl, limit=limit, offset=offset)
        for i in self.t_tree.get_children():
            self.t_tree.delete(i)
        for t in rows:
            self.t_tree.insert(
                "",
                tk.END,
                values=(
                    t.id,
                    t.label,
                    t.capacity,
                    t.zone.value,
                    t.is_active,
                    (t.notes or "")[:80],
                ),
            )

    def _table_load_for_update(self) -> None:
        tid = int(self.t_u_id.get().strip())
        t = backend.get_restaurant_table_by_id(tid)
        if not t:
            messagebox.showwarning("Нет данных", "Стол не найден.")
            return
        self.t_u_label.delete(0, tk.END)
        self.t_u_label.insert(0, t.label)
        self.t_u_capacity.delete(0, tk.END)
        self.t_u_capacity.insert(0, str(t.capacity))
        self.t_u_zone.set(t.zone.value)
        self.t_u_active.set(t.is_active)
        self.t_u_notes.delete(0, tk.END)
        if t.notes:
            self.t_u_notes.insert(0, t.notes)

    def _table_update(self) -> None:
        tid = int(self.t_u_id.get().strip())
        notes = self.t_u_notes.get().strip() or None
        t = RestaurantTable(
            label=self.t_u_label.get().strip(),
            capacity=int(self.t_u_capacity.get().strip()),
            zone=TableZone(self.t_u_zone.get()),
            is_active=self.t_u_active.get(),
            notes=notes,
        )
        n = backend.update_restaurant_table(tid, t)
        messagebox.showinfo("Готово", f"Обновлено строк: {n}")

    def _table_delete(self) -> None:
        tid = int(self.t_d_id.get().strip())
        if not messagebox.askyesno("Подтверждение", f"Удалить стол id={tid}?"):
            return
        n = backend.delete_restaurant_table(tid)
        messagebox.showinfo("Готово", f"Удалено строк: {n}")

    # --- Booking handlers ---

    def _booking_create(self) -> None:
        notes = self.b_c_notes.get().strip() or None
        b = Booking(
            user_id=int(self.b_c_user.get().strip()),
            restaurant_table_id=int(self.b_c_table.get().strip()),
            start_at=_parse_dt(self.b_c_start.get()),
            end_at=_parse_dt(self.b_c_end.get()),
            party_size=int(self.b_c_party.get().strip()),
            status=BookingStatus(self.b_c_status.get()),
            notes=notes,
        )
        new_id = backend.create_booking(b)
        messagebox.showinfo("Создано", f"ID бронирования: {new_id}")

    def _booking_get(self) -> None:
        bid = int(self.b_g_id.get().strip())
        b = backend.get_booking_by_id(bid)
        if not b:
            self._set_text(self.b_g_out, "Не найдено.")
            return
        text = (
            f"id: {b.id}\nuser_id: {b.user_id}\nrestaurant_table_id: {b.restaurant_table_id}\n"
            f"start_at: {b.start_at}\nend_at: {b.end_at}\nparty_size: {b.party_size}\n"
            f"status: {b.status.value}\nnotes: {b.notes}\n"
            f"created_at: {b.created_at}\nupdated_at: {b.updated_at}"
        )
        self._set_text(self.b_g_out, text)

    def _booking_list(self) -> None:
        filters: dict[str, Any] = {}
        u = self.b_l_user.get().strip()
        if u:
            filters["user_id"] = int(u)
        tid = self.b_l_table.get().strip()
        if tid:
            filters["restaurant_table_id"] = int(tid)
        st = self.b_l_status.get().strip()
        if st:
            filters["status"] = st
        fl = filters or None
        limit = _optional_int(self.b_l_limit.get())
        offset = _optional_int(self.b_l_offset.get())
        rows = backend.list_bookings(filters=fl, limit=limit, offset=offset)
        for i in self.b_tree.get_children():
            self.b_tree.delete(i)
        for b in rows:
            self.b_tree.insert(
                "",
                tk.END,
                values=(
                    b.id,
                    b.user_id,
                    b.restaurant_table_id,
                    str(b.start_at)[:19],
                    str(b.end_at)[:19],
                    b.party_size,
                    b.status.value,
                ),
            )

    def _booking_load_for_update(self) -> None:
        bid = int(self.b_u_id.get().strip())
        b = backend.get_booking_by_id(bid)
        if not b:
            messagebox.showwarning("Нет данных", "Бронирование не найдено.")
            return
        self.b_u_user.delete(0, tk.END)
        self.b_u_user.insert(0, str(b.user_id))
        self.b_u_table.delete(0, tk.END)
        self.b_u_table.insert(0, str(b.restaurant_table_id))
        self.b_u_start.delete(0, tk.END)
        self.b_u_start.insert(0, b.start_at.strftime("%Y-%m-%d %H:%M"))
        self.b_u_end.delete(0, tk.END)
        self.b_u_end.insert(0, b.end_at.strftime("%Y-%m-%d %H:%M"))
        self.b_u_party.delete(0, tk.END)
        self.b_u_party.insert(0, str(b.party_size))
        self.b_u_status.set(b.status.value)
        self.b_u_notes.delete(0, tk.END)
        if b.notes:
            self.b_u_notes.insert(0, b.notes)

    def _booking_update(self) -> None:
        bid = int(self.b_u_id.get().strip())
        notes = self.b_u_notes.get().strip() or None
        b = Booking(
            user_id=int(self.b_u_user.get().strip()),
            restaurant_table_id=int(self.b_u_table.get().strip()),
            start_at=_parse_dt(self.b_u_start.get()),
            end_at=_parse_dt(self.b_u_end.get()),
            party_size=int(self.b_u_party.get().strip()),
            status=BookingStatus(self.b_u_status.get()),
            notes=notes,
        )
        n = backend.update_booking(bid, b)
        messagebox.showinfo("Готово", f"Обновлено строк: {n}")

    @staticmethod
    def _booking_availability_message(
        table_id: int,
        ok: bool,
        conflicts: list[Booking],
    ) -> str:
        if ok:
            return (
                f"Стол id={table_id} свободен в выбранный интервал "
                "(нет активных пересекающихся броней; отменённые не учитываются)."
            )
        lines = [
            f"Стол id={table_id} занят: найдены пересечения по времени:\n",
        ]
        for c in conflicts:
            lines.append(
                f"  • бронь id={c.id}: {c.start_at} — {c.end_at}, статус {c.status.value}\n"
            )
        return "".join(lines)

    def _booking_check_availability_create(self) -> None:
        table_id = int(self.b_c_table.get().strip())
        start_at = _parse_dt(self.b_c_start.get())
        end_at = _parse_dt(self.b_c_end.get())
        ok, conflicts = backend.is_restaurant_table_available(table_id, start_at, end_at)
        msg = self._booking_availability_message(table_id, ok, conflicts)
        if ok:
            messagebox.showinfo("Доступность стола", msg)
        else:
            messagebox.showwarning("Доступность стола", msg)

    def _booking_check_availability_update(self) -> None:
        booking_id = int(self.b_u_id.get().strip())
        table_id = int(self.b_u_table.get().strip())
        start_at = _parse_dt(self.b_u_start.get())
        end_at = _parse_dt(self.b_u_end.get())
        ok, conflicts = backend.is_restaurant_table_available(
            table_id,
            start_at,
            end_at,
            exclude_booking_id=booking_id,
        )
        msg = self._booking_availability_message(table_id, ok, conflicts)
        if ok:
            messagebox.showinfo("Доступность стола", msg)
        else:
            messagebox.showwarning("Доступность стола", msg)

    def _booking_delete(self) -> None:
        bid = int(self.b_d_id.get().strip())
        if not messagebox.askyesno("Подтверждение", f"Удалить бронирование id={bid}?"):
            return
        n = backend.delete_booking(bid)
        messagebox.showinfo("Готово", f"Удалено строк: {n}")


def main() -> None:
    root = tk.Tk()
    BookingApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
