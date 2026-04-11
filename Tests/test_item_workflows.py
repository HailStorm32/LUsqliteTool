from __future__ import annotations

from Domain.domains import (
    INT_32_MAX,
    Components,
    Item,
    ItemComponent,
    ObjectSkillRow,
    ObjectSkills,
    ObjectTypes,
    RenderComponent,
)
from Repository.item import ItemRepository
from Service.services import ItemService
from Tests.helpers import connect_db, fetch_component_types


def _create_round_trip_item(repo: ItemRepository, object_id: int) -> Item:
    """Create and save a representative item with core components and one skill row.

    Args:
        repo: Repository used to assign component ids and persist the item.
        object_id: Object id to use for the new item row.

    Returns:
        Item: Freshly reloaded item after it has been saved.
    """
    item = Item(id=object_id, type=ObjectTypes.ITEM, name=f"Round Trip {object_id}")
    item.description = "Created for ItemRepository round-trip coverage."
    item.dirty = True
    item.components["ItemComponent"] = ItemComponent(
        id=repo.generate_new_component_id(object_id, "ItemComponent"),
        base_value=2500,
        rarity=6,
        dirty=True,
    )
    item.components["RenderComponent"] = RenderComponent(
        id=repo.generate_new_component_id(object_id, "RenderComponent"),
        render_asset="mesh/items/test_item.nif",
        icon_asset="textures/ui/items/test.dds",
        dirty=True,
    )
    item.components["ObjectSkill"] = ObjectSkills(
        skills=[
            ObjectSkillRow(
                object_Template=object_id,
                skill_id=88001,
                cast_on_type=3,
                ai_combat_weight=12,
            )
        ],
        dirty=True,
    )
    repo.save(item)
    return repo.get(object_id)


def test_get_returns_existing_item_with_components(baseline_conn, baseline_path, item_with_components_id):
    """Verify ItemRepository.get loads a real baseline item and its expected components.

    Args:
        baseline_conn: Connection to the baseline database used for validation.
        baseline_path: Path to the baseline database used by the repository.
        item_with_components_id: Baseline item id that has item and render components.

    Returns:
        None: Assertions validate repository behavior.
    """
    repo = ItemRepository(str(baseline_path))

    item = repo.get(item_with_components_id)
    row = baseline_conn.execute(
        "SELECT * FROM Objects WHERE id = ?",
        (item_with_components_id,),
    ).fetchone()

    assert item.object_id == int(row["id"])
    assert item.name == row["name"]
    assert item.description == row["description"]
    assert "ItemComponent" in item.components
    assert "RenderComponent" in item.components


def test_save_round_trip_persists_new_item_components_and_skills(temp_db_path):
    """Verify a newly created item round-trips through save and reload with all components intact.

    Args:
        temp_db_path: Writable copy of the baseline database for the test.

    Returns:
        None: Assertions validate repository and database behavior.
    """
    repo = ItemRepository(str(temp_db_path))
    object_id = repo.generate_new_id()

    saved_item = _create_round_trip_item(repo, object_id)

    assert saved_item.object_id == object_id
    assert saved_item.components["ItemComponent"].base_value == 2500
    assert saved_item.components["RenderComponent"].icon_asset == "textures/ui/items/test.dds"
    assert len(saved_item.components["ObjectSkill"].skills) == 1
    assert not saved_item.dirty
    assert not saved_item.components["ItemComponent"].dirty
    assert not saved_item.components["RenderComponent"].dirty
    assert not saved_item.components["ObjectSkill"].dirty

    # Confirm the database registry reflects the same component set seen in memory.
    conn = connect_db(temp_db_path)
    try:
        assert fetch_component_types(conn, object_id) == {
            Components.ITEM,
            Components.RENDER,
            Components.SKILL,
        }
    finally:
        conn.close()


def test_save_updates_existing_item_and_replaces_skill_rows(temp_db_path):
    """Verify saving an existing item updates scalar fields and replaces skill-row state.

    Args:
        temp_db_path: Writable copy of the baseline database for the test.

    Returns:
        None: Assertions validate repository behavior.
    """
    repo = ItemRepository(str(temp_db_path))
    object_id = repo.generate_new_id()
    item = _create_round_trip_item(repo, object_id)

    item.name = "Round Trip Updated"
    item.description = "Updated description"
    item.dirty = True

    item_component = item.components["ItemComponent"]
    item_component.base_value = 9999
    item_component.dirty = True

    render_component = item.components["RenderComponent"]
    render_component.icon_asset = "textures/ui/items/updated.dds"
    render_component.dirty = True

    skills = item.components["ObjectSkill"]
    skills.skills = [
        ObjectSkillRow(object_Template=object_id, skill_id=88002, cast_on_type=1, ai_combat_weight=4),
        ObjectSkillRow(object_Template=object_id, skill_id=88003, cast_on_type=2, ai_combat_weight=8),
    ]
    skills.dirty = True

    repo.save(item)
    reloaded = repo.get(object_id)

    assert reloaded.name == "Round Trip Updated"
    assert reloaded.description == "Updated description"
    assert reloaded.components["ItemComponent"].base_value == 9999
    assert reloaded.components["RenderComponent"].icon_asset == "textures/ui/items/updated.dds"
    assert {row.skill_id for row in reloaded.components["ObjectSkill"].skills} == {88002, 88003}


def test_service_create_default_item_persists_expected_components(temp_db_path):
    """Verify ItemService creates a default item with the expected persisted components.

    Args:
        temp_db_path: Writable copy of the baseline database for the test.

    Returns:
        None: Assertions validate service behavior.
    """
    service = ItemService(str(temp_db_path))

    created = service.create_default_item()

    assert created.object_id > 0
    assert {"ItemComponent", "RenderComponent"} <= set(created.components)

    conn = connect_db(temp_db_path)
    try:
        assert fetch_component_types(conn, created.object_id) == {
            Components.ITEM,
            Components.RENDER,
        }
    finally:
        conn.close()


def test_service_duplicate_item_copies_components_and_retargets_skills(temp_db_path):
    """Verify item duplication copies data while assigning fresh ids and retargeted skills.

    Args:
        temp_db_path: Writable copy of the baseline database for the test.

    Returns:
        None: Assertions validate service behavior.
    """
    service = ItemService(str(temp_db_path))

    source = service.create_default_item()
    source.name = "Duplicated Source"
    source.description = "Source description"
    source.dirty = True

    item_component = source.components["ItemComponent"]
    item_component.base_value = 5432
    item_component.dirty = True

    render_component = source.components["RenderComponent"]
    render_component.icon_asset = "textures/ui/items/source.dds"
    render_component.dirty = True

    skill_component = service.ensure_skills_component(source)
    skill_component.skills = [
        ObjectSkillRow(
            object_Template=source.object_id,
            skill_id=99001,
            cast_on_type=2,
            ai_combat_weight=14,
        )
    ]
    skill_component.dirty = True

    service.save_item(source)
    duplicated = service.duplicate_item(source.object_id)

    assert duplicated.object_id != source.object_id
    assert duplicated.name == source.name
    assert duplicated.description == source.description
    assert duplicated.components["ItemComponent"].id != source.components["ItemComponent"].id
    assert duplicated.components["RenderComponent"].id != source.components["RenderComponent"].id
    assert duplicated.components["ItemComponent"].base_value == 5432
    assert duplicated.components["RenderComponent"].icon_asset == "textures/ui/items/source.dds"

    # The duplicated skill keeps its gameplay data but must point at the new object.
    duplicated_skills = duplicated.components["ObjectSkill"].skills
    assert len(duplicated_skills) == 1
    assert duplicated_skills[0].object_Template == duplicated.object_id
    assert duplicated_skills[0].skill_id == 99001


def test_component_helpers_are_idempotent_and_assign_unique_blank_skill_ids(temp_db_path):
    """Verify item helper methods reuse existing components and assign unique placeholder skills.

    Args:
        temp_db_path: Writable copy of the baseline database for the test.

    Returns:
        None: Assertions validate service helper behavior.
    """
    service = ItemService(str(temp_db_path))
    repo = ItemRepository(str(temp_db_path))
    item = Item(id=repo.generate_new_id(), type=ObjectTypes.ITEM, name="Unsaved helper item")

    first_item_component = service.add_item_component(item)
    second_item_component = service.add_item_component(item)
    first_render_component = service.add_render_component(item)
    second_render_component = service.add_render_component(item)
    first_skill = service.add_blank_skill(item)
    second_skill = service.add_blank_skill(item)

    assert first_item_component is second_item_component
    assert first_render_component is second_render_component
    assert first_skill.object_Template == item.object_id
    assert second_skill.object_Template == item.object_id
    assert first_skill.skill_id == INT_32_MAX
    assert second_skill.skill_id == INT_32_MAX - 1
