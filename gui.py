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
        # Left sidebar --------------------------------------------------
        sidebar = ttk.Frame(self, width=200)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)

        create_btn = ttk.Button(sidebar, text="Create")
        create_btn.pack(padx=5, pady=5, fill=tk.X)

        self.tree = ttk.Treeview(sidebar, show="tree")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Example items – in a real app these would come from the service
        for obj_id in (20007, 2631):
            self.tree.insert("", tk.END, iid=str(obj_id), text=f"Item {obj_id}")

        self.tree.bind("<<TreeviewSelect>>", self._on_item_selected)

        # Right content area --------------------------------------------
        self.detail = ttk.Frame(self)
        self.detail.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.detail_label = ttk.Label(self.detail, text="Select an item to view details")
        self.detail_label.pack(padx=10, pady=10, anchor=tk.NW)

    # ------------------------------------------------------------------
    def _on_item_selected(self, event: tk.Event) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        obj_id = int(sel[0])
        try:
            item = self._service.get_item(obj_id)
            self.detail_label.configure(text=f"ID: {item.object_id}\nName: {item.name}")
        except Exception as exc:  # pragma: no cover - visual feedback only
            self.detail_label.configure(text=str(exc))


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