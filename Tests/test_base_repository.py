"""Per-method tests for baseRepository (mod test style).

Guiding principles:
1. Each test targets exactly ONE repository method (private via name mangle or protected/public).
2. Read-only tests use the read-only connection fixture (`ro_conn`).
3. Mutating tests run against an ephemeral copy of the baseline DB (`temp_db_path`).
4. Insert tests now populate (nearly) ALL writable fields with non‑default values to prove persistence works beyond defaults.
5. Update tests perform an insert first, then modify a subset of fields and verify the UPDATE branch executed (row changed, no duplicate row).
6. Private save/load helpers are accessed via name-mangled attribute names to keep surface API untouched.
7. Where practical, we re-load via the corresponding private loader to assert complete object equality (avoids duplicating column↔field mapping logic in tests).
"""
from __future__ import annotations
import sqlite3
import pytest
from typing import Dict

from Repository.base import baseRepository
from Domain.domains import (
    GameObject, ItemComponent, RenderComponent,
    ObjectSkills, ObjectSkillRow, Components, ObjectTypes,
    ItemType, EquipLocation
)

# ---------------- Candidate ID lists (adjust to match baseline) ----------------
EXISTING_OBJECT_IDS = [20007]
ITEM_OBJECT_IDS = EXISTING_OBJECT_IDS  # objects expected to possibly have ItemComponent
RENDER_OBJECT_IDS = EXISTING_OBJECT_IDS
SKILL_OBJECT_IDS = EXISTING_OBJECT_IDS

NEW_ID_BASE = 1_810_000_000  # high range for inserts

# ---------------- Helper utilities ----------------

def _first_existing_object_id(conn: sqlite3.Connection) -> int | None:
    for oid in EXISTING_OBJECT_IDS:
        if conn.execute("SELECT 1 FROM Objects WHERE id=?", (oid,)).fetchone():
            return oid
    return None

def _find_component_id(conn: sqlite3.Connection, oid_list, component_type: int) -> tuple[int, int] | None:
    for oid in oid_list:
        row = conn.execute(
            "SELECT component_id FROM ComponentsRegistry WHERE id=? AND component_type=?", (oid, component_type)
        ).fetchone()
        if row:
            return oid, row[0]
    return None

# ---------------- Load method tests ----------------

def test_load_object_table(ro_conn, baseline_path):
    repo = baseRepository(baseline_path)
    oid = _first_existing_object_id(ro_conn)
    if oid is None:
        pytest.skip("No candidate OBJECT_IDS present in baseline")
    obj = GameObject(object_id=oid, name="", placeable=False, type=ObjectTypes.ITEM)
    repo._load_object_table(obj)
    row = ro_conn.execute("SELECT * FROM Objects WHERE id=?", (oid,)).fetchone()
    assert row is not None
    assert obj.description == row['description']
    assert obj.localize == bool(row['localize'])
    assert obj.npc_template_id == row['npcTemplateID']
    assert obj.display_name == row['displayName']
    assert obj.interaction_distance == row['interactionDistance']
    assert obj.nametag == bool(row['nametag'])
    assert obj.internal_notes == row['_internalNotes']
    assert obj.loc_status == row['locStatus']
    assert obj.gate_version == row['gate_version']
    assert obj.hq_valid == bool(row['HQ_valid'])

def test_load_components(ro_conn, baseline_path):
    repo = baseRepository(baseline_path)
    oid = _first_existing_object_id(ro_conn)
    if oid is None:
        pytest.skip("No candidate OBJECT_IDS present in baseline")
    comps = repo._load_components(oid)
    assert isinstance(comps, dict)
    for k, v in comps.items():
        assert v is not None

def test__load_item_component(ro_conn, baseline_path):
    repo = baseRepository(baseline_path)
    match = _find_component_id(ro_conn, ITEM_OBJECT_IDS, Components.ITEM)
    if not match:
        pytest.skip("No ITEM component found for candidate IDs")
    oid, cid = match
    method = repo._baseRepository__load_item_component
    with repo._connect_to_db() as c:
        comp = method(c, oid, cid)
    row = ro_conn.execute("SELECT * FROM ItemComponent WHERE id=?", (cid,)).fetchone()
    assert row is not None
    assert comp.id == row['id']
    assert comp.base_value == row['baseValue']
    assert comp.rarity == row['rarity']

def test__load_render_component(ro_conn, baseline_path):
    repo = baseRepository(baseline_path)
    match = _find_component_id(ro_conn, RENDER_OBJECT_IDS, Components.RENDER)
    if not match:
        pytest.skip("No RENDER component found for candidate IDs")
    oid, cid = match
    method = repo._baseRepository__load_render_component
    with repo._connect_to_db() as c:
        comp = method(c, oid, cid)
    row = ro_conn.execute("SELECT * FROM RenderComponent WHERE id=?", (cid,)).fetchone()
    assert row is not None
    assert comp.id == row['id']
    assert comp.render_asset == row['render_asset']

def test__load_skill_component(ro_conn, baseline_path):
    repo = baseRepository(baseline_path)
    match = _find_component_id(ro_conn, SKILL_OBJECT_IDS, Components.SKILL)
    if not match:
        pytest.skip("No SKILL component found for candidate IDs")
    oid, cid = match
    method = repo._baseRepository__load_skill_component
    with repo._connect_to_db() as c:
        comp = method(c, oid, cid)
    assert len(comp.skills) > 0

# ---------------- Save method tests ----------------

def test_save_object_table_insert(temp_db_path):
    """Insert a brand new Objects row with most fields changed from defaults."""
    repo = baseRepository(temp_db_path)
    new_id = NEW_ID_BASE
    obj = GameObject(
        object_id=new_id,
        name="InsertedObject",
        placeable=True,
        type=ObjectTypes.ITEM,
    )
    # Set a broad set of attributes (exercise both bool + text + numeric columns)
    obj.description = "Inserted description"
    obj.localize = False
    obj.npc_template_id = 4242
    obj.display_name = "Display Name X"
    obj.interaction_distance = 7.5
    obj.nametag = True
    obj.internal_notes = "Internal notes"
    obj.loc_status = 9
    obj.gate_version = "g1.2.3"
    obj.hq_valid = False
    obj.dirty = True
    with repo._connect_to_db() as c:
        c.execute("BEGIN"); repo._save_object_table(c, obj); c.commit()
    # Re-load raw row to verify persistence
    with sqlite3.connect(temp_db_path) as c2:
        c2.row_factory = sqlite3.Row
        row = c2.execute("SELECT * FROM Objects WHERE id=?", (new_id,)).fetchone()
        assert row is not None
        assert row['name'] == obj.name
        assert row['description'] == obj.description
        assert row['localize'] == 0  # False stored as 0
        assert row['npcTemplateID'] == obj.npc_template_id
        assert row['displayName'] == obj.display_name
        assert abs(row['interactionDistance'] - obj.interaction_distance) < 1e-6
        assert row['nametag'] == 1
        assert row['_internalNotes'] == obj.internal_notes
        assert row['locStatus'] == obj.loc_status
        assert row['gate_version'] == obj.gate_version
        assert row['HQ_valid'] == 0

def test_save_object_table_update(temp_db_path):
    """Update ALL mutable columns of an existing Objects row and verify every change persisted.

    Columns covered: name, placeable, description, type, localize, npcTemplateID, displayName, interactionDistance,
    nametag, _internalNotes, locStatus, gate_version, HQ_valid.
    """
    repo = baseRepository(temp_db_path)
    existing_id = EXISTING_OBJECT_IDS[0]
    # Pull current row so we don't overwrite unrelated columns with defaults
    with sqlite3.connect(temp_db_path) as c:
        c.row_factory = sqlite3.Row
        base_row = c.execute("SELECT * FROM Objects WHERE id=?", (existing_id,)).fetchone()
        if not base_row:
            pytest.skip("Existing object id from list not present in baseline copy")
    # Build GameObject with current persisted core fields
    obj = GameObject(object_id=existing_id, name=base_row['name'], placeable=bool(base_row['placeable']), type=base_row['type'])
    # Load remaining columns into dataclass
    repo._load_object_table(obj)
    # Mutate ALL tracked columns with deterministic new values
    obj.name = "UpdName_" + str(existing_id)
    obj.placeable = not bool(base_row['placeable'])
    obj.description = "DescUpdated_" + str(existing_id)
    obj.localize = False if obj.localize else True  # toggle
    obj.npc_template_id = (obj.npc_template_id or 0) + 123
    obj.display_name = "DispUpdated_" + str(existing_id)
    obj.interaction_distance = (obj.interaction_distance or 0) + 3.14
    obj.nametag = not bool(obj.nametag)
    obj.internal_notes = "NotesUpdated_" + str(existing_id)
    obj.loc_status = (obj.loc_status or 0) + 7
    obj.gate_version = "gv_1_Updated"
    obj.hq_valid = not bool(obj.hq_valid)
    obj.dirty = True
    with repo._connect_to_db() as c:
        c.execute("BEGIN"); repo._save_object_table(c, obj); c.commit()
    # Verify changes
    with sqlite3.connect(temp_db_path) as c2:
        c2.row_factory = sqlite3.Row
        row = c2.execute("SELECT * FROM Objects WHERE id=?", (existing_id,)).fetchone()
        assert row is not None
        assert row['name'] == obj.name
        assert bool(row['placeable']) == obj.placeable
        assert row['description'] == obj.description
        assert row['type'] == obj.type
        assert bool(row['localize']) == obj.localize
        assert row['npcTemplateID'] == obj.npc_template_id
        assert row['displayName'] == obj.display_name
        assert abs(row['interactionDistance'] - obj.interaction_distance) < 1e-6
        assert bool(row['nametag']) == obj.nametag
        assert row['_internalNotes'] == obj.internal_notes
        assert row['locStatus'] == obj.loc_status
        assert row['gate_version'] == obj.gate_version
        assert bool(row['HQ_valid']) == obj.hq_valid

def test__save_item_component_insert_and_full_field_persistence(temp_db_path):
    """Insert ItemComponent with all fields customized then reload via loader to compare dataclasses."""
    repo = baseRepository(temp_db_path)
    new_id = NEW_ID_BASE + 10
    ic = ItemComponent(
        id=new_id,
        equip_location=EquipLocation.HEAD,
        base_value=777,
        is_kit_piece=True,
        rarity=8,
        item_type=ItemType.HAT,
        item_info=123456,
        in_loot_table=True,
        in_vendor=True,
        is_unique=False,
        is_bop=False,
        is_boe=True,
        req_flag_id=10,
        req_specialty_id=20,
        req_spec_rank=2,
        req_achievement_id=99,
        stack_size=5,
        color1=42,
        decal=11,
        offset_group_id=3,
        build_types=7,
        req_precondition="555", # Stored as TEXT4 in DB so loader yields a string; make test value a str for equality
        animation_flag=9,
        equip_effects=12,
        ready_for_qa=True,
        item_rating=321,
        is_two_handed=True,
        min_num_required=2,
        del_res_index=4,
        currency_lot=1001,
        alt_currency_cost=222,
        sub_items="1,2,3",
        audio_event_use="sound_use",
        no_equip_animation=True,
        commendation_lot=77,
        commendation_cost=88,
        audio_equip_meta_event_set="meta_evt",
        currency_costs="{gold:10}",
        ingredient_info="ing1",
        loc_status=5,
        forge_type=6,
        sell_multiplier=1.25,
    )
    ic.dirty = True
    save_method = repo._baseRepository__save_item_component
    with repo._connect_to_db() as c:
        c.execute("BEGIN"); save_method(c, ic); c.commit()
    # Reload through private loader for a complete field mapping equivalence check
    load_method = repo._baseRepository__load_item_component
    with repo._connect_to_db() as c:
        reloaded = load_method(c, ic.id, ic.id)  # object_id param only used for error msgs
    # Compare dataclasses (dirty flags ignored)
    ic.dirty = False
    assert reloaded == ic

def test__save_item_component_update(temp_db_path):
    """Update ALL columns of an existing ItemComponent and assert each persisted.

    (id immutable). Booleans toggled, numerics incremented or set to sentinels, optionals set non-null.
    """
    repo = baseRepository(temp_db_path)
    target = EXISTING_OBJECT_IDS[0]
    # Find component id for ITEM
    with sqlite3.connect(temp_db_path) as c:
        c.row_factory = sqlite3.Row
        comp_row = c.execute(
            "SELECT component_id FROM ComponentsRegistry WHERE id=? AND component_type=?",
            (target, Components.ITEM)
        ).fetchone()
        if not comp_row:
            pytest.skip("Existing object lacks ItemComponent")
        comp_id = comp_row['component_id']
    load_method = repo._baseRepository__load_item_component
    with repo._connect_to_db() as c:
        ic = load_method(c, target, comp_id)
    # Mutate ALL dataclass fields except id
    ic.equip_location = EquipLocation.HEAD if ic.equip_location != EquipLocation.HEAD else EquipLocation.CHEST
    ic.base_value = (ic.base_value or 0) + 555
    ic.is_kit_piece = not ic.is_kit_piece
    ic.rarity = (ic.rarity or 0) + 2
    ic.item_type = ItemType.HAT if ic.item_type != ItemType.HAT else ItemType.BRICK
    ic.item_info = (ic.item_info or 0) + 999
    ic.in_loot_table = not ic.in_loot_table
    ic.in_vendor = not ic.in_vendor
    ic.is_unique = not ic.is_unique
    ic.is_bop = not ic.is_bop
    ic.is_boe = not ic.is_boe
    ic.req_flag_id = (ic.req_flag_id or 0) + 1
    ic.req_specialty_id = (ic.req_specialty_id or 0) + 2
    ic.req_spec_rank = (ic.req_spec_rank or 0) + 3
    ic.req_achievement_id = (ic.req_achievement_id or 0) + 4
    ic.stack_size = (ic.stack_size or 0) + 10
    ic.color1 = (ic.color1 or 0) + 5
    ic.decal = (ic.decal or 0) + 6 if ic.decal is not None else 6
    ic.offset_group_id = (ic.offset_group_id or 0) + 7
    ic.build_types = (ic.build_types or 0) + 8
    # req_precondition stored as TEXT in DB; loader returns raw value (may be str). Normalize to int then back to str.
    _req_pre_int = int(ic.req_precondition) if isinstance(ic.req_precondition, (str, int)) and ic.req_precondition is not None else 0
    _req_pre_int += 9
    ic.req_precondition = str(_req_pre_int)
    ic.animation_flag = (ic.animation_flag or 0) + 10
    ic.equip_effects = (ic.equip_effects or 0) + 11
    ic.ready_for_qa = not ic.ready_for_qa
    ic.item_rating = (ic.item_rating or 0) + 12
    ic.is_two_handed = not ic.is_two_handed
    ic.min_num_required = (ic.min_num_required or 0) + 13
    ic.del_res_index = (ic.del_res_index or 0) + 14
    ic.currency_lot = (ic.currency_lot or 0) + 15
    ic.alt_currency_cost = (ic.alt_currency_cost or 0) + 16
    ic.sub_items = "upd_sub_items"
    ic.audio_event_use = "upd_audio_use"
    ic.no_equip_animation = not ic.no_equip_animation
    ic.commendation_lot = (ic.commendation_lot or 0) + 17
    ic.commendation_cost = (ic.commendation_cost or 0) + 18
    ic.audio_equip_meta_event_set = "upd_meta_evt"
    ic.currency_costs = "upd_currency_costs"
    ic.ingredient_info = "upd_ingredient"
    ic.loc_status = (ic.loc_status or 0) + 19
    ic.forge_type = (ic.forge_type or 0) + 20
    ic.sell_multiplier = (ic.sell_multiplier or 1.0) + 2.5
    ic.dirty = True
    save_method = repo._baseRepository__save_item_component
    with repo._connect_to_db() as c:
        c.execute("BEGIN"); save_method(c, ic); c.commit()
    with repo._connect_to_db() as c:
        reloaded = load_method(c, target, comp_id)
    # Assert each changed field
    assert reloaded.equip_location == ic.equip_location
    assert reloaded.base_value == ic.base_value
    assert reloaded.is_kit_piece == ic.is_kit_piece
    assert reloaded.rarity == ic.rarity
    assert reloaded.item_type == ic.item_type
    assert reloaded.item_info == ic.item_info
    assert reloaded.in_loot_table == ic.in_loot_table
    assert reloaded.in_vendor == ic.in_vendor
    assert reloaded.is_unique == ic.is_unique
    assert reloaded.is_bop == ic.is_bop
    assert reloaded.is_boe == ic.is_boe
    assert reloaded.req_flag_id == ic.req_flag_id
    assert reloaded.req_specialty_id == ic.req_specialty_id
    assert reloaded.req_spec_rank == ic.req_spec_rank
    assert reloaded.req_achievement_id == ic.req_achievement_id
    assert reloaded.stack_size == ic.stack_size
    assert reloaded.color1 == ic.color1
    assert reloaded.decal == ic.decal
    assert reloaded.offset_group_id == ic.offset_group_id
    assert reloaded.build_types == ic.build_types
    assert reloaded.req_precondition == ic.req_precondition
    assert reloaded.animation_flag == ic.animation_flag
    assert reloaded.equip_effects == ic.equip_effects
    assert reloaded.ready_for_qa == ic.ready_for_qa
    assert reloaded.item_rating == ic.item_rating
    assert reloaded.is_two_handed == ic.is_two_handed
    assert reloaded.min_num_required == ic.min_num_required
    assert reloaded.del_res_index == ic.del_res_index
    assert reloaded.currency_lot == ic.currency_lot
    assert reloaded.alt_currency_cost == ic.alt_currency_cost
    assert reloaded.sub_items == ic.sub_items
    assert reloaded.audio_event_use == ic.audio_event_use
    assert reloaded.no_equip_animation == ic.no_equip_animation
    assert reloaded.commendation_lot == ic.commendation_lot
    assert reloaded.commendation_cost == ic.commendation_cost
    assert reloaded.audio_equip_meta_event_set == ic.audio_equip_meta_event_set
    assert reloaded.currency_costs == ic.currency_costs
    assert reloaded.ingredient_info == ic.ingredient_info
    assert reloaded.loc_status == ic.loc_status
    assert reloaded.forge_type == ic.forge_type
    assert abs(reloaded.sell_multiplier - ic.sell_multiplier) < 1e-6

def test__save_render_component_insert_and_full_field_persistence(temp_db_path):
    """Insert RenderComponent with all fields customized then reload via loader for equality."""
    repo = baseRepository(temp_db_path)
    new_id = NEW_ID_BASE + 20
    rc = RenderComponent(
        id=new_id,
        render_asset="render/asset/path",
        icon_asset="icon/asset/path",
        icon_id=999,
        shader_id=44,
        effect1=1,
        effect2=2,
        effect3=3,
        effect4=4,
        effect5=5,
        effect6=6,
        animation_group_ids="10;20",
        fade=False,
        use_drop_shadow=True,
        preload_animations=True,
        fade_in_time=0.25,
        max_shadow_distance=123.0,
        ignore_camera_collision=True,
        render_component_lod1=77,
        render_component_lod2=88,
        gradual_snap=True,
        animation_flag=55,
        audio_meta_event_set="audio_evt",
        billboard_height=2.2,
        chat_bubble_offset=1.1,
        static_billboard=True,
        lxfml_folder="/foo/bar",
        attach_indicators_to_node=True,
    )
    rc.dirty = True
    save_method = repo._baseRepository__save_render_component
    with repo._connect_to_db() as c:
        c.execute("BEGIN"); save_method(c, rc); c.commit()
    load_method = repo._baseRepository__load_render_component
    with repo._connect_to_db() as c:
        reloaded = load_method(c, rc.id, rc.id)
    rc.dirty = False
    assert reloaded == rc

def test__save_render_component_update(temp_db_path):
    """Update ALL columns of an existing RenderComponent and assert each persisted."""
    repo = baseRepository(temp_db_path)
    target = EXISTING_OBJECT_IDS[0]
    with sqlite3.connect(temp_db_path) as c:
        c.row_factory = sqlite3.Row
        comp_row = c.execute(
            "SELECT component_id FROM ComponentsRegistry WHERE id=? AND component_type=?",
            (target, Components.RENDER)
        ).fetchone()
        if not comp_row:
            pytest.skip("Existing object lacks RenderComponent")
        comp_id = comp_row['component_id']
    load_method = repo._baseRepository__load_render_component
    with repo._connect_to_db() as c:
        rc = load_method(c, target, comp_id)
    # Mutate ALL fields (id immutable)
    rc.render_asset = (rc.render_asset or "ra") + "_upd"
    rc.icon_asset = (rc.icon_asset or "ia") + "_upd"
    rc.icon_id = (rc.icon_id or 0) + 101
    rc.shader_id = (rc.shader_id or 0) + 202
    rc.effect1 = (rc.effect1 or 0) + 1
    rc.effect2 = (rc.effect2 or 0) + 2
    rc.effect3 = (rc.effect3 or 0) + 3
    rc.effect4 = (rc.effect4 or 0) + 4
    rc.effect5 = (rc.effect5 or 0) + 5
    rc.effect6 = (rc.effect6 or 0) + 6
    rc.animation_group_ids = (rc.animation_group_ids or "") + ";99"
    rc.fade = not rc.fade
    rc.use_drop_shadow = not rc.use_drop_shadow
    rc.preload_animations = not rc.preload_animations
    rc.fade_in_time = (rc.fade_in_time or 0) + 0.5
    rc.max_shadow_distance = (rc.max_shadow_distance or 0) + 42.0
    rc.ignore_camera_collision = not rc.ignore_camera_collision
    rc.render_component_lod1 = (rc.render_component_lod1 or 0) + 7
    rc.render_component_lod2 = (rc.render_component_lod2 or 0) + 8
    rc.gradual_snap = not rc.gradual_snap
    rc.animation_flag = (rc.animation_flag or 0) + 9
    rc.audio_meta_event_set = (rc.audio_meta_event_set or "ame") + "_upd"
    rc.billboard_height = (rc.billboard_height or 0) + 3.14
    rc.chat_bubble_offset = (rc.chat_bubble_offset or 0) + 1.23
    rc.static_billboard = not rc.static_billboard
    rc.lxfml_folder = (rc.lxfml_folder or "/lxf") + "/upd"
    rc.attach_indicators_to_node = not rc.attach_indicators_to_node
    rc.dirty = True
    save_method = repo._baseRepository__save_render_component
    with repo._connect_to_db() as c:
        c.execute("BEGIN"); save_method(c, rc); c.commit()
    with repo._connect_to_db() as c:
        reloaded = load_method(c, target, comp_id)
    assert reloaded.render_asset == rc.render_asset
    assert reloaded.icon_asset == rc.icon_asset
    assert reloaded.icon_id == rc.icon_id
    assert reloaded.shader_id == rc.shader_id
    assert reloaded.effect1 == rc.effect1
    assert reloaded.effect2 == rc.effect2
    assert reloaded.effect3 == rc.effect3
    assert reloaded.effect4 == rc.effect4
    assert reloaded.effect5 == rc.effect5
    assert reloaded.effect6 == rc.effect6
    assert reloaded.animation_group_ids == rc.animation_group_ids
    assert reloaded.fade == rc.fade
    assert reloaded.use_drop_shadow == rc.use_drop_shadow
    assert reloaded.preload_animations == rc.preload_animations
    assert abs(reloaded.fade_in_time - rc.fade_in_time) < 1e-6
    assert abs(reloaded.max_shadow_distance - rc.max_shadow_distance) < 1e-6
    assert reloaded.ignore_camera_collision == rc.ignore_camera_collision
    assert reloaded.render_component_lod1 == rc.render_component_lod1
    assert reloaded.render_component_lod2 == rc.render_component_lod2
    assert reloaded.gradual_snap == rc.gradual_snap
    assert reloaded.animation_flag == rc.animation_flag
    assert reloaded.audio_meta_event_set == rc.audio_meta_event_set
    assert abs(reloaded.billboard_height - rc.billboard_height) < 1e-6
    assert abs(reloaded.chat_bubble_offset - rc.chat_bubble_offset) < 1e-6
    assert reloaded.static_billboard == rc.static_billboard
    assert reloaded.lxfml_folder == rc.lxfml_folder
    assert reloaded.attach_indicators_to_node == rc.attach_indicators_to_node

def test__save_skill_component_insert(temp_db_path):
    repo = baseRepository(temp_db_path)
    new_id = NEW_ID_BASE + 30
    obj = GameObject(object_id=new_id, name="SkillObj", placeable=False, type=ObjectTypes.ITEM); obj.dirty = True
    with repo._connect_to_db() as c:
        c.execute("BEGIN"); repo._save_object_table(c, obj); c.commit()
    skill_rows = [ObjectSkillRow(object_Template=new_id, skill_id=9999, cast_on_type=1, ai_combat_weight=5)]
    skills = ObjectSkills(skills=skill_rows, zero_component_id=True); skills.dirty = True
    skills.object_id = new_id  # dynamic attr used by save
    method = repo._baseRepository__save_skill_component
    with repo._connect_to_db() as c:
        c.execute("BEGIN"); method(c, new_id, skills); c.commit()
    with sqlite3.connect(temp_db_path) as c2:
        c2.row_factory = sqlite3.Row
        rows = c2.execute("SELECT * FROM ObjectSkills WHERE objectTemplate=?", (new_id,)).fetchall()
        assert len(rows) == 1 and rows[0]['skillID'] == 9999

def test__save_skill_component_update(temp_db_path):
    """Replace all skill rows for the object with a new set (exercise delete+reinsert over entire collection)."""
    repo = baseRepository(temp_db_path)
    target = EXISTING_OBJECT_IDS[0]
    # Determine if object has skill component in registry
    with sqlite3.connect(temp_db_path) as c:
        c.row_factory = sqlite3.Row
        comp_row = c.execute(
            "SELECT component_id FROM ComponentsRegistry WHERE id=? AND component_type=?",
            (target, Components.SKILL)
        ).fetchone()
        if not comp_row:
            pytest.skip("Existing object lacks Skill component")
    load_method = repo._baseRepository__load_skill_component
    with repo._connect_to_db() as c:
        skills = load_method(c, target, comp_row['component_id'])
    # If no skills, skip (unexpected but defensive)
    if not skills.skills:
        pytest.skip("Skill component has no rows to update")
    # Create an entirely new skill list of two entries
    new_rows = []
    base_template = target
    new_rows.append(ObjectSkillRow(object_Template=base_template, skill_id=900001, cast_on_type=2, ai_combat_weight=50))
    new_rows.append(ObjectSkillRow(object_Template=base_template, skill_id=900002, cast_on_type=3, ai_combat_weight=75))
    skills.skills = new_rows
    skills.dirty = True
    skills.object_id = target  # dynamic attr consumed by save implementation when zero_component_id True
    save_method = repo._baseRepository__save_skill_component
    with repo._connect_to_db() as c:
        c.execute("BEGIN"); save_method(c, target, skills); c.commit()
    # Verify DB reflects new single modified row
    with sqlite3.connect(temp_db_path) as c2:
        c2.row_factory = sqlite3.Row
        rows = c2.execute(
            "SELECT skillID, castOnType, AICombatWeight FROM ObjectSkills WHERE objectTemplate=?",
            (target,)
        ).fetchall()
    assert {r['skillID'] for r in rows} == {900001, 900002}
    row_map = {r['skillID']: r for r in rows}
    assert row_map[900001]['castOnType'] == 2 and row_map[900001]['AICombatWeight'] == 50
    assert row_map[900002]['castOnType'] == 3 and row_map[900002]['AICombatWeight'] == 75

def test__ensure_component_registry(temp_db_path):
    repo = baseRepository(temp_db_path)
    new_id = NEW_ID_BASE + 40
    obj = GameObject(object_id=new_id, name="RegObj", placeable=False, type=ObjectTypes.ITEM); obj.dirty = True
    with repo._connect_to_db() as c:
        c.execute("BEGIN"); repo._save_object_table(c, obj); c.commit()
    ic = ItemComponent(id=new_id); ic.dirty = True
    rc = RenderComponent(id=new_id); rc.dirty = True
    with repo._connect_to_db() as c:
        c.execute("BEGIN"); repo._baseRepository__save_item_component(c, ic); repo._baseRepository__save_render_component(c, rc); c.commit()
    with repo._connect_to_db() as c:
        c.execute("BEGIN"); repo._baseRepository__ensure_component_registry(c, new_id, {'ItemComponent': ic, 'RenderComponent': rc}); c.commit()
    with sqlite3.connect(temp_db_path) as c2:
        c2.row_factory = sqlite3.Row
        reg_rows = c2.execute("SELECT component_type FROM ComponentsRegistry WHERE id=?", (new_id,)).fetchall()
        types = {r[0] for r in reg_rows}
        assert Components.ITEM in types and Components.RENDER in types

def test__get_row_count(ro_conn, baseline_path):
    repo = baseRepository(baseline_path)
    oid = _first_existing_object_id(ro_conn)
    if oid is None:
        pytest.skip("No candidate OBJECT_IDS present in baseline")
    count = repo._baseRepository__get_row_count("Objects", oid, "id")
    direct = ro_conn.execute("SELECT COUNT(*) FROM Objects WHERE id=?", (oid,)).fetchone()[0]
    assert count == direct
