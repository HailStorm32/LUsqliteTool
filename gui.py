from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from pathlib import Path

from Service.services import ItemService, NPCService


class ItemsTab(ttk.Frame):
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
        for object in item_ids:
            parent_iid = f"item-{object['id']}"
            # Parent item node (collapsed by default)
            try:
                self.tree.insert("", tk.END, iid=parent_iid, text=f"{object['name']} ({object['id']})", open=False)
            except tk.TclError as e:
                # Case to handle 16995 being duplicated in the DB (might need to handle better)
                print(f"WARNING: duplicate item ID {object['id']}")
                parent_iid = f"item(1)-{object['id']}"
                self.tree.insert("", tk.END, iid=parent_iid, text=f"{object['name']} ({object['id']})", open=False)

            # Add dummy child to make expandable
            self.tree.insert(parent_iid, tk.END, iid=f"{parent_iid}:dummy", text="(loading...)")

        self.tree.bind("<<TreeviewSelect>>", self._on_item_selected)
        self.tree.bind("<<TreeviewOpen>>", self._on_item_expanded)

        # Right content area --------------------------------------------
        self.detail = ttk.Frame(paned)
        self.detail_label = ttk.Label(self.detail, text="Select an item to view details")
        self.detail_label.pack(padx=10, pady=10, anchor=tk.NW)

        # Add panes after they are populated so initial sizes take effect
        # Give sidebar a smaller weight so detail area expands more.
        paned.add(sidebar, weight=1)
        paned.add(self.detail, weight=4)

    # ------------------------------------------------------------------
    def _on_item_selected(self, event: tk.Event) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        iid = sel[0]
        # Determine if a child component was selected; derive item iid
        if ":" in iid:
            item_part, _ = iid.split(":", 1)
        else:
            item_part = iid
        if not item_part.startswith("item-"):
            return  # Not an item-related node
        try:
            obj_id = int(item_part.split("-", 1)[1])
        except ValueError:
            return
        try:
            item = self._service.get_item(obj_id)
            self.detail_label.configure(text=f"ID: {item.object_id}\nName: {item.name}")
        except Exception as exc:  # pragma: no cover - visual feedback only
            self.detail_label.configure(text=str(exc))

    def _on_item_expanded(self, event: tk.Event) -> None:
        sel = self.tree.selection()

        parent_iid = sel[0]

        # If there is a dummy child, remove it
        if self.tree.exists(f"{parent_iid}:dummy"):
            self.tree.delete(f"{parent_iid}:dummy")

        # If there already are children, do not re-load
        if self.tree.get_children(parent_iid):
            #TODO: Might want to refresh instead of ignoring
            return

        #Parse the item ID from the iid
        object_id = int(parent_iid.split("-", 1)[1])

        # Fetch item details from the service
        item = self._service.get_item(object_id)
        if item is None:
            print(f"ERROR: could not load item {object_id} for expansion")
            return

        component_children = item.components

        # Child component nodes
        for key in component_children:
            child_iid = f"{parent_iid}:{key}"
            self.tree.insert(parent_iid, tk.END, iid=child_iid, text=key)

        # if not sel:
        #     return
        # iid = sel[0]
        # # Determine if a child component was selected; derive item iid
        # if ":" in iid:
        #     item_part, _ = iid.split(":", 1)
        # else:
        #     item_part = iid
        # if not item_part.startswith("item-"):
        #     return


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

        items_tab = ItemsTab(notebook, self.item_service)
        notebook.add(items_tab, text="Items")

        # NPC tab placeholder ------------------------------------------
        npc_tab = ttk.Frame(notebook)
        ttk.Label(npc_tab, text="NPC tools coming soon").pack(padx=10, pady=10)
        notebook.add(npc_tab, text="NPCs")

    # ------------------------------------------------------------------
    def run(self) -> None:  # pragma: no cover - visual loop
        self.root.mainloop()
