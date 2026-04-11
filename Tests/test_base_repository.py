from __future__ import annotations

import pytest

from Domain.domains import (
    Components,
    Item,
    ItemComponent,
    ObjectSkillRow,
    ObjectSkills,
    ObjectTypes,
    RenderComponent,
)
from Repository.base import baseRepository
from Repository.item import ItemRepository
from Tests.helpers import connect_db, count_rows


def _build_saved_item(repo: ItemRepository, object_id: int) -> Item:
    """Create and persist an item that exercises object, component, and skill saves.

    Args:
        repo: Repository used to assign component ids and persist the item.
        object_id: Object id to use for the new item row.

    Returns:
        Item: Freshly reloaded item after it has been saved to the database.
    """
    # Assign explicit component ids so the registry, component tables, and skill
    # rows are all populated before delete-path assertions run.
    item_component_id = repo.generate_new_component_id(object_id, "ItemComponent")
    render_component_id = repo.generate_new_component_id(object_id, "RenderComponent")

    item = Item(id=object_id, type=ObjectTypes.ITEM, name=f"Test Item {object_id}")
    item.description = "Created by the rewritten test suite."
    item.dirty = True
    item.components["ItemComponent"] = ItemComponent(
        id=item_component_id,
        base_value=4321,
        rarity=7,
        dirty=True,
    )
    item.components["RenderComponent"] = RenderComponent(
        id=render_component_id,
        icon_asset="textures/ui/test_icon.dds",
        dirty=True,
    )
    item.components["ObjectSkill"] = ObjectSkills(
        skills=[
            ObjectSkillRow(
                object_Template=object_id,
                skill_id=61001,
                cast_on_type=1,
                ai_combat_weight=10,
            )
        ],
        dirty=True,
    )
    repo.save(item)
    return repo.get(object_id)


def test_generate_new_id_returns_next_available_object_id(temp_db_path):
    """Verify object id generation returns the next id after the current maximum.

    Args:
        temp_db_path: Writable copy of the baseline database for the test.

    Returns:
        None: Assertions validate repository behavior.
    """
    repo = baseRepository(str(temp_db_path))
    conn = connect_db(temp_db_path)
    try:
        row = conn.execute("SELECT MAX(id) AS max_id FROM Objects").fetchone()
    finally:
        conn.close()

    assert repo.generate_new_id() == int(row["max_id"]) + 1


def test_generate_new_component_id_prefers_requested_id_when_available(temp_db_path):
    """Verify component id generation reuses the preferred id when it is free.

    Args:
        temp_db_path: Writable copy of the baseline database for the test.

    Returns:
        None: Assertions validate repository behavior.
    """
    repo = baseRepository(str(temp_db_path))
    conn = connect_db(temp_db_path)
    try:
        free_id = int(conn.execute("SELECT MAX(id) AS max_id FROM ItemComponent").fetchone()["max_id"]) + 5000
    finally:
        conn.close()

    assert repo.generate_new_component_id(free_id, "ItemComponent") == free_id


def test_generate_new_component_id_skips_existing_ids(baseline_conn, baseline_path):
    """Verify component id generation skips forward when the preferred id is already taken.

    Args:
        baseline_conn: Connection to the baseline database used for validation.
        baseline_path: Path to the baseline database used by the repository.

    Returns:
        None: Assertions validate repository behavior.
    """
    repo = baseRepository(str(baseline_path))
    existing_id = int(
        baseline_conn.execute("SELECT id FROM ItemComponent ORDER BY id LIMIT 1").fetchone()["id"]
    )

    generated_id = repo.generate_new_component_id(existing_id, "ItemComponent")

    assert generated_id > existing_id
    assert baseline_conn.execute(
        "SELECT 1 FROM ItemComponent WHERE id = ?",
        (generated_id,),
    ).fetchone() is None


def test_list_objects_by_type_matches_objects_table(baseline_conn, baseline_path):
    """Verify list_objects_by_type mirrors the direct Objects table query.

    Args:
        baseline_conn: Connection to the baseline database used for validation.
        baseline_path: Path to the baseline database used by the repository.

    Returns:
        None: Assertions validate repository behavior.
    """
    repo = baseRepository(str(baseline_path))

    expected = {
        (int(row["id"]), row["name"])
        for row in baseline_conn.execute(
            "SELECT id, name FROM Objects WHERE type = ?",
            (ObjectTypes.ITEM.value,),
        ).fetchall()
    }

    assert {
        (int(row["id"]), row["name"])
        for row in repo.list_objects_by_type(ObjectTypes.ITEM.value)
    } == expected


def test_get_lookup_options_brick_colors_include_preview_fields(baseline_path):
    """Verify brick color lookups expose display and preview metadata for the UI.

    Args:
        baseline_path: Path to the baseline database used by the repository.

    Returns:
        None: Assertions validate repository behavior.
    """
    repo = baseRepository(str(baseline_path))

    options = repo.get_lookup_options("brick_colors")

    assert options
    first = options[0]
    assert {"id", "label", "detail", "preview_hex", "preview_text"} <= set(first)
    assert first["preview_hex"].startswith("#")
    assert first["detail"]


def test_get_lookup_options_rejects_invalid_identifiers(baseline_path):
    """Verify lookup specs reject unsafe SQL identifiers before querying the database.

    Args:
        baseline_path: Path to the baseline database used by the repository.

    Returns:
        None: Assertions validate repository behavior.
    """
    repo = baseRepository(str(baseline_path))

    invalid_spec = {
        "table": "Objects; DROP TABLE Objects",
        "column": "id",
    }

    with pytest.raises(ValueError):
        repo.get_lookup_options(invalid_spec)


def test_load_components_backfills_missing_skill_registry_entry(temp_db_path):
    """Verify loading components repairs missing skill registry metadata when skill rows exist.

    Args:
        temp_db_path: Writable copy of the baseline database for the test.

    Returns:
        None: Assertions validate repository behavior.
    """
    repo = baseRepository(str(temp_db_path))
    new_id = repo.generate_new_id()
    item = Item(id=new_id, type=ObjectTypes.ITEM, name="Skill-only object")
    item.description = "Used to verify skill-registry backfill."
    item.dirty = True

    # Simulate the data-integrity case the loader is designed to repair:
    # skill rows exist, but the ComponentsRegistry row is missing.
    conn = repo._connect_to_db()
    try:
        conn.execute("BEGIN")
        repo._save_object_table(conn, item)
        conn.execute(
            """
            INSERT INTO ObjectSkills (objectTemplate, skillID, castOnType, AICombatWeight)
            VALUES (?, ?, ?, ?)
            """,
            (new_id, 71111, 2, 25),
        )
        conn.commit()
    finally:
        conn.close()

    loaded_components = repo._load_components(new_id)

    assert "ObjectSkill" in loaded_components
    assert len(loaded_components["ObjectSkill"].skills) == 1

    conn = connect_db(temp_db_path)
    try:
        row = conn.execute(
            """
            SELECT component_id
            FROM ComponentsRegistry
            WHERE id = ? AND component_type = ?
            """,
            (new_id, Components.SKILL),
        ).fetchone()
    finally:
        conn.close()

    assert row is not None
    assert int(row["component_id"]) == 0


def test_delete_object_removes_components_registry_and_skill_rows(temp_db_path):
    """Verify full object deletion removes all linked component and skill data.

    Args:
        temp_db_path: Writable copy of the baseline database for the test.

    Returns:
        None: Assertions validate repository behavior.
    """
    repo = ItemRepository(str(temp_db_path))
    object_id = repo.generate_new_id()
    saved_item = _build_saved_item(repo, object_id)

    item_component_id = saved_item.components["ItemComponent"].id
    render_component_id = saved_item.components["RenderComponent"].id

    baseRepository(str(temp_db_path)).delete_object(object_id)

    conn = connect_db(temp_db_path)
    try:
        assert count_rows(conn, "Objects", "id = ?", (object_id,)) == 0
        assert count_rows(conn, "ItemComponent", "id = ?", (item_component_id,)) == 0
        assert count_rows(conn, "RenderComponent", "id = ?", (render_component_id,)) == 0
        assert count_rows(conn, "ObjectSkills", "objectTemplate = ?", (object_id,)) == 0
        assert count_rows(conn, "ComponentsRegistry", "id = ?", (object_id,)) == 0
    finally:
        conn.close()


def test_id_exists_reports_presence_and_absence(temp_db_path):
    """Verify id_exists reports both existing and missing object ids correctly.

    Args:
        temp_db_path: Writable copy of the baseline database for the test.

    Returns:
        None: Assertions validate repository behavior.
    """
    repo = baseRepository(str(temp_db_path))
    conn = connect_db(temp_db_path)
    try:
        existing_id = int(conn.execute("SELECT id FROM Objects ORDER BY id LIMIT 1").fetchone()["id"])
    finally:
        conn.close()

    assert repo.id_exists("Objects", existing_id)
    assert not repo.id_exists("Objects", repo.generate_new_id() + 1000)
