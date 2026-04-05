from __future__ import annotations

import logging
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any

from Domain.domains import RowCollection
from Service.services import NPCService
from .gui import BaseObjectEntityTab

log = logging.getLogger(__name__)


class NPCTab(BaseObjectEntityTab):
    """Tab containing NPC related widgets."""

    HIDDEN_COMPONENTS: set[str] = {
        "VendorLootMatrixIndex",
        "VendorLootTableIndex",
        "DestructibleLootMatrixIndex",
        "DestructibleLootTableIndex",
    }

    COMPONENT_DISPLAY_NAMES: dict[str, str] = {
        "VendorLootMatrixIndex": "LootMatrixIndex (Vendor)",
        "VendorLootMatrix": "LootMatrix (Vendor)",
        "VendorLootTableIndex": "LootTableIndex (Vendor)",
        "VendorLootTable": "LootTable (Vendor)",
        "DestructibleLootMatrixIndex": "LootMatrixIndex (Destructible)",
        "DestructibleLootMatrix": "LootMatrix (Destructible)",
        "DestructibleLootTableIndex": "LootTableIndex (Destructible)",
        "DestructibleLootTable": "LootTable (Destructible)",
        "CurrencyTable": "CurrencyTable",
    }

    ROW_COLLECTION_SPECS: dict[str, tuple[str, str]] = {
        "InventoryComponent": ("itemid", "Item"),
        "MissionNPCComponent": ("mission_id", "Mission"),
        "Missions": ("id", "Mission"),
        "MissionTasks": ("uid", "Task"),
        "MissionText": ("id", "Text"),
        "MissionEmail": ("id", "Email"),
        "VendorLootMatrixIndex": ("loot_matrix_index", "LootMatrixIndex"),
        "VendorLootMatrix": ("ui_key", "LootMatrix"),
        "VendorLootTableIndex": ("loot_table_index", "LootTableIndex"),
        "VendorLootTable": ("id", "LootTable"),
        "DestructibleLootMatrixIndex": ("loot_matrix_index", "LootMatrixIndex"),
        "DestructibleLootMatrix": ("ui_key", "LootMatrix"),
        "DestructibleLootTableIndex": ("loot_table_index", "LootTableIndex"),
        "DestructibleLootTable": ("id", "LootTable"),
        "CurrencyTable": ("id", "CurrencyTable"),
    }

    DELETE_COMPONENT_GROUPS: dict[str, list[str]] = {
        "RenderComponent": ["RenderComponent"],
        "MinifigComponent": ["MinifigComponent"],
        "PhysicsComponent": ["PhysicsComponent"],
        "InventoryComponent": ["InventoryComponent"],
        "DestructibleComponent": [
            "DestructibleComponent",
            "DestructibleLootMatrixIndex",
            "DestructibleLootMatrix",
            "DestructibleLootTableIndex",
            "DestructibleLootTable",
            "CurrencyTable",
        ],
        "VendorComponent": [
            "VendorComponent",
            "VendorLootMatrixIndex",
            "VendorLootMatrix",
            "VendorLootTableIndex",
            "VendorLootTable",
        ],
        "MissionNPCComponent": [
            "MissionNPCComponent",
            "Missions",
            "MissionTasks",
            "MissionText",
            "MissionEmail",
        ],
        "ScriptComponent": ["ScriptComponent"],
    }

    def __init__(self, master: tk.Misc, service: NPCService):
        super().__init__(master)
        self._service = service
        self.tree_prefix = "npc"
        self._build_widgets()

    def _load_list_data(self) -> list[dict[str, int | str]]:
        return self._service.list_npcs(limit=None)

    def _is_component_visible(self, component_type: str, component: Any | None = None) -> bool:
        return component_type not in self.HIDDEN_COMPONENTS

    def _get_component_display_name(self, component_type: str) -> str:
        return self.COMPONENT_DISPLAY_NAMES.get(component_type, component_type)

    def _format_collection_row_text(self, component: Any, row: Any) -> str:
        prefix = self._get_component_label_prefix(component)

        if prefix == "Task":
            mission_id = getattr(row, "id", None)
            if mission_id is not None:
                # Number tasks within each mission using the current collection order
                # so the sidebar shows Task #1, Task #2, etc. instead of raw uid values.
                mission_rows = [
                    task_row
                    for task_row in self._get_component_rows(component)
                    if getattr(task_row, "id", None) == mission_id
                ]
                for task_number, task_row in enumerate(mission_rows, start=1):
                    if task_row is row:
                        return f"Mission {mission_id} Task #{task_number}"

                row_uid = getattr(row, "uid", None)
                if row_uid is not None:
                    for task_number, task_row in enumerate(mission_rows, start=1):
                        if getattr(task_row, "uid", None) == row_uid:
                            return f"Mission {mission_id} Task #{task_number}"

                return f"Mission {mission_id} Task"

        if prefix == "Text":
            mission_id = getattr(row, "id", None)
            if mission_id is not None:
                return f"Mission {mission_id} Text"

        if prefix == "LootMatrix":
            loot_matrix_index = getattr(row, "loot_matrix_index", None)
            if loot_matrix_index is not None:
                return f"LootMatrix {loot_matrix_index}"

        if prefix == "LootTable":
            item_id = getattr(row, "itemid", None)
            if item_id is not None:
                return f"LootTable Item: {item_id}"

        return super()._format_collection_row_text(component, row)

    def _build_widgets(self) -> None:
        paned = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        sidebar = ttk.Frame(paned, width=260)

        create_row = ttk.Frame(sidebar)
        create_row.pack(fill=tk.X, padx=5, pady=(6, 2))
        ttk.Label(create_row, text="ID:").pack(side=tk.LEFT)
        self.create_id_var = tk.StringVar()
        id_entry = ttk.Entry(create_row, textvariable=self.create_id_var, width=12)
        id_entry.pack(side=tk.LEFT, padx=(4, 4))
        self._add_tooltip(id_entry, "Optional. Unsigned integer up to 2147483647. Leave empty to auto-assign.")

        ttk.Button(create_row, text="Create Vendor", command=self._on_create_vendor_npc).pack(side=tk.LEFT, padx=(4, 0))
        ttk.Button(create_row, text="Create Mission", command=self._on_create_mission_npc).pack(side=tk.LEFT, padx=(4, 0))
        dup_btn = ttk.Button(create_row, text="Duplicate", command=self._on_duplicate_npc)
        dup_btn.pack(side=tk.LEFT, padx=(4, 0))
        self._add_tooltip(dup_btn, "Duplicate the selected NPC. Uses the ID field if provided; otherwise auto-assigns.")

        undo_row = ttk.Frame(sidebar)
        undo_row.pack(fill=tk.X, padx=5, pady=(2, 6))
        self.undo_btn = ttk.Button(undo_row, text="Undo local deletes", command=self._undo_local_deletes)
        self.undo_btn.pack(side=tk.LEFT)
        try:
            self.undo_btn.configure(state=tk.DISABLED)
        except Exception:
            pass

        search_bar = ttk.Frame(sidebar)
        search_bar.pack(fill=tk.X, padx=5, pady=(0, 5))
        ttk.Label(search_bar, text="Search:").pack(side=tk.LEFT)
        search_entry = ttk.Entry(search_bar, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 4))
        self._search_after_id = None

        def _do_search(_e=None):
            self._apply_current_form_changes()
            self._rebuild_list_tree()

        def _debounced_search(*_args):
            try:
                if self._search_after_id is not None:
                    self.after_cancel(self._search_after_id)
            except Exception:
                pass
            self._search_after_id = self.after(150, _do_search)

        search_entry.bind("<Return>", _do_search)
        self.search_var.trace_add("write", _debounced_search)
        self._build_sort_bar(sidebar)

        tree_container = ttk.Frame(sidebar)
        tree_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        vsb = ttk.Scrollbar(tree_container, orient="vertical")
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree = ttk.Treeview(tree_container, show="tree", yscrollcommand=vsb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.configure(command=self.tree.yview)

        self._rebuild_list_tree()
        self.tree.bind("<<TreeviewSelect>>", self._on_list_node_select)
        self.tree.bind("<<TreeviewOpen>>", self._on_list_node_expanded)
        self.tree.bind("<Button-3>", self._on_tree_context_menu)
        self.tree.bind("<Button-1>", lambda e: None, add=True)

        self.detail = ttk.Frame(paned)
        self.detail_label = ttk.Label(self.detail, text="Select an NPC or component to edit")
        self.detail_label.pack(padx=10, pady=5, anchor=tk.NW)

        toggle_bar = ttk.Frame(self.detail)
        toggle_bar.pack(fill=tk.X, padx=10, pady=(0, 5))
        self.show_advanced_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            toggle_bar,
            text="Show advanced fields",
            variable=self.show_advanced_var,
            command=self._refresh_form,
        ).pack(side=tk.LEFT, anchor=tk.W)

        self.form_container = ttk.Frame(self.detail)
        self.form_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.save_button = ttk.Button(
            self.detail,
            text="Save",
            command=self._on_save_all,
            state=tk.DISABLED,
        )
        self.save_button.pack(padx=10, pady=10, anchor=tk.SE)

        self.current_object = None
        self.current_component_type: str | None = None

        paned.add(sidebar, weight=1)
        paned.add(self.detail, weight=4)

        status_bar = ttk.Frame(self)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        self.unsaved_label = ttk.Label(status_bar, text="", foreground="#d97706")
        self.unsaved_label.pack(side=tk.LEFT, padx=8, pady=(0, 4))
        self._update_unsaved_indicator()
        self._update_undo_button_state()

    def _parse_optional_id_from_entry(self) -> int | None:
        raw_id = (self.create_id_var.get() or "").strip() if hasattr(self, "create_id_var") else ""
        if raw_id == "":
            return None
        if not raw_id.isdigit():
            raise ValueError("ID must be an unsigned integer (digits only).")
        provided_id = int(raw_id)
        if provided_id <= 0:
            raise ValueError("ID must be a positive unsigned integer.")
        if provided_id > 2_147_483_647:
            raise ValueError("ID exceeds 32-bit signed integer maximum (2147483647).")
        return provided_id

    def _select_npc_target(self, npc: Any, component_type: str = "object", grandchild_iid: str | None = None) -> None:
        self._object_cache[npc.object_id] = npc
        root_iid = self._refresh_object_branch(npc.object_id, npc)
        if root_iid is None:
            self._list_data = []
            self._rebuild_list_tree()
            root_iid = self._refresh_object_branch(npc.object_id, npc)
        if root_iid is None:
            return

        target_iid = root_iid
        if component_type != "object":
            child_iid = f"{root_iid}:{component_type}"
            if self.tree.exists(child_iid):
                target_iid = child_iid
                try:
                    self.tree.item(root_iid, open=True)
                except Exception:
                    pass
            if grandchild_iid is not None:
                row_iid = f"{child_iid}:{grandchild_iid}"
                if self.tree.exists(row_iid):
                    target_iid = row_iid
                    try:
                        self.tree.item(child_iid, open=True)
                    except Exception:
                        pass

        try:
            self.tree.selection_set(target_iid)
            self.tree.focus(target_iid)
            self.tree.see(target_iid)
        except Exception:
            pass

        self.current_object = npc
        self.current_component_type = component_type
        self._last_grandchild_iid = grandchild_iid
        self._build_form_for(component_type, grandchild_iid)
        self._update_unsaved_indicator()

    def _clear_id_entry(self) -> None:
        try:
            self.create_id_var.set("")
        except Exception:
            pass

    def _get_selected_object_id(self) -> int | None:
        sel = self.tree.selection()
        if not sel:
            return None
        iid = sel[0]
        parent_iid = iid.split(":", 1)[0]
        try:
            return int(parent_iid.split("-", 1)[1])
        except Exception:
            return None

    def _ensure_collection(self, obj: Any, component_key: str) -> RowCollection:
        existing = obj.components.get(component_key)
        if isinstance(existing, RowCollection):
            return existing
        key_field, label_prefix = self.ROW_COLLECTION_SPECS[component_key]
        collection = RowCollection(rows=[], key_field=key_field, label_prefix=label_prefix)
        obj.components[component_key] = collection
        return collection

    def _restore_rows(self, obj: Any, component_key: str, rows: list[Any], dirty_before: bool = False) -> None:
        collection = self._ensure_collection(obj, component_key)
        key_field = self._get_component_key_field(collection)
        existing = {getattr(row, key_field, None) for row in self._get_component_rows(collection)}
        restored_rows = self._get_component_rows(collection)
        for row in rows:
            key = getattr(row, key_field, None)
            if key in existing:
                continue
            restored_rows.append(row)
        self._set_component_rows(collection, restored_rows)
        collection.dirty = dirty_before

    def _queue_deleted_components(self, object_id: int, component_type: str, removed_components: dict[str, Any]) -> None:
        target_component = removed_components.get(component_type)
        if not hasattr(self, "_deleted_components"):
            self._deleted_components = []
        self._deleted_components.append(
            {
                "type": component_type,
                "component_id": getattr(target_component, "id", None) or getattr(target_component, "component_id", None),
                "object_id": object_id,
                "components": removed_components,
            }
        )

    def _queue_deleted_row(self, payload: dict[str, Any]) -> None:
        if not hasattr(self, "_deleted_rows"):
            self._deleted_rows = []
        self._deleted_rows.append(payload)

    def _mark_tree_change(self) -> None:
        self._has_unsaved_changes = True
        self._update_unsaved_indicator()
        self._update_undo_button_state()

    def _on_create_vendor_npc(self) -> None:
        try:
            npc = self._service.create_default_vendor_npc(self._parse_optional_id_from_entry())
        except ValueError as exc:
            messagebox.showerror("Invalid ID", str(exc))
            return
        except Exception as exc:
            log.exception("Failed to create vendor NPC")
            messagebox.showerror("Create failed", str(exc))
            return
        log.info("Created vendor NPC object_id=%s", getattr(npc, "object_id", None))
        self._clear_id_entry()
        self._select_npc_target(npc)

    def _on_create_mission_npc(self) -> None:
        try:
            npc = self._service.create_default_mission_npc(self._parse_optional_id_from_entry())
        except ValueError as exc:
            messagebox.showerror("Invalid ID", str(exc))
            return
        except Exception as exc:
            log.exception("Failed to create mission NPC")
            messagebox.showerror("Create failed", str(exc))
            return
        log.info("Created mission NPC object_id=%s", getattr(npc, "object_id", None))
        self._clear_id_entry()
        self._select_npc_target(npc)

    def _on_duplicate_npc(self) -> None:
        source_id = self._get_selected_object_id()
        if source_id is None:
            messagebox.showerror("Duplicate failed", "Select an NPC to duplicate from the list.")
            return
        try:
            dest_id = self._parse_optional_id_from_entry()
        except ValueError as exc:
            messagebox.showerror("Invalid ID", str(exc))
            return
        try:
            npc = self._service.duplicate_npc(source_id, dest_id)
        except Exception as exc:
            log.exception("Failed duplicating NPC source_object_id=%s", source_id)
            messagebox.showerror("Duplicate failed", str(exc))
            return
        log.info("Duplicated NPC source_object_id=%s target_object_id=%s", source_id, getattr(npc, "object_id", None))
        self._clear_id_entry()
        self._select_npc_target(npc)

    def get_root_delete_label(self) -> str | None:
        return "Delete NPC (local)"

    def on_delete_root_local(self, object_id: int, iid: str) -> None:
        try:
            text = self.tree.item(iid, "text") or ""
        except Exception:
            text = ""
        if not messagebox.askyesno(
            "Delete NPC",
            f"Delete {text}?\n\nThis removes it from the view now and will delete it permanently when you press Save.",
            icon=messagebox.WARNING,
            default=messagebox.NO,
        ):
            return
        if not hasattr(self, "_deleted_root_ids"):
            self._deleted_root_ids = set()
        self._deleted_root_ids.add(int(object_id))
        log.info("Queued local NPC delete object_id=%s", object_id)
        try:
            self.tree.delete(iid)
        except Exception:
            pass
        if not self.tree.selection():
            self.current_object = None
            self.current_component_type = None
            self._show_message("Select an NPC or component to edit")
        self._rebuild_list_tree()
        self._update_undo_button_state()

    def get_root_add_component_actions(self, obj: Any) -> list[tuple[str, Any, bool]]:
        if obj is None:
            return []
        existing = set((getattr(obj, "components", {}) or {}).keys())

        def _select(component_type: str = "object", grandchild_iid: str | None = None) -> None:
            self._refresh_object_branch(obj.object_id, obj)
            self._select_npc_target(obj, component_type, grandchild_iid)
            self._mark_tree_change()

        actions: list[tuple[str, Any, bool]] = []

        def _add_render():
            self._service.add_render_component(obj)
            _select("RenderComponent")

        def _add_minifig():
            self._service.add_minifig_component(obj)
            _select("MinifigComponent")

        def _add_physics():
            self._service.add_physics_component(obj)
            _select("PhysicsComponent")

        def _add_inventory():
            self._service.ensure_inventory_component(obj)
            _select("InventoryComponent")

        def _add_destructible():
            self._service.add_destructible_component(obj)
            _select("DestructibleComponent")

        def _add_vendor():
            self._service.add_vendor_component(obj)
            _select("VendorComponent")

        def _add_mission_bundle():
            row = self._service.add_mission_bundle(obj)
            self._refresh_object_branch(obj.object_id, obj)
            self._select_npc_target(obj, "MissionNPCComponent", str(row.mission_id))
            self._mark_tree_change()

        def _add_script():
            self._service.add_script_component(obj)
            _select("ScriptComponent")

        actions.append(("Render Component", _add_render, "RenderComponent" not in existing))
        actions.append(("Minifig Component", _add_minifig, "MinifigComponent" not in existing))
        actions.append(("Physics Component", _add_physics, "PhysicsComponent" not in existing))
        actions.append(("Inventory Component", _add_inventory, "InventoryComponent" not in existing))
        actions.append(("Destructible Component", _add_destructible, "DestructibleComponent" not in existing))
        actions.append(("Vendor Component", _add_vendor, "VendorComponent" not in existing))
        actions.append(("Mission Bundle", _add_mission_bundle, True))
        actions.append(("Script Component", _add_script, "ScriptComponent" not in existing))
        return actions

    def get_component_delete_action(self, comp_name: str, obj: Any, iid: str, parent_iid: str) -> tuple[str, Any] | None:
        if comp_name not in self.DELETE_COMPONENT_GROUPS:
            return None

        def _delete_component_local() -> None:
            try:
                obj_id = int(parent_iid.split("-", 1)[1])
            except Exception:
                return
            target = obj or self._ctx_get_cached_or_load(parent_iid, obj_id)  # type: ignore[attr-defined]
            if target is None:
                messagebox.showerror("Delete failed", "Could not load NPC to modify component.")
                return
            if not messagebox.askyesno(
                "Delete component",
                f"Delete {comp_name} from NPC {obj_id}?\n\nThis removes it now and will delete it permanently when you press Save.",
                icon=messagebox.WARNING,
                default=messagebox.NO,
            ):
                return

            removed: dict[str, Any] = {}
            for key in self.DELETE_COMPONENT_GROUPS[comp_name]:
                component = target.components.pop(key, None)
                if component is not None:
                    removed[key] = component
            if not removed:
                return
            log.info("Queued local NPC component delete object_id=%s component=%s", obj_id, comp_name)
            self._queue_deleted_components(obj_id, comp_name, removed)
            self._select_npc_target(target)
            self._mark_tree_change()

        return ("Delete component (local)", _delete_component_local)

    def get_component_add_subitem_actions(self, comp_name: str, obj: Any, iid: str, parent_iid: str) -> list[tuple[str, Any]]:
        if obj is None:
            return []

        def _add_inventory_row() -> None:
            row = self._service.add_inventory_row(obj)
            self._select_npc_target(obj, "InventoryComponent", str(row.itemid))
            self._mark_tree_change()

        def _add_mission_bundle(target_component: str) -> None:
            row = self._service.add_mission_bundle(obj)
            self._select_npc_target(obj, target_component, str(row.mission_id))
            self._mark_tree_change()

        def _add_task() -> None:
            row = self._service.add_task_row(obj)
            self._select_npc_target(obj, "MissionTasks", str(row.uid))
            self._mark_tree_change()

        def _add_email() -> None:
            row = self._service.add_email_row(obj)
            self._select_npc_target(obj, "MissionEmail", str(row.id))
            self._mark_tree_change()

        def _add_vendor_loot(target_component: str) -> None:
            if target_component == "VendorLootTable":
                matrix_row, loot_row = self._service.add_loot_table_row(obj, "vendor")
            else:
                matrix_row = self._service.add_loot_entry(obj, "vendor")
            if target_component == "VendorLootTable":
                self._select_npc_target(obj, "VendorLootTable", str(loot_row.id))
            else:
                self._select_npc_target(obj, "VendorLootMatrix", str(matrix_row.ui_key))
            self._mark_tree_change()

        def _add_destructible_loot(target_component: str) -> None:
            if target_component == "DestructibleLootTable":
                matrix_row, loot_row = self._service.add_loot_table_row(obj, "destructible")
            else:
                matrix_row = self._service.add_loot_entry(obj, "destructible")
            if target_component == "DestructibleLootTable":
                self._select_npc_target(obj, "DestructibleLootTable", str(loot_row.id))
            else:
                self._select_npc_target(obj, "DestructibleLootMatrix", str(matrix_row.ui_key))
            self._mark_tree_change()

        def _add_currency() -> None:
            row = self._service.add_currency_row(obj)
            self._select_npc_target(obj, "CurrencyTable", str(row.id))
            self._mark_tree_change()

        action_map: dict[str, list[tuple[str, Any]]] = {
            "InventoryComponent": [("Add inventory row", _add_inventory_row)],
            "MissionNPCComponent": [("Add mission bundle", lambda: _add_mission_bundle("MissionNPCComponent"))],
            "Missions": [("Add mission bundle", lambda: _add_mission_bundle("Missions"))],
            "MissionText": [("Add mission bundle", lambda: _add_mission_bundle("MissionText"))],
            "MissionTasks": [("Add task row", _add_task)],
            "MissionEmail": [("Add email row", _add_email)],
            "VendorLootMatrix": [("Add loot entry", lambda: _add_vendor_loot("VendorLootMatrix"))],
            "VendorLootTable": [("Add loot entry", lambda: _add_vendor_loot("VendorLootTable"))],
            "DestructibleLootMatrix": [("Add loot entry", lambda: _add_destructible_loot("DestructibleLootMatrix"))],
            "DestructibleLootTable": [("Add loot entry", lambda: _add_destructible_loot("DestructibleLootTable"))],
            "CurrencyTable": [("Add currency row", _add_currency)],
        }
        return action_map.get(comp_name, [])

    def _delete_simple_collection_row(self, obj: Any, component_key: str, parent_iid: str, row_key: str) -> None:
        collection = obj.components.get(component_key)
        if not self._is_row_collection_component(collection):
            return
        row = self._find_component_row(collection, row_key)
        if row is None:
            return
        if not messagebox.askyesno(
            "Delete row",
            f"Delete {self._format_collection_row_text(collection, row)} from NPC {obj.object_id}?",
            icon=messagebox.WARNING,
            default=messagebox.NO,
        ):
            return
        key_field = self._get_component_key_field(collection)
        deleted_key = getattr(row, key_field, None)
        dirty_before = bool(getattr(collection, "dirty", False))
        remaining = [item for item in self._get_component_rows(collection) if getattr(item, key_field, None) != deleted_key]
        self._set_component_rows(collection, remaining)
        collection.dirty = True
        self._queue_deleted_row(
            {
                "kind": "row",
                "object_id": obj.object_id,
                "component_key": component_key,
                "rows": [row],
                "dirty_before": dirty_before,
            }
        )
        log.info("Queued local NPC row delete object_id=%s component=%s row_key=%s", obj.object_id, component_key, deleted_key)
        self._select_npc_target(obj, component_key)
        self._mark_tree_change()

    def _delete_mission_bundle(self, obj: Any, component_key: str, mission_id: int) -> None:
        if not messagebox.askyesno(
            "Delete mission bundle",
            f"Delete mission bundle {mission_id} from NPC {obj.object_id}?\n\nAll linked mission rows will be removed locally until you save.",
            icon=messagebox.WARNING,
            default=messagebox.NO,
        ):
            return
        snapshot: dict[str, list[Any]] = {}
        dirty_before: dict[str, bool] = {}
        for key, attr in (
            ("MissionNPCComponent", "mission_id"),
            ("Missions", "id"),
            ("MissionTasks", "id"),
            ("MissionText", "id"),
            ("MissionEmail", "mission_id"),
        ):
            collection = obj.components.get(key)
            if not self._is_row_collection_component(collection):
                continue
            dirty_before[key] = bool(getattr(collection, "dirty", False))
            rows = [row for row in self._get_component_rows(collection) if getattr(row, attr, None) == mission_id]
            if rows:
                snapshot[key] = rows
        if not snapshot:
            return
        self._service.remove_mission_bundle(obj, mission_id)
        self._queue_deleted_row(
            {
                "kind": "mission_bundle",
                "object_id": obj.object_id,
                "mission_id": mission_id,
                "rows": snapshot,
                "dirty_before": dirty_before,
            }
        )
        log.info("Queued local NPC mission delete object_id=%s mission_id=%s", obj.object_id, mission_id)
        self._select_npc_target(obj, component_key)
        self._mark_tree_change()

    def _delete_loot_entry(self, obj: Any, component_key: str, family: str, loot_table_index: int) -> None:
        if not messagebox.askyesno(
            "Delete loot entry",
            f"Delete loot entry {loot_table_index} from NPC {obj.object_id}?",
            icon=messagebox.WARNING,
            default=messagebox.NO,
        ):
            return
        matrix_key, table_index_key, table_key = (
            ("VendorLootMatrix", "VendorLootTableIndex", "VendorLootTable")
            if family == "vendor"
            else ("DestructibleLootMatrix", "DestructibleLootTableIndex", "DestructibleLootTable")
        )
        snapshot: dict[str, list[Any]] = {}
        dirty_before: dict[str, bool] = {}
        for key in (matrix_key, table_index_key, table_key):
            collection = obj.components.get(key)
            if not self._is_row_collection_component(collection):
                continue
            dirty_before[key] = bool(getattr(collection, "dirty", False))
            rows = [
                row
                for row in self._get_component_rows(collection)
                if getattr(row, "loot_table_index", None) == loot_table_index
            ]
            if rows:
                snapshot[key] = rows
        if not snapshot:
            return
        self._service.remove_loot_entry(obj, family, loot_table_index)
        self._queue_deleted_row(
            {
                "kind": "loot_entry",
                "object_id": obj.object_id,
                "family": family,
                "loot_table_index": loot_table_index,
                "rows": snapshot,
                "dirty_before": dirty_before,
            }
        )
        log.info(
            "Queued local NPC loot delete object_id=%s family=%s loot_table_index=%s",
            obj.object_id,
            family,
            loot_table_index,
        )
        self._select_npc_target(obj, component_key)
        self._mark_tree_change()

    def _delete_loot_table_row(self, obj: Any, component_key: str, family: str, row_id: int) -> None:
        if not messagebox.askyesno(
            "Delete loot item",
            f"Delete loot item {row_id} from NPC {obj.object_id}?",
            icon=messagebox.WARNING,
            default=messagebox.NO,
        ):
            return
        table_key = "VendorLootTable" if family == "vendor" else "DestructibleLootTable"
        collection = obj.components.get(table_key)
        if not self._is_row_collection_component(collection):
            return
        dirty_before = bool(getattr(collection, "dirty", False))
        rows = [row for row in self._get_component_rows(collection) if getattr(row, "id", None) == row_id]
        if not rows:
            return
        self._service.remove_loot_table_row(obj, family, row_id)
        self._queue_deleted_row(
            {
                "kind": "loot_row",
                "object_id": obj.object_id,
                "family": family,
                "row_id": row_id,
                "rows": {table_key: rows},
                "dirty_before": {table_key: dirty_before},
            }
        )
        log.info(
            "Queued local NPC loot row delete object_id=%s family=%s loot_row_id=%s",
            obj.object_id,
            family,
            row_id,
        )
        self._select_npc_target(obj, component_key)
        self._mark_tree_change()

    def get_grandchild_delete_action(self, parts: list[str], obj: Any) -> tuple[str, Any] | None:
        if len(parts) != 3 or obj is None:
            return None

        component_key = parts[1]
        row_key = parts[2]
        collection = obj.components.get(component_key)
        if not self._is_row_collection_component(collection):
            return None
        row = self._find_component_row(collection, row_key)
        if row is None:
            return None

        if component_key in {"InventoryComponent", "CurrencyTable"}:
            return (
                "Delete row (local)",
                lambda: self._delete_simple_collection_row(obj, component_key, parts[0], row_key),
            )

        if component_key in {"MissionNPCComponent", "Missions", "MissionTasks", "MissionText", "MissionEmail"}:
            mission_id = None
            if component_key == "MissionNPCComponent":
                mission_id = getattr(row, "mission_id", None)
            elif component_key == "MissionEmail":
                mission_id = getattr(row, "mission_id", None)
            else:
                mission_id = getattr(row, "id", None)
            if mission_id is None:
                return None
            return ("Delete mission bundle (local)", lambda: self._delete_mission_bundle(obj, component_key, int(mission_id)))

        if component_key in {"VendorLootMatrix", "DestructibleLootMatrix"}:
            loot_table_index = getattr(row, "loot_table_index", None)
            if loot_table_index is None:
                return None
            family = "vendor" if component_key.startswith("Vendor") else "destructible"
            return ("Delete loot entry (local)", lambda: self._delete_loot_entry(obj, component_key, family, int(loot_table_index)))

        if component_key in {"VendorLootTable", "DestructibleLootTable"}:
            loot_row_id = getattr(row, "id", None)
            if loot_row_id is None:
                return None
            family = "vendor" if component_key.startswith("Vendor") else "destructible"
            return ("Delete loot item (local)", lambda: self._delete_loot_table_row(obj, component_key, family, int(loot_row_id)))

        return None

    def _undo_local_deletes(self) -> None:
        comp_queue = getattr(self, "_deleted_components", []) or []
        row_queue = getattr(self, "_deleted_rows", []) or []

        for item in list(comp_queue):
            oid = item.get("object_id")
            if oid is None:
                continue
            obj = self._object_cache.get(oid)
            if obj is None:
                try:
                    obj = self._service.get(int(oid))
                except Exception:
                    obj = None
                if obj is not None:
                    self._object_cache[int(oid)] = obj
            if obj is None:
                continue
            for key, component in (item.get("components") or {}).items():
                obj.components[key] = component
            comp_queue.remove(item)

        for item in list(row_queue):
            oid = item.get("object_id")
            if oid is None:
                continue
            obj = self._object_cache.get(oid)
            if obj is None:
                try:
                    obj = self._service.get(int(oid))
                except Exception:
                    obj = None
                if obj is not None:
                    self._object_cache[int(oid)] = obj
            if obj is None:
                continue

            kind = item.get("kind")
            if kind == "row":
                self._restore_rows(
                    obj,
                    str(item["component_key"]),
                    list(item.get("rows") or []),
                    bool(item.get("dirty_before", False)),
                )
            elif kind in {"mission_bundle", "loot_entry", "loot_row"}:
                dirty_before = item.get("dirty_before") or {}
                for component_key, rows in (item.get("rows") or {}).items():
                    self._restore_rows(
                        obj,
                        component_key,
                        list(rows or []),
                        bool(dirty_before.get(component_key, False)),
                    )
            row_queue.remove(item)

        try:
            if hasattr(self, "_deleted_root_ids"):
                self._deleted_root_ids.clear()
        except Exception:
            pass

        self._has_unsaved_changes = False
        self._rebuild_list_tree()
        self._update_unsaved_indicator()
        self._update_undo_button_state()
        try:
            messagebox.showinfo("Undo", "Local deletes have been undone.")
        except Exception:
            pass

