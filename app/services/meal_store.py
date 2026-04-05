from threading import Lock
from uuid import uuid4

from app.contracts.meal_log import MealLogCreate, MealLogEntry


class MealStore:
    def __init__(self) -> None:
        self._items: dict[str, MealLogEntry] = {}
        self._lock = Lock()

    def create(self, payload: MealLogCreate) -> MealLogEntry:
        with self._lock:
            item = MealLogEntry(id=str(uuid4()), **payload.model_dump())
            self._items[item.id] = item
            return item

    def list_items(self) -> list[MealLogEntry]:
        return list(self._items.values())

    def list_by_prefix_date(self, date_prefix: str) -> list[MealLogEntry]:
        return [item for item in self._items.values() if item.timestamp.startswith(date_prefix)]


meal_store = MealStore()
