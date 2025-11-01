from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from enum import Enum, IntEnum, StrEnum
from pathlib import Path

from Service.services import ItemService, NPCService
from metadata import component_field_metadata
from dataclasses import fields, is_dataclass
from typing import Any
from Domain.domains import ColorType  # Color enum used for item color field and swatch

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

    # ------------------------------------------------------------------
    # Context menu (right-click) core – delegated to subclasses via hooks
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
            declared_type = f.type
            py_type = field_meta.get("type", declared_type)
            if isinstance(declared_type, type) and issubclass(declared_type, Enum):
                py_type = declared_type
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
                combo = ttk.Combobox(inner, state='readonly', values=options, textvariable=var, width=28)
                if readonly:
                    combo.configure(state='disabled')
                combo.grid(row=row, column=1, sticky=tk.W, padx=2, pady=2)
                widget_for_tooltip = combo

                # Prevent accidental value changes by mouse wheel when hovering the dropdown.
                # Instead, route the wheel to scroll the form's canvas for a better UX.
                try:
                    self._attach_combobox_wheel_passthrough(combo, canvas)
                except Exception:
                    pass

                # If this is the ColorType enum, show a live color swatch and hex value next to the dropdown
                if enum_type is ColorType:
                    # Build swatch UI elements and wire them to follow dropdown selection
                    swatch, hex_label = self._create_color_swatch(inner, row)
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
                    if isinstance(typ, type) and issubclass(typ, Enum):
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
                    elif typ in (int, 'int') or (hasattr(typ, '__origin__') and getattr(typ, '__origin__', None) is int):
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

            # Also persist any queued root deletions
            try:
                self._persist_root_deletions()
            except Exception as exc:
                try:
                    messagebox.showerror("Delete failed", f"Could not delete some items: {exc}")
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

    def _on_save_all(self) -> None:
        """Save current form AND all other dirty cached objects/components.

        This keeps the existing behavior of _on_save(persist=True) for the
        currently open object (including UI label updates), then persists any
        remaining dirty objects in the cache and queued deletions. Ensures the
        unsaved indicator is cleared if everything is saved successfully.
        """
        # First, save the currently focused form (handles UI updates like renames)
        try:
            self._on_save(persist=True)
        except Exception:
            # _on_save already surfaces its own errors to the UI; continue to try saving the rest
            pass

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
    # Undo button state helper
    # ------------------------------------------------------------------
    def _update_undo_button_state(self) -> None:
        """Enable the Undo button only when there are local deletions to undo.

        This looks for any of the local delete buffers/sets that we maintain:
        - _deleted_root_ids (set)
        - _deleted_components (list)
        - _deleted_skill_rows (list)
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
                    # Service is provided by subclasses (e.g., ItemsTab)
                    self._service.save_item(obj)
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
                # Use service layer to delete fully (components + object + registry)
                self._service.delete_item(int(oid))
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
                if ctype == 'ItemComponent' and cid is not None:
                    self._service.delete_item_component(int(cid))
                elif ctype == 'RenderComponent' and cid is not None:
                    self._service.delete_render_component(int(cid))
                elif ctype == 'ObjectSkill' and oid is not None:
                    self._service.delete_skill_component(int(oid))
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
        self.items_tab = ItemsTab(notebook, self.item_service)
        notebook.add(self.items_tab, text="Items")

        # NPC tab placeholder ------------------------------------------
        npc_tab = ttk.Frame(notebook)
        ttk.Label(npc_tab, text="NPC tools coming soon").pack(padx=10, pady=10)
        notebook.add(npc_tab, text="NPCs")

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
            for tab in [getattr(self, 'items_tab', None)]:
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
                    messagebox.showerror("Save failed", f"Could not save all changes:\n{exc}")
                    return
                self.root.destroy()
                return
            # False -> Discard and exit
            self.root.destroy()
        except Exception:
            # If anything unexpected, fall back to normal close
            self.root.destroy()

    # ------------------------------------------------------------------
    def run(self) -> None:  # pragma: no cover - visual loop
        self.root.mainloop()
