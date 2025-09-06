from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from pathlib import Path

from Service.services import ItemService, NPCService
from dataclasses import fields, is_dataclass
from typing import Any

# Import Item for type hinting
from Service.services import Item

class BaseObjectEntityTab(ttk.Frame):
    """Base class for a tab object entries in the notebook."""

    def __init__(self, master: tk.Misc):
        super().__init__(master)

        self.object_type = None

    # --- abstract methods to be implemented by subclasses ---
    # def _build_form_for(self, component_kind: str) -> None:
    #     raise NotImplementedError()
    def _on_save(self) -> None:
        raise NotImplementedError()

    # ------------------------------------------------------------------
    def _build_form_for(self, component_type: str, grandchild_iid: str = None) -> None:
        """Build a form for the given component type of the currently loaded object.
            Responsible for the right-hand detail area where fields are shown and edited."""

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

        # Store entry widgets for saving
        self._entry_widgets: list[tuple[str, tk.Variable, Any]] = []

        # Build a scrollable canvas for many fields
        canvas = tk.Canvas(self.form_container, highlightthickness=0)
        scroll_y = ttk.Scrollbar(self.form_container, orient='vertical', command=canvas.yview)
        inner = ttk.Frame(canvas)
        inner.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=inner, anchor='nw')
        canvas.configure(yscrollcommand=scroll_y.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        # Build form fields
        for row, f in enumerate(fields(target_obj)):
            if f.name in exclude:
                continue
            ttk.Label(inner, text=f.name).grid(row=row, column=0, sticky=tk.W, padx=2, pady=2)
            value = getattr(target_obj, f.name)
            var: tk.Variable
            if isinstance(value, bool):
                var = tk.BooleanVar(value=value)
                cb = ttk.Checkbutton(inner, variable=var)
                cb.grid(row=row, column=1, sticky=tk.W, padx=2, pady=2)
            else:
                # Represent enums by their name; fall back to str
                if hasattr(value, 'name') and hasattr(value, 'value'):
                    display = value.name
                elif value is None:
                    display = ''
                else:
                    display = str(value)
                var = tk.StringVar(value=display)
                entry = ttk.Entry(inner, textvariable=var, width=30)
                entry.grid(row=row, column=1, sticky=tk.W, padx=2, pady=2)
            self._entry_widgets.append((f.name, var, f.type))

        self.save_button.configure(state=tk.NORMAL)

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

        # Save current component type then build form
        self.current_component_type = component_type
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
    def __load_relevant_object(self, parent_iid: str, obj_id: int) -> Item: #TODO: add NPC type hint when implemented
        """Load the relevant object (Item or NPC) based on the parent iid prefix and object ID."""
        if parent_iid.startswith("item-"):
            return self._service.get_item(obj_id)
        elif parent_iid.startswith("npc-"):
            # Placeholder for future NPC support
            return self._service.get_npc(obj_id) # TODO
        else:
            return None


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

        self.form_container = ttk.Frame(self.detail)
        self.form_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Save button at bottom
        self.save_button = ttk.Button(self.detail, text="Save", command=self._on_save, state=tk.DISABLED)
        self.save_button.pack(padx=10, pady=10, anchor=tk.SE)

        self.current_object = None  # type: Any
        self.current_component_type: str | None = None

        # Add panes after they are populated so initial sizes take effect
        # Give sidebar a smaller weight so detail area expands more.
        paned.add(sidebar, weight=1)
        paned.add(self.detail, weight=4)

    # ------------------------------------------------------------------
    def _on_save(self) -> None:
        """Callback when the Save button is clicked. Persists changes to the currently loaded object."""
        item = self.current_object
        if not item or not self.current_component_type:
            return
        if self.current_component_type == 'object':
            target_obj = item
        else:
            target_obj = item.components.get(self.current_component_type)
            if target_obj is None:
                self._show_message('Nothing to save')
                return

        # Apply values
        for name, var, typ in self._entry_widgets:
            raw = var.get()
            if isinstance(var, tk.BooleanVar):
                setattr(target_obj, name, bool(raw))
                continue
            if raw == '':
                value = None
            else:
                # Basic type inference
                try:
                    if typ in (int, 'int') or (hasattr(typ, '__origin__') and typ.__origin__ is int):
                        value = int(raw)
                    elif typ in (float, 'float'):
                        value = float(raw)
                    else:
                        value = raw
                except Exception:
                    value = raw
            setattr(target_obj, name, value)

        # Mark dirty and persist
        try:
            target_obj.dirty = True  # type: ignore[attr-defined]
        except Exception:
            pass
        try:
            self._service.save_item(item)
            self._show_message('Saved successfully')
        except Exception as exc:  # pragma: no cover
            self._show_message(f'Error saving: {exc}')



class Application:
    """Main Tkinter application window."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.root = tk.Tk()
        self.root.title("LU SQLite Tool")

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
