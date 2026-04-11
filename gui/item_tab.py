from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any

from Service.services import ItemService

from .gui import BaseObjectEntityTab


class ItemsTab(BaseObjectEntityTab):
    """Tab containing item related widgets."""

    def __init__(self, master: tk.Misc, service: ItemService):
        super().__init__(master)
        self._service = service
        # Identify root node prefix for generic tree helpers
        self.tree_prefix = "item"
        self._build_widgets()

    # Provide data to the base list builder
    def _load_list_data(self) -> list[dict[str, int | str]]:
        return self._service.list_items(limit=None)

    # ------------------------------------------------------------------
    def _build_widgets(self) -> None:
        # Use a Panedwindow to allow user-resizable sidebar -------------
        paned = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # Left sidebar --------------------------------------------------
        sidebar = ttk.Frame(paned, width=260)  # initial width hint

        # Create row: optional ID entry + Create button + Duplicate button
        create_row = ttk.Frame(sidebar)
        create_row.pack(fill=tk.X, padx=5, pady=(6, 2))
        ttk.Label(create_row, text="ID:").pack(side=tk.LEFT)
        self.create_id_var = tk.StringVar()
        id_entry = ttk.Entry(create_row, textvariable=self.create_id_var, width=12)
        id_entry.pack(side=tk.LEFT, padx=(4, 4))
        self._add_tooltip(id_entry, "Optional. Unsigned integer up to 2147483647. Leave empty to auto-assign.")

        create_btn = ttk.Button(create_row, text="Create", command=self._on_create_item)
        create_btn.pack(side=tk.LEFT, padx=(4, 0))

        dup_btn = ttk.Button(create_row, text="Duplicate", command=self._on_duplicate_item)
        dup_btn.pack(side=tk.LEFT, padx=(4, 0))
        self._add_tooltip(dup_btn, "Duplicate the selected item. Uses the ID field if provided; otherwise auto-assigns.")

        # Undo local deletes button
        undo_row = ttk.Frame(sidebar)
        undo_row.pack(fill=tk.X, padx=5, pady=(2, 6))
        self.undo_btn = ttk.Button(undo_row, text="Undo local deletes", command=self._undo_local_deletes)
        self.undo_btn.pack(side=tk.LEFT)
        # Initially disabled until there is something to undo
        try:
            self.undo_btn.configure(state=tk.DISABLED)
        except Exception:
            pass

        # Search controls ------------------------------------------------
        search_bar = ttk.Frame(sidebar)
        search_bar.pack(fill=tk.X, padx=5, pady=(0, 5))
        ttk.Label(search_bar, text="Search:").pack(side=tk.LEFT)
        search_entry = ttk.Entry(search_bar, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 4))
        # Debounced live search: rebuild list after a short pause in typing
        self._search_after_id = None
        def _do_search(_e=None):
            # Clear any in-memory unsaved edits before refiltering
            self._apply_current_form_changes()
            self._rebuild_list_tree()
        def _debounced_search(*_args):
            try:
                if self._search_after_id is not None:
                    self.after_cancel(self._search_after_id)
            except Exception:
                pass
            # 150ms debounce window
            self._search_after_id = self.after(150, _do_search)
        search_entry.bind('<Return>', _do_search)
        self.search_var.trace_add('write', _debounced_search)
        # Sort controls (provided by base)
        self._build_sort_bar(sidebar)

        # Tree + vertical scrollbar container
        tree_container = ttk.Frame(sidebar)
        tree_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        vsb = ttk.Scrollbar(tree_container, orient="vertical")
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree = ttk.Treeview(tree_container, show="tree", yscrollcommand=vsb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.configure(command=self.tree.yview)

        # Build the tree according to current sort settings
        self._rebuild_list_tree()

        self.tree.bind("<<TreeviewSelect>>", self._on_list_node_select)
        self.tree.bind("<<TreeviewOpen>>", self._on_list_node_expanded)
        # Right-click (context menu) for delete actions
        self.tree.bind("<Button-3>", self._on_tree_context_menu)
        # Also ensure left-click sets selection before context menu
        self.tree.bind("<Button-1>", lambda e: None, add=True)

        # Right content area --------------------------------------------
        self.detail = ttk.Frame(paned)
        self.detail_label = ttk.Label(self.detail, text="Select an item or component to edit")
        self.detail_label.pack(padx=10, pady=5, anchor=tk.NW)

        # Advanced field toggle (affects filtering logic in form build)
        toggle_bar = ttk.Frame(self.detail)
        toggle_bar.pack(fill=tk.X, padx=10, pady=(0, 5))
        self.show_advanced_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            toggle_bar,
            text="Show advanced fields",
            variable=self.show_advanced_var,
            command=self._refresh_form
        ).pack(side=tk.LEFT, anchor=tk.W)

        self.form_container = ttk.Frame(self.detail)
        self.form_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Save button at bottom (explicit lambda so signature can take persist flag)
        self.save_button = ttk.Button(
            self.detail,
            text="Save",
            command=self._on_save_all,
            state=tk.DISABLED,
        )
        self.save_button.pack(padx=10, pady=10, anchor=tk.SE)

        self.current_object = None  # type: Any
        self.current_component_type: str | None = None

        # Add panes after they are populated so initial sizes take effect
        # Give sidebar a smaller weight so detail area expands more.
        paned.add(sidebar, weight=1)
        paned.add(self.detail, weight=4)

        # Footer status bar for unsaved changes indicator
        status_bar = ttk.Frame(self)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        self.unsaved_label = ttk.Label(status_bar, text="", foreground="#d97706")
        self.unsaved_label.pack(side=tk.LEFT, padx=8, pady=(0, 4))
        # Initialize indicator
        self._update_unsaved_indicator()
        # Initialize undo button state
        self._update_undo_button_state()

    # (tree rebuild now handled by BaseObjectEntityTab._rebuild_list_tree)

    # --------------------------------------------------------------
    # Actions
    # --------------------------------------------------------------
    def _parse_optional_id_from_entry(self) -> int | None:
        """Parse the optional ID entry used by create/duplicate.

        Returns an int or None when empty. Validates positive 32-bit signed range.
        Raises ValueError with a user-readable message for invalid input.
        """
        raw_id = (self.create_id_var.get() or "").strip() if hasattr(self, 'create_id_var') else ""
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

    def _on_create_item(self) -> None:
        """Create a brand new item with default components and select it in the tree.

        Uses the service layer to construct and persist the new item, then refreshes
        the left list and selects the new entry, opening its base object form.
        """
        try:
            # Parse optional ID from entry; ensure unsigned integer if provided
            try:
                provided_id = self._parse_optional_id_from_entry()
            except ValueError as ve:
                messagebox.showerror("Invalid ID", str(ve))
                return

            # Ask service to create and persist a default item
            new_item = self._service.create_default_item(provided_id)
            if not new_item:
                messagebox.showerror("Create failed", "Could not create item.")
                return

            # Invalidate cached list data so a rebuild pulls the new row
            self._list_data = []
            # Also drop any cached object with the same id to read fresh
            self._object_cache.pop(new_item.object_id, None)

            # Rebuild tree and select the newly created item
            self._rebuild_list_tree()
            # Compute possible iids and try to select
            candidate_iids = [self._make_root_iid(new_item.object_id), self._make_root_iid_alt(new_item.object_id)]
            target_iid = next((iid for iid in candidate_iids if self.tree.exists(iid)), None)
            if target_iid is not None:
                try:
                    # Ensure node is visible & focused
                    self.tree.selection_set(target_iid)
                    self.tree.focus(target_iid)
                    self.tree.see(target_iid)
                    # Build the base form for the new object
                    self.current_object = new_item
                    self.current_component_type = "object"
                    self._build_form_for("object")
                except Exception:
                    pass
            else:
                # Fallback: notify creation succeeded
                messagebox.showinfo("Item created", f"Created item {new_item.object_id}.")

        except Exception as exc:
            messagebox.showerror("Create failed", str(exc))

    def _on_duplicate_item(self) -> None:
        """Duplicate the currently selected item to a new ID (optional ID entry)."""
        # Determine selected source item id (use parent iid if a child is selected)
        sel = self.tree.selection()
        if not sel:
            messagebox.showerror("Duplicate failed", "Select an item to duplicate from the list.")
            return
        iid = sel[0]
        parent_iid = iid.split(":", 1)[0] if ":" in iid else iid
        try:
            src_id = int(parent_iid.split("-", 1)[1])
        except Exception:
            messagebox.showerror("Duplicate failed", "Unable to determine selected item id.")
            return

        # Parse optional destination id using same rules as Create
        try:
            dest_id = self._parse_optional_id_from_entry()
        except ValueError as ve:
            messagebox.showerror("Invalid ID", str(ve))
            return

        try:
            dup = self._service.duplicate_item(src_id, dest_id)
        except Exception as exc:
            messagebox.showerror("Duplicate failed", str(exc))
            return

        if not dup:
            messagebox.showerror("Duplicate failed", "Could not duplicate item.")
            return

        # Clear the ID entry after successful creation/duplication to avoid accidental reuse
        try:
            self.create_id_var.set("")
        except Exception:
            pass

        # Invalidate cached list data and reload
        self._list_data = []
        self._object_cache.pop(dup.object_id, None)
        self._rebuild_list_tree()

        # Select the new item and open its object form
        candidate_iids = [self._make_root_iid(dup.object_id), self._make_root_iid_alt(dup.object_id)]
        target_iid = next((iid for iid in candidate_iids if self.tree.exists(iid)), None)
        if target_iid is not None:
            try:
                self.tree.selection_set(target_iid)
                self.tree.focus(target_iid)
                self.tree.see(target_iid)
                self.current_object = dup
                self.current_component_type = "object"
                self._build_form_for("object")
            except Exception:
                pass
        else:
            messagebox.showinfo("Item duplicated", f"Created item {dup.object_id}.")

    # --------------------------------------------------------------
    # Context menu: delete (local) root items and skill subitems
    # --------------------------------------------------------------
    # ---- Context menu hooks (implement base abstract hooks) ----
    def get_root_delete_label(self) -> str | None:
        return "Delete item (local)"

    def on_delete_root_local(self, object_id: int, iid: str) -> None:
        # Confirm
        try:
            text = self.tree.item(iid, 'text') or ''
        except Exception:
            text = ''
        if not messagebox.askyesno(
            "Delete item",
            f"Delete {text}?\n\nThis removes it from the view now and will delete it permanently when you press Save.\nAll of its components and skills will also be deleted.",
            icon=messagebox.WARNING,
            default=messagebox.NO,
        ):
            return
        # Track local deletion and update tree
        if not hasattr(self, '_deleted_root_ids'):
            self._deleted_root_ids = set()
        self._deleted_root_ids.add(int(object_id))
        try:
            self.tree.delete(iid)
        except Exception:
            pass
        # Clear form if we deleted the currently viewed object
        sel = self.tree.selection()
        if not sel:
            self.current_object = None
            self.current_component_type = None
            self._show_message("Select an item or component to edit")
        # Reflect change in the left list immediately
        self._rebuild_list_tree()
        # Update undo button state
        try:
            self._update_undo_button_state()
        except Exception:
            pass

    def get_root_add_component_actions(self, obj) -> list[tuple[str, any, bool]]:
        actions: list[tuple[str, any, bool]] = []
        if obj is None:
            return actions
        existing = set(getattr(getattr(obj, 'components', {}), 'keys', lambda: [])())
        iid = self.tree.selection()[0] if self.tree.selection() else ''

        def _add_item_component():
            comp = self._service.add_item_component(obj)
            child_iid = f"{iid}:ItemComponent"
            if not self.tree.exists(child_iid):
                try:
                    self.tree.insert(iid, tk.END, iid=child_iid, text="ItemComponent")
                except Exception:
                    pass
            try:
                self.tree.selection_set(child_iid)
                self.tree.focus(child_iid)
                self.current_object = obj
                self.current_component_type = "ItemComponent"
                self._build_form_for("ItemComponent")
            except Exception:
                pass
            self._ctx_mark_unsaved_indicator()  # type: ignore[attr-defined]

        def _add_render_component():
            comp = self._service.add_render_component(obj)
            child_iid = f"{iid}:RenderComponent"
            if not self.tree.exists(child_iid):
                try:
                    self.tree.insert(iid, tk.END, iid=child_iid, text="RenderComponent")
                except Exception:
                    pass
            try:
                self.tree.selection_set(child_iid)
                self.tree.focus(child_iid)
                self.current_object = obj
                self.current_component_type = "RenderComponent"
                self._build_form_for("RenderComponent")
            except Exception:
                pass
            self._ctx_mark_unsaved_indicator()  # type: ignore[attr-defined]

        def _add_skill_from_root():
            new_row = self._service.add_blank_skill(obj)
            skill_parent_iid = f"{iid}:ObjectSkill"
            if not self.tree.exists(skill_parent_iid):
                try:
                    self.tree.insert(iid, tk.END, iid=skill_parent_iid, text="ObjectSkill")
                except Exception:
                    pass
            skill_iid = f"{skill_parent_iid}:{getattr(new_row, 'skill_id', '')}"
            if not self.tree.exists(skill_iid):
                try:
                    self.tree.insert(skill_parent_iid, tk.END, iid=skill_iid, text=f"Skill {getattr(new_row, 'skill_id', '')}")
                except Exception:
                    pass
            try:
                self.tree.item(skill_parent_iid, open=True)
                self.tree.selection_set(skill_iid)
                self.tree.focus(skill_iid)
                self.current_object = obj
                self.current_component_type = "ObjectSkill"
                self._last_grandchild_iid = str(getattr(new_row, 'skill_id', ''))
                self._build_form_for("ObjectSkill", self._last_grandchild_iid)
            except Exception:
                pass
            self._ctx_mark_unsaved_indicator()  # type: ignore[attr-defined]

        actions.append(("Item Component", _add_item_component, ("ItemComponent" not in existing)))
        actions.append(("Render Component", _add_render_component, ("RenderComponent" not in existing)))
        actions.append(("Skill", _add_skill_from_root, True))
        return actions

    def get_component_delete_action(self, comp_name: str, obj, iid: str, parent_iid: str):
        if comp_name not in ("ItemComponent", "RenderComponent", "ObjectSkill"):
            return None
        def _delete_component_local():
            # Parse object id
            try:
                obj_id = int(parent_iid.split('-', 1)[1])
            except Exception:
                return
            # Load object (cache or service via base helper)
            obj_local = obj or self._ctx_get_cached_or_load(parent_iid, obj_id)  # type: ignore[attr-defined]
            if obj_local is None:
                messagebox.showerror("Delete failed", "Could not load object to modify component.")
                return
            # Confirm
            if not messagebox.askyesno(
                "Delete component",
                f"Delete {comp_name} from object {obj_id}?\n\nThis removes it now and will delete it permanently when you press Save.",
                icon=messagebox.WARNING,
                default=messagebox.NO,
            ):
                return
            # Queue deletion specifics and remove from in-memory object
            if comp_name == 'ItemComponent':
                comp = obj_local.components.get('ItemComponent')
                if comp is None:
                    return
                comp_id = getattr(comp, 'id', None)
                deleted_copy = comp
                obj_local.components.pop('ItemComponent', None)
                if not hasattr(self, '_deleted_components'):
                    self._deleted_components = []
                if comp_id:
                    self._deleted_components.append({'type': 'ItemComponent', 'component_id': int(comp_id), 'object_id': obj_id, 'component': deleted_copy})
            elif comp_name == 'RenderComponent':
                comp = obj_local.components.get('RenderComponent')
                if comp is None:
                    return
                comp_id = getattr(comp, 'id', None)
                deleted_copy = comp
                obj_local.components.pop('RenderComponent', None)
                if not hasattr(self, '_deleted_components'):
                    self._deleted_components = []
                if comp_id:
                    self._deleted_components.append({'type': 'RenderComponent', 'component_id': int(comp_id), 'object_id': obj_id, 'component': deleted_copy})
            elif comp_name == 'ObjectSkill':
                comp = obj_local.components.get('ObjectSkill')
                if comp is None:
                    return
                deleted_copy = comp
                obj_local.components.pop('ObjectSkill', None)
                if not hasattr(self, '_deleted_components'):
                    self._deleted_components = []
                self._deleted_components.append({'type': 'ObjectSkill', 'component_id': None, 'object_id': obj_id, 'component': deleted_copy})
            # Mark unsaved and update indicator/undo
            self._has_unsaved_changes = True
            self._update_unsaved_indicator()
            self._update_undo_button_state()
            # Remove node (and grandchildren for ObjectSkill)
            try:
                if comp_name == 'ObjectSkill':
                    for child in self.tree.get_children(iid):
                        try:
                            self.tree.delete(child)
                        except Exception:
                            pass
                self.tree.delete(iid)
            except Exception:
                pass
            # If we were viewing this component, clear/switch the form
            sel = self.tree.selection()
            if not sel:
                self.current_component_type = 'object'
                self.current_object = obj_local
                self._build_form_for('object')
        return ("Delete component (local)", _delete_component_local)

    def get_component_add_subitem_actions(self, comp_name: str, obj, iid: str, parent_iid: str):
        actions: list[tuple[str, any]] = []
        if comp_name != 'ObjectSkill':
            return actions
        def _add_skill_under_component():
            # prefer cached obj, else via base helper
            try:
                obj_id = int(parent_iid.split('-', 1)[1])
            except Exception:
                return
            target = obj or self._ctx_get_cached_or_load(parent_iid, obj_id)  # type: ignore[attr-defined]
            if target is None:
                return
            new_row = self._service.add_blank_skill(target)
            skill_parent_iid = iid
            skill_iid = f"{skill_parent_iid}:{getattr(new_row, 'skill_id', '')}"
            if not self.tree.exists(skill_iid):
                try:
                    self.tree.insert(skill_parent_iid, tk.END, iid=skill_iid, text=f"Skill {getattr(new_row, 'skill_id', '')}")
                except Exception:
                    pass
            try:
                self.tree.item(skill_parent_iid, open=True)
                self.tree.selection_set(skill_iid)
                self.tree.focus(skill_iid)
                self.current_object = target
                self.current_component_type = 'ObjectSkill'
                self._last_grandchild_iid = str(getattr(new_row, 'skill_id', ''))
                self._build_form_for('ObjectSkill', self._last_grandchild_iid)
            except Exception:
                pass
            self._ctx_mark_unsaved_indicator()  # type: ignore[attr-defined]
        actions.append(("Add skill", _add_skill_under_component))
        return actions

    def get_grandchild_delete_action(self, parts: list[str], obj):
        # Only handle ObjectSkill grandchildren
        if len(parts) != 3 or parts[1] != 'ObjectSkill':
            return None
        iid = self.tree.selection()[0] if self.tree.selection() else ''
        def _delete_skill_row():
            parent_iid = parts[0]
            try:
                obj_id = int(parent_iid.split('-', 1)[1])
                skill_id = int(parts[2])
            except Exception:
                return
            if not messagebox.askyesno(
                "Delete skill",
                f"Delete Skill {skill_id} from object {obj_id}?\n\nThis removes it now and will delete it permanently when you press Save.",
                icon=messagebox.WARNING,
                default=messagebox.NO,
            ):
                return
            target = obj or self._ctx_get_cached_or_load(parent_iid, obj_id)  # type: ignore[attr-defined]
            if target is None:
                messagebox.showerror("Delete failed", "Could not load object to modify skills.")
                return
            skill_comp = target.components.get('ObjectSkill')
            if not skill_comp or not hasattr(skill_comp, 'skills'):
                messagebox.showerror("Delete failed", "Object has no skills component.")
                return
            removed_rows = [row for row in skill_comp.skills if getattr(row, 'skill_id', None) == skill_id]
            original_len = len(skill_comp.skills)
            skill_comp.skills = [row for row in skill_comp.skills if getattr(row, 'skill_id', None) != skill_id]
            if len(skill_comp.skills) == original_len:
                return
            if removed_rows:
                if not hasattr(self, '_deleted_skill_rows'):
                    self._deleted_skill_rows = []
                for r in removed_rows:
                    self._deleted_skill_rows.append({'object_id': obj_id, 'row': r})
            try:
                skill_comp.dirty = True
            except Exception:
                pass
            self._has_unsaved_changes = True
            self._update_unsaved_indicator()
            self._update_undo_button_state()
            try:
                self.tree.delete(iid)
            except Exception:
                pass
            sel = self.tree.selection()
            if not sel:
                parent_skill_iid = f"{parent_iid}:ObjectSkill"
                if self.tree.exists(parent_skill_iid):
                    try:
                        self.tree.selection_set(parent_skill_iid)
                        self.tree.focus(parent_skill_iid)
                        self.tree.see(parent_skill_iid)
                        self.current_object = target
                        self.current_component_type = 'ObjectSkill'
                        self._build_form_for('ObjectSkill', None)
                    except Exception:
                        pass
            try:
                self.tree.item(f"{parent_iid}:ObjectSkill", open=True)
            except Exception:
                pass
        return ("Delete skill", _delete_skill_row)

    def _undo_local_deletes(self) -> None:
        """Undo all local (not yet persisted) deletions: roots, components, and individual skill rows.

        - Restores removed components back onto the cached objects.
        - Restores removed skill rows to the in-memory skill lists.
        - Clears the local deletion queues/sets.
        - Refreshes the left list and form indicator.
        """
        # Restore components
        try:
            comp_queue = getattr(self, '_deleted_components', []) or []
            for item in list(comp_queue):
                oid = item.get('object_id')
                comp = item.get('component')
                ctype = item.get('type')
                if oid is None or comp is None or not ctype:
                    continue
                # Load or use cached object
                obj = self._object_cache.get(oid)
                if obj is None:
                    try:
                        obj = self._service.get_item(int(oid))
                        if obj is not None:
                            self._object_cache[oid] = obj
                    except Exception:
                        obj = None
                if obj is None:
                    continue
                # Restore component
                obj.components[ctype] = comp
                try:
                    comp.dirty = False
                except Exception:
                    pass
                # Remove from queue
                comp_queue.remove(item)
        except Exception:
            pass

        # Restore removed individual skill rows
        try:
            skill_queue = getattr(self, '_deleted_skill_rows', []) or []
            for item in list(skill_queue):
                oid = item.get('object_id')
                row = item.get('row')
                if oid is None or row is None:
                    continue
                obj = self._object_cache.get(oid)
                if obj is None:
                    try:
                        obj = self._service.get_item(int(oid))
                        if obj is not None:
                            self._object_cache[oid] = obj
                    except Exception:
                        obj = None
                if obj is None:
                    continue
                skill_comp = obj.components.get('ObjectSkill')
                if skill_comp is None:
                    # If skill component was also deleted and restored above, it exists now; if not, create minimal container
                    try:
                        from Domain.domains import ObjectSkills
                        skill_comp = ObjectSkills(skills=[]); obj.components['ObjectSkill'] = skill_comp
                    except Exception:
                        continue
                # Avoid duplicate by skill_id
                sid = getattr(row, 'skill_id', None)
                if sid is not None and any(getattr(r, 'skill_id', None) == sid for r in skill_comp.skills):
                    pass
                else:
                    skill_comp.skills.append(row)
                try:
                    skill_comp.dirty = False
                except Exception:
                    pass
                # Remove from queue
                skill_queue.remove(item)
        except Exception:
            pass

        # Clear local root deletion filter and refresh list/tree
        try:
            if hasattr(self, '_deleted_root_ids'):
                self._deleted_root_ids.clear()
        except Exception:
            pass

        # Rebuild list and clear right panel message
        try:
            self._rebuild_list_tree()
            self._update_unsaved_indicator()
            self._update_undo_button_state()
            try:
                messagebox.showinfo("Undo", "Local deletes have been undone.")
            except Exception:
                pass
        except Exception:
            pass

