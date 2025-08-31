from __future__ import annotations
from pathlib import Path
from typing import List

from Domain.domains import Item
from Repository.item import ItemRepository


class ItemService:
    """High level operations for Item domain objects.

    This layer performs orchestration/validation before delegating to the
    repository.  For now the logic is thin but provides a clear extension
    point for future business rules.
    """

    def __init__(self, db_path: Path | str):
        self._repo = ItemRepository(str(db_path))

    # ------------------------------------------------------------------
    # Retrieval operations
    # ------------------------------------------------------------------
    def get_item(self, object_id: int) -> Item:
        """Return a single item from the database."""
        return self._repo.get(object_id)

    # Future expansion – e.g. listing items or searching – can be added here.

    # ------------------------------------------------------------------
    # Mutation operations
    # ------------------------------------------------------------------
    def save_item(self, item: Item) -> None:
        """Persist an item using the underlying repository."""
        self._repo.save(item)


# Placeholder for future NPCService so the GUI has an obvious insertion point.
class NPCService:
    """Service layer for NPC related operations (not yet implemented)."""

    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        # Implementation will mirror ItemService when NPC repositories exist.