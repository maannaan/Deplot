"""
In-memory store for hackathon MVP.

Swap for SQLAlchemy repositories later without changing service interfaces.
"""

from __future__ import annotations

from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel

from app.models.aiops import Incident
from app.models.analysis import AnalysisSession
from app.models.deployment import Deployment

T = TypeVar("T", bound=BaseModel)


class InMemoryStore(Generic[T]):
    def __init__(self) -> None:
        self._items: dict[UUID, T] = {}

    def save(self, item: T) -> T:
        item_id = getattr(item, "id")
        self._items[item_id] = item
        return item

    def get(self, item_id: UUID) -> T | None:
        return self._items.get(item_id)

    def list_all(self) -> list[T]:
        return list(self._items.values())

    def delete(self, item_id: UUID) -> bool:
        return self._items.pop(item_id, None) is not None


session_store: InMemoryStore[AnalysisSession] = InMemoryStore()
deployment_store: InMemoryStore[Deployment] = InMemoryStore()
incident_store: InMemoryStore[Incident] = InMemoryStore()
