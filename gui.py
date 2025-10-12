from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

from Service.services import ItemService, NPCService
from metadata import component_field_metadata
from dataclasses import fields, is_dataclass
from typing import Any

# Import Item for type hinting
from Service.services import Item

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
        self.tree_prefix: str = ""  # e.g., 'item' or 'npc' – subclasses set this
        # Search/filter state shared by subclasses
        self.search_var = tk.StringVar(value="")
        # Unsaved changes state (UI indicator updated via _update_unsaved_indicator)
        self._has_unsaved_changes = False

    # --- abstract methods to be implemented by subclasses ---
    # def _build_form_for(self, component_kind: str) -> None:
    #     raise NotImplementedError()
    # def _on_save(self, persist: bool = True) -> None:
    #     raise NotImplementedError()

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

        # Get the currently loaded object
        obj = self.current_object
        if obj is None:
            self._show_message("No object loaded")
            return

        ####
        # Special case: object entity itself
        ####
        if component_type == "object":
            target_obj = obj  # GameObject fields

            # Set title and component class members to not display
            title = f"GameObject: ({obj.object_id}) {obj.name}"
            exclude = {"components", "dirty"}

        ####
        # Special case: ObjectSkill component with skill ID sub-selection
        ####
        elif component_type == "ObjectSkill":
            if grandchild_iid is None:
                self._show_message("No skill selected")
                return

            # Parse skill ID
            try:
                skill_id = int(grandchild_iid)
            except ValueError:
                self._show_message("Invalid skill ID")
                return

            # Find the skill object with the given skill_id
            object_skill_component = obj.components.get("ObjectSkill", None)
            target_obj = None
            if object_skill_component is not None and hasattr(object_skill_component, "skills"):
                for skill in object_skill_component.skills:
                    if getattr(skill, "skill_id", None) == skill_id:
                        target_obj = skill
                        break

            if target_obj is None:
                self._show_message(f"Skill ID {skill_id} not found")
                return

            # Set title and component class members to not display
            title = f"Skill ID {skill_id} of {obj.object_id}"
            exclude = {"dirty"}

        ####
        # General case: other components
        ####
        else:
            target_obj = obj.components.get(component_type)
            if target_obj is None:
                self._show_message(f"Component '{component_type}' not present")
                return

            # Set title and component class members to not display
            title = f"Component '{component_type}' of {obj.object_id}"
            exclude = {"dirty"}

        self.detail_label.configure(text=title)

        if not is_dataclass(target_obj):
            self._show_message("Unsupported component type")
            return

        # Store entry widgets for saving (name, tk.Variable, py_type, readonly)
        self._entry_widgets: list[tuple[str, tk.Variable, Any, bool]] = []

        # Resolve metadata key used for lookup into component_field_metadata.
        if component_type == "object":
            metadata_key = "GameObject"
        elif component_type == "ObjectSkill":
            metadata_key = "ObjectSkillRow"
        else:
            metadata_key = component_type
        comp_meta = component_field_metadata.get(metadata_key, {})

        # Build a scrollable canvas for many fields
        canvas = tk.Canvas(self.form_container, highlightthickness=0)
        scroll_y = ttk.Scrollbar(self.form_container, orient='vertical', command=canvas.yview)
        inner = ttk.Frame(canvas)
        inner.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=inner, anchor='nw')
        canvas.configure(yscrollcommand=scroll_y.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

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
            py_type = field_meta.get("type", f.type)
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
            if isinstance(value, bool):
                var = tk.BooleanVar(value=value)
                cb = ttk.Checkbutton(inner, variable=var)
                if readonly:
                    cb.state(["disabled"])  # ttk style disable
                cb.grid(row=row, column=1, sticky=tk.W, padx=2, pady=2)
                widget_for_tooltip = cb
            else:
                # For non-boolean fields we use a simple text Entry.
                # If the value looks like an enum (has .name and .value) show the enum name.
                # If the value is None show an empty string so the Entry is blank.
                if hasattr(value, 'name') and hasattr(value, 'value'):
                    display = value.name
                elif value is None:
                    display = ''
                else:
                    # Fallback: convert the value to string for display
                    display = str(value)

                var = tk.StringVar(value=display)
                entry = ttk.Entry(inner, textvariable=var, width=30)
                if readonly:
                    entry.configure(state='disabled')
                entry.grid(row=row, column=1, sticky=tk.W, padx=2, pady=2)
                widget_for_tooltip = entry

            # Keep track of the field so the Save handler can apply changes later.
            # We save the declared dataclass field type (f.type) to guide basic coercion.
            self._entry_widgets.append((f.name, var, py_type, readonly))

            # Mark unsaved state as soon as a field value changes
            try:
                var.trace_add('write', lambda *_args: self._mark_unsaved())
            except Exception:
                pass

            # If there is a tip, add a small info symbol (ⓘ) next to the field.
            # Hovering over this symbol shows the tooltip; avoids accidental popups
            # when just moving across the form.
            if tip_text:
                info_label = ttk.Label(inner, text="ⓘ")  # Unicode info symbol
                info_label.grid(row=row, column=2, sticky=tk.W, padx=(4, 2), pady=2)
                self._add_tooltip(info_label, tip_text)

        # Enable the Save button once there is an editable form
        self.save_button.configure(state=tk.NORMAL)

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
            self.current_object = self.__load_relevant_object(parent_iid, obj_id)

            if self.current_object is None:
                self._show_message("Could not load object")
                return

        except Exception as exc:  # pragma: no cover - visual feedback only
            self._show_message(str(exc))
            return

        # Save current component type then build form (store grandchild for refresh)
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

        # If there is a dummy child, remove it
        if self.tree.exists(f"{parent_iid}:dummy"):
            self.tree.delete(f"{parent_iid}:dummy")

        # If there already are children, do not re-load
        if self.tree.get_children(parent_iid):
            #TODO: Might want to refresh instead of ignoring
            return

        # Parse the object ID from the iid
        object_id = int(parent_iid.split("-", 1)[1])

        # Fetch object details from the respective service
        obj = self.__load_relevant_object(parent_iid, object_id)
        if obj is None:
            print(f"ERROR: could not load object {object_id} for expansion")
            return

        component_list = obj.components

        # Child list nodes (ie components from ComponentRegistry)
        for key in component_list: # key is component name
            child_iid = f"{parent_iid}:{key}"
            self.tree.insert(parent_iid, tk.END, iid=child_iid, text=key)

            # Special case – ObjectSkills (has sub children)
            if key == "ObjectSkill":
                for skill in component_list[key].skills:
                    skill_iid = f"{child_iid}:{skill.skill_id}"
                    self.tree.insert(child_iid, tk.END, iid=skill_iid, text=f"Skill {skill.skill_id}")

    # ------------------------------------------------------------------
    def _on_save(self, persist: bool = True) -> None:
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
            return

        # Resolve target object to edit

        ####
        # Special case: object entity itself
        ####
        if component_type == 'object':
            target_obj = obj

        ####
        # Special case: ObjectSkill component with skill ID sub-selection
        ####
        elif component_type == 'ObjectSkill':
            skill_id_str = getattr(self, '_last_grandchild_iid', None)
            if not skill_id_str:
                return
            try:
                skill_id = int(skill_id_str)
            except ValueError:
                return
            skill_comp = obj.components.get('ObjectSkill')
            if not skill_comp or not hasattr(skill_comp, 'skills'):
                return
            target_obj = next((row for row in skill_comp.skills if getattr(row, 'skill_id', None) == skill_id), None)
            if target_obj is None:
                return
            # Track the original skill id so we can rename the left tree node if it changes
            original_skill_id = getattr(target_obj, 'skill_id', None)

            # Duplicate-prevention: read the prospective new id from the form and block if it already exists
            try:
                var_skill = next((v for (n, v, _t, ro) in getattr(self, '_entry_widgets', []) if n == 'skill_id' and not ro), None)
            except Exception:
                var_skill = None
            if var_skill is not None:
                try:
                    new_proposed_id = int(var_skill.get())
                except Exception:
                    new_proposed_id = original_skill_id
                if isinstance(new_proposed_id, int) and new_proposed_id != original_skill_id:
                    if any((row is not target_obj) and getattr(row, 'skill_id', None) == new_proposed_id for row in getattr(skill_comp, 'skills', [])):
                        try:
                            messagebox.showerror("Duplicate Skill ID", f"Skill ID {new_proposed_id} already exists for this object.")
                        except Exception:
                            pass
                        # Reset entry back to original and abort save (no changes applied)
                        try:
                            var_skill.set(str(original_skill_id))
                        except Exception:
                            pass
                        return

        ####
        # General case: other components
        ####
        else:
            target_obj = obj.components.get(component_type)
            if target_obj is None:
                if persist:
                    self._show_message('Nothing to save')
                return

        entry_widgets = getattr(self, '_entry_widgets', [])
        if not entry_widgets:
            return

        # Apply widget values to target object, track if anything changed
        any_changed = False
        for name, var, typ, readonly in entry_widgets:
            if readonly:
                continue
            raw = var.get()
            old_val = getattr(target_obj, name, None)
            if isinstance(var, tk.BooleanVar):
                new_val = bool(raw)
                if new_val != bool(old_val):
                    setattr(target_obj, name, new_val)
                    any_changed = True
                continue
            if raw == '':
                new_val = None
            else:
                try:
                    if typ in (int, 'int') or (hasattr(typ, '__origin__') and getattr(typ, '__origin__', None) is int):
                        new_val = int(raw)
                    elif typ in (float, 'float'):
                        new_val = float(raw)
                    elif typ in (bool, 'bool'):
                        raise NotImplementedError("Boolean fields should use Checkbutton/BooleanVar")
                        # value = str(raw).lower() in {"1", "true", "yes", "on"} TODO: Remove?
                    else:
                        new_val = raw
                except Exception:
                    new_val = raw
            if new_val != old_val:
                setattr(target_obj, name, new_val)
                any_changed = True

        # Mark dirty
        try:
            if any_changed:
                # For skills, mark both skill row and ObjectSkill component dirty
                if component_type == 'ObjectSkill':
                    target_obj.dirty = True
                    obj.components['ObjectSkill'].dirty = True
                else:
                    target_obj.dirty = True
        except Exception:
            pass

        # Persist if requested
        if persist:
            # Persist changes through the service layer (to save to DB)
            try:
                self._service.save_item(obj)
                self._show_message('Saved successfully')
            except Exception as exc:  # pragma: no cover
                self._show_message(f'Error saving: {exc}')

            # Remove from cache so next load is fresh from DB
            self._object_cache.pop(obj.object_id, None)
            # Clear unsaved flag after successful save (recomputed in indicator)
            self._has_unsaved_changes = False
        else:
            # Track unsaved state locally only if we actually changed anything
            if any_changed:
                self._has_unsaved_changes = True


        ##################################
        ### Ensure left tree is in sync with any changes
        #################################

        # Keep left list in sync when a skill's skill_id is changed: update node iid/text and our refresh context
        if component_type == 'ObjectSkill':
            try:
                new_skill_id = getattr(target_obj, 'skill_id', None)
                if (
                    'original_skill_id' in locals()
                    and isinstance(original_skill_id, int)
                    and isinstance(new_skill_id, int)
                    and original_skill_id != new_skill_id
                ):
                    # Find the correct parent skill iid (handle both normal and alternate root iids)
                    candidates = [self._make_root_iid(obj.object_id), self._make_root_iid_alt(obj.object_id)]
                    old_iid = None
                    parent_skill_iid = None
                    for root in candidates:
                        cand_parent = f"{root}:ObjectSkill"
                        cand_old = f"{cand_parent}:{original_skill_id}"
                        if self.tree.exists(cand_old):
                            old_iid = cand_old
                            parent_skill_iid = cand_parent
                            break
                    # Fallback: try current selection
                    if old_iid is None:
                        sel = self.tree.selection()
                        if sel and self.tree.exists(sel[0]) and sel[0].count(":") == 2:
                            old_iid = sel[0]
                            parent_skill_iid = old_iid.rsplit(":", 1)[0]
                    if old_iid is None or parent_skill_iid is None:
                        # No visible node to rename; nothing to do
                        raise RuntimeError("Skill node not found for rename")

                    new_iid = f"{parent_skill_iid}:{new_skill_id}"
                    if self.tree.exists(new_iid):
                        # If target already exists, delete old and switch selection
                        try:
                            self.tree.delete(old_iid)
                        except Exception:
                            pass
                        self.tree.item(new_iid, text=f"Skill {new_skill_id}")
                        self.tree.selection_set(new_iid)
                        self.tree.focus(new_iid)
                    else:
                        # Insert replacement at same index, then remove old
                        try:
                            idx = self.tree.index(old_iid)
                        except Exception:
                            idx = tk.END
                        self.tree.insert(parent_skill_iid, idx, iid=new_iid, text=f"Skill {new_skill_id}")
                        try:
                            self.tree.delete(old_iid)
                        except Exception:
                            pass
                        self.tree.selection_set(new_iid)
                        self.tree.focus(new_iid)
                    # Update context for future form refreshes
                    self._last_grandchild_iid = str(new_skill_id)
            except Exception:
                # Best-effort label update if anything above fails
                try:
                    sel = self.tree.selection()
                    if sel:
                        self.tree.item(sel[0], text=f"Skill {getattr(target_obj, 'skill_id', '')}")
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

    # ------------------------------------------------------------------
    def __load_relevant_object(self, parent_iid: str, obj_id: int) -> Item: #TODO: add NPC type hint when implemented
        """Load the relevant object (Item or NPC) based on the parent iid prefix and object ID."""

        # Return cached object if already loaded (preserves unsaved edits)
        cached = self._object_cache.get(obj_id)
        if cached is not None:
            return cached

        # Load from the appropriate service based on prefix
        obj = None
        if parent_iid.startswith("item-"):
             obj = self._service.get_item(obj_id)
        elif parent_iid.startswith("npc-"):
            # Placeholder for future NPC support
            # return self._service.get_npc(obj_id) # TODO
            raise NotImplementedError("NPC support not yet implemented")

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
                # Special-case nested rows like ObjectSkill
                if hasattr(comp, 'skills'):
                    for row in getattr(comp, 'skills', []) or []:
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
            print(f"WARNING: invalid sort_by '{sort_by}' – defaulting to 'auto'")
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
              3 -> error case (conversion failed) — sorts last
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
                        # Neither id nor name present — stringify as fallback
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
            except Exception as exc:
                print(f"ERROR loading list data: {exc}")
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
        for r in (self._list_data or []):
            try:
                rid = r.get('id')
                rid_int = int(rid)
            except Exception:
                rid_int = r.get('id')
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
        sidebar = ttk.Frame(paned, width=220)  # initial width hint

        create_btn = ttk.Button(sidebar, text="Create")
        create_btn.pack(padx=5, pady=(5, 2), fill=tk.X)

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

        # Right content area --------------------------------------------
        self.detail = ttk.Frame(paned)
        self.detail_label = ttk.Label(self.detail, text="Select an item or component to edit")
        self.detail_label.pack(padx=10, pady=5, anchor=tk.NW)

        # Advanced field toggle (affects filtering logic in form build)
        toggle_bar = ttk.Frame(self.detail)
        toggle_bar.pack(fill=tk.X, padx=10, pady=(0, 5))
        self.show_advanced_var = tk.BooleanVar(value=False)
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
            command=lambda: self._on_save(persist=True),
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

    # (tree rebuild now handled by BaseObjectEntityTab._rebuild_list_tree)


class Application:
    """Main Tkinter application window."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.root = tk.Tk()
        self.root.title("LU SQLite Tool")
        # Set a larger initial window size so more fields are visible without resizing.
        # Width x Height; adjust if you prefer different default dimensions.
        self.root.geometry("1280x900")

        # Services ------------------------------------------------------
        self.item_service = ItemService(self.db_path)
        self.npc_service = NPCService(self.db_path)  # placeholder for future use

        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True)

        # Item tab --------------------------------------------------
        items_tab = ItemsTab(notebook, self.item_service)
        notebook.add(items_tab, text="Items")

        # NPC tab placeholder ------------------------------------------
        npc_tab = ttk.Frame(notebook)
        ttk.Label(npc_tab, text="NPC tools coming soon").pack(padx=10, pady=10)
        notebook.add(npc_tab, text="NPCs")

    # ------------------------------------------------------------------
    def run(self) -> None:  # pragma: no cover - visual loop
        self.root.mainloop()
