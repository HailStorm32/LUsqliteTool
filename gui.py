from __future__ import annotations

import tkinter as tk
from tkinter import ttk
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
            "RenderComponent" -> any normal component name (must exist in object.components)
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
    def _on_save(self, persist: bool = True) -> None: #TODO: standardize and place in base class
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

        # Apply widget values to target object
        for name, var, typ, readonly in entry_widgets:
            if readonly:
                continue
            raw = var.get()
            if isinstance(var, tk.BooleanVar):
                setattr(target_obj, name, bool(raw))
                continue
            if raw == '':
                value = None
            else:
                try:
                    if typ in (int, 'int') or (hasattr(typ, '__origin__') and getattr(typ, '__origin__', None) is int):
                        value = int(raw)
                    elif typ in (float, 'float'):
                        value = float(raw)
                    elif typ in (bool, 'bool'):
                        raise NotImplementedError("Boolean fields should use Checkbutton/BooleanVar")
                        # value = str(raw).lower() in {"1", "true", "yes", "on"} TODO: Remove?
                    else:
                        value = raw
                except Exception:
                    value = raw
            setattr(target_obj, name, value)

        # Mark dirty
        try:
            target_obj.dirty = True  # type: ignore[attr-defined]
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


class ItemsTab(BaseObjectEntityTab):
    """Tab containing item related widgets."""

    def __init__(self, master: tk.Misc, service: ItemService):
        super().__init__(master)
        self._service = service
        self._build_widgets()

    # ------------------------------------------------------------------
    def _build_widgets(self) -> None:
        # Use a Panedwindow to allow user-resizable sidebar -------------
        paned = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # Left sidebar --------------------------------------------------
        sidebar = ttk.Frame(paned, width=220)  # initial width hint

        create_btn = ttk.Button(sidebar, text="Create")
        create_btn.pack(padx=5, pady=5, fill=tk.X)

        # Tree + vertical scrollbar container
        tree_container = ttk.Frame(sidebar)
        tree_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        vsb = ttk.Scrollbar(tree_container, orient="vertical")
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree = ttk.Treeview(tree_container, show="tree", yscrollcommand=vsb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.configure(command=self.tree.yview)

        item_ids = self._service.list_items(limit=None)

        # Populate tree with items
        for item_info in item_ids:
            parent_iid = f"item-{item_info['id']}"
            # Parent item node (collapsed by default)
            try:
                self.tree.insert("", tk.END, iid=parent_iid, text=f"({item_info['id']}) {item_info['name']}", open=False)
            except tk.TclError as e:
                # Case to handle 16995 being duplicated in the DB (might need to handle better)
                print(f"WARNING: duplicate item ID {item_info['id']}")
                parent_iid = f"item(1)-{item_info['id']}"
                self.tree.insert("", tk.END, iid=parent_iid, text=f"({item_info['id']}) {item_info['name']}", open=False)

            # Add dummy child to make expandable
            self.tree.insert(parent_iid, tk.END, iid=f"{parent_iid}:dummy", text="(loading...)")

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
