from __future__ import annotations

import json
import logging
import re
import sqlite3
import tkinter as tk
from copy import deepcopy
from tkinter import ttk, messagebox
from enum import Enum, IntEnum, StrEnum
from pathlib import Path

from Service.services import ItemService, NPCService
from metadata import component_field_metadata
from dataclasses import fields, is_dataclass
from typing import Any, Callable, get_args, get_origin
from Domain.domains import ColorType  # Color enum used for item color field and swatch

# Import Item for type hinting
from Service.services import Item

log = logging.getLogger(__name__)

class BaseObjectEntityTab(ttk.Frame):
    """Base class for a tab object entries in the notebook."""

    def __init__(self, master: tk.Misc):
        super().__init__(master)
        self.object_type = None

        # Cache of loaded domain objects (keyed by object_id) so in-memory edits
        # remain when navigating away and back without saving to DB yet.
        self._object_cache: dict[int, Any] = {}

        # Generic list (left pane) sorting state and data cache
        # Subclasses should provide data via _load_list_data(); base will sort/build UI.
        self.sort_by_var = tk.StringVar(value="id")      # 'id' or 'name'
        self.sort_desc_var = tk.BooleanVar(value=False)    # False=ascending, True=descending
        self._list_data: list[dict[str, int | str]] = []   # cached rows for left tree
        self.tree_prefix: str = ""  # e.g., 'item' or 'npc' - subclasses set this
        # Search/filter state shared by subclasses
        self.search_var = tk.StringVar(value="")
        # Unsaved changes state (UI indicator updated via _update_unsaved_indicator)
        self._has_unsaved_changes = False
        # Track which text variables are currently showing the special NULL placeholder
        # so we can interpret it as None on save and manage styling/behavior.
        # Keyed by the tk.Variable instance used by a field in the form.
        # Using a plain dict to keep compatibility with older Python/linters
        self._null_var_flags = {}
        self._lookup_cache: dict[str, list[dict[str, Any]]] = {}

    def _var_key(self, var: tk.Variable) -> str:
        """Return a stable, hashable key for a tk.Variable used in dicts.

        Uses the Tcl variable name when available (e.g., 'PY_VAR42'),
        otherwise falls back to str(var) or id(var).
        """
        try:
            key = getattr(var, "_name", None)
            if key:
                return str(key)
        except Exception:
            pass
        try:
            return str(var)
        except Exception:
            return str(id(var))

    def _normalize_field_type(self, field_type: Any) -> Any:
        """Collapse Optional/union annotations down to the concrete editable type."""
        if field_type is None:
            return None
        if isinstance(field_type, str):
            type_name = field_type.replace(" ", "")
            if type_name.startswith("Optional[") and type_name.endswith("]"):
                return self._normalize_field_type(type_name[9:-1])
            if "|" in type_name:
                members = [member for member in type_name.split("|") if member not in {"None", "NoneType"}]
                if len(members) == 1:
                    return self._normalize_field_type(members[0])
            builtin_types = {
                "int": int,
                "float": float,
                "bool": bool,
                "str": str,
                "ColorType": ColorType,
            }
            return builtin_types.get(type_name, globals().get(type_name, field_type))

        origin = get_origin(field_type)
        if origin is not None:
            members = [member for member in get_args(field_type) if member is not type(None)]
            if len(members) == 1:
                return self._normalize_field_type(members[0])
        return field_type

    def _is_row_collection_component(self, component: Any) -> bool:
        return bool(component is not None and hasattr(component, "rows") and hasattr(component, "key_field"))

    def _get_component_rows(self, component: Any) -> list[Any]:
        rows = getattr(component, "rows", None)
        return list(rows or [])

    def _set_component_rows(self, component: Any, rows: list[Any]) -> None:
        # ObjectSkills exposes a read-only rows property backed by skills.
        if hasattr(component, "skills"):
            component.skills = rows
            return
        component.rows = rows

    def _get_component_key_field(self, component: Any) -> str:
        return str(getattr(component, "key_field", "id"))

    def _get_component_label_prefix(self, component: Any) -> str:
        return str(getattr(component, "label_prefix", "Row"))

    def _get_collection_row_key(self, component: Any, row: Any) -> Any:
        return getattr(row, self._get_component_key_field(component), None)

    def _get_collection_row_display_key(self, component: Any, row: Any) -> Any:
        # Some collections use a temporary UI key before the database assigns a
        # persisted identity. In that case we keep tree identity stable with the
        # UI key, but show a cleaner display key in labels/titles.
        display_key = getattr(row, "display_key", None)
        if display_key is not None:
            return display_key
        return self._get_collection_row_key(component, row)

    def _iter_collection_parent_iids(self, obj_id: int, component_type: str) -> list[str]:
        return [
            f"{self._make_root_iid(obj_id)}:{component_type}",
            f"{self._make_root_iid_alt(obj_id)}:{component_type}",
        ]

    def _find_collection_row_iid(self, obj_id: int, component_type: str, row_key: Any) -> str | None:
        for parent_iid in self._iter_collection_parent_iids(obj_id, component_type):
            row_iid = f"{parent_iid}:{row_key}"
            if self.tree.exists(row_iid):
                return row_iid
        return None

    def _parse_collection_key(self, component: Any, raw_key: Any) -> Any:
        key_field = self._get_component_key_field(component)
        rows = self._get_component_rows(component)
        for row in rows:
            value = self._get_collection_row_key(component, row)
            if value is None:
                continue
            if isinstance(value, bool):
                text = str(raw_key).strip().lower()
                if text in {"true", "1", "yes"}:
                    return True
                if text in {"false", "0", "no"}:
                    return False
            if isinstance(value, int):
                try:
                    return int(raw_key)
                except Exception:
                    return raw_key
            if isinstance(value, float):
                try:
                    return float(raw_key)
                except Exception:
                    return raw_key
            return raw_key
        try:
            return int(raw_key)
        except Exception:
            return raw_key

    def _find_component_row(self, component: Any, raw_key: Any) -> Any | None:
        key_field = self._get_component_key_field(component)
        parsed_key = self._parse_collection_key(component, raw_key)
        for row in self._get_component_rows(component):
            value = self._get_collection_row_key(component, row)
            if value == parsed_key or str(value) == str(raw_key):
                return row
        return None

    def _format_collection_row_text(self, component: Any, row: Any) -> str:
        prefix = self._get_component_label_prefix(component)
        return f"{prefix} {self._get_collection_row_display_key(component, row)}"

    def _get_component_display_name(self, component_type: str) -> str:
        return component_type

    def _is_component_visible(self, component_type: str, component: Any | None = None) -> bool:
        return True

    def _resolve_form_target(
        self,
        obj: Any,
        component_type: str,
        grandchild_iid: str | None = None,
    ) -> dict[str, Any]:
        if obj is None:
            return {"message": "No object loaded"}

        if component_type == "object":
            return {
                "target": obj,
                "exclude": {"components", "dirty"},
                "title": f"GameObject: ({obj.object_id}) {obj.name}",
                "metadata_key": "GameObject",
                "collection": None,
                "key_field": None,
                "original_key": None,
            }

        component = obj.components.get(component_type)
        if component is None:
            return {"message": f"Component '{component_type}' not present"}
        if not self._is_component_visible(component_type, component):
            display_name = self._get_component_display_name(component_type)
            return {"message": f"{display_name} is managed automatically."}

        display_name = self._get_component_display_name(component_type)

        if self._is_row_collection_component(component):
            key_field = self._get_component_key_field(component)
            row = None
            if grandchild_iid is None:
                rows = self._get_component_rows(component)
                if not rows:
                    return {"message": "No rows available"}
                row = rows[0]
                grandchild_iid = str(self._get_collection_row_key(component, row) or "")
            else:
                row = self._find_component_row(component, grandchild_iid)
            if row is None:
                return {"message": f"Row '{grandchild_iid}' not found"}
            return {
                "target": row,
                "exclude": {"dirty"},
                "title": f"{display_name} row {self._get_collection_row_display_key(component, row)} of {obj.object_id}",
                "metadata_key": row.__class__.__name__,
                "collection": component,
                "key_field": key_field,
                "original_key": self._get_collection_row_key(component, row),
                "resolved_grandchild_iid": str(self._get_collection_row_key(component, row) or ""),
            }

        return {
            "target": component,
            "exclude": {"dirty"},
            "title": f"Component '{display_name}' of {obj.object_id}",
            "metadata_key": component_type,
            "collection": None,
            "key_field": None,
            "original_key": None,
        }

    def _get_lookup_cache_key(self, lookup_spec: Any) -> str:
        if isinstance(lookup_spec, str):
            return lookup_spec
        try:
            return json.dumps(lookup_spec, sort_keys=True, separators=(",", ":"))
        except Exception:
            return repr(lookup_spec)

    def _get_lookup_options(self, lookup_spec: Any) -> list[dict[str, Any]]:
        lookup_key = self._get_lookup_cache_key(lookup_spec)
        if lookup_key not in self._lookup_cache:
            try:
                self._lookup_cache[lookup_key] = self._service.get_lookup_options(lookup_spec)
            except Exception:
                log.exception("Failed loading lookup options for %s", lookup_spec)
                self._lookup_cache[lookup_key] = []
        return list(self._lookup_cache.get(lookup_key, []))

    def _format_lookup_label(self, option: dict[str, Any]) -> str:
        parts: list[str] = []
        ident = option.get("id", "")
        label = str(option.get("label") or "").strip()
        detail = str(option.get("detail") or "").strip()
        if ident not in (None, ""):
            parts.append(str(ident))
        if label:
            parts.append(label)
        if detail:
            parts.append(detail)
        return " | ".join(parts)

    def _get_lookup_search_text(self, option: dict[str, Any]) -> str:
        return " ".join(
            str(option.get(key) or "").strip()
            for key in ("id", "label", "detail", "preview_text")
        ).lower()

    def _normalize_lookup_filter_text(self, lookup_spec: Any, search_text: Any) -> str:
        text = str(search_text or "").strip()
        if not text:
            return ""

        lowered = text.lower()
        for option in self._get_lookup_options(lookup_spec):
            if self._format_lookup_label(option).strip().lower() == lowered:
                # If the field currently contains an exact selected label,
                # opening the dropdown should still show the full option set.
                return ""
        return text

    def _filter_lookup_options(self, lookup_spec: Any, search_text: Any) -> list[dict[str, Any]]:
        options = self._get_lookup_options(lookup_spec)
        term = self._normalize_lookup_filter_text(lookup_spec, search_text).lower()
        if not term:
            return options
        return [option for option in options if term in self._get_lookup_search_text(option)]

    def _resolve_lookup_option(self, lookup_spec: Any, selection: Any) -> dict[str, Any] | None:
        try:
            option_id = self._parse_lookup_value(selection)
        except Exception:
            return None
        for option in self._get_lookup_options(lookup_spec):
            if option.get("id") == option_id:
                return option
        return None

    def _lookup_supports_color_preview(self, lookup_spec: Any) -> bool:
        return any(
            isinstance(option.get("preview_hex"), str) and str(option.get("preview_hex")).strip()
            for option in self._get_lookup_options(lookup_spec)
        )

    def _build_lookup_display(self, lookup_spec: Any, current_value: Any) -> tuple[list[str], str]:
        options = self._get_lookup_options(lookup_spec)
        values = [""] + [self._format_lookup_label(option) for option in options]
        if current_value in (None, ""):
            return values, ""
        for option in options:
            if option.get("id") == current_value:
                return values, self._format_lookup_label(option)
        missing = f"{current_value} | [missing]"
        if missing not in values:
            values.append(missing)
        return values, missing

    def _get_lookup_widget_width(self, options: list[str], minimum: int = 42, maximum: int = 96) -> int:
        if not options:
            return minimum
        longest = max(len(option) for option in options)
        return max(minimum, min(maximum, longest + 2))

    def _parse_lookup_value(self, selection: Any) -> int | None:
        text = str(selection or "").strip()
        if not text:
            return None
        if text.startswith("(") and ")" in text:
            try:
                return int(text[1:text.index(")")])
            except Exception:
                pass
        match = re.match(r"^\s*(-?\d+)\b", text)
        if match:
            return int(match.group(1))
        try:
            return int(text)
        except Exception:
            raise ValueError(f"'{text}' is not a valid lookup id")

    def _refresh_lookup_combobox_values(self, combo: ttk.Combobox, lookup_spec: Any, search_text: Any) -> None:
        values = [""] + [self._format_lookup_label(option) for option in self._filter_lookup_options(lookup_spec, search_text)]
        try:
            combo.configure(values=values)
        except Exception:
            pass

    def _bind_lookup_combobox_search(self, combo: ttk.Combobox, lookup_spec: Any, var: tk.Variable) -> None:
        def _refresh(_event=None) -> None:
            self._refresh_lookup_combobox_values(combo, lookup_spec, var.get())

        try:
            combo.configure(postcommand=lambda: self._refresh_lookup_combobox_values(combo, lookup_spec, var.get()))
        except Exception:
            pass
        try:
            combo.bind("<KeyRelease>", _refresh, add=True)
        except Exception:
            pass
        try:
            combo.bind("<FocusIn>", _refresh, add=True)
        except Exception:
            pass

    def _sync_collection_row_node(self, obj_id: int, component_type: str, component: Any, original_key: Any, row: Any) -> None:
        """Keep collection-node identity stable when the edited row key changes."""
        if component is None:
            return
        new_key = self._get_collection_row_key(component, row)
        if original_key == new_key:
            current_iid = self._find_collection_row_iid(obj_id, component_type, new_key)
            if current_iid is not None:
                try:
                    self.tree.item(current_iid, text=self._format_collection_row_text(component, row))
                except Exception:
                    pass
            return

        for parent_iid in self._iter_collection_parent_iids(obj_id, component_type):
            old_iid = f"{parent_iid}:{original_key}"
            new_iid = f"{parent_iid}:{new_key}"
            if not self.tree.exists(old_iid):
                continue
            if self.tree.exists(new_iid):
                try:
                    self.tree.delete(old_iid)
                except Exception:
                    pass
                try:
                    self.tree.item(new_iid, text=self._format_collection_row_text(component, row))
                    self.tree.selection_set(new_iid)
                    self.tree.focus(new_iid)
                    self._last_grandchild_iid = str(new_key)
                except Exception:
                    pass
                return
            try:
                idx = self.tree.index(old_iid)
            except Exception:
                idx = tk.END
            try:
                self.tree.insert(parent_iid, idx, iid=new_iid, text=self._format_collection_row_text(component, row))
                self.tree.delete(old_iid)
                self.tree.selection_set(new_iid)
                self.tree.focus(new_iid)
                self._last_grandchild_iid = str(new_key)
            except Exception:
                pass
            return

    def _populate_object_children(self, parent_iid: str, obj: Any) -> None:
        """Populate the fixed three-level tree: object -> component/group -> row."""
        # Keep row collections flat under their group node so deeper schema chains
        # still fit the existing tree without turning the sidebar into a maze.
        for key, component in (getattr(obj, "components", {}) or {}).items():
            if not self._is_component_visible(key, component):
                continue
            child_iid = f"{parent_iid}:{key}"
            self.tree.insert(parent_iid, tk.END, iid=child_iid, text=self._get_component_display_name(key))
            if not self._is_row_collection_component(component):
                continue
            for row in self._get_component_rows(component):
                row_key = self._get_collection_row_key(component, row)
                self.tree.insert(
                    child_iid,
                    tk.END,
                    iid=f"{child_iid}:{row_key}",
                    text=self._format_collection_row_text(component, row),
                )

    def _refresh_object_branch(self, object_id: int, obj: Any | None = None) -> str | None:
        """Rebuild one root branch from the cached object after local edits."""
        candidate_iids = [self._make_root_iid(object_id), self._make_root_iid_alt(object_id)]
        root_iid = next((iid for iid in candidate_iids if self.tree.exists(iid)), None)
        if root_iid is None:
            return None
        try:
            for child in self.tree.get_children(root_iid):
                self.tree.delete(child)
        except Exception:
            pass
        if obj is None:
            obj = self._object_cache.get(object_id)
        if obj is None:
            return root_iid
        self._populate_object_children(root_iid, obj)
        return root_iid

    def _focus_object_target(
        self,
        obj: Any,
        component_type: str = "object",
        grandchild_iid: str | None = None,
    ) -> None:
        """Rebuild and reselect a target inside the current object branch."""
        self._object_cache[obj.object_id] = obj
        root_iid = self._refresh_object_branch(obj.object_id, obj)
        if root_iid is None:
            return

        if component_type != "object":
            component = (getattr(obj, "components", {}) or {}).get(component_type)
            if component is None or not self._is_component_visible(component_type, component):
                component_type = "object"
                grandchild_iid = None

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

        self.current_object = obj
        self.current_component_type = component_type
        self._last_grandchild_iid = grandchild_iid
        self._build_form_for(component_type, grandchild_iid)

    def _format_save_error(self, exc: Exception) -> str:
        message = str(exc).strip() or exc.__class__.__name__
        if isinstance(exc, sqlite3.IntegrityError) and "FOREIGN KEY constraint failed" in message:
            return (
                "Foreign key constraint failed.\n\n"
                "One or more referenced IDs do not exist in the database."
            )
        return message

    # ------------------------------------------------------------------
    # Context menu (right-click) core - delegated to subclasses via hooks
    # ------------------------------------------------------------------
    def _on_tree_context_menu(self, event: tk.Event) -> None:
        """Generic right-click handler for the left tree.

        The base builds the context menu shell (root/component/grandchild cases)
        and delegates item-specific options to subclass hooks:
          - get_root_delete_label() -> str
          - on_delete_root_local(obj_id: int, iid: str) -> None
          - get_root_add_component_actions(obj) -> list[(label, callback, enabled)]
          - get_component_delete_action(comp_name, obj, iid, parent_iid) -> (label, cb)|None
          - get_component_add_subitem_actions(comp_name, obj, iid, parent_iid) -> list[(label, cb)]
          - get_grandchild_delete_action(parts, obj) -> (label, cb)|None
        Subclasses should use base helpers like _parse_obj_id_from_iid(),
        _get_cached_or_load(), and _mark_unsaved_indicator() inside callbacks.
        """
        if not hasattr(self, 'tree'):
            return

        # Ensure the row under the cursor is selected
        iid = self.tree.identify_row(event.y)  # type: ignore[attr-defined]
        if not iid:
            return
        try:
            self.tree.selection_set(iid)
        except Exception:
            pass

        menu = tk.Menu(self.tree, tearoff=0)  # type: ignore[arg-type]
        parts = str(iid).split(":")
        is_root = (":" not in iid)
        is_child = (":" in iid and len(parts) == 2)
        is_grandchild = (":" in iid and len(parts) == 3)

        # ---------------- Helpers used by subclass callbacks ----------------
        # Expose as attributes so lambdas from hooks can reuse them
        def _parse_obj_id_from_iid(root_iid: str) -> int | None:
            try:
                return int(root_iid.split('-', 1)[1])
            except Exception:
                return None
        def _get_cached_or_load(parent_iid: str, obj_id: int):
            cached = self._object_cache.get(obj_id)
            if cached is not None:
                return cached
            try:
                obj = self.__load_relevant_object(parent_iid, obj_id)
                if obj is not None:
                    self._object_cache[obj_id] = obj
                return obj
            except Exception:
                return None
        def _mark_unsaved_indicator() -> None:
            self._has_unsaved_changes = True
            self._update_unsaved_indicator()
            # Some actions enable undo
            try:
                self._update_undo_button_state()
            except Exception:
                pass
        # Attach for subclass access
        self._ctx_parse_obj_id_from_iid = _parse_obj_id_from_iid  # type: ignore[attr-defined]
        self._ctx_get_cached_or_load = _get_cached_or_load        # type: ignore[attr-defined]
        self._ctx_mark_unsaved_indicator = _mark_unsaved_indicator # type: ignore[attr-defined]

        # ---------------- Root node actions ----------------
        if is_root:
            # Delete root (local)
            try:
                del_label = self.get_root_delete_label()
            except Exception:
                del_label = None
            if del_label:
                def _do_root_delete():
                    oid = _parse_obj_id_from_iid(iid)
                    if oid is None:
                        return
                    try:
                        self.on_delete_root_local(oid, iid)
                    finally:
                        _mark_unsaved_indicator()
                try:
                    menu.add_command(label=del_label, command=_do_root_delete)
                except Exception:
                    pass

            # Add Component submenu provided by subclass
            obj_id = _parse_obj_id_from_iid(iid)
            obj = _get_cached_or_load(iid, obj_id) if obj_id is not None else None
            try:
                actions = self.get_root_add_component_actions(obj)
            except Exception:
                actions = []
            if actions:
                add_menu = tk.Menu(menu, tearoff=0)
                for label, cb, enabled in actions:
                    state = (tk.NORMAL if enabled else tk.DISABLED)
                    try:
                        add_menu.add_command(label=label, command=cb, state=state)
                    except Exception:
                        pass
                try:
                    menu.add_cascade(label="Add Component", menu=add_menu)
                except Exception:
                    pass

        # ---------------- Component (child) actions ----------------
        if is_child:
            parent_iid = parts[0]
            comp_name = parts[1]
            obj_id = _parse_obj_id_from_iid(parent_iid)
            obj = _get_cached_or_load(parent_iid, obj_id) if obj_id is not None else None
            # Delete component provided by subclass
            try:
                delete_action = self.get_component_delete_action(comp_name, obj, iid, parent_iid)
            except Exception:
                delete_action = None
            if delete_action:
                label, cb = delete_action
                try:
                    menu.add_command(label=label, command=cb)
                except Exception:
                    pass
            # Add sub-items under component (e.g., add skill row)
            try:
                add_subs = self.get_component_add_subitem_actions(comp_name, obj, iid, parent_iid)
            except Exception:
                add_subs = []
            for label, cb in (add_subs or []):
                try:
                    menu.add_command(label=label, command=cb)
                except Exception:
                    pass

        # ---------------- Grandchild actions ----------------
        if is_grandchild:
            parent_iid = parts[0]
            obj_id = _parse_obj_id_from_iid(parent_iid)
            obj = _get_cached_or_load(parent_iid, obj_id) if obj_id is not None else None
            try:
                grand = self.get_grandchild_delete_action(parts, obj)
            except Exception:
                grand = None
            if grand:
                label, cb = grand
                try:
                    menu.add_command(label=label, command=cb)
                except Exception:
                    pass

        # Ensure focus follows selection and show
        try:
            self.tree.focus(iid)
        except Exception:
            pass
        if menu.index("end") is not None:
            try:
                menu.tk_popup(event.x_root, event.y_root)  # type: ignore[attr-defined]
            finally:
                try:
                    menu.grab_release()
                except Exception:
                    pass

    # ---------------- Abstract hooks for subclasses ----------------
    def get_root_delete_label(self) -> str | None:
        """Return the label for root delete action, or None to hide it."""
        raise NotImplementedError

    def on_delete_root_local(self, object_id: int, iid: str) -> None:
        """Perform a local delete of the root object (update local state and tree)."""
        raise NotImplementedError

    def get_root_add_component_actions(self, obj: Any) -> list[tuple[str, Any, bool]]:
        """Return a list of (label, callback, enabled) actions for Add Component submenu."""
        return []

    def get_component_delete_action(self, comp_name: str, obj: Any, iid: str, parent_iid: str) -> tuple[str, Any] | None:
        """Return (label, callback) for deleting a component at child-node level, or None."""
        return None

    def get_component_add_subitem_actions(self, comp_name: str, obj: Any, iid: str, parent_iid: str) -> list[tuple[str, Any]]:
        """Return additional actions under a component (e.g., add skill row)."""
        return []

    def get_grandchild_delete_action(self, parts: list[str], obj: Any) -> tuple[str, Any] | None:
        """Return (label, callback) for deleting a grandchild node, or None to hide."""
        return None


    # ------------------------------------------------------------------
    def _build_form_for(self, component_type: str, grandchild_iid: str = None) -> None:
        """Build (or rebuild) the right-hand form for the selected component.

        component_type values:
            "object"          -> base GameObject fields
            "   "             -> any normal component name (must exist in object.components)
            "ObjectSkill"     -> special case; uses grandchild_iid (skill_id) to select row

        grandchild_iid: for nested collections (currently ObjectSkill rows) the nested id.
        Uses component_field_metadata for:
            display_name : override for label text
            readonly     : disables editing & excluded from save
            tip          : shown as tooltip on hover
            advanced     : hidden unless the 'Show advanced' toggle is on
        """

        # Clear existing form widgets
        for w in self.form_container.winfo_children():
            w.destroy()
        # Reset NULL placeholder tracking for the form being (re)built
        self._null_var_flags = {}

        # Get the currently loaded object
        obj = self.current_object
        form_target = self._resolve_form_target(obj, component_type, grandchild_iid)
        if "message" in form_target:
            self._show_message(str(form_target["message"]))
            return

        target_obj = form_target["target"]
        title = str(form_target["title"])
        exclude = set(form_target["exclude"])
        resolved_grandchild_iid = form_target.get("resolved_grandchild_iid")
        if resolved_grandchild_iid is not None:
            self._last_grandchild_iid = str(resolved_grandchild_iid)

        self.detail_label.configure(text=title)

        if not is_dataclass(target_obj):
            self._show_message("Unsupported component type")
            return

        # Store entry widgets for saving (name, tk.Variable, py_type, readonly)
        self._entry_widgets: list[tuple[str, tk.Variable, Any, bool]] = []
        self._field_lookup_specs: dict[str, Any] = {}

        comp_meta = component_field_metadata.get(str(form_target["metadata_key"]), {})

        # Build a scrollable canvas for many fields
        canvas = tk.Canvas(self.form_container, highlightthickness=0)
        scroll_y = ttk.Scrollbar(self.form_container, orient='vertical', command=canvas.yview)
        inner = ttk.Frame(canvas)
        inner.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=inner, anchor='nw')
        canvas.configure(yscrollcommand=scroll_y.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        # Enable intuitive mouse-wheel scrolling when hovering over the form area
        # (works on Windows, macOS, and Linux). This is centralized so future
        # NPC tabs/forms can reuse the same behavior.
        self._setup_mousewheel_scrolling(canvas, inner)

        # Build form fields (labels + entry/checkbutton)
        # Iterate over dataclass fields and create a row for each
        # `row` is used for grid placement so fields appear vertically stacked.
        # Enumerate dataclass fields and lay them out (skipping excluded & filtered advanced)
        for row, f in enumerate(fields(target_obj)):
            # Skip any fields we explicitly excluded (like internal flags)
            if f.name in exclude:
                continue

            field_meta = comp_meta.get(f.name, {})
            readonly = bool(field_meta.get("readonly", False))
            display_name = field_meta.get("display_name") or f.name
            # Prefer the declared dataclass type; if it's an Enum subclass, don't let metadata override it
            declared_type = self._normalize_field_type(f.type)
            py_type = self._normalize_field_type(field_meta.get("type", declared_type))
            if isinstance(declared_type, type) and issubclass(declared_type, Enum):
                py_type = declared_type
            lookup_spec = field_meta.get("lookup")
            is_advanced = bool(field_meta.get("advanced", False))
            tip_text = field_meta.get("tip", "")

            # Filter advanced fields unless checkbox is enabled
            show_adv_var = getattr(self, "show_advanced_var", None)
            if is_advanced and (show_adv_var is None or not show_adv_var.get()):
                continue

            # Label for the field name on the left (use display_name if provided)
            label_widget = ttk.Label(inner, text=display_name)
            label_widget.grid(row=row, column=0, sticky=tk.W, padx=2, pady=2)

            # Read the current value from the target object
            value = getattr(target_obj, f.name)

            # Prepare a tkinter Variable to hold the editable value for this field.
            # We store (name, var, type) in self._entry_widgets so _on_save can read
            # back the values, coerce to the right Python type and persist changes.
            var: tk.Variable

            # Boolean fields get a Checkbutton bound to a BooleanVar
            if lookup_spec:
                options, display = self._build_lookup_display(lookup_spec, value)
                widget_width = self._get_lookup_widget_width(options)
                var = tk.StringVar(value=display)
                combo: ttk.Combobox | None = None
                self._field_lookup_specs[f.name] = lookup_spec
                if readonly:
                    entry_ro = ttk.Entry(inner, textvariable=var, width=widget_width, state='readonly')
                    entry_ro.grid(row=row, column=1, sticky=tk.W, padx=2, pady=2)
                    widget_for_tooltip = entry_ro
                else:
                    combo = ttk.Combobox(inner, state='normal', values=options, textvariable=var, width=widget_width)
                    combo.grid(row=row, column=1, sticky=tk.W, padx=2, pady=2)
                    widget_for_tooltip = combo
                    try:
                        self._bind_lookup_combobox_search(combo, lookup_spec, var)
                    except Exception:
                        pass
                    try:
                        self._attach_combobox_wheel_passthrough(combo, canvas)
                    except Exception:
                        pass

                if self._lookup_supports_color_preview(lookup_spec):
                    swatch, preview_label = self._create_color_swatch(inner, row)
                    self._update_lookup_color_preview(combo, var, lookup_spec, swatch, preview_label)
                    try:
                        var.trace_add(
                            'write',
                            lambda *_args, c=combo, v=var, l=lookup_spec, s=swatch, p=preview_label: self._update_lookup_color_preview(c, v, l, s, p),
                        )
                    except Exception:
                        pass
                    if combo is not None:
                        try:
                            combo.bind(
                                '<<ComboboxSelected>>',
                                lambda _e, c=combo, v=var, l=lookup_spec, s=swatch, p=preview_label: self._update_lookup_color_preview(c, v, l, s, p),
                            )
                        except Exception:
                            pass

                try:
                    self._attach_copy_context_menu(
                        widget_for_tooltip,
                        lambda v=var: str(v.get() or ""),
                        field_name=f.name,
                    )
                except Exception:
                    pass
            elif isinstance(value, bool) or py_type in (bool, 'bool'):
                var = tk.BooleanVar(value=value)
                cb = ttk.Checkbutton(inner, variable=var)
                if readonly:
                    # Keep the checkbox disabled (not editable), but still allow copying its value
                    # via a right-click context menu bound below.
                    cb.state(["disabled"])  # ttk style disable
                cb.grid(row=row, column=1, sticky=tk.W, padx=2, pady=2)
                widget_for_tooltip = cb
                # Right-click-to-copy on readonly/any boolean (copies "True"/"False")
                try:
                    self._attach_copy_context_menu(
                        cb,
                        lambda v=var: "True" if bool(v.get()) else "False",
                        field_name=f.name,
                    )
                except Exception:
                    pass
            elif (
                isinstance(value, Enum)
                or (isinstance(py_type, type) and issubclass(py_type, Enum))
                or (isinstance(declared_type, type) and issubclass(declared_type, Enum))
            ):
                # Enum fields -> use a readonly Combobox with enum member names
                if isinstance(value, Enum):
                    enum_type = value.__class__
                elif isinstance(py_type, type) and issubclass(py_type, Enum):
                    enum_type = py_type
                else:
                    enum_type = declared_type

                # Build member list and labels via centralized helpers
                included_members, options = self._build_enum_display(enum_type)

                # Resolve current value to an enum member without using exceptions for control flow
                current_member = self._resolve_enum_member(enum_type, value)

                # Determine display for current value
                if current_member is not None and current_member in included_members:
                    display = self._format_enum_label(enum_type, current_member)
                elif current_member is None and any(m.name.upper() == 'NONE' for m in included_members):
                    display = 'NONE'
                else:
                    display = ''

                var = tk.StringVar(value=display)

                if readonly:
                    # Read-only enum fields: show a read-only Entry with the display text so
                    # users can select/copy, but not change the value. This avoids the ability
                    # to alter selection that a Combobox in 'readonly' state would otherwise allow.
                    entry_ro = ttk.Entry(inner, textvariable=var, width=30, state='readonly')
                    entry_ro.grid(row=row, column=1, sticky=tk.W, padx=2, pady=2)
                    widget_for_tooltip = entry_ro
                    # Allow convenient copying via context menu as well.
                    try:
                        self._attach_copy_context_menu(
                            entry_ro,
                            lambda v=var: str(v.get() or ""),
                            field_name=f.name,
                        )
                    except Exception:
                        pass
                else:
                    combo = ttk.Combobox(inner, state='readonly', values=options, textvariable=var, width=28)
                    combo.grid(row=row, column=1, sticky=tk.W, padx=2, pady=2)
                    widget_for_tooltip = combo

                # Prevent accidental value changes by mouse wheel when hovering the dropdown.
                # Instead, route the wheel to scroll the form's canvas for a better UX.
                try:
                    # Only attach for actual Combobox widgets (not the read-only Entry case)
                    if not readonly:
                        self._attach_combobox_wheel_passthrough(combo, canvas)
                except Exception:
                    pass

                # If this is the ColorType enum, show a live color swatch and hex value next to the dropdown
                if enum_type is ColorType:
                    # Build swatch UI elements and wire them to follow dropdown selection
                    swatch, hex_label = self._create_color_swatch(inner, row)
                    if readonly:
                        # In read-only mode, no dropdown - just reflect the current value into the swatch once.
                        try:
                            # Simulate update using the current text in var
                            sel_text = var.get() or ""
                            # Normalize '(id)NAME' labels to NAME
                            if sel_text.startswith('(') and ')' in sel_text:
                                sel_text = sel_text.split(')', 1)[1]
                            member = self._coerce_enum_from_selection(enum_type, sel_text)
                            color_hex = getattr(member, 'hex', '#FFFFFF') if member else '#FFFFFF'
                            swatch.configure(background=color_hex)
                            hex_label.configure(text=color_hex)
                        except Exception:
                            pass
                    else:
                        # Initialize and keep in sync with dropdown selection/events
                        self._update_color_swatch(combo, var, enum_type, swatch, hex_label)
                        try:
                            var.trace_add('write', lambda *_: self._update_color_swatch(combo, var, enum_type, swatch, hex_label))
                        except Exception:
                            pass
                        try:
                            combo.bind('<<ComboboxSelected>>', lambda _e: self._update_color_swatch(combo, var, enum_type, swatch, hex_label))
                        except Exception:
                            pass

                # Allow copy via context menu for editable enum Combobox too (copies current label)
                if not readonly:
                    try:
                        self._attach_copy_context_menu(
                            widget_for_tooltip,
                            lambda v=var: str(v.get() or ""),
                            field_name=f.name,
                        )
                    except Exception:
                        pass
            else:
                # For non-boolean, non-enum fields we use a text Entry.
                # Special handling for string fields to support a greyed-out NULL placeholder.
                is_string_field = (
                    py_type in (str, 'str')
                    or declared_type is str
                )

                # Derive display text for the field
                if hasattr(value, 'name') and hasattr(value, 'value'):
                    display = value.name
                elif value is None and is_string_field:
                    # Show our special placeholder for None strings
                    display = 'NULL'
                elif value is None:
                    display = ''
                else:
                    display = str(value)

                var = tk.StringVar(value=display)

                if is_string_field:
                    # Use tk.Entry (not ttk) so we can control foreground color per-widget
                    entry = tk.Entry(inner, textvariable=var, width=30)
                    # If we're showing the NULL placeholder, style it grey and track it
                    if value is None:
                        try:
                            entry.configure(fg="#9CA3AF")  # Tailwind gray-400
                        except Exception:
                            pass
                        self._null_var_flags[self._var_key(var)] = True
                        # Clear placeholder when user focuses the field so typing just works
                        try:
                            entry.bind(
                                "<FocusIn>",
                                lambda _e, v=var, ent=entry, fname=f.name: self._clear_string_null_placeholder_on_focus(v, ent, fname),
                                add=True,
                            )
                        except Exception:
                            pass
                    if readonly:
                        try:
                            entry.configure(state='readonly')
                        except Exception:
                            entry.configure(state='disabled')
                    entry.grid(row=row, column=1, sticky=tk.W, padx=2, pady=2)
                    widget_for_tooltip = entry
                    # Right-click menu: copy + Set to NULL (only when not readonly)
                    try:
                        self._attach_string_field_context_menu(entry, var, f.name, readonly)
                    except Exception:
                        pass
                else:
                    # Non-string text field; standard ttk.Entry is fine
                    entry = ttk.Entry(inner, textvariable=var, width=30)
                    if readonly:
                        try:
                            entry.configure(state='readonly')
                        except Exception:
                            entry.configure(state='disabled')
                    entry.grid(row=row, column=1, sticky=tk.W, padx=2, pady=2)
                    widget_for_tooltip = entry
                    try:
                        self._attach_copy_context_menu(
                            entry,
                            lambda v=var: str(v.get() or ""),
                            field_name=f.name,
                        )
                    except Exception:
                        pass

            # Keep track of the field so the Save handler can apply changes later.
            # We save the declared dataclass field type (f.type) to guide basic coercion.
            self._entry_widgets.append((f.name, var, py_type, readonly))

            # Mark unsaved state as soon as a field value changes
            try:
                var.trace_add('write', lambda *_args: self._mark_unsaved())
            except Exception:
                pass

            # If there is a tip, add a small info symbol next to the field.
            # Hovering over this symbol shows the tooltip; avoids accidental popups
            # when just moving across the form.
            if tip_text:
                info_label = ttk.Label(inner, text="\u24D8")  # Unicode info symbol
                info_label.grid(row=row, column=2, sticky=tk.W, padx=(4, 2), pady=2)
                self._add_tooltip(info_label, tip_text)

        # Enable the Save button once there is an editable form
        self.save_button.configure(state=tk.NORMAL)

    # ------------------------------------------------------------------
    # Tooltip helpers
    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    # Scrollable form mousewheel helpers (shared by all object tabs)
    # ------------------------------------------------------------------
    def _setup_mousewheel_scrolling(self, canvas: tk.Canvas, inner: tk.Widget) -> None:
        """Make the scrollable form area respond to mouse-wheel when hovered.

        Implementation details:
        - We bind/unbind global wheel events on <Enter>/<Leave> because Tk on
          Windows typically sends <MouseWheel> to the focused widget, not the
          one under the pointer. This technique enables "hover-to-scroll".
        - Linux uses <Button-4>/<Button-5> for wheel up/down; we support both.
        - Binding is limited to the lifetime of the hover to avoid side effects
          elsewhere in the UI.
        """
        # Bind on both the canvas and the inner frame so moving across their
        # boundary keeps scrolling working.

        def _bind_all(_event=None):
            # Route all wheel events to this canvas while hovered
            try:
                canvas.bind_all("<MouseWheel>", lambda e: self._on_mousewheel_scroll(e, canvas), add=True)
            except Exception:
                pass
            # Linux (X11) wheel events
            try:
                canvas.bind_all("<Button-4>", lambda e: self._on_mousewheel_scroll(e, canvas), add=True)
                canvas.bind_all("<Button-5>", lambda e: self._on_mousewheel_scroll(e, canvas), add=True)
            except Exception:
                pass

        def _unbind_all(_event=None):
            # Remove our global bindings; other bindings (if any) remain intact
            try:
                canvas.unbind_all("<MouseWheel>")
            except Exception:
                pass
            try:
                canvas.unbind_all("<Button-4>")
            except Exception:
                pass
            try:
                canvas.unbind_all("<Button-5>")
            except Exception:
                pass

        for w in (canvas, inner):
            try:
                w.bind("<Enter>", _bind_all)
                w.bind("<Leave>", _unbind_all)
            except Exception:
                pass

    def _attach_combobox_wheel_passthrough(self, combo: ttk.Combobox, canvas: tk.Canvas | None) -> None:
        """On hover over a Combobox, prevent wheel from changing selection.

        Wheel events will instead scroll the provided canvas (if any). This avoids
        accidental changes to enum fields when the user is scrolling the form.
        The dropdown popup list (when open) is a separate window and will still
        scroll normally, which is desirable when a user explicitly opens it.
        """
        if canvas is None:
            return

        def _wheel(e):
            # If form isn't scrollable, still block to avoid changing selection
            try:
                if not self._canvas_is_scrollable(canvas):
                    return "break"
            except Exception:
                return "break"
            # Scroll the form and block default Combobox behavior
            self._on_mousewheel_scroll(e, canvas)
            return "break"

        try:
            combo.bind("<MouseWheel>", _wheel, add=True)  # Windows/macOS
        except Exception:
            pass
        try:
            combo.bind("<Button-4>", _wheel, add=True)   # Linux up
            combo.bind("<Button-5>", _wheel, add=True)   # Linux down
        except Exception:
            pass

    def _on_mousewheel_scroll(self, event: tk.Event, canvas: tk.Canvas) -> None:
        """Scroll the canvas from a wheel event (cross-platform).

        - Windows/macOS deliver <MouseWheel> with event.delta multiples of 120.
        - Linux (X11) delivers <Button-4> (up) and <Button-5> (down).
        We normalize both to small unit scrolls for a predictable feel.
        """
        # If the canvas isn't scrollable (everything fits), do nothing
        try:
            if not self._canvas_is_scrollable(canvas):
                return
        except Exception:
            return
        # Determine direction/amount
        move_units = 0
        try:
            # X11: buttons 4/5
            num = getattr(event, 'num', None)
            if num == 4:
                move_units = -3  # up
            elif num == 5:
                move_units = 3   # down
            else:
                # Windows/macOS: delta positive is up on Windows (typically 120 per notch)
                delta = getattr(event, 'delta', 0)
                if isinstance(delta, (int, float)) and delta != 0:
                    # Scale to roughly 3 units per notch; invert for natural scroll
                    move_units = -int(delta / 40)  # 120 -> -3, -120 -> 3
        except Exception:
            move_units = 0

        if move_units == 0:
            # Fallback to a single unit in the appropriate direction, if known
            try:
                if getattr(event, 'delta', 0) > 0:
                    move_units = -1
                elif getattr(event, 'delta', 0) < 0:
                    move_units = 1
            except Exception:
                move_units = 0

        if move_units:
            # Avoid overscrolling when already at extremes
            try:
                first, last = canvas.yview()
                if move_units < 0 and first <= 0.0:
                    return
                if move_units > 0 and last >= 1.0:
                    return
            except Exception:
                pass
            try:
                canvas.yview_scroll(move_units, 'units')
            except Exception:
                pass

    def _canvas_is_scrollable(self, canvas: tk.Canvas) -> bool:
        """Return True if the canvas content exceeds its viewport vertically.

        Uses yview fractions to determine if the full content (0.0..1.0) is visible.
        """
        try:
            canvas.update_idletasks()
            first, last = canvas.yview()
            # Not scrollable when the full range is visible
            return not (first <= 0.0 and last >= 1.0)
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Tooltip helpers
    # ------------------------------------------------------------------
    def _add_tooltip(self, widget: tk.Widget, text: str) -> None:
        """Attach a simple tooltip to a widget.

        Keeps implementation local & lightweight (no external deps)."""
        if not text:
            return

        def show_tip(_event):
            # Create only one tooltip per widget; store reference on widget
            if getattr(widget, "_tooltip_win", None):
                return
            tw = tk.Toplevel(widget)
            tw.wm_overrideredirect(True)
            tw.configure(background="#FFFFE0", padx=4, pady=2, borderwidth=1, relief="solid")
            label = tk.Label(tw, text=text, justify=tk.LEFT, background="#FFFFE0")
            label.pack()
            # Position next to cursor
            x = widget.winfo_rootx() + 20
            y = widget.winfo_rooty() + 20
            tw.wm_geometry(f"+{x}+{y}")
            widget._tooltip_win = tw  # type: ignore[attr-defined]

        def hide_tip(_event):
            tw = getattr(widget, "_tooltip_win", None)
            if tw:
                try:
                    tw.destroy()
                except Exception:
                    pass
                widget._tooltip_win = None  # type: ignore[attr-defined]

        widget.bind("<Enter>", show_tip)
        widget.bind("<Leave>", hide_tip)

    # ------------------------------------------------------------------
    # Copy helpers (right-click to copy field values, including read-only)
    # ------------------------------------------------------------------
    def _attach_copy_context_menu(self, widget: tk.Widget, text_getter: Callable[[], str], field_name: str = "") -> None:
        """Attach a simple right-click context menu to copy the widget's value.

        This keeps read-only fields useful while preventing edits. Works across
        Entry, Combobox (editable), and Checkbutton (copies "True"/"False").
        """
        if widget is None:
            return

        def _do_copy() -> None:
            text = ""
            try:
                text = str(text_getter() or "")
            except Exception:
                # If we cannot read the value, copy nothing and log
                log.exception("Failed to read value for copy on field '%s'", field_name)
                text = ""
            self._copy_value_to_clipboard(text, field_name)

        def _show_menu(event: tk.Event) -> str:
            try:
                menu = tk.Menu(widget, tearoff=0)  # type: ignore[arg-type]
                menu.add_command(label="Copy value", command=_do_copy)
                try:
                    menu.tk_popup(event.x_root, event.y_root)  # type: ignore[attr-defined]
                finally:
                    try:
                        menu.grab_release()
                    except Exception:
                        pass
            except Exception:
                pass
            # Prevent default right-click behaviors (e.g., focus steal)
            return "break"

        try:
            widget.bind("<Button-3>", _show_menu, add=True)
        except Exception:
            pass

    def _attach_string_field_context_menu(self, widget: tk.Widget, var: tk.StringVar, field_name: str, readonly: bool) -> None:
        """Attach a right-click menu for string Entry fields.

        Includes:
        - Copy value
        - Set to NULL (adds grey placeholder), only when not readonly
        """
        if widget is None:
            return

        def _do_copy() -> None:
            try:
                self._copy_value_to_clipboard(str(var.get() or ""), field_name)
            except Exception:
                log.exception("Copy failed for field '%s' (object_id=%s)", field_name, getattr(getattr(self, 'current_object', None), 'object_id', None))

        def _do_set_null() -> None:
            try:
                self._set_string_field_to_null(widget, var, field_name)
            except Exception:
                log.exception("Set NULL failed for field '%s' (object_id=%s)", field_name, getattr(getattr(self, 'current_object', None), 'object_id', None))

        def _show_menu(event: tk.Event) -> str:
            try:
                menu = tk.Menu(widget, tearoff=0)  # type: ignore[arg-type]
                menu.add_command(label="Copy value", command=_do_copy)
                if not readonly:
                    menu.add_command(label="Set to NULL", command=_do_set_null)
                try:
                    menu.tk_popup(event.x_root, event.y_root)  # type: ignore[attr-defined]
                finally:
                    try:
                        menu.grab_release()
                    except Exception:
                        pass
            except Exception:
                pass
            return "break"

        try:
            widget.bind("<Button-3>", _show_menu, add=True)
        except Exception:
            pass

    def _set_string_field_to_null(self, entry: tk.Widget, var: tk.StringVar, field_name: str) -> None:
        """Set a string field to represent SQL NULL in the UI and track it for save-time conversion.

        - Sets the entry text to 'NULL'
        - Greys out the text
        - Flags the variable so _on_save will store None
        - Marks the form as having unsaved changes
        """
        try:
            var.set("NULL")
            self._null_var_flags[self._var_key(var)] = True
            try:
                # tk.Entry supports 'fg'; ttk.Entry does not. Ignore failures silently.
                entry.configure(fg="#9CA3AF")
            except Exception:
                pass
            # Log with context
            oid = getattr(getattr(self, 'current_object', None), 'object_id', None)
            log.info("Field '%s' set to NULL placeholder (object_id=%s)", field_name, oid)
            # Mark unsaved since this is a user action
            self._mark_unsaved()
        except Exception:
            pass

    def _clear_string_null_placeholder_on_focus(self, var: tk.StringVar, entry: tk.Widget, field_name: str) -> None:
        """Clear the grey 'NULL' placeholder when the field gains focus to let the user type.

        Keeps behavior simple and predictable; the user can still re-apply NULL via the context menu.
        """
        try:
            if self._null_var_flags.get(self._var_key(var), False):
                var.set("")
                self._null_var_flags[self._var_key(var)] = False
                try:
                    entry.configure(fg="#000000")
                except Exception:
                    pass
                # No need to mark unsaved here; the trace on var will do it after first keystroke
        except Exception:
            pass

    def _copy_value_to_clipboard(self, text: str, field_name: str | None = None) -> None:
        """Copy text to the OS clipboard and log the action (with object id when available)."""
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
        except Exception:
            # Fallback via toplevel
            try:
                top = self.winfo_toplevel()
                top.clipboard_clear()
                top.clipboard_append(text)
            except Exception:
                log.exception("Clipboard operation failed for field '%s'", field_name or "?")
                return
        # Log the copy action with object id context when available
        try:
            oid = getattr(getattr(self, 'current_object', None), 'object_id', None)
            if oid is not None:
                log.info("Copied value from field '%s' (object_id=%s)", field_name or "?", oid)
            else:
                log.info("Copied value from field '%s'", field_name or "?")
        except Exception:
            # Don't let logging issues affect UX
            pass

    # ------------------------------------------------------------------
    # Enum resolution helpers (avoid exceptions for control flow)
    # ------------------------------------------------------------------
    def _resolve_enum_member(self, enum_type: type[Enum], value: Any) -> Enum | None:
        """Map a raw value (int/str/Enum) to an enum member without raising.

        - If already an Enum of the target type, return it.
        - If value is int-like and enum is IntEnum, match by .value.
        - If value is str and a member name exists, match by name.
        - If value is str and enum is StrEnum and a member with that value exists, match by .value.
        Returns None if no match.
        """
        # Already the right enum
        if isinstance(value, enum_type):
            return value
        # Special-case: enums like ColorType whose members carry .id and .hex
        # Support resolving from integer id, numeric string, hex string, or tuple (id, hex)
        try:
            _sample = next(iter(enum_type))
            is_color_like = hasattr(_sample, 'id') and hasattr(_sample, 'hex')
        except Exception:
            is_color_like = False
        if is_color_like:
            # Tuple form (id, hex)
            try:
                if isinstance(value, tuple) and len(value) >= 1:
                    vid = value[0]
                    vhex = value[1] if len(value) > 1 else None
                    for m in enum_type:
                        if getattr(m, 'id', None) == vid or (vhex is not None and getattr(m, 'hex', None) == vhex):
                            return m
            except Exception:
                pass
            # Integer id
            if isinstance(value, int):
                for m in enum_type:
                    if getattr(m, 'id', None) == value:
                        return m
            # String inputs: numeric id, hex code, or labels like '(id)NAME'
            if isinstance(value, str):
                v = value.strip()
                # Strip '(id)NAME' to NAME for name/other resolution below
                if v.startswith('(') and ')' in v:
                    try:
                        v = v.split(')', 1)[1]
                    except Exception:
                        pass
                # Hex code
                if v.startswith('#'):
                    for m in enum_type:
                        if getattr(m, 'hex', None) == v:
                            return m
                # Numeric string id
                if v.isdigit():
                    try:
                        iv = int(v)
                        for m in enum_type:
                            if getattr(m, 'id', None) == iv:
                                return m
                    except Exception:
                        pass
        # Try int-like for IntEnum
        try:
            if issubclass(enum_type, IntEnum):
                if isinstance(value, (int,)):
                    for m in enum_type:
                        if m.value == value:
                            return m
                # numeric string case
                if isinstance(value, str) and value.isdigit():
                    iv = int(value)
                    for m in enum_type:
                        if m.value == iv:
                            return m
        except Exception:
            pass
        # Try name lookup
        if isinstance(value, str):
            name = value
            # Normalize '(value)NAME' labels to NAME for robust lookup
            try:
                if name.startswith('(') and ')' in name:
                    name = name.split(')', 1)[1]
            except Exception:
                pass
            if name in getattr(enum_type, '__members__', {}):
                return enum_type.__members__[name]
        # Try StrEnum by value
        try:
            if issubclass(enum_type, StrEnum) and isinstance(value, str):
                for m in enum_type:
                    if m.value == value:
                        return m
        except Exception:
            pass
        return None

    def _coerce_enum_from_selection(self, enum_type: type[Enum], sel: str) -> Enum | None:
        """Coerce a Combobox selection (member name string) to an enum member without raising."""
        if not sel:
            return None
        # Allow labels formatted as '(value)NAME' by extracting NAME
        try:
            if sel.startswith('(') and ')' in sel:
                sel = sel.split(')', 1)[1]
        except Exception:
            pass
        members = getattr(enum_type, '__members__', {})
        return members.get(sel)

    # ------------------------------------------------------------------
    # Enum display helpers (centralized label formatting for dropdowns)
    # ------------------------------------------------------------------
    def _format_enum_label(self, enum_type: type[Enum], member: Enum) -> str:
        """Return a user-friendly label for an enum member in dropdowns.

        Rules (kept consistent across the UI):
        - IntEnum: show "(value)NAME" for clarity, except plain 'NONE'.
        - ColorType: show "(id)NAME" (no hex) to keep the list concise.
        - Others: show the member's NAME.

        This centralization avoids duplicated closures and keeps formatting
        consistent across all enum fields.
        """
        # IntEnum: include numeric value prefix, except for NONE
        try:
            if issubclass(enum_type, IntEnum) and member.name.upper() != 'NONE':
                return f"({member.value}){member.name}"
        except Exception:
            pass
        # ColorType-like enums: prefer id prefix instead of hex in list
        try:
            if enum_type is ColorType and member.name.upper() != 'NONE':
                cid = getattr(member, 'id', None)
                if isinstance(cid, int):
                    return f"({cid}){member.name}"
        except Exception:
            pass
        # Fallback: just the name
        return member.name

    def _build_enum_display(self, enum_type: type[Enum]) -> tuple[list[Enum], list[str]]:
        """Return (included_members, option_labels) for a given enum type.

        - Filters out UNKNOWN/INVALID-like members by name.
        - Applies _format_enum_label to each included member to build the labels.
        """
        # Filter out sentinel/invalid entries from enum options
        excluded = {"UNKNOWN", "INVALID"}
        try:
            included_members = [m for m in enum_type if m.name.upper() not in excluded]
        except Exception:
            included_members = []
        option_labels = [self._format_enum_label(enum_type, m) for m in included_members]
        return included_members, option_labels

    # ------------------------------------------------------------------
    # Color enum helpers (UI + resolution) for maintainability
    # ------------------------------------------------------------------
    def _create_color_swatch(self, parent: tk.Misc, row: int) -> tuple[tk.Widget, ttk.Label]:
        """Create a fixed-size color swatch and hex label placed at the given grid row.

        Returns (swatch_frame, hex_label).
        """
        # Swatch: fixed size for consistent preview, placed in column 3
        swatch = tk.Frame(parent, relief='solid', borderwidth=1, width=32, height=18)
        swatch.grid(row=row, column=3, sticky=tk.W, padx=(6, 6), pady=2)
        try:
            swatch.grid_propagate(False)
        except Exception:
            pass
        # Hex value label in column 4
        hex_label = ttk.Label(parent, text="")
        hex_label.grid(row=row, column=4, sticky=tk.W, padx=(0, 0), pady=2)
        return swatch, hex_label

    def _update_color_swatch(
        self,
        combo: ttk.Combobox,
        var: tk.Variable,
        enum_type: type[Enum],
        swatch: tk.Widget,
        hex_label: ttk.Label,
    ) -> None:
        """Update the color swatch and hex label from the current combobox selection.

        - Prefer combo.get() to avoid timing issues where the StringVar is still '' during
          the selection event; fall back to var.get() if needed.
        - Accept labels formatted as '(id)NAME' by normalizing to NAME before lookup.
        - Resolve the enum member and use its .hex to color the swatch and label; default to white.
        """
        # Read latest selection text from the dropdown control
        try:
            sel = combo.get()
        except Exception:
            sel = ''
        if not sel:
            try:
                sel = var.get()
            except Exception:
                sel = ''
        # Normalize '(id)NAME' to NAME for lookup
        try:
            if sel and sel.startswith('(') and ')' in sel:
                sel = sel.split(')', 1)[1]
        except Exception:
            pass
        # Resolve enum member and extract color hex
        member = self._coerce_enum_from_selection(enum_type, sel)
        try:
            color_hex = getattr(member, 'hex', None)
        except Exception:
            color_hex = None
        if not color_hex or not isinstance(color_hex, str):
            color_hex = '#FFFFFF'
        # Apply to UI elements
        try:
            swatch.configure(background=color_hex)
        except Exception:
            pass
        try:
            hex_label.configure(text=color_hex)
        except Exception:
            pass

    # ------------------------------------------------------------------
    def _update_lookup_color_preview(
        self,
        combo: ttk.Combobox | None,
        var: tk.Variable,
        lookup_spec: Any,
        swatch: tk.Widget,
        preview_label: ttk.Label,
    ) -> None:
        """Update a lookup-backed color preview from the current selection."""
        try:
            selection = combo.get() if combo is not None else ''
        except Exception:
            selection = ''
        if not selection:
            try:
                selection = var.get()
            except Exception:
                selection = ''

        option = self._resolve_lookup_option(lookup_spec, selection)
        color_hex = str(option.get('preview_hex') or '#FFFFFF') if option else '#FFFFFF'
        preview_text = ''
        if option is not None:
            preview_text = str(option.get('preview_text') or option.get('detail') or '')

        try:
            swatch.configure(background=color_hex)
        except Exception:
            pass
        try:
            preview_label.configure(text=preview_text)
        except Exception:
            pass

    def _refresh_form(self) -> None:
        """Rebuild the current form (used when toggling advanced fields)."""
        if getattr(self, "current_component_type", None):
            self._build_form_for(self.current_component_type, getattr(self, "_last_grandchild_iid", None))

    # ------------------------------------------------------------------
    def _show_message(self, msg: str) -> None:
        """Clear the form area and show a message."""
        for w in self.form_container.winfo_children():
            w.destroy()
        self.detail_label.configure(text=msg)
        self.save_button.configure(state=tk.DISABLED)

    # ------------------------------------------------------------------
    def _on_list_node_select(self, event: tk.Event) -> None:
        """Callback when a node in the tree is selected. Loads the relevant object and builds the form."""
        grandchild_iid = None

        # First, apply any pending unsaved form edits to the current in-memory object
        # so switching away doesn't lose them.
        self._apply_current_form_changes()

        sel = self.tree.selection()
        if not sel:
            return
        iid = sel[0]

        # Determine if a child node was selected; derive component type and/or parent iid
        if ":" in iid: #if a child node
            parent_iid, component_type = iid.split(":", 1) # Split out the object component

            # If there is a grandchild, we nee to split again
            if iid.count(":") > 1:
                component_type, grandchild_iid = component_type.split(":", 1)
        else:
            parent_iid = iid
            component_type = "object"

        # Parse the object ID from the parent iid
        try:
            obj_id = int(parent_iid.split("-", 1)[1])
        except ValueError:
            return

        # Load the relevant object from the service
        try:
            loaded_object = self.__load_relevant_object(parent_iid, obj_id)

            if loaded_object is None:
                self._show_message("Could not load object")
                return

        except Exception as exc:  # pragma: no cover - visual feedback only
            self._show_message(str(exc))
            return

        if grandchild_iid is None and component_type != "object":
            component = loaded_object.components.get(component_type)
            if self._is_row_collection_component(component):
                rows = self._get_component_rows(component)
                if rows:
                    first_row_iid = f"{iid}:{self._get_collection_row_key(component, rows[0])}"
                    if self.tree.exists(first_row_iid):
                        try:
                            self.tree.item(iid, open=True)
                            self.tree.selection_set(first_row_iid)
                            self.tree.focus(first_row_iid)
                            self.tree.see(first_row_iid)
                        except Exception:
                            pass
                        return

        # Save current component type then build form (store grandchild for refresh)
        self.current_object = loaded_object
        self.current_component_type = component_type
        self._last_grandchild_iid = grandchild_iid  # store for refresh
        self._build_form_for(component_type, grandchild_iid)
        # Reflect unsaved state for the newly selected object
        self._update_unsaved_indicator()

    # ------------------------------------------------------------------
    def _on_list_node_expanded(self, event: tk.Event) -> None:
        """Callback when a node in the tree is expanded. Loads child nodes if needed."""
        sel = self.tree.selection()
        if not sel:
            return

        parent_iid = sel[0]
        if ":" in parent_iid:
            return

        # If there is a dummy child, remove it
        if self.tree.exists(f"{parent_iid}:dummy"):
            self.tree.delete(f"{parent_iid}:dummy")

        # If there already are children, do not re-load
        if self.tree.get_children(parent_iid):
            # Branch refreshes are driven explicitly after local edits.
            return

        # Parse the object ID from the iid
        object_id = int(parent_iid.split("-", 1)[1])

        # Fetch object details from the respective service
        obj = self.__load_relevant_object(parent_iid, object_id)
        if obj is None:
            log.error("Could not load object %s for expansion", object_id)
            return

        self._populate_object_children(parent_iid, obj)

    # ------------------------------------------------------------------
    def _on_save(self, persist: bool = True) -> bool:
        """Apply current form values to the in-memory object and optionally persist.

        This method serves BOTH as:
          * The command behind the "Save" button (default persist=True)
          * The internal mechanism used to keep edits when navigating between
            tree nodes (persist=False)

        persist: when True (default) changes are flushed to the DB through the
            service layer; when False they only update cached objects.
        """
        # Identify current object & component
        obj = getattr(self, 'current_object', None)
        component_type = getattr(self, 'current_component_type', None)
        if not obj or not component_type:
            return False
        form_target = self._resolve_form_target(
            obj,
            component_type,
            getattr(self, '_last_grandchild_iid', None),
        )
        if "message" in form_target:
            if persist:
                self._show_message(str(form_target["message"]))
            return False

        target_obj = form_target["target"]
        row_collection = form_target.get("collection")
        original_row_key = form_target.get("original_key")
        key_field = form_target.get("key_field")

        entry_widgets = getattr(self, '_entry_widgets', [])
        if not entry_widgets:
            return False

        if row_collection is not None and key_field:
            try:
                key_var = next(
                    (v for (n, v, _t, ro) in entry_widgets if n == key_field and not ro),
                    None,
                )
            except Exception:
                key_var = None
            if key_var is not None:
                proposed_key = self._parse_collection_key(row_collection, key_var.get())
                if proposed_key != original_row_key:
                    existing_row = self._find_component_row(row_collection, proposed_key)
                    if existing_row is not None and existing_row is not target_obj:
                        try:
                            messagebox.showerror(
                                "Duplicate row key",
                                f"{component_type} already contains a row with {key_field}={proposed_key}.",
                            )
                        except Exception:
                            pass
                        try:
                            key_var.set("" if original_row_key is None else str(original_row_key))
                        except Exception:
                            pass
                        return

        # Apply widget values to target object, track if anything changed
        any_changed = False
        for name, var, typ, readonly in entry_widgets:
            if readonly:
                continue
            # Special-case: our NULL placeholder for string fields. If active, persist None and skip parsing.
            try:
                if (typ in (str, 'str')) and self._null_var_flags.get(self._var_key(var), False):
                    old_val = getattr(target_obj, name, None)
                    if old_val is not None:
                        setattr(target_obj, name, None)
                        any_changed = True
                    # When already None, no change needed
                    continue
            except Exception:
                # Fall through to normal handling if anything goes wrong
                pass
            raw = var.get()
            old_val = getattr(target_obj, name, None)
            if isinstance(var, tk.BooleanVar):
                new_val = bool(raw)
                if new_val != bool(old_val):
                    setattr(target_obj, name, new_val)
                    any_changed = True
                continue
            lookup_spec = getattr(self, '_field_lookup_specs', {}).get(name)
            if raw == '':
                # Empty string should be saved as empty string for string-typed fields.
                # For non-string types, treat empty as None to represent SQL NULL.
                if typ in (str, 'str'):
                    new_val = ''
                else:
                    new_val = None
            else:
                try:
                    if lookup_spec:
                        new_val = self._parse_lookup_value(raw)
                    elif isinstance(typ, type) and issubclass(typ, Enum):
                        sel = str(raw)
                        # If blank (e.g., excluded original like UNKNOWN), skip updating this field
                        if sel == '':
                            continue
                        # If the selection is NONE (and exists in this enum), store None so DB gets NULL
                        if sel.upper() == 'NONE' and 'NONE' in getattr(typ, '__members__', {}):
                            new_val = None
                        else:
                            # For IntEnum formatted as '(value)NAME', extract NAME
                            name_part = sel
                            if sel.startswith('(') and ')' in sel:
                                try:
                                    name_part = sel.split(')', 1)[1]
                                except Exception:
                                    name_part = sel
                            # Resolve by name
                            resolved = self._coerce_enum_from_selection(typ, name_part)
                            if resolved is None:
                                continue
                            # Convert enum to DB-friendly scalar based on enum kind
                            try:
                                if issubclass(typ, IntEnum):
                                    # Store integer value
                                    new_val = int(resolved)
                                elif typ is ColorType:
                                    # Store color id (integer)
                                    try:
                                        new_val = int(resolved)  # ColorType.__int__ returns id
                                    except Exception:
                                        new_val = getattr(resolved, 'id', None)
                                elif issubclass(typ, StrEnum):
                                    # Store string value
                                    new_val = resolved.value
                                else:
                                    # Fallback: store enum name
                                    new_val = resolved.name
                            except Exception:
                                # As a last resort, attempt to store .value
                                try:
                                    new_val = resolved.value
                                except Exception:
                                    new_val = resolved
                    elif typ in (int, 'int'):
                        new_val = int(raw)
                    elif typ in (float, 'float'):
                        new_val = float(raw)
                    elif typ in (bool, 'bool'):
                        raise NotImplementedError("Boolean fields should use Checkbutton/BooleanVar")
                    else:
                        new_val = raw
                except Exception:
                    # Handle inputting incorrect value type into field and revert this field to previous value
                    try:
                        type_name = typ if isinstance(typ, str) else getattr(typ, '__name__', str(typ))
                        messagebox.showerror(
                            "Invalid input",
                            f"Field '{name}': '{raw}' is not a valid {type_name}.\nReverting to previous value.",
                        )
                    except Exception:
                        pass
                    # Revert entry text to prior display value
                    try:
                        revert_text = '' if old_val is None else str(old_val)
                        var.set(revert_text)
                    except Exception:
                        pass
                    # Skip updating this attribute; move to next field
                    continue
            if new_val != old_val:
                setattr(target_obj, name, new_val)
                any_changed = True

        # Translate any active NULL placeholders for string fields to None before marking dirty
        try:
            for name, var, typ, readonly in entry_widgets:
                if readonly:
                    continue
                if (typ in (str, 'str')) and self._null_var_flags.get(self._var_key(var), False):
                    old_val = getattr(target_obj, name, None)
                    if old_val is not None:
                        setattr(target_obj, name, None)
                        any_changed = True
                    else:
                        # Already None; nothing to change
                        pass
        except Exception:
            # Don't block save on placeholder handling failure
            log.exception("Failed translating NULL placeholder to None during save (object_id=%s)", getattr(obj, 'object_id', None))

        # Mark dirty
        try:
            if any_changed:
                # Row-collection edits mark both the row and its owning collection dirty.
                if row_collection is not None:
                    target_obj.dirty = True
                    row_collection.dirty = True
                else:
                    target_obj.dirty = True
        except Exception:
            pass

        # Persist if requested
        active_row_key = None
        if row_collection is not None:
            try:
                active_row_key = str(self._get_collection_row_key(row_collection, target_obj))
            except Exception:
                active_row_key = getattr(self, "_last_grandchild_iid", None)
        if persist:
            save_snapshot = deepcopy(obj)
            # Persist changes through the service layer (to save to DB)
            try:
                self._service.save(obj)
            except Exception as exc:  # pragma: no cover
                restored_obj = save_snapshot
                self.current_object = restored_obj
                self._object_cache[restored_obj.object_id] = restored_obj
                self._has_unsaved_changes = True
                self._focus_object_target(restored_obj, component_type, active_row_key)
                self._update_unsaved_indicator()
                try:
                    messagebox.showerror("Save failed", self._format_save_error(exc))
                except Exception:
                    pass
                return False

            self._show_message('Saved successfully')

            # Remove from cache so next load is fresh from DB
            self._object_cache.pop(obj.object_id, None)
            # Clear unsaved flag after successful save (recomputed in indicator)
            self._has_unsaved_changes = False

            # Also persist any queued root deletions
            try:
                self._persist_root_deletions()
            except Exception as exc:
                try:
                    messagebox.showerror("Delete failed", f"Could not delete some objects: {exc}")
                except Exception:
                    pass
            # Persist queued component deletions
            try:
                self._persist_component_deletions()
            except Exception as exc:
                try:
                    messagebox.showerror("Delete failed", f"Could not delete some components: {exc}")
                except Exception:
                    pass
        else:
            # Track unsaved state locally only if we actually changed anything
            if any_changed:
                self._has_unsaved_changes = True


        ##################################
        ### Ensure left tree is in sync with any changes
        #################################

        # Keep nested row nodes in sync if their identity key changed during editing.
        if row_collection is not None:
            try:
                self._sync_collection_row_node(
                    obj.object_id,
                    component_type,
                    row_collection,
                    original_row_key,
                    target_obj,
                )
            except Exception:
                try:
                    sel = self.tree.selection()
                    if sel:
                        self.tree.item(sel[0], text=self._format_collection_row_text(row_collection, target_obj))
                except Exception:
                    pass

        # If editing the base object, update the root node label to reflect a name change
        if component_type == 'object':
            try:
                root_iid = self._make_root_iid(obj.object_id)
                if not self.tree.exists(root_iid):
                    root_iid = self._make_root_iid_alt(obj.object_id)
                if self.tree.exists(root_iid):
                    self.tree.item(root_iid, text=self._format_node_text({'id': obj.object_id, 'name': obj.name}))
            except Exception:
                pass

        # Update unsaved changes indicator after applying/persisting
        self._update_unsaved_indicator()
        return True

    # ------------------------------------------------------------------
    def __load_relevant_object(self, parent_iid: str, obj_id: int) -> Any:
        """Load the relevant object for this tab, preserving unsaved cached edits."""

        # Return cached object if already loaded (preserves unsaved edits)
        cached = self._object_cache.get(obj_id)
        if cached is not None:
            return cached

        obj = self._service.get(obj_id)

        # Cache the loaded object if found
        if obj is not None:
            self._object_cache[obj_id] = obj

        return obj

    # ------------------------------------------------------------------
    def _apply_current_form_changes(self) -> None:
        """Retain unsaved edits by applying form values in-memory only.

        Delegates to _on_save(persist=False) so conversion logic lives in one place.
        """
        self._on_save(persist=False)
        self._update_unsaved_indicator()

    def _on_save_all(self) -> None:
        """Save current form AND all other dirty cached objects/components.

        This keeps the existing behavior of _on_save(persist=True) for the
        currently open object (including UI label updates), then persists any
        remaining dirty objects in the cache and queued deletions. Ensures the
        unsaved indicator is cleared if everything is saved successfully.
        """
        # First, save the currently focused form (handles UI updates like renames)
        if not self._on_save(persist=True):
            self._update_unsaved_indicator()
            return

        # Then, persist any other dirty cached objects and queued deletions
        try:
            self.save_all_dirty()
        except Exception as exc:
            try:
                messagebox.showerror("Save failed", f"Could not save all changes:\n{exc}")
            except Exception:
                pass
        finally:
            # Ensure indicator reflects final state
            self._update_unsaved_indicator()

    def _mark_unsaved(self) -> None:
        """Set the unsaved flag and update UI indicator."""
        self._has_unsaved_changes = True
        self._update_unsaved_indicator()

    # ------------------------------------------------------------------
    # Unsaved changes indicator helpers
    # ------------------------------------------------------------------
    def _object_is_dirty(self, obj: Any) -> bool:
        try:
            if getattr(obj, 'dirty', False):
                return True
            comps = getattr(obj, 'components', {}) or {}
            for comp in comps.values():
                if getattr(comp, 'dirty', False):
                    return True
                if self._is_row_collection_component(comp):
                    for row in self._get_component_rows(comp):
                        if getattr(row, 'dirty', False):
                            return True
        except Exception:
            pass
        return False

    def _any_unsaved_changes(self) -> bool:
        # If we flipped the local flag recently, honor it, otherwise scan cache
        if self._has_unsaved_changes:
            return True
        try:
            for obj in self._object_cache.values():
                if self._object_is_dirty(obj):
                    return True
        except Exception:
            return False
        return False

    def _update_unsaved_indicator(self) -> None:
        label = getattr(self, 'unsaved_label', None)
        if not label:
            return
        if self._any_unsaved_changes():
            label.configure(text="Unsaved changes", foreground="#d97706")
        else:
            label.configure(text="")

    # ------------------------------------------------------------------
    # Undo button state helper
    # ------------------------------------------------------------------
    def _update_undo_button_state(self) -> None:
        """Enable the Undo button only when there are local deletions to undo.

        This looks for any of the local delete buffers/sets that we maintain:
        - _deleted_root_ids (set)
        - _deleted_components (list)
        - _deleted_skill_rows (list)
        - _deleted_rows (list)
        If none exist or all are empty, the button is disabled; otherwise enabled.
        Safe no-op for tabs that don't define an undo button.
        """
        btn = getattr(self, 'undo_btn', None)
        if not btn:
            return
        has_local = False
        try:
            if getattr(self, '_deleted_root_ids', None):
                has_local = True
            elif getattr(self, '_deleted_components', None):
                has_local = bool(getattr(self, '_deleted_components'))
            elif getattr(self, '_deleted_rows', None):
                has_local = bool(getattr(self, '_deleted_rows'))
            elif getattr(self, '_deleted_skill_rows', None):
                has_local = bool(getattr(self, '_deleted_skill_rows'))
        except Exception:
            has_local = False
        try:
            btn.configure(state=(tk.NORMAL if has_local else tk.DISABLED))
        except Exception:
            pass

    # Public helpers for Application to use on exit
    def has_unsaved_changes(self) -> bool:
        return self._any_unsaved_changes()

    def save_all_dirty(self) -> list[int]:
        """Persist all dirty cached objects for this tab. Returns list of saved object ids.

        Applies current form changes in-memory before saving to ensure latest edits are included.
        """
        # Ensure form edits are applied to the cached object but not yet persisted
        try:
            self._apply_current_form_changes()
        except Exception:
            pass

        saved_ids: list[int] = []
        # First, persist any pending root deletions
        try:
            self._persist_root_deletions()
        except Exception as exc:
            raise RuntimeError(f"Failed to delete some objects: {exc}")
        # Persist any pending component deletions
        try:
            self._persist_component_deletions()
        except Exception as exc:
            raise RuntimeError(f"Failed to delete some components: {exc}")
        # Iterate over a static list of items as we may modify _object_cache during saves
        for obj_id, obj in list(self._object_cache.items()):
            try:
                if self._object_is_dirty(obj):
                    self._service.save(obj)
                    # Remove from cache so it reloads fresh next time
                    self._object_cache.pop(obj_id, None)
                    saved_ids.append(obj_id)
            except Exception as exc:
                # Surface the error to caller by re-raising with context
                raise RuntimeError(f"Failed to save object {obj_id}: {exc}")
        # Refresh indicator after saving
        self._update_unsaved_indicator()
        return saved_ids

    def _persist_root_deletions(self) -> None:
        """Persist queued root deletions to the database via the service layer.

        After successful deletion, remove ids from cache, clear from deletion set,
        and refresh the left list/tree to reflect permanent removal.
        """
        deleted = getattr(self, '_deleted_root_ids', None)
        if not deleted:
            return
        errors: list[str] = []
        for oid in list(deleted):
            try:
                self._service.delete_object(int(oid))
                # Clean up local state
                self._object_cache.pop(int(oid), None)
                deleted.remove(oid)
            except Exception as exc:
                errors.append(f"{oid}: {exc}")
        # Rebuild list to drop deleted entries permanently
        try:
            self._list_data = []  # force reload
            self._rebuild_list_tree()
        except Exception:
            pass
        if errors:
            raise RuntimeError("; ".join(errors))
        # Update undo button state after persistence
        try:
            self._update_undo_button_state()
        except Exception:
            pass

    def _persist_component_deletions(self) -> None:
        """Persist queued component deletions to the database via the service layer."""
        queue = getattr(self, '_deleted_components', None)
        if not queue:
            return
        errors: list[str] = []
        for item in list(queue):
            try:
                ctype = item.get('type')
                cid = item.get('component_id')
                oid = item.get('object_id')
                self._service.delete_component(str(ctype), component_id=cid, object_id=oid)
                # Remove from queue after successful deletion
                queue.remove(item)
            except Exception as exc:
                errors.append(f"{ctype or '?'}: {exc}")
        # Force left list refresh to reflect permanent removal of components where applicable
        try:
            self._list_data = []
            self._rebuild_list_tree()
        except Exception:
            pass
        if errors:
            raise RuntimeError("; ".join(errors))
        # Update undo button after persistence
        try:
            self._update_undo_button_state()
        except Exception:
            pass

    # ------------------------------------------------------------------
    def _sort_list(
        self,
        items: list[dict[str, int | str]] | None,
        sort_by: str = "auto",
        reverse: bool = False,
    ) -> list[dict[str, int | str]]:
        """Sort a list of dicts returned by the services.

        sort_by: "auto" (default) -> prefer numeric 'id', then case-insensitive 'name',
                 "id"  -> force sort by numeric id when present (falls back to name/string)
                 "name"-> force sort by name (case-insensitive) when present (falls back to id/string)
        """
        # Normalize inputs: ensure items is a list and sort_by is a lowercase string
        items = items or []
        sort_by = (sort_by or "auto").lower()

        # Validate sort_by
        if sort_by not in {"auto", "id", "name"}:
            log.warning("Invalid sort_by '%s' - defaulting to 'auto'", sort_by)
            sort_by = "auto"

        def _key(obj):
            """
            Produce a tuple key for sorting:
              - First element is a priority group (lower sorts earlier)
              - Second element is the comparable value for that group

            Groups:
              0 -> primary preferred value present (e.g. id when sorting by id)
              1 -> secondary fallback value present (e.g. name when id missing)
              2 -> generic fallback using str(item)
              3 -> error case (conversion failed) - sorts last
            """
            try:
                # Prefer dict-style service results (expected shape {'id':..., 'name':...})
                if isinstance(obj, dict):
                    if sort_by == "id":
                        # Prefer numeric id ordering when available
                        if "id" in obj:
                            return (0, int(obj["id"]))
                        # Fall back to name if id missing
                        if "name" in obj:
                            return (1, str(obj["name"]).lower())
                        # Neither id nor name present - stringify as fallback
                        return (2, str(obj))

                    if sort_by == "name":
                        # Prefer case-insensitive name ordering when available
                        if "name" in obj:
                            return (0, str(obj["name"]).lower())
                        # Fall back to numeric id if name missing
                        if "id" in obj:
                            return (1, int(obj["id"]))
                        return (2, str(obj))

                    # auto: prefer id first, then name
                    if "id" in obj:
                        return (0, int(obj["id"]))
                    if "name" in obj:
                        return (1, str(obj["name"]).lower())

                # Non-dict items: use string representation as a neutral fallback
                return (2, str(obj))

            except Exception:
                # If conversion fails (e.g. int() on bad data), push to end but still compare by string
                return (3, str(obj))

        return sorted(items, key=_key, reverse=reverse)

    # ------------------------------------------------------------------
    # Generic left-pane list rebuilding (shared by tabs)
    # ------------------------------------------------------------------
    def _build_sort_bar(self, parent: tk.Misc) -> None:
        """Build a reusable sort controls bar (Sort by + Descending).

        Subclasses should call this when constructing their left sidebar.
        It binds controls to _rebuild_list_tree so changes take effect immediately.
        """
        sort_bar = ttk.Frame(parent)
        sort_bar.pack(fill=tk.X, padx=5, pady=(0, 5))
        ttk.Label(sort_bar, text="Sort by:").pack(side=tk.LEFT)
        sort_combo = ttk.Combobox(
            sort_bar,
            state="readonly",
            values=("id", "name"),
            textvariable=self.sort_by_var,
            width=8,
        )
        sort_combo.pack(side=tk.LEFT, padx=(4, 8))
        sort_combo.bind("<<ComboboxSelected>>", lambda _e: self._rebuild_list_tree())
        ttk.Checkbutton(
            sort_bar,
            text="Descending",
            variable=self.sort_desc_var,
            command=self._rebuild_list_tree,
        ).pack(side=tk.LEFT)

    def _load_list_data(self) -> list[dict[str, int | str]]:
        """Hook for subclasses to fetch list rows for the left tree.

        Each row should at minimum include keys 'id' (int/str) and 'name' (str) so
        the base renderer can build labels and stable iids.

        Subclasses must override.
        """
        raise NotImplementedError()

    def _format_node_text(self, info: dict[str, Any]) -> str:
        """Format the display text for a root node in the left tree.

        Default: "(<id>) <name>".

        Subclasses can override for custom labels.
        """
        return f"({info.get('id', '?')}) {info.get('name', '')}"

    def _make_root_iid(self, id_val: int | str) -> str:
        """Construct a unique-ish Treeview iid for a root node.

        Uses self.tree_prefix if set, defaulting to 'node'.
        """
        prefix = self.tree_prefix or "node"
        return f"{prefix}-{id_val}"

    def _make_root_iid_alt(self, id_val: int | str) -> str:
        """Alternate iid if the primary collides (e.g., duplicate ids in data)."""
        prefix = self.tree_prefix or "node"
        return f"{prefix}(1)-{id_val}"

    def _rebuild_list_tree(self) -> None:
        """Rebuild the left tree according to current sort settings (generic).

        Requires: self.tree (Treeview) to be created by subclass UI setup.
        Will lazy-load _list_data via _load_list_data if empty.
        Preserves selection by object id when possible.
        """
        if not hasattr(self, 'tree'):
            return

        # Lazy load list data once
        if not self._list_data:
            try:
                self._list_data = self._load_list_data() or []
            except Exception:
                log.exception("Error loading list data")
                self._list_data = []

        # Try to preserve current selection by parsing the id from the label text
        selected_obj_id: int | None = None
        sel = self.tree.selection()
        if sel:
            sel_iid = sel[0]
            parent_iid = sel_iid.split(":", 1)[0]
            try:
                text = self.tree.item(parent_iid, "text")
                if isinstance(text, str) and text.startswith("("):
                    end = text.find(")")
                    if end > 1:
                        selected_obj_id = int(text[1:end])
            except Exception:
                selected_obj_id = None

        # Overlay cached (possibly unsaved) names so filtering/display reflects local edits
        rows: list[dict[str, int | str]] = []
        # Skip locally deleted roots (user removed from view; not persisted yet)
        deleted_roots = getattr(self, '_deleted_root_ids', set())
        for r in (self._list_data or []):
            try:
                rid = r.get('id')
                rid_int = int(rid)
            except Exception:
                rid_int = r.get('id')
            # Filter out if user deleted this root item locally
            try:
                if rid_int in deleted_roots:
                    continue
            except Exception:
                pass
            cached = self._object_cache.get(rid_int)
            if cached is not None:
                # Prefer cached name if available
                name = getattr(cached, 'name', r.get('name'))
                rows.append({'id': r.get('id'), 'name': name})
            else:
                rows.append(r)

        # Apply search filter (by fuzzy id contains and/or name contains; id equality also supported)
        term = (self.search_var.get() or "").strip()
        filtered = list(rows)
        if term:
            t_lower = term.lower()
            id_val = None
            try:
                id_val = int(term)
            except Exception:
                id_val = None

            def _matches(row: dict[str, int | str]) -> bool:
                rid = row.get('id')
                rid_str = str(rid)
                rname = str(row.get('name', ''))
                cond_name = t_lower in rname.lower()
                # Fuzzy id match: substring match on the string form of the id
                cond_id_fuzzy = term in rid_str
                # Exact id match when term is numeric
                cond_id_exact = False
                if id_val is not None:
                    try:
                        cond_id_exact = int(rid) == id_val
                    except Exception:
                        cond_id_exact = False
                return cond_name or cond_id_fuzzy or cond_id_exact

            filtered = [r for r in filtered if _matches(r)]

        # Clear existing root nodes
        for child in self.tree.get_children(""):
            self.tree.delete(child)

        # Sort and rebuild
        sort_by = (self.sort_by_var.get() or "id").lower()
        reverse = bool(self.sort_desc_var.get())
        sorted_objs = self._sort_list(filtered, sort_by=sort_by, reverse=reverse)

        for info in sorted_objs:
            object_id = info.get('id')
            if object_id is None:
                continue
            parent_iid = self._make_root_iid(object_id)
            text = self._format_node_text(info)
            try:
                self.tree.insert("", tk.END, iid=parent_iid, text=text, open=False)
            except tk.TclError:
                # Collision (duplicate iid). Use alternate iid variant.
                parent_iid = self._make_root_iid_alt(object_id)
                self.tree.insert("", tk.END, iid=parent_iid, text=text, open=False)
                log.warning("Duplicate iid for object id %s; using alternate iid %s", object_id, parent_iid)
            # Add dummy child to make expandable
            self.tree.insert(parent_iid, tk.END, iid=f"{parent_iid}:dummy", text="(loading...)")

        # Restore selection if possible
        if selected_obj_id is not None:
            pattern = f"({selected_obj_id}) "
            for node in self.tree.get_children(""):
                text = self.tree.item(node, "text")
                if isinstance(text, str) and text.startswith(pattern):
                    try:
                        self.tree.selection_set(node)
                        self.tree.focus(node)
                        self.tree.see(node)
                    except Exception:
                        pass
                    break




class Application:
    """Main Tkinter application window."""

    def __init__(self, db_path: Path, version: str | None = None, window_size: str | None = None):
        """Create the main window.

        version: optional version string to display in the window title, e.g. "0.1.0".
        Keeping this argument optional preserves backward compatibility and makes it
        easy for packaging/CI to stamp the version in the entry point without
        touching this module.

        window_size: optional Tk geometry string for the initial window size,
        e.g. "1280x900". If omitted, the default startup size is used.
        """
        self.db_path = Path(db_path)
        self.version = version
        self.window_size = window_size
        self.root = tk.Tk()
        # Compose a friendly title that includes the version when provided
        base_title = "LU SQLite Tool"
        try:
            if isinstance(self.version, str) and self.version.strip():
                self.root.title(f"{base_title} v{self.version.strip()}")
            else:
                self.root.title(base_title)
        except Exception:
            # Last-resort fallback to a static title
            self.root.title(base_title)
        # Set the initial window size from the entry-point configuration when provided.
        if isinstance(self.window_size, str) and self.window_size.strip():
            self.root.geometry(self.window_size.strip())
        else:
            self.root.geometry("1280x900")

        # Route Tkinter callback exceptions to logger (helps catch UI errors)
        try:
            # Called when exceptions escape widget callbacks
            self.root.report_callback_exception = self._on_tk_callback_exception  # type: ignore[attr-defined]
        except Exception:
            log.debug("Failed to attach Tkinter report_callback_exception", exc_info=True)

        # Services ------------------------------------------------------
        self.item_service = ItemService(self.db_path)
        self.npc_service = NPCService(self.db_path)

        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        from .item_tab import ItemsTab
        from .npc_tab import NPCTab

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True)

        # Item tab --------------------------------------------------
        self.items_tab = ItemsTab(notebook, self.item_service)
        notebook.add(self.items_tab, text="Items")

        # NPC tab --------------------------------------------------
        self.npc_tab = NPCTab(notebook, self.npc_service)
        notebook.add(self.npc_tab, text="NPCs")

        # Intercept window close to warn about unsaved changes
        try:
            self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        except Exception:
            pass

    def _on_close(self) -> None:  # pragma: no cover - UI interaction
        """Prompt to save/discard unsaved changes on exit."""
        try:
            tabs_with_changes = []
            # Extend this list when more tabs inherit BaseObjectEntityTab
            for tab in [getattr(self, 'items_tab', None), getattr(self, 'npc_tab', None)]:
                if tab is not None and hasattr(tab, 'has_unsaved_changes') and tab.has_unsaved_changes():
                    tabs_with_changes.append(tab)

            if not tabs_with_changes:
                self.root.destroy()
                return

            res = messagebox.askyesnocancel(
                "Unsaved changes",
                "You have unsaved changes. Save before exiting?",
                default=messagebox.YES,
                icon=messagebox.WARNING,
            )
            # None -> Cancel
            if res is None:
                return
            # True -> Save then exit
            if res is True:
                try:
                    for tab in tabs_with_changes:
                        tab.save_all_dirty()
                except Exception as exc:
                    log.exception("Save-all on close failed")
                    messagebox.showerror("Save failed", f"Could not save all changes:\n{exc}")
                    return
                self.root.destroy()
                return
            # False -> Discard and exit
            self.root.destroy()
        except Exception:
            # If anything unexpected, fall back to normal close
            log.exception("Unexpected error during close handler")
            self.root.destroy()

    # ------------------------------------------------------------------
    def run(self) -> None:  # pragma: no cover - visual loop
        self.root.mainloop()

    # ------------------------------------------------------------------
    def _on_tk_callback_exception(self, exc_type, exc_value, exc_traceback):
        """Log uncaught exceptions from Tkinter widget callbacks."""
        try:
            log.critical("Tkinter callback exception", exc_info=(exc_type, exc_value, exc_traceback))
        except Exception:
            # Avoid crashing the UI if logging itself fails
            pass


