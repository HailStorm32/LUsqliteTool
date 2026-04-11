from __future__ import annotations

import pytest

from Domain.domains import Components, RowCollection
from Repository.npc import NPCRepository
from Service.services import NPCService
from Tests.helpers import connect_db, count_rows, fetch_component_types


def test_list_npcs_matches_direct_query(baseline_conn, baseline_path):
    """Verify NPCRepository.list_npcs matches the direct Objects table query.

    Args:
        baseline_conn: Connection to the baseline database used for validation.
        baseline_path: Path to the baseline database used by the repository.

    Returns:
        None: Assertions validate repository behavior.
    """
    repo = NPCRepository(str(baseline_path))

    expected = [
        {"id": int(row["id"]), "name": row["name"]}
        for row in baseline_conn.execute(
            """
            SELECT id, name
            FROM Objects
            WHERE type IN (?, ?)
            ORDER BY id
            """,
            ("UserGeneratedNPCs", "NPC"),
        ).fetchall()
    ]

    assert repo.list_npcs() == expected


def test_get_returns_existing_vendor_npc_with_vendor_state(baseline_conn, baseline_path, vendor_npc_id):
    """Verify NPCRepository.get loads a real vendor NPC and its vendor-linked collections.

    Args:
        baseline_conn: Connection to the baseline database used for validation.
        baseline_path: Path to the baseline database used by the repository.
        vendor_npc_id: Baseline NPC id that has a vendor component.

    Returns:
        None: Assertions validate repository behavior.
    """
    repo = NPCRepository(str(baseline_path))

    npc = repo.get(vendor_npc_id)
    row = baseline_conn.execute(
        "SELECT * FROM Objects WHERE id = ?",
        (vendor_npc_id,),
    ).fetchone()

    assert npc.object_id == int(row["id"])
    assert npc.name == row["name"]
    assert npc.description == row["description"]
    assert "VendorComponent" in npc.components

    vendor_loot_matrix = npc.components.get("VendorLootMatrix")
    vendor_loot_table = npc.components.get("VendorLootTable")
    assert isinstance(vendor_loot_matrix, RowCollection)
    assert isinstance(vendor_loot_table, RowCollection)


def test_create_default_vendor_npc_persists_required_components_and_loot_rows(temp_db_path):
    """Verify vendor NPC creation persists its component set and the initial loot records.

    Args:
        temp_db_path: Writable copy of the baseline database for the test.

    Returns:
        None: Assertions validate service behavior.
    """
    service = NPCService(str(temp_db_path))

    npc = service.create_default_vendor_npc()
    vendor = npc.components["VendorComponent"]
    vendor_matrix = npc.components["VendorLootMatrix"]
    vendor_table_indices = npc.components["VendorLootTableIndex"]
    vendor_table = npc.components["VendorLootTable"]

    assert vendor.loot_matrix_index > 0
    assert len(vendor_matrix.rows) == 1
    assert len(vendor_table_indices.rows) == 1
    assert len(vendor_table.rows) == 1

    # Validate both the component registry and the linked loot tables created by the service.
    conn = connect_db(temp_db_path)
    try:
        assert fetch_component_types(conn, npc.object_id) == {
            Components.RENDER,
            Components.SIMPLE_PHYSICS,
            Components.DESTROYABLE,
            Components.VENDOR,
            Components.INVENTORY,
            Components.MINIFIG,
        }
        assert count_rows(conn, "LootMatrix", "LootMatrixIndex = ?", (vendor.loot_matrix_index,)) == 1
        assert count_rows(conn, "LootMatrixIndex", "LootMatrixIndex = ?", (vendor.loot_matrix_index,)) == 1
        linked_loot_table_index = vendor_matrix.rows[0].loot_table_index
        assert count_rows(conn, "LootTable", "LootTableIndex = ?", (linked_loot_table_index,)) == 1
        assert count_rows(conn, "LootTableIndex", "LootTableIndex = ?", (linked_loot_table_index,)) == 1
    finally:
        conn.close()


def test_create_default_mission_npc_persists_bundle_and_added_rows(temp_db_path):
    """Verify mission NPC creation persists the mission bundle plus newly added task/email rows.

    Args:
        temp_db_path: Writable copy of the baseline database for the test.

    Returns:
        None: Assertions validate service behavior.
    """
    service = NPCService(str(temp_db_path))

    npc = service.create_default_mission_npc()
    task = service.add_task_row(npc)
    email = service.add_email_row(npc)
    service.save_npc(npc)

    reloaded = service.get_npc(npc.object_id)
    mission_component = reloaded.components["MissionNPCComponent"]
    missions = reloaded.components["Missions"]
    mission_text = reloaded.components["MissionText"]
    mission_tasks = reloaded.components["MissionTasks"]
    mission_email = reloaded.components["MissionEmail"]

    assert len(mission_component.rows) == 1
    assert len(missions.rows) == 1
    assert len(mission_text.rows) == 1
    assert len(mission_tasks.rows) == 1
    assert len(mission_email.rows) == 1

    mission_id = mission_component.rows[0].mission_id
    assert mission_tasks.rows[0].id == mission_id
    assert mission_email.rows[0].mission_id == mission_id
    assert task.uid == mission_tasks.rows[0].uid
    assert email.id == mission_email.rows[0].id


def test_vendor_loot_table_add_reuses_existing_matrix_bucket(temp_db_path):
    """Verify adding vendor loot-table rows reuses the existing loot-matrix bucket.

    Args:
        temp_db_path: Writable copy of the baseline database for the test.

    Returns:
        None: Assertions validate service behavior.
    """
    service = NPCService(str(temp_db_path))

    npc = service.create_default_vendor_npc()
    service.add_loot_table_row(npc, "vendor")
    service.save_npc(npc)

    reloaded = service.get_npc(npc.object_id)
    vendor = reloaded.components["VendorComponent"]
    matrix_rows = reloaded.components["VendorLootMatrix"].rows
    table_rows = reloaded.components["VendorLootTable"].rows

    assert len(matrix_rows) == 1
    assert len(table_rows) == 2
    assert matrix_rows[0].loot_matrix_index == vendor.loot_matrix_index
    assert {row.loot_table_index for row in table_rows} == {matrix_rows[0].loot_table_index}


def test_save_npc_rejects_task_not_owned_by_npc(temp_db_path):
    """Verify NPC save validation rejects mission-task rows linked to foreign mission ids.

    Args:
        temp_db_path: Writable copy of the baseline database for the test.

    Returns:
        None: Assertions validate service validation behavior.
    """
    service = NPCService(str(temp_db_path))

    npc = service.create_default_mission_npc()
    invalid_task = service.add_task_row(npc)
    # MissionTaskRow.id is the owning mission id; bump it to break the link intentionally.
    invalid_task.id += 999999

    with pytest.raises(ValueError, match="MissionTasks"):
        service.save_npc(npc)


def test_duplicate_npc_retargets_mission_bundle_and_component_ids(temp_db_path):
    """Verify NPC duplication allocates fresh ids and retargets mission-owned rows.

    Args:
        temp_db_path: Writable copy of the baseline database for the test.

    Returns:
        None: Assertions validate service behavior.
    """
    service = NPCService(str(temp_db_path))

    source = service.create_default_mission_npc()
    service.add_task_row(source)
    service.add_email_row(source)
    service.save_npc(source)

    duplicated = service.duplicate_npc(source.object_id)

    source_mission_ids = {
        row.mission_id for row in source.components["MissionNPCComponent"].rows
    }
    duplicated_mission_ids = {
        row.mission_id for row in duplicated.components["MissionNPCComponent"].rows
    }

    assert duplicated.object_id != source.object_id
    assert duplicated.components["RenderComponent"].id != source.components["RenderComponent"].id
    assert duplicated.components["MinifigComponent"].id != source.components["MinifigComponent"].id
    assert duplicated_mission_ids
    assert duplicated_mission_ids.isdisjoint(source_mission_ids)
    assert {row.id for row in duplicated.components["MissionTasks"].rows} == duplicated_mission_ids
    assert {row.mission_id for row in duplicated.components["MissionEmail"].rows} == duplicated_mission_ids
    assert {row.offer_object_id for row in duplicated.components["Missions"].rows} == {duplicated.object_id}
    assert {row.target_object_id for row in duplicated.components["Missions"].rows} == {duplicated.object_id}


def test_delete_component_removes_vendor_and_linked_rows(temp_db_path):
    """Verify deleting a vendor component also deletes its linked loot records and registry row.

    Args:
        temp_db_path: Writable copy of the baseline database for the test.

    Returns:
        None: Assertions validate repository cleanup behavior through the service API.
    """
    service = NPCService(str(temp_db_path))

    npc = service.create_default_vendor_npc()
    vendor = npc.components["VendorComponent"]
    loot_matrix_index = vendor.loot_matrix_index
    loot_table_indices = {
        row.loot_table_index for row in npc.components["VendorLootTable"].rows
    }

    # Delete through the public service API so the repository cleanup path is exercised.
    service.delete_component("VendorComponent", component_id=vendor.id, object_id=npc.object_id)

    conn = connect_db(temp_db_path)
    try:
        assert count_rows(conn, "VendorComponent", "id = ?", (vendor.id,)) == 0
        assert count_rows(
            conn,
            "ComponentsRegistry",
            "id = ? AND component_type = ?",
            (npc.object_id, Components.VENDOR),
        ) == 0
        assert count_rows(conn, "LootMatrix", "LootMatrixIndex = ?", (loot_matrix_index,)) == 0
        assert count_rows(conn, "LootMatrixIndex", "LootMatrixIndex = ?", (loot_matrix_index,)) == 0
        for loot_table_index in loot_table_indices:
            assert count_rows(conn, "LootTable", "LootTableIndex = ?", (loot_table_index,)) == 0
            assert count_rows(conn, "LootTableIndex", "LootTableIndex = ?", (loot_table_index,)) == 0
    finally:
        conn.close()
