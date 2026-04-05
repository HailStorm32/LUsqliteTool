from __future__ import annotations
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable, Optional, Type

import logging
from metadata import component_field_metadata
from Domain.domains import (
    CurrencyTableRow,
    DestructibleComponent,
    InventoryComponentRow,
    Item,
    ItemComponent,
    LootMatrixIndexRow,
    LootMatrixRow,
    LootTableRow,
    LootTableIndexRow,
    MinifigComponent,
    MissionEmailRow,
    MissionNPCComponentRow,
    MissionRow,
    MissionTaskRow,
    MissionTextRow,
    NPC,
    ObjectSkills,
    ObjectSkillRow,
    ObjectTypes,
    PhysicsComponent,
    RenderComponent,
    RowCollection,
    ScriptComponent,
    INT_32_MAX,
    VendorComponent,
)
from Repository.item import ItemRepository
from Repository.npc import NPCRepository
from Repository.exceptions import *

log = logging.getLogger(__name__)

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
        except Exception:
            # Capture full traceback for post-mortem analysis
            log.exception("Error retrieving object %s", oid)
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

    def delete_component(
        self,
        component_key: str,
        component_id: int | None = None,
        object_id: int | None = None,
    ) -> None:
        """Delete a component using the repository's generic API when available."""
        if self._repo is None:
            raise RuntimeError("Repository not configured for this service")
        if hasattr(self._repo, "delete_component"):
            self._repo.delete_component(component_key, component_id=component_id, object_id=object_id)
            return
        if component_key == "ItemComponent" and component_id is not None:
            self.delete_item_component(component_id)
            return
        if component_key == "RenderComponent" and component_id is not None:
            self.delete_render_component(component_id)
            return
        if component_key == "ObjectSkill" and object_id is not None:
            self.delete_skill_component(object_id)
            return
        raise ValueError(f"Unsupported component delete key: {component_key}")

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

    def get_lookup_options(self, lookup_spec: Any) -> list[dict[str, Any]]:
        """Return lookup rows used by UI dropdowns, when supported by the repository."""
        if self._repo is None:
            raise RuntimeError("Repository not configured for this service")
        if hasattr(self._repo, "get_lookup_options"):
            return self._repo.get_lookup_options(lookup_spec)
        return []

    def _get_metadata_defaults(
        self,
        metadata_key: str,
        *,
        profile: str | None = None,
    ) -> dict[str, Any]:
        defaults: dict[str, Any] = {}
        for field_name, meta in component_field_metadata.get(metadata_key, {}).items():
            if "default" not in meta:
                continue
            value = meta.get("default")
            if isinstance(value, dict):
                value = value.get(profile)
            if value is None:
                continue
            defaults[field_name] = deepcopy(value)
        return defaults

    def _apply_metadata_defaults(self, target: Any, metadata_key: str, *, profile: str | None = None) -> None:
        for field_name, value in self._get_metadata_defaults(metadata_key, profile=profile).items():
            setattr(target, field_name, value)

    def _build_component_with_metadata_defaults(
        self,
        component_cls: Type[Any],
        metadata_key: str,
        *,
        profile: str | None = None,
        **overrides: Any,
    ) -> Any:
        values = self._get_metadata_defaults(metadata_key, profile=profile)
        values.update(overrides)
        return component_cls(**values)

    def _copy_fields(self, src_obj: Any, dst_obj: Any, *, exclude: set[str] | None = None) -> None:
        """Best-effort attribute copier used by duplicate flows."""
        exclude = set(exclude or set()) | {"dirty"}
        for attr in vars(src_obj).keys():
            if attr in exclude:
                continue
            try:
                setattr(dst_obj, attr, getattr(src_obj, attr))
            except Exception:
                log.debug("Failed to copy attribute '%s' during duplicate; skipping", attr, exc_info=True)


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

        except Exception:
            log.exception("Error listing item IDs")
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
        render = self._build_component_with_metadata_defaults(
            RenderComponent,
            "RenderComponent",
            id=render_comp_id,
        )
        render.dirty = True
        item_comp = self._build_component_with_metadata_defaults(
            ItemComponent,
            "ItemComponent",
            id=item_comp_id,
        )
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
                    # Best-effort; log at debug and skip attributes that aren't compatible
                    log.debug("Failed to copy attribute '%s' during duplicate; skipping", attr, exc_info=True)

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
                    # Log at debug and skip malformed rows
                    log.debug("Failed to duplicate a skill row for object %s; skipping row", new_id, exc_info=True)
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
        comp = self._build_component_with_metadata_defaults(
            ItemComponent,
            "ItemComponent",
            id=comp_id,
        )
        comp.dirty = True
        item.components["ItemComponent"] = comp
        return comp

    def add_render_component(self, item: Item) -> RenderComponent:
        """Attach a new RenderComponent to the given item (no-op if already present)."""
        if item.components.get("RenderComponent") is not None:
            return item.components["RenderComponent"]  # type: ignore[index]
        comp_id = self.generate_new_component_id(item.object_id, "RenderComponent")
        comp = self._build_component_with_metadata_defaults(
            RenderComponent,
            "RenderComponent",
            id=comp_id,
        )
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
        return self._build_component_with_metadata_defaults(
            ObjectSkillRow,
            "ObjectSkillRow",
            object_Template=object_id,
            skill_id=sid,
            cast_on_type=1,
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


class NPCService(BaseService):
    """Service layer for NPC objects and linked NPC-owned tables."""

    def __init__(self, db_path: Path | str):
        super().__init__(db_path, NPCRepository)

    def get_npc(self, object_id: int) -> NPC:
        return self.get(object_id)

    def list_npcs(self, limit: int | None = None) -> list[dict[str, int | str]]:
        try:
            return self._repo.list_npcs(limit)
        except Exception:
            log.exception("Error listing NPC IDs")
            return []

    def save(self, obj: Any) -> None:
        if isinstance(obj, NPC):
            self._validate_npc_before_save(obj)
        super().save(obj)

    def save_npc(self, npc: NPC) -> None:
        self.save(npc)

    def _validate_npc_before_save(self, npc: NPC) -> None:
        self._validate_vendor_loot_state(npc)

    def _validate_vendor_loot_state(self, npc: NPC) -> None:
        vendor = npc.components.get("VendorComponent")
        if not isinstance(vendor, VendorComponent):
            return

        loot_matrix_index = getattr(vendor, "loot_matrix_index", None)
        if not self._has_linked_index(loot_matrix_index):
            log.error(
                "Vendor save validation failed object_id=%s reason=missing_loot_matrix_index",
                npc.object_id,
            )
            raise ValueError(
                "VendorComponent requires a valid LootMatrix before saving.\n\n"
                "Add a vendor loot matrix and at least one linked loot table entry."
            )

        matrix_collection = npc.components.get("VendorLootMatrix")
        matrix_rows = [
            row
            for row in getattr(matrix_collection, "rows", []) or []
            if getattr(row, "loot_matrix_index", None) == loot_matrix_index
        ] if isinstance(matrix_collection, RowCollection) else []
        if not matrix_rows:
            log.error(
                "Vendor save validation failed object_id=%s loot_matrix_index=%s reason=no_matrix_rows",
                npc.object_id,
                loot_matrix_index,
            )
            raise ValueError(
                f"VendorComponent LootMatrixIndex {loot_matrix_index} does not link to any LootMatrix rows.\n\n"
                "Add a vendor loot matrix and at least one linked loot table entry before saving."
            )

        table_collection = npc.components.get("VendorLootTable")
        table_rows = list(getattr(table_collection, "rows", []) or []) if isinstance(table_collection, RowCollection) else []
        table_indices_with_rows = {
            int(getattr(row, "loot_table_index"))
            for row in table_rows
            if isinstance(getattr(row, "loot_table_index", None), int) and int(getattr(row, "loot_table_index")) > 0
        }
        invalid_linked_table_indices = sorted({
            getattr(row, "loot_table_index", None)
            for row in matrix_rows
            if not isinstance(getattr(row, "loot_table_index", None), int) or int(getattr(row, "loot_table_index")) <= 0
        })
        linked_table_indices = {
            int(getattr(row, "loot_table_index"))
            for row in matrix_rows
            if isinstance(getattr(row, "loot_table_index", None), int) and int(getattr(row, "loot_table_index")) > 0
        }

        if invalid_linked_table_indices:
            invalid_text = ", ".join(str(index) for index in invalid_linked_table_indices)
            log.error(
                "Vendor save validation failed object_id=%s loot_matrix_index=%s invalid_loot_table_indices=%s",
                npc.object_id,
                loot_matrix_index,
                invalid_text,
            )
            raise ValueError(
                f"VendorComponent LootMatrixIndex {loot_matrix_index} contains LootMatrix rows with invalid LootTableIndex values: {invalid_text}.\n\n"
                "Each vendor loot matrix entry must link to a valid loot table row before saving."
            )

        if not linked_table_indices:
            log.error(
                "Vendor save validation failed object_id=%s loot_matrix_index=%s reason=no_linked_loot_tables",
                npc.object_id,
                loot_matrix_index,
            )
            raise ValueError(
                f"VendorComponent LootMatrixIndex {loot_matrix_index} does not link to any LootTable rows.\n\n"
                "Add at least one vendor loot table entry before saving."
            )

        missing_table_indices = sorted(linked_table_indices - table_indices_with_rows)
        if missing_table_indices:
            missing_text = ", ".join(str(index) for index in missing_table_indices)
            log.error(
                "Vendor save validation failed object_id=%s loot_matrix_index=%s missing_loot_table_indices=%s",
                npc.object_id,
                loot_matrix_index,
                missing_text,
            )
            raise ValueError(
                f"VendorComponent LootMatrixIndex {loot_matrix_index} references LootTableIndex values with no LootTable rows: {missing_text}.\n\n"
                "Each vendor loot matrix entry must link to at least one loot table row before saving."
            )

    def _resolve_new_object_id(self, object_id: int | None) -> int:
        if object_id is not None:
            oid = self._require_positive_int(object_id, "Object ID")
            try:
                existing = self._repo.get(oid)
                if existing is not None:
                    raise ValueError(f"Object ID {oid} already exists")
            except NotFoundError:
                pass
            return oid
        return self._repo.generate_new_id()

    def _ensure_row_collection(self, npc: NPC, key: str, *, key_field: str, label_prefix: str) -> RowCollection:
        collection = npc.components.get(key)
        if isinstance(collection, RowCollection):
            return collection
        collection = RowCollection(rows=[], key_field=key_field, label_prefix=label_prefix, dirty=True)
        npc.components[key] = collection
        return collection

    def _ensure_component_row_collection(
        self,
        npc: NPC,
        key: str,
        *,
        table: str,
        key_field: str,
        label_prefix: str,
    ) -> RowCollection:
        collection = self._ensure_row_collection(npc, key, key_field=key_field, label_prefix=label_prefix)
        component_id = getattr(collection, "component_id", None)
        if isinstance(component_id, int) and component_id > 0:
            collection.loaded_keys = {component_id}
            return collection

        component_id = self._repo.generate_new_component_id(npc.object_id, table)
        collection.component_id = component_id
        collection.loaded_keys = {component_id}
        collection.dirty = True
        log.debug(
            "Assigned row-collection component_id=%s key=%s object_id=%s",
            component_id,
            key,
            npc.object_id,
        )
        return collection

    def _get_or_create_primary_mission_id(self, npc: NPC) -> int:
        collection = npc.components.get("MissionNPCComponent")
        if isinstance(collection, RowCollection) and collection.rows:
            return collection.rows[0].mission_id
        return self.add_mission_bundle(npc).mission_id

    def _collect_row_values(self, npc: NPC, component_keys: tuple[str, ...], attr: str) -> set[int]:
        values: set[int] = set()
        for component_key in component_keys:
            collection = npc.components.get(component_key)
            if not isinstance(collection, RowCollection):
                continue
            for row in collection.rows:
                value = getattr(row, attr, None)
                if isinstance(value, int):
                    values.add(value)
        return values

    def _collect_component_values(self, npc: NPC, component_keys: tuple[str, ...], attr: str) -> set[int]:
        values: set[int] = set()
        for component_key in component_keys:
            component = npc.components.get(component_key)
            if component is None:
                continue
            value = getattr(component, attr, None)
            if isinstance(value, int):
                values.add(value)
        return values

    def _reserve_next_int(
        self,
        generator: Callable[[], int],
        used_values: set[int],
        *,
        label: str,
        object_id: int | None,
    ) -> int:
        candidate = int(generator())
        while candidate in used_values:
            candidate += 1
        used_values.add(candidate)
        log.debug("Reserved %s=%s object_id=%s", label, candidate, object_id)
        return candidate

    def _has_linked_index(self, value: Any) -> bool:
        return isinstance(value, int) and value > 0

    def _collect_loot_matrix_indices(self, npc: NPC) -> set[int]:
        return self._collect_component_values(npc, ("VendorComponent", "DestructibleComponent"), "loot_matrix_index") | self._collect_row_values(
            npc,
            ("VendorLootMatrixIndex", "DestructibleLootMatrixIndex", "VendorLootMatrix", "DestructibleLootMatrix"),
            "loot_matrix_index",
        )

    def _collect_currency_indices(self, npc: NPC) -> set[int]:
        return self._collect_component_values(npc, ("DestructibleComponent",), "currency_index") | self._collect_row_values(
            npc,
            ("CurrencyTable",),
            "currency_index",
        )

    def _collect_loot_table_indices(self, npc: NPC) -> set[int]:
        return self._collect_row_values(
            npc,
            (
                "VendorLootTableIndex",
                "DestructibleLootTableIndex",
                "VendorLootMatrix",
                "VendorLootTable",
                "DestructibleLootMatrix",
                "DestructibleLootTable",
            ),
            "loot_table_index",
        )

    def _collect_loot_table_row_ids(self, npc: NPC) -> set[int]:
        return self._collect_row_values(npc, ("VendorLootTable", "DestructibleLootTable"), "id")

    def _collect_loot_matrix_row_ids(self, npc: NPC) -> set[int]:
        return self._collect_row_values(npc, ("VendorLootMatrix", "DestructibleLootMatrix"), "id")

    def _collect_currency_row_ids(self, npc: NPC) -> set[int]:
        return self._collect_row_values(npc, ("CurrencyTable",), "id")

    def _collect_mission_ids(self, npc: NPC) -> set[int]:
        return (
            self._collect_row_values(npc, ("MissionNPCComponent",), "mission_id")
            | self._collect_row_values(npc, ("Missions", "MissionTasks", "MissionText"), "id")
            | self._collect_row_values(npc, ("MissionEmail",), "mission_id")
        )

    def _collect_task_uids(self, npc: NPC) -> set[int]:
        return self._collect_row_values(npc, ("MissionTasks",), "uid")

    def _collect_mission_email_ids(self, npc: NPC) -> set[int]:
        return self._collect_row_values(npc, ("MissionEmail",), "id")

    def _ensure_loot_matrix_index_collection(self, npc: NPC, family: str) -> RowCollection:
        key = "VendorLootMatrixIndex" if family == "vendor" else "DestructibleLootMatrixIndex"
        return self._ensure_row_collection(npc, key, key_field="loot_matrix_index", label_prefix="LootMatrixIndex")

    def _ensure_loot_table_index_collection(self, npc: NPC, family: str) -> RowCollection:
        key = "VendorLootTableIndex" if family == "vendor" else "DestructibleLootTableIndex"
        return self._ensure_row_collection(npc, key, key_field="loot_table_index", label_prefix="LootTableIndex")

    def _ensure_loot_matrix_index_row(self, npc: NPC, family: str, loot_matrix_index: int) -> LootMatrixIndexRow:
        collection = self._ensure_loot_matrix_index_collection(npc, family)
        existing = next(
            (row for row in collection.rows if getattr(row, "loot_matrix_index", None) == loot_matrix_index),
            None,
        )
        if isinstance(existing, LootMatrixIndexRow):
            if collection.rows != [existing]:
                collection.dirty = True
            collection.rows = [existing]
            return existing
        row = self._build_component_with_metadata_defaults(
            LootMatrixIndexRow,
            "LootMatrixIndexRow",
            loot_matrix_index=loot_matrix_index,
        )
        collection.rows = [row]
        collection.dirty = True
        return row

    def _ensure_loot_table_index_row(self, npc: NPC, family: str, loot_table_index: int) -> LootTableIndexRow:
        collection = self._ensure_loot_table_index_collection(npc, family)
        existing = next(
            (row for row in collection.rows if getattr(row, "loot_table_index", None) == loot_table_index),
            None,
        )
        if isinstance(existing, LootTableIndexRow):
            return existing
        row = self._build_component_with_metadata_defaults(
            LootTableIndexRow,
            "LootTableIndexRow",
            loot_table_index=loot_table_index,
        )
        collection.rows.append(row)
        collection.dirty = True
        return row

    def _ensure_vendor_loot_matrix_index(self, npc: NPC) -> int:
        vendor = self.add_vendor_component(npc)
        if not self._has_linked_index(getattr(vendor, "loot_matrix_index", None)):
            vendor.loot_matrix_index = self._reserve_next_int(
                self._repo.generate_new_loot_matrix_index,
                self._collect_loot_matrix_indices(npc),
                label="loot_matrix_index",
                object_id=npc.object_id,
            )
            vendor.dirty = True
        self._ensure_loot_matrix_index_row(npc, "vendor", int(vendor.loot_matrix_index))
        return int(vendor.loot_matrix_index)

    def _ensure_destructible_loot_matrix_index(self, npc: NPC) -> int:
        component = npc.components.get("DestructibleComponent")
        if not isinstance(component, DestructibleComponent):
            component = self.add_destructible_component(npc)
        if component.loot_matrix_index is None:
            component.loot_matrix_index = self._reserve_next_int(
                self._repo.generate_new_loot_matrix_index,
                self._collect_loot_matrix_indices(npc),
                label="loot_matrix_index",
                object_id=npc.object_id,
            )
            component.dirty = True
        self._ensure_loot_matrix_index_row(npc, "destructible", int(component.loot_matrix_index))
        return int(component.loot_matrix_index)

    def create_default_vendor_npc(self, object_id: int | None = None) -> NPC:
        new_id = self._resolve_new_object_id(object_id)
        log.info("Creating default vendor NPC object_id=%s", new_id)
        npc = NPC(id=new_id, type=ObjectTypes.NPC)
        npc.dirty = True
        self._apply_metadata_defaults(npc, "GameObject")
        render = self._build_component_with_metadata_defaults(
            RenderComponent,
            "RenderComponent",
            id=self._repo.generate_new_component_id(new_id, "RenderComponent"),
            profile="vendor",
        )
        render.dirty = True
        npc.components["RenderComponent"] = render
        minifig = self._build_component_with_metadata_defaults(
            MinifigComponent,
            "MinifigComponent",
            id=self._repo.generate_new_component_id(new_id, "MinifigComponent"),
        )
        minifig.dirty = True
        npc.components["MinifigComponent"] = minifig
        physics = self._build_component_with_metadata_defaults(
            PhysicsComponent,
            "PhysicsComponent",
            id=self._repo.generate_new_component_id(new_id, "PhysicsComponent"),
        )
        physics.dirty = True
        npc.components["PhysicsComponent"] = physics
        destructible = self._build_component_with_metadata_defaults(
            DestructibleComponent,
            "DestructibleComponent",
            id=self._repo.generate_new_component_id(new_id, "DestructibleComponent"),
        )
        destructible.dirty = True
        npc.components["DestructibleComponent"] = destructible
        self._ensure_component_row_collection(
            npc,
            "InventoryComponent",
            table="InventoryComponent",
            key_field="itemid",
            label_prefix="Item",
        )
        vendor = self._build_component_with_metadata_defaults(
            VendorComponent,
            "VendorComponent",
            id=self._repo.generate_new_component_id(new_id, "VendorComponent"),
        )
        vendor.dirty = True
        npc.components["VendorComponent"] = vendor
        npc.components["VendorLootMatrix"] = RowCollection(
            rows=[],
            key_field="ui_key",
            label_prefix="LootMatrix",
            loaded_keys={vendor.loot_matrix_index} if self._has_linked_index(vendor.loot_matrix_index) else set(),
            dirty=True,
        )
        npc.components["VendorLootTableIndex"] = RowCollection(
            rows=[],
            key_field="loot_table_index",
            label_prefix="LootTableIndex",
            loaded_keys=set(),
            dirty=True,
        )
        npc.components["VendorLootTable"] = RowCollection(
            rows=[],
            key_field="id",
            label_prefix="LootTable",
            loaded_keys=set(),
            dirty=True,
        )
        self.add_loot_table_row(npc, "vendor")
        self.save(npc)
        return self._repo.get(new_id) or npc

    def create_default_mission_npc(self, object_id: int | None = None) -> NPC:
        new_id = self._resolve_new_object_id(object_id)
        log.info("Creating default mission NPC object_id=%s", new_id)
        npc = NPC(id=new_id, type=ObjectTypes.NPC)
        npc.dirty = True
        self._apply_metadata_defaults(npc, "GameObject")
        render = self._build_component_with_metadata_defaults(
            RenderComponent,
            "RenderComponent",
            id=self._repo.generate_new_component_id(new_id, "RenderComponent"),
            profile="mission",
        )
        render.dirty = True
        npc.components["RenderComponent"] = render
        minifig = self._build_component_with_metadata_defaults(
            MinifigComponent,
            "MinifigComponent",
            id=self._repo.generate_new_component_id(new_id, "MinifigComponent"),
        )
        minifig.dirty = True
        npc.components["MinifigComponent"] = minifig
        physics = self._build_component_with_metadata_defaults(
            PhysicsComponent,
            "PhysicsComponent",
            id=self._repo.generate_new_component_id(new_id, "PhysicsComponent"),
        )
        physics.dirty = True
        npc.components["PhysicsComponent"] = physics
        destructible = self._build_component_with_metadata_defaults(
            DestructibleComponent,
            "DestructibleComponent",
            id=self._repo.generate_new_component_id(new_id, "DestructibleComponent"),
        )
        destructible.dirty = True
        npc.components["DestructibleComponent"] = destructible
        self._ensure_component_row_collection(
            npc,
            "InventoryComponent",
            table="InventoryComponent",
            key_field="itemid",
            label_prefix="Item",
        )
        self.add_mission_bundle(npc, mark_existing_dirty=True)
        self.save(npc)
        return self._repo.get(new_id) or npc

    def add_render_component(self, npc: NPC) -> RenderComponent:
        comp = npc.components.get("RenderComponent")
        if isinstance(comp, RenderComponent):
            return comp
        comp = self._build_component_with_metadata_defaults(
            RenderComponent,
            "RenderComponent",
            id=self._repo.generate_new_component_id(npc.object_id, "RenderComponent"),
            profile=(
                "vendor"
                if isinstance(npc.components.get("VendorComponent"), VendorComponent)
                else "mission"
                if isinstance(npc.components.get("MissionNPCComponent"), RowCollection)
                else None
            ),
        )
        comp.dirty = True
        npc.components["RenderComponent"] = comp
        return comp

    def add_minifig_component(self, npc: NPC) -> MinifigComponent:
        comp = npc.components.get("MinifigComponent")
        if isinstance(comp, MinifigComponent):
            return comp
        comp = self._build_component_with_metadata_defaults(
            MinifigComponent,
            "MinifigComponent",
            id=self._repo.generate_new_component_id(npc.object_id, "MinifigComponent"),
        )
        comp.dirty = True
        npc.components["MinifigComponent"] = comp
        return comp

    def add_physics_component(self, npc: NPC) -> PhysicsComponent:
        comp = npc.components.get("PhysicsComponent")
        if isinstance(comp, PhysicsComponent):
            return comp
        comp = self._build_component_with_metadata_defaults(
            PhysicsComponent,
            "PhysicsComponent",
            id=self._repo.generate_new_component_id(npc.object_id, "PhysicsComponent"),
        )
        comp.dirty = True
        npc.components["PhysicsComponent"] = comp
        return comp

    def ensure_inventory_component(self, npc: NPC) -> RowCollection:
        return self._ensure_component_row_collection(
            npc,
            "InventoryComponent",
            table="InventoryComponent",
            key_field="itemid",
            label_prefix="Item",
        )

    def add_vendor_component(self, npc: NPC) -> VendorComponent:
        comp = npc.components.get("VendorComponent")
        if isinstance(comp, VendorComponent):
            return comp
        comp = self._build_component_with_metadata_defaults(
            VendorComponent,
            "VendorComponent",
            id=self._repo.generate_new_component_id(npc.object_id, "VendorComponent"),
        )
        comp.dirty = True
        npc.components["VendorComponent"] = comp
        npc.components["VendorLootMatrix"] = RowCollection(
            rows=[],
            key_field="ui_key",
            label_prefix="LootMatrix",
            loaded_keys={comp.loot_matrix_index} if self._has_linked_index(comp.loot_matrix_index) else set(),
            dirty=True,
        )
        npc.components["VendorLootTableIndex"] = RowCollection(
            rows=[],
            key_field="loot_table_index",
            label_prefix="LootTableIndex",
            loaded_keys=set(),
            dirty=True,
        )
        npc.components["VendorLootTable"] = RowCollection(
            rows=[],
            key_field="id",
            label_prefix="LootTable",
            loaded_keys=set(),
            dirty=True,
        )
        return comp

    def add_destructible_component(self, npc: NPC) -> DestructibleComponent:
        comp = npc.components.get("DestructibleComponent")
        if isinstance(comp, DestructibleComponent):
            return comp
        comp = self._build_component_with_metadata_defaults(
            DestructibleComponent,
            "DestructibleComponent",
            id=self._repo.generate_new_component_id(npc.object_id, "DestructibleComponent"),
        )
        comp.dirty = True
        npc.components["DestructibleComponent"] = comp
        npc.components["DestructibleLootMatrix"] = RowCollection(
            rows=[],
            key_field="ui_key",
            label_prefix="LootMatrix",
            loaded_keys={comp.loot_matrix_index} if self._has_linked_index(comp.loot_matrix_index) else set(),
            dirty=True,
        )
        npc.components["DestructibleLootTableIndex"] = RowCollection(
            rows=[],
            key_field="loot_table_index",
            label_prefix="LootTableIndex",
            loaded_keys=set(),
            dirty=True,
        )
        npc.components["DestructibleLootTable"] = RowCollection(
            rows=[],
            key_field="id",
            label_prefix="LootTable",
            loaded_keys=set(),
            dirty=True,
        )
        npc.components["CurrencyTable"] = RowCollection(
            rows=[],
            key_field="id",
            label_prefix="CurrencyTable",
            loaded_keys={comp.currency_index} if self._has_linked_index(comp.currency_index) else set(),
            dirty=True,
        )
        return comp

    def add_script_component(self, npc: NPC) -> ScriptComponent:
        comp = npc.components.get("ScriptComponent")
        if isinstance(comp, ScriptComponent):
            return comp
        comp = self._build_component_with_metadata_defaults(
            ScriptComponent,
            "ScriptComponent",
            id=self._repo.generate_new_component_id(npc.object_id, "ScriptComponent"),
        )
        comp.dirty = True
        npc.components["ScriptComponent"] = comp
        return comp

    def add_inventory_row(self, npc: NPC) -> InventoryComponentRow:
        collection = self.ensure_inventory_component(npc)
        component_id = int(collection.component_id or npc.object_id)
        used = {row.itemid for row in collection.rows}
        candidate = INT_32_MAX
        while candidate in used and candidate > 1:
            candidate -= 1
        row = self._build_component_with_metadata_defaults(
            InventoryComponentRow,
            "InventoryComponentRow",
            id=component_id,
            itemid=candidate,
        )
        collection.rows.append(row)
        collection.dirty = True
        return row

    def add_mission_bundle(self, npc: NPC, *, mark_existing_dirty: bool = False) -> MissionNPCComponentRow:
        mission_collection = self._ensure_component_row_collection(
            npc,
            "MissionNPCComponent",
            table="MissionNPCComponent",
            key_field="mission_id",
            label_prefix="Mission",
        )
        missions = self._ensure_row_collection(npc, "Missions", key_field="id", label_prefix="Mission")
        mission_text = self._ensure_row_collection(npc, "MissionText", key_field="id", label_prefix="Text")
        mission_tasks = self._ensure_row_collection(npc, "MissionTasks", key_field="uid", label_prefix="Task")
        mission_email = self._ensure_row_collection(npc, "MissionEmail", key_field="id", label_prefix="Email")

        mission_id = self._reserve_next_int(
            self._repo.generate_new_mission_id,
            self._collect_mission_ids(npc),
            label="mission_id",
            object_id=npc.object_id,
        )
        component_id = int(mission_collection.component_id or npc.object_id)
        mission_row = self._build_component_with_metadata_defaults(
            MissionNPCComponentRow,
            "MissionNPCComponentRow",
            id=component_id,
            mission_id=mission_id,
        )
        mission_collection.rows.append(mission_row)
        missions.rows.append(
            self._build_component_with_metadata_defaults(
                MissionRow,
                "MissionRow",
                id=mission_id,
                offer_object_id=npc.object_id,
                target_object_id=npc.object_id,
                is_mission=True,
                localize=True,
            )
        )
        mission_text.rows.append(
            self._build_component_with_metadata_defaults(
                MissionTextRow,
                "MissionTextRow",
                id=mission_id,
            )
        )

        mission_collection.dirty = True
        missions.dirty = True
        mission_text.dirty = True
        if mark_existing_dirty:
            mission_tasks.dirty = True
            mission_email.dirty = True
        return mission_row

    def add_task_row(self, npc: NPC) -> MissionTaskRow:
        mission_id = self._get_or_create_primary_mission_id(npc)
        collection = self._ensure_row_collection(npc, "MissionTasks", key_field="uid", label_prefix="Task")
        row = self._build_component_with_metadata_defaults(
            MissionTaskRow,
            "MissionTaskRow",
            id=mission_id,
            uid=self._reserve_next_int(
                self._repo.generate_new_task_uid,
                self._collect_task_uids(npc),
                label="task_uid",
                object_id=npc.object_id,
            ),
        )
        collection.rows.append(row)
        collection.dirty = True
        return row

    def add_email_row(self, npc: NPC) -> MissionEmailRow:
        mission_id = self._get_or_create_primary_mission_id(npc)
        collection = self._ensure_row_collection(npc, "MissionEmail", key_field="id", label_prefix="Email")
        row = self._build_component_with_metadata_defaults(
            MissionEmailRow,
            "MissionEmailRow",
            id=self._reserve_next_int(
                self._repo.generate_new_mission_email_id,
                self._collect_mission_email_ids(npc),
                label="mission_email_id",
                object_id=npc.object_id,
            ),
            mission_id=mission_id,
        )
        collection.rows.append(row)
        collection.dirty = True
        return row

    def _resolve_loot_collections(self, npc: NPC, family: str) -> tuple[RowCollection, RowCollection, RowCollection, RowCollection, int]:
        if family == "vendor":
            loot_matrix_index = self._ensure_vendor_loot_matrix_index(npc)
            matrix_index_collection = self._ensure_loot_matrix_index_collection(npc, "vendor")
            matrix_collection = self._ensure_row_collection(npc, "VendorLootMatrix", key_field="ui_key", label_prefix="LootMatrix")
            table_index_collection = self._ensure_loot_table_index_collection(npc, "vendor")
            table_collection = self._ensure_row_collection(npc, "VendorLootTable", key_field="id", label_prefix="LootTable")
        else:
            loot_matrix_index = self._ensure_destructible_loot_matrix_index(npc)
            matrix_index_collection = self._ensure_loot_matrix_index_collection(npc, "destructible")
            matrix_collection = self._ensure_row_collection(npc, "DestructibleLootMatrix", key_field="ui_key", label_prefix="LootMatrix")
            table_index_collection = self._ensure_loot_table_index_collection(npc, "destructible")
            table_collection = self._ensure_row_collection(npc, "DestructibleLootTable", key_field="id", label_prefix="LootTable")
        return matrix_index_collection, matrix_collection, table_index_collection, table_collection, loot_matrix_index

    def _create_loot_table_row(self, npc: NPC, loot_table_index: int) -> LootTableRow:
        return self._build_component_with_metadata_defaults(
            LootTableRow,
            "LootTableRow",
            loot_table_index=loot_table_index,
            id=self._reserve_next_int(
                self._repo.generate_new_loot_table_row_id,
                self._collect_loot_table_row_ids(npc),
                label="loot_table_row_id",
                object_id=npc.object_id,
            ),
        )

    def add_loot_entry(self, npc: NPC, family: str) -> LootMatrixRow:
        _matrix_index_collection, matrix_collection, table_index_collection, _table_collection, loot_matrix_index = self._resolve_loot_collections(npc, family)
        loot_table_index = self._reserve_next_int(
            self._repo.generate_new_loot_table_index,
            self._collect_loot_table_indices(npc),
            label="loot_table_index",
            object_id=npc.object_id,
        )
        rarity_table_index = int(self._repo.get_default_rarity_table_index())
        self._ensure_loot_table_index_row(npc, family, loot_table_index)
        table_index_collection.dirty = True
        matrix_row = self._build_component_with_metadata_defaults(
            LootMatrixRow,
            "LootMatrixRow",
            loot_matrix_index=loot_matrix_index,
            loot_table_index=loot_table_index,
            id=self._reserve_next_int(
                self._repo.generate_new_loot_matrix_row_id,
                self._collect_loot_matrix_row_ids(npc),
                label="loot_matrix_row_id",
                object_id=npc.object_id,
            ),
            rarity_table_index=rarity_table_index,
        )
        matrix_collection.rows.append(matrix_row)
        matrix_collection.dirty = True
        log.info(
            "Added %s loot matrix row object_id=%s loot_matrix_index=%s loot_table_index=%s",
            family,
            npc.object_id,
            loot_matrix_index,
            loot_table_index,
        )
        return matrix_row

    def add_loot_table_row(self, npc: NPC, family: str) -> tuple[LootMatrixRow, LootTableRow]:
        _matrix_index_collection, matrix_collection, table_index_collection, table_collection, _loot_matrix_index = self._resolve_loot_collections(npc, family)
        matrix_rows = list(matrix_collection.rows or [])

        # LootTable rows belong to an existing LootMatrix bucket. Reuse the first
        # bucket when present so adding under the table does not create a new matrix.
        if matrix_rows:
            matrix_row = matrix_rows[0]
            self._ensure_loot_table_index_row(npc, family, matrix_row.loot_table_index)
            table_index_collection.dirty = True
            loot_row = self._create_loot_table_row(npc, matrix_row.loot_table_index)
            table_collection.rows.append(loot_row)
            table_collection.dirty = True
            log.info(
                "Added %s loot table row object_id=%s loot_table_index=%s loot_table_row_id=%s reused_matrix_key=%s",
                family,
                npc.object_id,
                matrix_row.loot_table_index,
                loot_row.id,
                matrix_row.ui_key,
            )
            return matrix_row, loot_row

        log.info("No existing %s loot matrix for object_id=%s; creating a new matrix bucket", family, npc.object_id)
        matrix_row = self.add_loot_entry(npc, family)
        loot_row = self._create_loot_table_row(npc, matrix_row.loot_table_index)
        table_collection.rows.append(loot_row)
        table_collection.dirty = True
        log.info(
            "Added %s loot table row object_id=%s loot_table_index=%s loot_table_row_id=%s after creating_matrix_key=%s",
            family,
            npc.object_id,
            matrix_row.loot_table_index,
            loot_row.id,
            matrix_row.ui_key,
        )
        return matrix_row, loot_row

    def add_currency_row(self, npc: NPC) -> CurrencyTableRow:
        destructible = npc.components.get("DestructibleComponent")
        if not isinstance(destructible, DestructibleComponent):
            destructible = self.add_destructible_component(npc)
        if destructible.currency_index is None:
            destructible.currency_index = self._reserve_next_int(
                self._repo.generate_new_currency_index,
                self._collect_currency_indices(npc),
                label="currency_index",
                object_id=npc.object_id,
            )
            destructible.dirty = True
        collection = self._ensure_row_collection(npc, "CurrencyTable", key_field="id", label_prefix="CurrencyTable")
        row = self._build_component_with_metadata_defaults(
            CurrencyTableRow,
            "CurrencyTableRow",
            currency_index=destructible.currency_index,
            id=self._reserve_next_int(
                self._repo.generate_new_currency_row_id,
                self._collect_currency_row_ids(npc),
                label="currency_row_id",
                object_id=npc.object_id,
            ),
        )
        collection.rows.append(row)
        collection.dirty = True
        return row

    def remove_mission_bundle(self, npc: NPC, mission_id: int) -> None:
        for key, attr in (
            ("MissionNPCComponent", "mission_id"),
            ("Missions", "id"),
            ("MissionTasks", "id"),
            ("MissionText", "id"),
            ("MissionEmail", "mission_id"),
        ):
            collection = npc.components.get(key)
            if not isinstance(collection, RowCollection):
                continue
            before = len(collection.rows)
            collection.rows = [row for row in collection.rows if getattr(row, attr, None) != mission_id]
            if len(collection.rows) != before:
                collection.dirty = True

    def remove_loot_entry(self, npc: NPC, family: str, loot_table_index: int) -> None:
        if family == "vendor":
            keys = ("VendorLootMatrix", "VendorLootTable")
            table_index_key = "VendorLootTableIndex"
        else:
            keys = ("DestructibleLootMatrix", "DestructibleLootTable")
            table_index_key = "DestructibleLootTableIndex"
        for key in keys:
            collection = npc.components.get(key)
            if not isinstance(collection, RowCollection):
                continue
            before = len(collection.rows)
            collection.rows = [row for row in collection.rows if getattr(row, "loot_table_index", None) != loot_table_index]
            if len(collection.rows) != before:
                collection.dirty = True
        table_index_collection = npc.components.get(table_index_key)
        if isinstance(table_index_collection, RowCollection):
            before = len(table_index_collection.rows)
            table_index_collection.rows = [
                row for row in table_index_collection.rows if getattr(row, "loot_table_index", None) != loot_table_index
            ]
            if len(table_index_collection.rows) != before:
                table_index_collection.dirty = True

    def remove_loot_table_row(self, npc: NPC, family: str, row_id: int) -> None:
        key = "VendorLootTable" if family == "vendor" else "DestructibleLootTable"
        collection = npc.components.get(key)
        if not isinstance(collection, RowCollection):
            return
        before = len(collection.rows)
        collection.rows = [row for row in collection.rows if getattr(row, "id", None) != row_id]
        if len(collection.rows) != before:
            collection.dirty = True

    def duplicate_npc(self, source_object_id: int, target_object_id: int | None = None) -> NPC:
        src_id = self._require_positive_int(source_object_id, "Source Object ID")
        try:
            src = self._repo.get(src_id)
        except NotFoundError:
            raise ValueError(f"Source NPC {src_id} does not exist")

        new_id = self._resolve_new_object_id(target_object_id)
        log.info("Duplicating NPC source_object_id=%s target_object_id=%s", src_id, new_id)
        dup = NPC(id=new_id, type=getattr(src, "type", ObjectTypes.NPC_2), name=src.name)
        self._copy_fields(src, dup, exclude={"object_id", "components", "type"})
        dup.object_id = new_id
        dup.type = getattr(src, "type", ObjectTypes.NPC_2)
        dup.dirty = True

        if src.components.get("RenderComponent") is not None:
            comp = RenderComponent(id=self._repo.generate_new_component_id(new_id, "RenderComponent"))
            self._copy_fields(src.components["RenderComponent"], comp, exclude={"id"})
            comp.dirty = True
            dup.components["RenderComponent"] = comp

        if src.components.get("MinifigComponent") is not None:
            comp = MinifigComponent(id=self._repo.generate_new_component_id(new_id, "MinifigComponent"))
            self._copy_fields(src.components["MinifigComponent"], comp, exclude={"id"})
            comp.dirty = True
            dup.components["MinifigComponent"] = comp

        if src.components.get("PhysicsComponent") is not None:
            comp = PhysicsComponent(id=self._repo.generate_new_component_id(new_id, "PhysicsComponent"))
            self._copy_fields(src.components["PhysicsComponent"], comp, exclude={"id"})
            comp.dirty = True
            dup.components["PhysicsComponent"] = comp

        if src.components.get("ScriptComponent") is not None:
            comp = ScriptComponent(id=self._repo.generate_new_component_id(new_id, "ScriptComponent"))
            self._copy_fields(src.components["ScriptComponent"], comp, exclude={"id"})
            comp.dirty = True
            dup.components["ScriptComponent"] = comp

        inventory = src.components.get("InventoryComponent")
        if isinstance(inventory, RowCollection):
            inventory_component_id = self._repo.generate_new_component_id(new_id, "InventoryComponent")
            dup.components["InventoryComponent"] = RowCollection(
                rows=[
                    InventoryComponentRow(id=inventory_component_id, itemid=row.itemid, count=row.count, equip=row.equip)
                    for row in inventory.rows
                ],
                key_field="itemid",
                label_prefix="Item",
                component_id=inventory_component_id,
                loaded_keys={inventory_component_id},
                dirty=True,
            )

        self._duplicate_vendor_state(src, dup, new_id)
        self._duplicate_destructible_state(src, dup, new_id)
        self._duplicate_mission_state(src, dup, new_id)

        self.save(dup)
        return self._repo.get(new_id) or dup

    def _duplicate_vendor_state(self, src: NPC, dup: NPC, new_id: int) -> None:
        src_vendor = src.components.get("VendorComponent")
        if not isinstance(src_vendor, VendorComponent):
            return
        loot_matrix_indices = self._collect_loot_matrix_indices(dup)
        vendor = VendorComponent(
            id=self._repo.generate_new_component_id(new_id, "VendorComponent"),
            loot_matrix_index=self._reserve_next_int(
                self._repo.generate_new_loot_matrix_index,
                loot_matrix_indices,
                label="loot_matrix_index",
                object_id=new_id,
            ),
        )
        self._copy_fields(src_vendor, vendor, exclude={"id", "loot_matrix_index"})
        vendor.dirty = True
        dup.components["VendorComponent"] = vendor
        dup.components["VendorLootMatrixIndex"] = RowCollection(
            rows=[LootMatrixIndexRow(loot_matrix_index=vendor.loot_matrix_index, in_npc_editor=True)],
            key_field="loot_matrix_index",
            label_prefix="LootMatrixIndex",
            loaded_keys=set(),
            dirty=True,
        )

        loot_index_map: dict[int, int] = {}
        loot_table_indices = self._collect_loot_table_indices(dup)
        src_matrix = src.components.get("VendorLootMatrix")
        if isinstance(src_matrix, RowCollection):
            for row in src_matrix.rows:
                if row.loot_table_index not in loot_index_map:
                    loot_index_map[row.loot_table_index] = self._reserve_next_int(
                        self._repo.generate_new_loot_table_index,
                        loot_table_indices,
                        label="loot_table_index",
                        object_id=new_id,
                    )
            dup.components["VendorLootMatrix"] = RowCollection(
                rows=[
                    LootMatrixRow(
                        loot_matrix_index=vendor.loot_matrix_index,
                        loot_table_index=loot_index_map[row.loot_table_index],
                        rarity_table_index=row.rarity_table_index,
                        percent=row.percent,
                        min_to_drop=row.min_to_drop,
                        max_to_drop=row.max_to_drop,
                        id=row.id,
                        flag_id=row.flag_id,
                        gate_version=row.gate_version,
                    )
                    for row in src_matrix.rows
                ],
                key_field="ui_key",
                label_prefix="LootMatrix",
                loaded_keys={vendor.loot_matrix_index},
                dirty=True,
            )

        src_table = src.components.get("VendorLootTable")
        if isinstance(src_table, RowCollection):
            for row in src_table.rows:
                if row.loot_table_index not in loot_index_map:
                    loot_index_map[row.loot_table_index] = self._reserve_next_int(
                        self._repo.generate_new_loot_table_index,
                        loot_table_indices,
                        label="loot_table_index",
                        object_id=new_id,
                    )
            loot_table_row_ids = self._collect_loot_table_row_ids(dup)
            dup.components["VendorLootTable"] = RowCollection(
                rows=[
                    LootTableRow(
                        itemid=row.itemid,
                        loot_table_index=loot_index_map[row.loot_table_index],
                        id=self._reserve_next_int(
                            self._repo.generate_new_loot_table_row_id,
                            loot_table_row_ids,
                            label="loot_table_row_id",
                            object_id=new_id,
                        ),
                        mission_drop=row.mission_drop,
                        sort_priority=row.sort_priority,
                    )
                    for row in src_table.rows
                ],
                key_field="id",
                label_prefix="LootTable",
                loaded_keys=set(loot_index_map.values()),
                dirty=True,
            )
        dup.components["VendorLootTableIndex"] = RowCollection(
            rows=[LootTableIndexRow(loot_table_index=index) for index in sorted(loot_index_map.values())],
            key_field="loot_table_index",
            label_prefix="LootTableIndex",
            loaded_keys=set(),
            dirty=bool(loot_index_map),
        )

    def _duplicate_destructible_state(self, src: NPC, dup: NPC, new_id: int) -> None:
        src_destructible = src.components.get("DestructibleComponent")
        if not isinstance(src_destructible, DestructibleComponent):
            return

        loot_matrix_indices = self._collect_loot_matrix_indices(dup)
        currency_indices = self._collect_currency_indices(dup)
        destructible = DestructibleComponent(
            id=self._repo.generate_new_component_id(new_id, "DestructibleComponent"),
            loot_matrix_index=(
                self._reserve_next_int(
                    self._repo.generate_new_loot_matrix_index,
                    loot_matrix_indices,
                    label="loot_matrix_index",
                    object_id=new_id,
                )
                if src_destructible.loot_matrix_index is not None else None
            ),
            currency_index=(
                self._reserve_next_int(
                    self._repo.generate_new_currency_index,
                    currency_indices,
                    label="currency_index",
                    object_id=new_id,
                )
                if src_destructible.currency_index is not None else None
            ),
        )
        self._copy_fields(
            src_destructible,
            destructible,
            exclude={"id", "loot_matrix_index", "currency_index"},
        )
        destructible.dirty = True
        dup.components["DestructibleComponent"] = destructible
        if destructible.loot_matrix_index is not None:
            dup.components["DestructibleLootMatrixIndex"] = RowCollection(
                rows=[LootMatrixIndexRow(loot_matrix_index=destructible.loot_matrix_index, in_npc_editor=True)],
                key_field="loot_matrix_index",
                label_prefix="LootMatrixIndex",
                loaded_keys=set(),
                dirty=True,
            )

        loot_index_map: dict[int, int] = {}
        loot_table_indices = self._collect_loot_table_indices(dup)
        src_matrix = src.components.get("DestructibleLootMatrix")
        if isinstance(src_matrix, RowCollection):
            for row in src_matrix.rows:
                if row.loot_table_index not in loot_index_map:
                    loot_index_map[row.loot_table_index] = self._reserve_next_int(
                        self._repo.generate_new_loot_table_index,
                        loot_table_indices,
                        label="loot_table_index",
                        object_id=new_id,
                    )
            dup.components["DestructibleLootMatrix"] = RowCollection(
                rows=[
                    LootMatrixRow(
                        loot_matrix_index=destructible.loot_matrix_index or 0,
                        loot_table_index=loot_index_map[row.loot_table_index],
                        rarity_table_index=row.rarity_table_index,
                        percent=row.percent,
                        min_to_drop=row.min_to_drop,
                        max_to_drop=row.max_to_drop,
                        id=row.id,
                        flag_id=row.flag_id,
                        gate_version=row.gate_version,
                    )
                    for row in src_matrix.rows
                ],
                key_field="ui_key",
                label_prefix="LootMatrix",
                loaded_keys={destructible.loot_matrix_index} if destructible.loot_matrix_index is not None else set(),
                dirty=True,
            )

        src_table = src.components.get("DestructibleLootTable")
        if isinstance(src_table, RowCollection):
            for row in src_table.rows:
                if row.loot_table_index not in loot_index_map:
                    loot_index_map[row.loot_table_index] = self._reserve_next_int(
                        self._repo.generate_new_loot_table_index,
                        loot_table_indices,
                        label="loot_table_index",
                        object_id=new_id,
                    )
            loot_table_row_ids = self._collect_loot_table_row_ids(dup)
            dup.components["DestructibleLootTable"] = RowCollection(
                rows=[
                    LootTableRow(
                        itemid=row.itemid,
                        loot_table_index=loot_index_map[row.loot_table_index],
                        id=self._reserve_next_int(
                            self._repo.generate_new_loot_table_row_id,
                            loot_table_row_ids,
                            label="loot_table_row_id",
                            object_id=new_id,
                        ),
                        mission_drop=row.mission_drop,
                        sort_priority=row.sort_priority,
                    )
                    for row in src_table.rows
                ],
                key_field="id",
                label_prefix="LootTable",
                loaded_keys=set(loot_index_map.values()),
                dirty=True,
            )
        dup.components["DestructibleLootTableIndex"] = RowCollection(
            rows=[LootTableIndexRow(loot_table_index=index) for index in sorted(loot_index_map.values())],
            key_field="loot_table_index",
            label_prefix="LootTableIndex",
            loaded_keys=set(),
            dirty=bool(loot_index_map),
        )

        src_currency = src.components.get("CurrencyTable")
        if isinstance(src_currency, RowCollection) and destructible.currency_index is not None:
            currency_row_ids = self._collect_currency_row_ids(dup)
            dup.components["CurrencyTable"] = RowCollection(
                rows=[
                    CurrencyTableRow(
                        currency_index=destructible.currency_index,
                        npcminlevel=row.npcminlevel,
                        minvalue=row.minvalue,
                        maxvalue=row.maxvalue,
                        id=self._reserve_next_int(
                            self._repo.generate_new_currency_row_id,
                            currency_row_ids,
                            label="currency_row_id",
                            object_id=new_id,
                        ),
                    )
                    for row in src_currency.rows
                ],
                key_field="id",
                label_prefix="CurrencyTable",
                loaded_keys={destructible.currency_index},
                dirty=True,
            )

    def _duplicate_mission_state(self, src: NPC, dup: NPC, new_id: int) -> None:
        src_mission_component = src.components.get("MissionNPCComponent")
        if not isinstance(src_mission_component, RowCollection):
            return

        mission_ids = self._collect_mission_ids(dup)
        mission_id_map: dict[int, int] = {}
        for row in src_mission_component.rows:
            if row.mission_id not in mission_id_map:
                mission_id_map[row.mission_id] = self._reserve_next_int(
                    self._repo.generate_new_mission_id,
                    mission_ids,
                    label="mission_id",
                    object_id=new_id,
                )
        if not mission_id_map:
            return

        mission_component_id = self._repo.generate_new_component_id(new_id, "MissionNPCComponent")
        dup.components["MissionNPCComponent"] = RowCollection(
            rows=[
                MissionNPCComponentRow(
                    id=mission_component_id,
                    mission_id=mission_id_map[row.mission_id],
                )
                for row in src_mission_component.rows
            ],
            key_field="mission_id",
            label_prefix="Mission",
            component_id=mission_component_id,
            loaded_keys={mission_component_id},
            dirty=True,
        )

        src_missions = src.components.get("Missions")
        if isinstance(src_missions, RowCollection):
            mission_rows: list[MissionRow] = []
            for row in src_missions.rows:
                mission_row_id = mission_id_map.get(row.id)
                if mission_row_id is None:
                    mission_row_id = self._reserve_next_int(
                        self._repo.generate_new_mission_id,
                        mission_ids,
                        label="mission_id",
                        object_id=new_id,
                    )
                    mission_id_map[row.id] = mission_row_id
                new_row = MissionRow(id=mission_row_id)
                self._copy_fields(row, new_row, exclude={"id"})
                if getattr(new_row, "offer_object_id", None) == src.object_id:
                    new_row.offer_object_id = new_id
                if getattr(new_row, "target_object_id", None) == src.object_id:
                    new_row.target_object_id = new_id
                mission_rows.append(new_row)
            dup.components["Missions"] = RowCollection(
                rows=mission_rows,
                key_field="id",
                label_prefix="Mission",
                loaded_keys=set(mission_id_map.values()),
                dirty=True,
            )

        src_tasks = src.components.get("MissionTasks")
        if isinstance(src_tasks, RowCollection):
            task_rows: list[MissionTaskRow] = []
            task_uids = self._collect_task_uids(dup)
            for row in src_tasks.rows:
                new_row = MissionTaskRow(
                    id=mission_id_map.get(row.id, row.id),
                    uid=self._reserve_next_int(
                        self._repo.generate_new_task_uid,
                        task_uids,
                        label="task_uid",
                        object_id=new_id,
                    ),
                )
                self._copy_fields(row, new_row, exclude={"id", "uid"})
                task_rows.append(new_row)
            dup.components["MissionTasks"] = RowCollection(
                rows=task_rows,
                key_field="uid",
                label_prefix="Task",
                loaded_keys=set(mission_id_map.values()),
                dirty=True,
            )

        src_text = src.components.get("MissionText")
        if isinstance(src_text, RowCollection):
            mission_text_rows: list[MissionTextRow] = []
            for row in src_text.rows:
                new_row = MissionTextRow(id=mission_id_map.get(row.id, row.id))
                self._copy_fields(row, new_row, exclude={"id"})
                mission_text_rows.append(new_row)
            dup.components["MissionText"] = RowCollection(
                rows=mission_text_rows,
                key_field="id",
                label_prefix="Text",
                loaded_keys=set(mission_id_map.values()),
                dirty=True,
            )

        src_email = src.components.get("MissionEmail")
        if isinstance(src_email, RowCollection):
            email_rows: list[MissionEmailRow] = []
            email_ids = self._collect_mission_email_ids(dup)
            for row in src_email.rows:
                new_row = MissionEmailRow(
                    id=self._reserve_next_int(
                        self._repo.generate_new_mission_email_id,
                        email_ids,
                        label="mission_email_id",
                        object_id=new_id,
                    ),
                    mission_id=mission_id_map.get(row.mission_id, row.mission_id),
                )
                self._copy_fields(row, new_row, exclude={"id", "mission_id"})
                email_rows.append(new_row)
            dup.components["MissionEmail"] = RowCollection(
                rows=email_rows,
                key_field="id",
                label_prefix="Email",
                loaded_keys=set(mission_id_map.values()),
                dirty=True,
            )
