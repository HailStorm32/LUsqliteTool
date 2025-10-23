from __future__ import annotations
from pathlib import Path
from typing import Any, Callable, Optional, Type, TypeVar

from Domain.domains import Item, ObjectTypes, ItemComponent, RenderComponent
from Repository.item import ItemRepository
from Repository.exceptions import *


# Generic type for domain objects returned by repositories
T = TypeVar("T")


class BaseService:
    """Common service-layer utilities shared by Item and NPC services.

    Responsibilities:
    - Construct the underlying repository (_repo).
    - Provide shared validation and thin orchestration around repository calls.
    - Centralize common component deletion helpers to avoid duplication.

    Subclasses should pass their repository class into the constructor:

        class ItemService(BaseService):
            def __init__(self, db_path: Path | str):
                super().__init__(db_path, ItemRepository)

    Notes for future NPC implementation:
    - NPCService can follow the same pattern (inject NPCRepository).
    - Any methods that are domain-agnostic (get/save/delete component helpers)
      should live here so we don't repeat code.
    """

    def __init__(self, db_path: Path | str, repo_cls: Optional[Type[Any]]):
        # Allow a None repo_cls for placeholder services (e.g., NPC until repo exists)
        self._repo = repo_cls(str(db_path)) if repo_cls is not None else None

    # ------------------------------
    # Validation helpers
    # ------------------------------
    def _require_positive_int(self, value: Any, name: str) -> int:
        """Ensure value is a positive integer; raise ValueError otherwise."""
        try:
            iv = int(value)
        except Exception:
            raise ValueError(f"{name} must be a positive unsigned integer")
        if iv <= 0:
            raise ValueError(f"{name} must be a positive unsigned integer")
        return iv

    # ------------------------------
    # Generic CRUD pass-throughs
    # ------------------------------
    def get(self, object_id: int) -> Any | None:
        """Generic safe get with basic validation and NotFound handling.

        Returns the domain object or None if not found/invalid.
        """
        oid = self._require_positive_int(object_id, "Object ID")
        if self._repo is None:
            raise RuntimeError("Repository not configured for this service")
        try:
            return self._repo.get(oid)
        except NotFoundError:
            return None
        except Exception as e:
            print(f"Error retrieving object {oid}: {e}")
            return None

    def save(self, obj: Any) -> None:
        """Persist a domain object using the underlying repository."""
        if self._repo is None:
            raise RuntimeError("Repository not configured for this service")
        self._repo.save(obj)

    def delete_object(self, object_id: int) -> None:
        """Delete an object and its related data via the repository base delete path."""
        oid = self._require_positive_int(object_id, "Object ID")
        if self._repo is None:
            raise RuntimeError("Repository not configured for this service")
        # Repositories expose delete() which delegates to base.delete_object
        self._repo.delete(oid)

    # ------------------------------
    # Common component deletion helpers
    # ------------------------------
    def delete_item_component(self, component_id: int) -> None:
        """Permanently delete an ItemComponent and its registry references."""
        cid = self._require_positive_int(component_id, "Component ID")
        if self._repo is None:
            raise RuntimeError("Repository not configured for this service")
        self._repo.delete_item_component(cid)

    def delete_render_component(self, component_id: int) -> None:
        """Permanently delete a RenderComponent and its registry references."""
        cid = self._require_positive_int(component_id, "Component ID")
        if self._repo is None:
            raise RuntimeError("Repository not configured for this service")
        self._repo.delete_render_component(cid)

    def delete_skill_component(self, object_id: int) -> None:
        """Permanently delete all skills for an object and remove the registry entry."""
        oid = self._require_positive_int(object_id, "Object ID")
        if self._repo is None:
            raise RuntimeError("Repository not configured for this service")
        self._repo.delete_skill_component(oid)


class ItemService(BaseService):
    """High level operations for Item domain objects.

    This layer performs orchestration/validation before delegating to the
    repository.  For now the logic is thin but provides a clear extension
    point for future business rules.
    """

    def __init__(self, db_path: Path | str):
        # BaseService wires up the repository so we don't repeat that here
        super().__init__(db_path, ItemRepository)

    # ------------------------------------------------------------------
    # Retrieval operations
    # ------------------------------------------------------------------
    def get_item(self, object_id: int) -> Item:
        """Return a single item from the database."""
        return self.get(object_id)

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
        self.save(item)

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

    # ------------------------------------------------------------------
    # Deletion operations
    # ------------------------------------------------------------------
    def delete_item(self, object_id: int) -> None:
        """Permanently delete an item and all of its components from the database."""
        self.delete_object(object_id)


# Placeholder for future NPCService so the GUI has an obvious insertion point.
class NPCService(BaseService):
    """Service layer for NPC related operations (not yet implemented)."""

    def __init__(self, db_path: Path | str):
        # No NPCRepository yet; wire up base without a repo for now.
        # When an NPCRepository is added, call: super().__init__(db_path, NPCRepository)
        super().__init__(db_path, repo_cls=None)
        self.db_path = Path(db_path)
        # Implementation will mirror ItemService when NPC repositories exist.