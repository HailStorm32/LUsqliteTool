import sqlite3
from Domain.domains import *
from Repository.base import *
from Repository.exceptions import NotFoundError, DataIntegrityError, SaveError

class ItemRepository(baseRepository):
    """Repository for managing items in the database."""

    def __init__(self, db_path: str):
        super().__init__(db_path)


    def list_item_ids(self, limit: int | None = None) -> list[int]:
        """Return a list of item IDs from the database, optionally limited in number."""
        conn = self._connect_to_db()
        try:
            query = "SELECT id FROM Objects WHERE type=?"
            params = (ObjectTypes.ITEM.value,)
            if limit is not None:
                query += " LIMIT ?"
                params += (limit,)
            rows = conn.execute(query, params).fetchall()
            return [row['id'] for row in rows]
        finally:
            conn.close()

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
                raise NotFoundError(f"Item {object_id} not found", table="Objects", column="id", value=object_id)

            # Create an Item object with the base data
            item = Item(id=base['id'], name=base['name'], placeable=base['placeable'], type=base['type'])

            # Load components for the item
            item.components = self._load_components(object_id)

            # Load the Object table data into the Item object
            self._load_object_table(item)

            return item

        except:
            if conn:
                conn.close()
            raise

        finally:
            conn.close()

    ##########################
    #-------- SAVE -----------
    ##########################
    def save(self, item: Item) -> None:
        """Save the item to the database."""
        conn = self._connect_to_db()

        try:
            conn.execute("BEGIN")

            # Save object table if dirty
            if item.dirty:
                self._save_object_table(conn, item)
                item.dirty = False

            # Save components (dirty check is handled in base class)
            self._save_components(conn, item.object_id, item.components)

            conn.commit()  # Commit the transaction

        except Exception:
            conn.rollback()
            raise

        finally:
            conn.close()




    # def close(self):
    #     pass
