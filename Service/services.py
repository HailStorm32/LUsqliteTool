from __future__ import annotations
from pathlib import Path
from typing import Any, Callable, Optional, Type, TypeVar

from Domain.domains import (
    Item,
    ObjectTypes,
    ItemComponent,
    RenderComponent,
    ObjectSkills,
    ObjectSkillRow,
    INT_32_MAX,
)
from Repository.item import ItemRepository
from Repository.exceptions import *

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

    # ------------------------------
    # Component id helpers (exposed for UI orchestration)
    # ------------------------------
    def generate_new_component_id(self, preferred_id: int, table: str) -> int:
        """Generate a new component id, preferring the object's id when possible.

        Delegates to the repository implementation. Public so the GUI can
        request ids without reaching into repository internals.
        """
        if self._repo is None:
            raise RuntimeError("Repository not configured for this service")
        return self._repo.generate_new_component_id(preferred_id, table)


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

        # Generate component ids: try to use object id, else next available in each table
        item_comp_id = self._repo.generate_new_component_id(new_id, "ItemComponent")
        render_comp_id = self._repo.generate_new_component_id(new_id, "RenderComponent")

        # Construct domain object and components with defaults
        item = Item(id=new_id, type=ObjectTypes.ITEM)
        # Mark base object dirty so it inserts/updates
        item.dirty = True

        # Attach default RenderComponent and ItemComponent; mark dirty so they are saved
        render = RenderComponent(id=render_comp_id)
        render.dirty = True
        item_comp = ItemComponent(id=item_comp_id)
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

    def duplicate_item(self, source_object_id: int, target_object_id: int | None = None) -> Item:
        """Duplicate an existing item (and its components) to a new object id.

        - Copies GameObject fields (name, description, etc.)
        - Copies present components and keeps all values the same
        - Assigns NEW component ids for the duplicate using the rule:
          try object id first; if already used in that component table, pick the next free id
        - Duplicates skills so their objectTemplate points to the new id

        If target_object_id is None, a new id is generated. When provided, the number
        must be a positive integer and not already present in Objects.
        """
        if self._repo is None:
            raise RuntimeError("Repository not configured for this service")

        # Validate and fetch the source item
        src_id = self._require_positive_int(source_object_id, "Source Object ID")
        try:
            src = self._repo.get(src_id)
        except NotFoundError:
            raise ValueError(f"Source item {src_id} does not exist")

        # Choose/validate destination id (reuse same rules as create)
        if target_object_id is not None:
            if not isinstance(target_object_id, int) or target_object_id <= 0:
                raise ValueError("Target Object ID must be a positive unsigned integer")
            # Ensure destination does not already exist
            try:
                existing = self._repo.get(target_object_id)
                if existing is not None:
                    raise ValueError(f"Target Object ID {target_object_id} already exists")
            except NotFoundError:
                pass
            new_id = target_object_id
        else:
            new_id = self._repo.generate_new_id()

        # Pre-compute component ids following requested logic
        new_item_comp_id = self._repo.generate_new_component_id(new_id, "ItemComponent")
        new_render_comp_id = self._repo.generate_new_component_id(new_id, "RenderComponent")

        # Build new domain object, copying base object fields
        dup = Item(id=new_id, type=ObjectTypes.ITEM, name=src.name)
        # Copy remaining GameObject attributes (explicit for clarity/maintainability)
        dup.placeable = bool(getattr(src, 'placeable', False))
        dup.description = getattr(src, 'description', '')
        dup.localize = getattr(src, 'localize', True)
        dup.npc_template_id = getattr(src, 'npc_template_id', None)
        dup.display_name = getattr(src, 'display_name', None)
        dup.interaction_distance = getattr(src, 'interaction_distance', None)
        dup.nametag = getattr(src, 'nametag', False)
        dup.internal_notes = getattr(src, 'internal_notes', None)
        dup.loc_status = getattr(src, 'loc_status', None)
        dup.gate_version = getattr(src, 'gate_version', None)
        dup.hq_valid = getattr(src, 'hq_valid', True)
        dup.dirty = True  # ensure Objects row is written

        # Duplicate components present on the source (assign fresh ids)
        comps: dict[str, Any] = {}

        # Helper: copy dataclass attributes by name (excluding 'id'/'dirty')
        def _copy_fields(src_obj, dst_obj):
            for attr in vars(src_obj).keys():
                if attr in ("id", "dirty"):
                    continue
                try:
                    setattr(dst_obj, attr, getattr(src_obj, attr))
                except Exception:
                    # Best-effort; skip attributes that aren't compatible
                    pass

        src_item_comp = getattr(src.components, 'get', lambda _x: None)('ItemComponent')
        if src_item_comp is not None:
            new_ic = ItemComponent(id=new_item_comp_id)
            _copy_fields(src_item_comp, new_ic)
            new_ic.id = new_item_comp_id
            new_ic.dirty = True
            comps['ItemComponent'] = new_ic

        src_render = getattr(src.components, 'get', lambda _x: None)('RenderComponent')
        if src_render is not None:
            new_rc = RenderComponent(id=new_render_comp_id)
            _copy_fields(src_render, new_rc)
            new_rc.id = new_render_comp_id
            new_rc.dirty = True
            comps['RenderComponent'] = new_rc

        src_skills = getattr(src.components, 'get', lambda _x: None)('ObjectSkill')
        if src_skills is not None and hasattr(src_skills, 'skills'):
            # Duplicate skills rows, retargeting object_Template to the new id
            new_rows: list[ObjectSkillRow] = []
            for row in getattr(src_skills, 'skills', []) or []:
                try:
                    new_rows.append(
                        ObjectSkillRow(
                            object_Template=new_id,
                            skill_id=getattr(row, 'skill_id', None),
                            cast_on_type=getattr(row, 'cast_on_type', None),
                            ai_combat_weight=getattr(row, 'ai_combat_weight', None),
                        )
                    )
                except Exception:
                    # Skip malformed rows
                    pass
            if new_rows:
                new_skills = ObjectSkills(skills=new_rows, zero_component_id=getattr(src_skills, 'zero_component_id', True))
                new_skills.dirty = True
                comps['ObjectSkill'] = new_skills

        dup.components = comps

        # Persist new item
        self._repo.save(dup)
        # Reload the freshly saved duplicate and return it
        saved = self._repo.get(new_id)
        return saved or dup

    # ------------------------------------------------------------------
    # Deletion operations
    # ------------------------------------------------------------------
    def delete_item(self, object_id: int) -> None:
        """Permanently delete an item and all of its components from the database."""
        self.delete_object(object_id)

    # ------------------------------------------------------------------
    # Component add helpers (used by GUI context menu)
    # ------------------------------------------------------------------
    def add_item_component(self, item: Item) -> ItemComponent:
        """Attach a new ItemComponent to the given item (no-op if already present).

        Creates a fresh component id using the requested policy, marks it
        dirty so Save will persist, and returns the component reference.
        """
        if item.components.get("ItemComponent") is not None:
            return item.components["ItemComponent"]  # type: ignore[index]
        comp_id = self.generate_new_component_id(item.object_id, "ItemComponent")
        comp = ItemComponent(id=comp_id)
        comp.dirty = True
        item.components["ItemComponent"] = comp
        return comp

    def add_render_component(self, item: Item) -> RenderComponent:
        """Attach a new RenderComponent to the given item (no-op if already present)."""
        if item.components.get("RenderComponent") is not None:
            return item.components["RenderComponent"]  # type: ignore[index]
        comp_id = self.generate_new_component_id(item.object_id, "RenderComponent")
        comp = RenderComponent(id=comp_id)
        comp.dirty = True
        item.components["RenderComponent"] = comp
        return comp

    def ensure_skills_component(self, item: Item) -> ObjectSkills:
        """Ensure the item has an ObjectSkills component; create if missing.

        Returns the ObjectSkills component. Newly created components are marked
        dirty so Save will persist a registry entry and any rows added.
        """
        skills = item.components.get("ObjectSkill")
        if isinstance(skills, ObjectSkills):
            return skills
        skills = ObjectSkills(skills=[], zero_component_id=True)
        skills.dirty = True
        item.components["ObjectSkill"] = skills
        return skills

    def _next_blank_skill_id(self, used: set[int]) -> int:
        """Pick a placeholder skill_id not already in use.

        Start from INT_32_MAX and decrement until free, but stop at 1.
        This avoids colliding when the user adds multiple blank rows.
        """
        candidate = INT_32_MAX
        while candidate in used and candidate > 1:
            candidate -= 1
        return candidate

    def make_blank_skill_row(self, object_id: int, used_ids: Optional[set[int]] = None) -> ObjectSkillRow:
        """Create a blank ObjectSkillRow for the given object id with a unique placeholder id."""
        used_ids = used_ids or set()
        sid = self._next_blank_skill_id(used_ids)
        return ObjectSkillRow(
            object_Template=object_id,
            skill_id=sid,
            cast_on_type=1,
            ai_combat_weight=None,
        )

    def add_blank_skill(self, item: Item) -> ObjectSkillRow:
        """Append a blank skill row to the item's ObjectSkills component (creating it if absent)."""
        skills = self.ensure_skills_component(item)
        used = {getattr(r, "skill_id", 0) for r in (skills.skills or [])}
        row = self.make_blank_skill_row(item.object_id, used)
        skills.skills.append(row)
        # Mark skills dirty so save will persist new row(s)
        skills.dirty = True
        return row


# Placeholder for future NPCService so the GUI has an obvious insertion point.
class NPCService(BaseService):
    """Service layer for NPC related operations (not yet implemented)."""

    def __init__(self, db_path: Path | str):
        # No NPCRepository yet; wire up base without a repo for now.
        # When an NPCRepository is added, call: super().__init__(db_path, NPCRepository)
        super().__init__(db_path, repo_cls=None)
        self.db_path = Path(db_path)
        # Implementation will mirror ItemService when NPC repositories exist.