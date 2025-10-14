from __future__ import annotations
from pathlib import Path
from typing import List

from Domain.domains import Item, ObjectTypes, ItemComponent, RenderComponent
from Repository.item import ItemRepository
from Repository.exceptions import *


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
        if object_id <= 0:
            print(f"Invalid object ID: {object_id}")
            return None

        try:
            item = self._repo.get(object_id)

            return item

        except NotFoundError as e:
            return None

        except Exception as e:
            print(f"Error retrieving item {object_id}: {e}")
            return None

    def list_items(self, limit: int | None = None) -> list[dict[str, int | str]]:
        """
        Return a list of item IDs and their name from the database, optionally limited in number.

        Ex:
        [
            {'id': 20007, 'name': 'Health Potion'},
            {'id': 20008, 'name': 'Mana Potion'},
            ...
        ]
        """
        try:
           item_list = self._repo.list_items(limit)

        except Exception as e:
            print(f"Error listing item IDs: {e}")
            return []

        return item_list

    # Future expansion – e.g. listing items or searching – can be added here.

    # ------------------------------------------------------------------
    # Mutation operations
    # ------------------------------------------------------------------
    def save_item(self, item: Item) -> None:
        """Persist an item using the underlying repository."""
        self._repo.save(item)

    # ------------------------------------------------------------------
    # Creation operations
    # ------------------------------------------------------------------
    def create_default_item(self, object_id: int | None = None) -> Item:
        """Create a new Item with sensible defaults and persist it.

        The new item includes:
        - GameObject (Objects table) base row
        - RenderComponent with default values
        - ItemComponent with default values
        - No skills by default

        Returns the created Item domain object (freshly saved).
        """
        # Determine id: use caller-provided if valid, otherwise generate a new one
        if object_id is not None:
            if not isinstance(object_id, int) or object_id <= 0:
                raise ValueError("Object ID must be a positive unsigned integer")
            # Ensure it doesn't already exist
            try:
                _existing = self._repo.get(object_id)
                if _existing is not None:
                    raise ValueError(f"Object ID {object_id} already exists")
            except NotFoundError:
                # Not found -> OK to use
                pass
            new_id = object_id
        else:
            new_id = self._repo.generate_new_id()

        # Construct domain object and components with defaults
        item = Item(id=new_id, type=ObjectTypes.ITEM)
        # Mark base object dirty so it inserts/updates
        item.dirty = True

        # Attach default RenderComponent and ItemComponent; mark dirty so they are saved
        render = RenderComponent(id=new_id)
        render.dirty = True
        item_comp = ItemComponent(id=new_id)
        item_comp.dirty = True
        item.components = {
            "RenderComponent": render,
            "ItemComponent": item_comp,
        }

        # Persist via repository (single transaction inside repo)
        self._repo.save(item)

        # Reload to ensure any repo-side normalization is reflected (optional but safer)
        saved = self._repo.get(new_id)
        return saved or item


# Placeholder for future NPCService so the GUI has an obvious insertion point.
class NPCService:
    """Service layer for NPC related operations (not yet implemented)."""

    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        # Implementation will mirror ItemService when NPC repositories exist.