"""Per-method tests for ItemRepository.

Methods covered:
- get
- save (insert)
- save (update)

Uses candidate ID list for existing fetch tests and temp DB copies for mutations.
"""
from __future__ import annotations
import sqlite3
import pytest
from Repository.item import ItemRepository
from Domain.domains import Item, ObjectTypes, ItemComponent, Components

EXISTING_ITEM_IDS = [20007]
NEW_ID_BASE = 1_820_000_000

# Helpers removed – tests now use EXISTING_ITEM_IDS directly.

# ---------------- Tests ----------------

def test_get_item(ro_conn, baseline_path):
    repo = ItemRepository(baseline_path)
    obj_id = EXISTING_ITEM_IDS[0]
    row = ro_conn.execute("SELECT * FROM Objects WHERE id=?", (obj_id,)).fetchone()
    if row is None:
        pytest.skip("Configured EXISTING_ITEM_IDS[0] not present in baseline DB")
    item = repo.get(obj_id)
    assert item.object_id == row['id']
    assert item.name == row['name']
    assert item.placeable == row['placeable']
    assert item.type == row['type']
    assert item.description == row['description']


def test_save_insert_item(temp_db_path):
    repo = ItemRepository(temp_db_path)
    new_id = NEW_ID_BASE
    itm = Item(id=new_id, placeable=False, type=ObjectTypes.ITEM, name='ItemInsert')
    itm.description = 'Insert version'; itm.dirty = True
    comp = ItemComponent(id=new_id); comp.dirty = True
    itm.components['ItemComponent'] = comp
    repo.save(itm)
    with sqlite3.connect(temp_db_path) as c:
        c.row_factory = sqlite3.Row
        row = c.execute("SELECT * FROM Objects WHERE id=?", (new_id,)).fetchone()
        assert row['name'] == 'ItemInsert'
        ic_row = c.execute("SELECT * FROM ItemComponent WHERE id=?", (new_id,)).fetchone()
        assert ic_row is not None
        reg = c.execute("SELECT component_type FROM ComponentsRegistry WHERE id=?", (new_id,)).fetchall()
        assert any(r[0] == Components.ITEM for r in reg)


def test_save_update_item(temp_db_path):
    repo = ItemRepository(temp_db_path)
    new_id = NEW_ID_BASE + 1
    itm = Item(id=new_id, placeable=False, type=ObjectTypes.ITEM, name='ItemUpd')
    itm.description = 'v1'; itm.dirty = True
    repo.save(itm)
    # Update
    itm.name = 'ItemUpd2'; itm.description = 'v2'; itm.dirty = True
    repo.save(itm)
    with sqlite3.connect(temp_db_path) as c:
        c.row_factory = sqlite3.Row
        row = c.execute("SELECT * FROM Objects WHERE id=?", (new_id,)).fetchone()
        assert row['name'] == 'ItemUpd2'
        assert row['description'] == 'v2'
