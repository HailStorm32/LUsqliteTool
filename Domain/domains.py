from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, IntEnum, StrEnum
from typing import Any, Dict, List, Optional

#####################################
# Types and Constants
#####################################
INT_32_MAX = 2_147_483_647  # Maximum value for a 32-bit signed integer
INT_32_MIN = -2_147_483_648  # Minimum value for a 32-bit signed integer
INT_NULL = INT_32_MIN  # Representation of NULL for INT32 fields
PLACEHOLDER_TEXT = "Placeholder String"


class NPCProfession(IntEnum):
    VENDOR = 1
    MISSION_GIVER = 2


class ItemType(IntEnum):
    UNKNOWN = -1  # An unknown item type
    NONE = INT_NULL  # No item type
    BRICK = 1  # A brick
    HAT = 2  # A hat / head item
    HAIR = 3  # A hair item
    NECK = 4  # A neck item
    LEFT_HAND = 5  # A left handed item
    RIGHT_HAND = 6  # A right handed item
    LEGS = 7  # A pants item
    LEFT_TRINKET = 8  # A left handed trinket item
    RIGHT_TRINKET = 9  # A right handed trinket item
    BEHAVIOR = 10  # A behavior
    PROPERTY = 11  # A property
    MODEL = 12  # A model
    COLLECTIBLE = 13  # A collectible item
    CONSUMABLE = 14  # A consumable item
    CHEST = 15  # A chest item
    EGG = 16  # An egg
    PET_FOOD = 17  # A pet food item
    QUEST_OBJECT = 18  # A quest item
    PET_INVENTORY_ITEM = 19  # A pet inventory item
    PACKAGE = 20  # A package
    LOOT_MODEL = 21  # A loot model
    VEHICLE = 22  # A vehicle
    CURRENCY = 23  # Currency
    MOUNT = 24  # A mount


class ColorType(Enum):
    NONE = (INT_NULL, "NULL")
    BRIGHT_RED = (0, "#de000d")
    BRIGHT_BLUE = (1, "#0057a8")
    BRIGHT_YELLOW = (2, "#fec400")
    DARK_GREEN = (3, "#007b28")
    BRIGHT_ORANGE = (5, "#e76318")
    BLACK = (6, "#323232")
    DARK_STONE_GREY = (7, "#4c5156")
    MEDIUM_STONE_GREY = (8, "#9c9191")
    REDDISH_BROWN = (9, "#5b1c0c")
    WHITE = (10, "#f4f4f4")
    MEDIUM_BLUE = (11, "#478cc6")
    BRIGHT_YELLOWISH_GREEN = (12, "#94b80a")
    DARK_RED = (13, "#80081b")
    EARTH_BLUE = (14, "#002541")
    EARTH_GREEN = (15, "#003416")
    BRICK_YELLOW = (16, "#d9ba7a")
    LIGHT_PURPLE = (17, "#ed9ec2")
    COOL_YELLOW = (18, "#ffe369")
    NOUGAT = (19, "#d67240")
    NATURE_TRANSPARENT = (36, "#f7d689")
    BRIGHT_GREEN = (42, "#009624")
    DARK_ORANGE = (43, "#a83d15")
    TRANSPARENT = (45, "#eeeeee")
    TRANSPARENT_RED = (46, "#e02a29")
    TRANSPARENT_LIGHT_BLUE = (47, "#b6e0ef")
    TRANSPARENT_BLUE = (48, "#50b1e8")
    TRANSPARENT_YELLOW = (49, "#f9ef69")
    TRANSPARENT_FLUORESCENT_REDDISH_ORANGE = (51, "#e66645")
    TRANSPARENT_GREEN = (52, "#61b36e")
    TRANSPARENT_FLUORESCENT_GREEN = (53, "#f7eb59")
    TRANSPARENT_BROWN = (63, "#bdaba3")
    TRANSPARENT_MEDIUM_REDDISH_VIOLET = (65, "#ee9dc3")
    LIGHT_YELLOWISH_GREEN = (71, "#d6e38c")
    BRIGHT_REDDISH_VIOLET = (75, "#9c006b")
    TRANSPARENT_BRIGHT_BLUISH_VIOLET = (77, "#9c94c7")
    SILVER_PLASTIC = (81, "#8c9494")
    SAND_BLUE = (84, "#5e748c")
    SAND_YELLOW = (87, "#8c7552")
    COPPER = (88, "#744930")
    TRANSPARENT_FLUORESCENT_BLUE = (89, "#cfe2f7")
    DARK_GREY_METALLIC = (93, "#47403b")
    SAND_GREEN = (96, "#5f8265")
    TRANSPARENT_BRIGHT_ORANGE = (105, "#ec760e")
    FLAME_YELLOWISH_ORANGE = (113, "#f29900")
    LIGHT_STONE_GREY = (119, "#e3e3d9")
    LIGHT_ROYAL_BLUE = (123, "#87bfeb")
    BRIGHT_PURPLE = (130, "#de378b")
    MEDIUM_LILAC = (142, "#2c1577")
    FLESH = (143, "#f5c189")
    PHOSPHORESCENT_WHITE_REPLACE_50 = (146, "#fefcd5")
    WARM_GOLD = (147, "#aa7f2e")
    LU_METALLIC_SHADER = (150, "#9ca3a8")
    DARK_BROWN_FLESH = (151, "#342100")

    def __init__(self, id_value: int, hex_code: str):
        self.id = id_value
        self.hex = hex_code

    def __int__(self):
        return self.id

    def __str__(self):
        return self.hex


class EquipLocation(StrEnum):
    NONE = "NULL"
    HAIR = "hair"
    HEAD = "head"
    NECK = "clavicle"
    CHEST = "chest"
    LEFT_HAND = "special_l"
    RIGHT_HAND = "special_r"
    LEGS = "legs"
    ACCESSORY = "accessory"


class ObjectTypes(StrEnum):
    ITEM = "Loot"
    NPC = "UserGeneratedNPCs"
    NPC_2 = "NPC"
    ENEMY = "Enemies"


class Components(IntEnum):
    CONTROLLABLE_PHYSICS = 1
    RENDER = 2
    SIMPLE_PHYSICS = 3
    SCRIPT = 5
    DESTROYABLE = 7
    SKILL = 9
    ITEM = 11
    VENDOR = 16
    INVENTORY = 17
    MINIFIG = 35
    MISSION_OFFER = 73


####################################
# Dataclass Definitions
####################################


@dataclass
class RowCollection:
    """Container used by the GUI and repository to treat row groups uniformly."""

    rows: List[Any] = field(default_factory=list)
    key_field: str = "id"
    label_prefix: str = "Row"
    # Some row-backed components use a distinct ComponentsRegistry component_id.
    component_id: Optional[int] = None
    loaded_keys: set[Any] = field(default_factory=set, repr=False)
    dirty: bool = False


# ------------------------------------------
# ---------- RenderComponent --------------
@dataclass
class RenderComponent:
    id: int = INT_32_MAX
    render_asset: str = ""
    icon_asset: str = ""
    icon_id: int = 3964
    shader_id: int = 23
    effect1: Optional[int] = None
    effect2: Optional[int] = None
    effect3: Optional[int] = None
    effect4: Optional[int] = None
    effect5: Optional[int] = None
    effect6: Optional[int] = None
    animation_group_ids: Optional[str] = None
    fade: bool = True
    use_drop_shadow: bool = False
    preload_animations: bool = False
    fade_in_time: float = 1.0
    max_shadow_distance: float = 0.0
    ignore_camera_collision: bool = False
    render_component_lod1: Optional[int] = None
    render_component_lod2: Optional[int] = None
    gradual_snap: bool = False
    animation_flag: Optional[int] = None
    audio_meta_event_set: Optional[str] = None
    billboard_height: Optional[float] = None
    chat_bubble_offset: Optional[float] = None
    static_billboard: bool = False
    lxfml_folder: Optional[str] = None
    attach_indicators_to_node: bool = False
    dirty: bool = False


# ------------------------------------------
# ----- ObjectSkills (SkillComponent) -----
@dataclass
class ObjectSkillRow:
    object_Template: int = INT_32_MAX
    skill_id: int = INT_32_MAX
    cast_on_type: int = 1
    ai_combat_weight: Optional[int] = None
    dirty: bool = False


@dataclass
class ObjectSkills:
    skills: List[ObjectSkillRow] = field(default_factory=list)
    zero_component_id: bool = True
    dirty: bool = False
    key_field: str = field(default="skill_id", repr=False)
    label_prefix: str = field(default="Skill", repr=False)

    @property
    def rows(self) -> List[ObjectSkillRow]:
        return self.skills


# ------------------------------------------
# ---------- ItemComponent ----------------
@dataclass
class ItemComponent:
    id: int = INT_32_MAX
    equip_location: EquipLocation = EquipLocation.CHEST
    base_value: int = 1000
    is_kit_piece: bool = False
    rarity: int = 4
    item_type: ItemType = ItemType.CHEST
    item_info: int = 0
    in_loot_table: bool = False
    in_vendor: bool = False
    is_unique: bool = True
    is_bop: bool = True
    is_boe: bool = False
    req_flag_id: int = 0
    req_specialty_id: int = 0
    req_spec_rank: int = 0
    req_achievement_id: int = 0
    stack_size: int = 1
    color1: ColorType = ColorType.WHITE
    decal: Optional[int] = None
    offset_group_id: Optional[int] = None
    build_types: int = 0
    req_precondition: str = "214"
    animation_flag: Optional[int] = None
    equip_effects: Optional[int] = None
    ready_for_qa: bool = False
    item_rating: int = 0
    is_two_handed: bool = False
    min_num_required: Optional[int] = None
    del_res_index: Optional[int] = None
    currency_lot: Optional[int] = None
    alt_currency_cost: Optional[int] = None
    sub_items: Optional[str] = None
    audio_event_use: Optional[str] = None
    no_equip_animation: bool = False
    commendation_lot: Optional[int] = None
    commendation_cost: Optional[int] = None
    audio_equip_meta_event_set: Optional[str] = None
    currency_costs: Optional[str] = None
    ingredient_info: Optional[str] = None
    loc_status: Optional[int] = None
    forge_type: Optional[int] = None
    sell_multiplier: Optional[float] = None
    dirty: bool = False


# ------------------------------------------
# ---------- NPC Components ----------------
@dataclass
class MinifigComponent:
    id: int = INT_32_MAX
    head: Optional[int] = None
    chest: Optional[int] = None
    legs: Optional[int] = None
    hairstyle: Optional[int] = None
    haircolor: Optional[int] = None
    chestdecal: Optional[int] = None
    headcolor: Optional[int] = None
    lefthand: Optional[int] = None
    righthand: Optional[int] = None
    eyebrowstyle: Optional[int] = None
    eyesstyle: Optional[int] = None
    mouthstyle: Optional[int] = None
    dirty: bool = False


@dataclass
class PhysicsComponent:
    id: int = INT_32_MAX
    static: float = 0.0
    physics_asset: Optional[str] = None
    jump: float = 0.0
    doublejump: float = 0.0
    speed: Optional[float] = None
    rot_speed: Optional[float] = None
    player_height: Optional[float] = None
    player_radius: Optional[float] = None
    pc_shape_type: int = 0
    collision_group: int = 0
    air_speed: float = 10.0
    boundary_asset: Optional[str] = None
    jump_air_speed: Optional[float] = 25.0
    friction: Optional[float] = None
    gravity_volume_asset: Optional[str] = None
    dirty: bool = False


@dataclass
class DestructibleComponent:
    id: int = INT_32_MAX
    faction: Optional[int] = None
    faction_list: Optional[str] = None
    life: Optional[int] = None
    imagination: Optional[int] = None
    loot_matrix_index: Optional[int] = None
    currency_index: Optional[int] = None
    level: Optional[int] = None
    armor: Optional[float] = None
    death_behavior: int = 0
    is_npc: bool = True
    attack_priority: int = 1
    is_smashable: bool = False
    difficulty_level: Optional[int] = None
    dirty: bool = False


@dataclass
class VendorComponent:
    id: int = INT_32_MAX
    buy_scalar: float = 1.0
    sell_scalar: float = 1.0
    refresh_time_seconds: float = 1800.0
    loot_matrix_index: int = 0
    dirty: bool = False


@dataclass
class ScriptComponent:
    id: int = INT_32_MAX
    script_name: Optional[str] = None
    client_script_name: Optional[str] = None
    dirty: bool = False


# ------------------------------------------
# ---------- NPC Row Collections ----------
@dataclass
class InventoryComponentRow:
    id: int = INT_32_MAX
    itemid: int = INT_32_MAX
    count: int = 1
    equip: bool = False
    dirty: bool = False


@dataclass
class MissionNPCComponentRow:
    id: int = INT_32_MAX
    mission_id: int = INT_32_MAX
    offers_mission: bool = True
    accepts_mission: bool = True
    gate_version: Optional[str] = None
    dirty: bool = False


@dataclass
class LootMatrixRow:
    row_id: Optional[int] = None
    loot_matrix_index: int = 0
    loot_table_index: int = 0
    rarity_table_index: int = 1
    percent: float = 1.0
    min_to_drop: int = 0
    max_to_drop: int = 1
    id: Optional[int] = None
    flag_id: Optional[int] = None
    gate_version: Optional[str] = None
    dirty: bool = False

    @property
    def ui_key(self) -> str | int:
        if self.row_id is not None:
            return self.row_id
        return f"new-{self.loot_table_index}"

    @property
    def display_key(self) -> int:
        if self.row_id is not None:
            return self.row_id
        return self.loot_table_index


@dataclass
class LootTableRow:
    itemid: int = INT_32_MAX
    loot_table_index: int = 0
    id: int = INT_32_MAX
    mission_drop: bool = False
    sort_priority: int = 0
    dirty: bool = False


@dataclass
class CurrencyTableRow:
    currency_index: int = 0
    npcminlevel: int = 0
    minvalue: int = 0
    maxvalue: int = 0
    id: int = INT_32_MAX
    dirty: bool = False


@dataclass
class MissionRow:
    id: int = INT_32_MAX
    defined_type: Optional[str] = None
    defined_subtype: Optional[str] = None
    ui_sort_order: Optional[int] = None
    offer_object_id: Optional[int] = None
    target_object_id: Optional[int] = None
    reward_currency: Optional[int] = None
    lego_score: Optional[int] = None
    reward_reputation: Optional[int] = None
    is_choice_reward: bool = False
    reward_item1: int = -1
    reward_item1_count: int = 1
    reward_item2: int = -1
    reward_item2_count: int = 1
    reward_item3: int = -1
    reward_item3_count: int = 1
    reward_item4: int = -1
    reward_item4_count: int = 1
    reward_emote: int = -1
    reward_emote2: int = -1
    reward_emote3: int = -1
    reward_emote4: int = -1
    reward_max_imagination: int = 0
    reward_max_health: int = 0
    reward_max_inventory: Optional[int] = None
    reward_max_model: Optional[int] = None
    reward_max_widget: Optional[int] = None
    reward_max_wallet: Optional[int] = None
    repeatable: bool = False
    reward_currency_repeatable: Optional[int] = None
    reward_item1_repeatable: int = -1
    reward_item1_repeat_count: int = 1
    reward_item2_repeatable: int = -1
    reward_item2_repeat_count: int = 1
    reward_item3_repeatable: int = -1
    reward_item3_repeat_count: int = 1
    reward_item4_repeatable: int = -1
    reward_item4_repeat_count: int = 1
    time_limit: Optional[int] = None
    is_mission: bool = True
    mission_icon_id: Optional[int] = None
    prereq_mission_id: Optional[str] = None
    localize: bool = True
    in_motd: bool = False
    cooldown_time: Optional[int] = None
    is_random: bool = False
    random_pool: Optional[str] = None
    ui_prereq_id: Optional[int] = None
    gate_version: Optional[str] = None
    hud_states: Optional[str] = None
    loc_status: int = 0
    reward_bank_inventory: Optional[int] = None
    dirty: bool = False


@dataclass
class MissionTaskRow:
    id: int = INT_32_MAX
    loc_status: int = 0
    task_type: Optional[int] = None
    target: Optional[int] = None
    target_group: Optional[str] = None
    target_value: Optional[int] = None
    task_param1: Optional[str] = None
    large_task_icon: Optional[str] = None
    icon_id: Optional[int] = None
    uid: int = INT_32_MAX
    large_task_icon_id: Optional[int] = None
    localize: bool = True
    gate_version: Optional[str] = None
    dirty: bool = False


@dataclass
class MissionTextRow:
    id: int = INT_32_MAX
    story_icon: Optional[str] = None
    mission_icon: Optional[str] = None
    offer_npc_icon: Optional[str] = None
    icon_id: Optional[int] = None
    state_1_anim: Optional[str] = None
    state_2_anim: Optional[str] = None
    state_3_anim: Optional[str] = None
    state_4_anim: Optional[str] = None
    state_3_turnin_anim: Optional[str] = None
    state_4_turnin_anim: Optional[str] = None
    onclick_anim: Optional[str] = None
    cinematic_accepted: Optional[str] = None
    cinematic_accepted_leadin: Optional[float] = None
    cinematic_completed: Optional[str] = None
    cinematic_completed_leadin: Optional[float] = None
    cinematic_repeatable: Optional[str] = None
    cinematic_repeatable_leadin: Optional[float] = None
    cinematic_repeatable_completed: Optional[str] = None
    cinematic_repeatable_completed_leadin: Optional[float] = None
    audio_event_guid_interact: Optional[str] = None
    audio_event_guid_offer_accept: Optional[str] = None
    audio_event_guid_offer_deny: Optional[str] = None
    audio_event_guid_completed: Optional[str] = None
    audio_event_guid_turn_in: Optional[str] = None
    audio_event_guid_failed: Optional[str] = None
    audio_event_guid_progress: Optional[str] = None
    audio_music_cue_offer_accept: Optional[str] = None
    audio_music_cue_turn_in: Optional[str] = None
    turn_in_icon_id: Optional[int] = None
    localize: bool = True
    loc_status: int = 0
    gate_version: Optional[str] = None
    dirty: bool = False


@dataclass
class MissionEmailRow:
    id: int = INT_32_MAX
    message_type: int = 0
    notification_group: int = 0
    mission_id: int = INT_32_MAX
    attachment_lot: Optional[int] = None
    localize: bool = True
    loc_status: int = 0
    gate_version: Optional[str] = None
    dirty: bool = False


# ------------------------------------------
# -------- GameObject (Objects)------------
@dataclass
class GameObject:
    def __init__(self, id: int, name: str, type: ObjectTypes | str, description: str):
        # This class keeps a manual __init__ so Item/NPC constructors can stay compact.
        # When we do that, dataclass default_factory fields like `components` are not
        # auto-created, so initialize the full instance state here.
        self.object_id = id
        self.name = name
        self.placeable = False
        self.type = type
        self.description = description
        self.localize = True
        self.npc_template_id = None
        self.display_name = PLACEHOLDER_TEXT
        self.interaction_distance = None
        self.nametag = False
        self.internal_notes = PLACEHOLDER_TEXT
        self.loc_status = 2
        self.gate_version = None
        self.hq_valid = True
        self.dirty = False
        self.components = {}

    object_id: int = INT_32_MAX
    name: str = PLACEHOLDER_TEXT
    placeable: bool = False
    type: ObjectTypes | str | None = None
    description: str = PLACEHOLDER_TEXT
    localize: Optional[bool] = True
    npc_template_id: Optional[int] = None
    display_name: Optional[str] = PLACEHOLDER_TEXT
    interaction_distance: Optional[float] = None
    nametag: Optional[bool] = False
    internal_notes: Optional[str] = PLACEHOLDER_TEXT
    loc_status: Optional[int] = 2
    gate_version: Optional[str] = None
    hq_valid: Optional[bool] = True
    dirty: bool = False
    components: Dict[str, object] = field(default_factory=dict)


#####################################
# GameObject Subclasses
#####################################


class Item(GameObject):
    def __init__(self, id: int, type: ObjectTypes | str, name: Optional[str] = None):
        super().__init__(id, name or f"Item: {id}", type, "An item in the game.")


class NPC(GameObject):
    def __init__(self, id: int, type: ObjectTypes | str, name: Optional[str] = None):
        super().__init__(id, name or f"NPC: {id}", type, "An NPC in the game.")
