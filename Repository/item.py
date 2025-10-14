import sqlite3
from Domain.domains import *
from Repository.base import *
from Repository.exceptions import NotFoundError, DataIntegrityError, SaveError

class ItemRepository(baseRepository):
    """Repository for managing items in the database."""

    def __init__(self, db_path: str):
        super().__init__(db_path)

    def generate_new_id(self) -> int:
        """Generate a new unique object id.

        Strategy: use MAX(id)+1 from Objects table. This keeps ids monotonic and
        avoids collisions without guessing. Guards against 32-bit overflow.
        """
        conn = self._connect_to_db()
        try:
            row = conn.execute("SELECT MAX(id) AS max_id FROM Objects").fetchone()
            max_id = row[0] if row is not None else None
            new_id = (int(max_id) + 1) if max_id is not None else 1
            # Basic overflow guard for 32-bit signed range
            if new_id > 2_147_483_647:
                raise SaveError("Exhausted id space; cannot create new object id.")
            return new_id
        finally:
            conn.close()

    def list_items(self, limit: int | None = None) -> list[dict[str, int | str]]:
        """
        Return a list of item IDs from the database, optionally limited in number.

        Ex:
        [
            {'id': 20007, 'name': 'Health Potion'},
            {'id': 20008, 'name': 'Mana Potion'},
            ...
        ]

        """
        conn = self._connect_to_db()
        try:
            query = "SELECT id,name FROM Objects WHERE type=?"
            params = (ObjectTypes.ITEM.value,)
            if limit is not None:
                query += " LIMIT ?"
                params += (limit,)
            rows = conn.execute(query, params).fetchall()
            return [{'id':row['id'], 'name':row['name']} for row in rows]
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
                    "SELECT id, name, type FROM Objects WHERE id=?",
                    (object_id,)
                ).fetchone()
            if not base:
                raise NotFoundError(f"Item {object_id} not found", table="Objects", column="id", value=object_id)

            # Create an Item object with the base data
            item = Item(id=base['id'], name=base['name'], type=base['type'])

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
