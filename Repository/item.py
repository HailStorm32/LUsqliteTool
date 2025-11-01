import sqlite3
from Domain.domains import *
from Repository.base import *
from Repository.exceptions import NotFoundError, DataIntegrityError, SaveError

class ItemRepository(baseRepository):
    """Repository for managing items in the database."""

    def __init__(self, db_path: str):
        super().__init__(db_path)

    # generate_new_id is implemented in baseRepository; inherit for reuse.

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
        # Delegate to base for shared behavior (keeps this small and consistent)
        return self.list_objects_by_type(ObjectTypes.ITEM.value, limit)

    # Delete operations are provided by baseRepository:
    # - delete(object_id)
    # - delete_item_component(component_id)
    # - delete_render_component(component_id)
    # - delete_skill_component(object_id)
    # No need to redefine passthroughs here; rely on inherited methods.

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

        except Exception:
            # Log repository failure with traceback for diagnostics, then re-raise
            logging.getLogger(__name__).exception("ItemRepository.get(%s) failed", object_id)
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
            logging.getLogger(__name__).exception("ItemRepository.save(%s) failed; rolling back", getattr(item, 'object_id', '?'))
            conn.rollback()
            raise

        finally:
            conn.close()




    # def close(self):
    #     pass
