import sqlite3
from Domain.domains import *
from Repository.base import *

class ItemRepository(baseRepository):
    """Repository for managing items in the database."""

    def __init__(self, db_path: str):
        super().__init__(db_path)

    ##########################
    #-------- LOAD -----------
    ##########################
    def get(self, object_id: int) -> Item:
        try:
            conn = self._connect_to_db()

            # Fetch the required columns from the Objects table to create an Item object
            base = conn.execute(
                    "SELECT id, name, placeable, type FROM Objects WHERE id=?",
                    (object_id,)
                ).fetchone()
            if not base:
                raise KeyError(f"Item {object_id} not found")

            # Create an Item object with the base data
            item = Item(id=base['id'], name=base['name'], placeable=base['placeable'], type=base['type'])

            # Load components for the item
            item.components = self._load_components(object_id)

            # Load the Object table data into the Item object
            self._load_object_table(item)

            return item

        finally:
            conn.close()

    ##########################
    #-------- SAVE -----------
    ##########################
    # def save(self, item: Item) -> None:
    #     """Save the item to the database."""
    #     conn = self._conn()

    #     try:
    #         conn.execute("BEGIN")




    # def close(self):
    #     pass
