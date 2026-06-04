import sqlite3
from uuid import uuid4

from app.contracts.meal_log import MealLogCreate, MealLogEntry
from app.db import connection

_COLUMNS = ("id", "name", "calories", "protein", "carbs", "fat", "fiber", "timestamp", "type")


def _row_to_entry(row: sqlite3.Row) -> MealLogEntry:
    return MealLogEntry(**{key: row[key] for key in _COLUMNS})


class MealStore:
    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path

    def create(self, user_id: str, payload: MealLogCreate) -> MealLogEntry:
        item = MealLogEntry(id=str(uuid4()), **payload.model_dump())
        with connection(self._db_path) as conn:
            conn.execute(
                "INSERT INTO meals"
                " (id, user_id, name, calories, protein, carbs, fat, fiber, timestamp, type)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (item.id, user_id, *(getattr(item, key) for key in _COLUMNS[1:])),
            )
        return item

    def list_items(self, user_id: str) -> list[MealLogEntry]:
        with connection(self._db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM meals WHERE user_id = ? ORDER BY rowid", (user_id,)
            ).fetchall()
        return [_row_to_entry(row) for row in rows]

    def list_by_prefix_date(self, user_id: str, date_prefix: str) -> list[MealLogEntry]:
        with connection(self._db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM meals WHERE user_id = ? AND timestamp LIKE ? ORDER BY rowid",
                (user_id, f"{date_prefix}%"),
            ).fetchall()
        return [_row_to_entry(row) for row in rows]


meal_store = MealStore()
