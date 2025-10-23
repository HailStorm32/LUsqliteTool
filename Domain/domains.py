from dataclasses import dataclass, field
from enum import IntEnum, StrEnum
from typing import List, Dict, Optional
from enum import Enum

#####################################
# Types and Constants
#####################################
INT_32_MAX = 2_147_483_647  # Maximum value for a 32-bit signed integer
INT_32_MIN = -2_147_483_648 # Minimum value for a 32-bit signed integer
INT_NULL = INT_32_MIN       # Representation of NULL for INT32 fields
PLACEHOLDER_TEXT = "Placeholder String"

class NPCProfession(IntEnum):
    VENDOR              = 1
    MISSION_GIVER       = 2

class ItemType(IntEnum):
    UNKNOWN             = -1   # An unknown item type
    NONE                = INT_NULL  # No item type
    BRICK               = 1    # A brick
    HAT                 = 2    # A hat / head item
    HAIR                = 3    # A hair item
    NECK                = 4    # A neck item
    LEFT_HAND           = 5    # A left handed item
    RIGHT_HAND          = 6    # A right handed item
    LEGS                = 7    # A pants item
    LEFT_TRINKET        = 8    # A left handed trinket item
    RIGHT_TRINKET       = 9    # A right handed trinket item
    BEHAVIOR            = 10   # A behavior
    PROPERTY            = 11   # A property
    MODEL               = 12   # A model
    COLLECTIBLE         = 13   # A collectible item
    CONSUMABLE          = 14   # A consumable item
    CHEST               = 15   # A chest item
    EGG                 = 16   # An egg
    PET_FOOD            = 17   # A pet food item
    QUEST_OBJECT        = 18   # A quest item
    PET_INVENTORY_ITEM  = 19   # A pet inventory item
    PACKAGE             = 20   # A package
    LOOT_MODEL          = 21   # A loot model
    VEHICLE             = 22   # A vehicle
    CURRENCY            = 23   # Currency
    MOUNT               = 24   # A mount

class ColorType(Enum):
    NONE                                    = (INT_NULL, "NULL")
    BRIGHT_RED                              = (0,   "#de000d")
    BRIGHT_BLUE                             = (1,   "#0057a8")
    BRIGHT_YELLOW                           = (2,   "#fec400")
    DARK_GREEN                              = (3,   "#007b28")
    BRIGHT_ORANGE                           = (5,   "#e76318")
    BLACK                                   = (6,   "#323232")
    DARK_STONE_GREY                         = (7,   "#4c5156")
    MEDIUM_STONE_GREY                       = (8,   "#9c9191")
    REDDISH_BROWN                           = (9,   "#5b1c0c")
    WHITE                                   = (10,  "#f4f4f4")
    MEDIUM_BLUE                             = (11,  "#478cc6")
    BRIGHT_YELLOWISH_GREEN                  = (12,  "#94b80a")
    DARK_RED                                = (13,  "#80081b")
    EARTH_BLUE                              = (14,  "#002541")
    EARTH_GREEN                             = (15,  "#003416")
    BRICK_YELLOW                            = (16,  "#d9ba7a")
    LIGHT_PURPLE                            = (17,  "#ed9ec2")
    COOL_YELLOW                             = (18,  "#ffe369")
    NOUGAT                                  = (19,  "#d67240")
    NATURE_TRANSPARENT                      = (36,  "#f7d689")
    BRIGHT_GREEN                            = (42,  "#009624")
    DARK_ORANGE                             = (43,  "#a83d15")
    TRANSPARENT                             = (45,  "#eeeeee")
    TRANSPARENT_RED                         = (46,  "#e02a29")
    TRANSPARENT_LIGHT_BLUE                  = (47,  "#b6e0ef")
    TRANSPARENT_BLUE                        = (48,  "#50b1e8")
    TRANSPARENT_YELLOW                      = (49,  "#f9ef69")
    TRANSPARENT_FLUORESCENT_REDDISH_ORANGE  = (51,  "#e66645")
    TRANSPARENT_GREEN                       = (52,  "#61b36e")
    TRANSPARENT_FLUORESCENT_GREEN           = (53,  "#f7eb59")
    TRANSPARENT_BROWN                       = (63,  "#bdaba3")
    TRANSPARENT_MEDIUM_REDDISH_VIOLET       = (65,  "#ee9dc3")
    LIGHT_YELLOWISH_GREEN                   = (71,  "#d6e38c")
    BRIGHT_REDDISH_VIOLET                   = (75,  "#9c006b")
    TRANSPARENT_BRIGHT_BLUISH_VIOLET        = (77,  "#9c94c7")
    SILVER_PLASTIC                          = (81,  "#8c9494")
    SAND_BLUE                               = (84,  "#5e748c")
    SAND_YELLOW                             = (87,  "#8c7552")
    COPPER                                  = (88,  "#744930")
    TRANSPARENT_FLUORESCENT_BLUE            = (89,  "#cfe2f7")
    DARK_GREY_METALLIC                      = (93,  "#47403b")
    SAND_GREEN                              = (96,  "#5f8265")
    TRANSPARENT_BRIGHT_ORANGE               = (105, "#ec760e")
    FLAME_YELLOWISH_ORANGE                  = (113, "#f29900")
    LIGHT_STONE_GREY                        = (119, "#e3e3d9")
    LIGHT_ROYAL_BLUE                        = (123, "#87bfeb")
    BRIGHT_PURPLE                           = (130, "#de378b")
    MEDIUM_LILAC                            = (142, "#2c1577")
    FLESH                                   = (143, "#f5c189")
    PHOSPHORESCENT_WHITE_REPLACE_50         = (146, "#fefcd5")
    WARM_GOLD                               = (147, "#aa7f2e")
    LU_METALLIC_SHADER                      = (150, "#9ca3a8")
    DARK_BROWN_FLESH                        = (151, "#342100")

    def __init__(self, id_value: int, hex_code: str):
        self.id = id_value
        self.hex = hex_code

    def __int__(self):
        return self.id

    def __str__(self):
        return self.hex

class EquipLocation(StrEnum):
    NONE                = "NULL"
    HAIR                = "hair"
    HEAD                = "head"
    NECK                = "clavicle"
    CHEST               = "chest"
    LEFT_HAND           = "special_l"
    RIGHT_HAND          = "special_r"
    LEGS                = "legs"
    ACCESSORY           = "accessory"

class ObjectTypes(StrEnum):
    ITEM                = "Loot"
    NPC                 = "UserGeneratedNPCs"
    NPC_2               = "NPC"
    ENEMY               = "Enemies"

class Components(IntEnum):
    CONTROLLABLE_PHYSICS = 1
    RENDER               = 2
    SIMPLE_PHYSICS       = 3
    SCRIPT               = 5
    DESTROYABLE          = 7
    SKILL                = 9
    ITEM                 = 11
    VENDOR               = 16
    INVENTORY            = 17
    MINIFIG              = 35
    MISSION_OFFER        = 73


####################################
# Dataclass Definitions
####################################

#------------------------------------------
# ---------- RenderComponent --------------
@dataclass
class RenderComponent:
    id:                         int             = INT_32_MAX            # INT32_MAX
    render_asset:               str             = ""                    # TEXT4
    icon_asset:                 str             = ""                    # TEXT4
    icon_id:                    int             = 3964                  # INT32
    shader_id:                  int             = 23                    # INT32
    effect1:                    Optional[int]   = None                  # INT32
    effect2:                    Optional[int]   = None                  # INT32
    effect3:                    Optional[int]   = None                  # INT32
    effect4:                    Optional[int]   = None                  # INT32
    effect5:                    Optional[int]   = None                  # INT32
    effect6:                    Optional[int]   = None                  # INT32
    animation_group_ids:        Optional[str]   = None                  # TEXT4
    fade:                       bool            = True                  # INT_BOOL (1)
    use_drop_shadow:            bool            = False                 # INT_BOOL (0)
    preload_animations:         bool            = False                 # INT_BOOL (0)
    fade_in_time:               float           = 1.0                   # REAL
    max_shadow_distance:        float           = 0.0                   # REAL
    ignore_camera_collision:    bool            = False                 # INT_BOOL (0)
    render_component_lod1:      Optional[int]   = None                  # INT32
    render_component_lod2:      Optional[int]   = None                  # INT32
    gradual_snap:               bool            = False                 # INT_BOOL (0)
    animation_flag:             Optional[int]   = None                  # INT32
    audio_meta_event_set:       Optional[str]   = None                  # TEXT4
    billboard_height:           Optional[float] = None                  # REAL
    chat_bubble_offset:         Optional[float] = None                  # REAL
    static_billboard:           bool            = False                 # INT_BOOL (0)
    lxfml_folder:               Optional[str]   = None                  # TEXT4
    attach_indicators_to_node:  bool            = False                 # INT_BOOL (0)

    dirty: bool = False

#------------------------------------------
# ----- ObjectSkills (SkillComponent) -----
@dataclass
class ObjectSkillRow:
    object_Template:            int             = INT_32_MAX            # INT32   (is the ID of the object)
    skill_id:                   int             = INT_32_MAX            # INT32   (is a skillID from SkillBehavior table)
    cast_on_type:               int             = 1                     # INT32
    ai_combat_weight:           Optional[int]   = None                  # INT32


@dataclass
class ObjectSkills:
    skills:                     List[ObjectSkillRow] = field(default_factory=list)
    zero_component_id:          bool            = True                 # Does this use a zero component ID in the ComponentsRegistry? (Will pretty much always be True)
                                                                       # If the component ID is zero, then it means you need to look up the object ID in the ObjectSkills table
    dirty:                      bool            = False

#------------------------------------------
# ---------- ItemComponent ----------------
@dataclass
class ItemComponent:
    id:                         int             = INT_32_MAX            # INT32
    equip_location:             EquipLocation   = EquipLocation.CHEST   # TEXT4
    base_value:                 int             = 1000                  # INT32
    is_kit_piece:               bool            = False                 # INT_BOOL (0)
    rarity:                     int             = 4                     # INT32
    item_type:                  ItemType        = ItemType.CHEST        # INT32
    item_info:                  int             = 0                     # INT64
    in_loot_table:              bool            = False                 # INT_BOOL (0)
    in_vendor:                  bool            = False                 # INT_BOOL (0)
    is_unique:                  bool            = True                  # INT_BOOL (1)
    is_bop:                     bool            = True                  # INT_BOOL (1)
    is_boe:                     bool            = False                 # INT_BOOL (0)
    req_flag_id:                int             = 0                     # INT32
    req_specialty_id:           int             = 0                     # INT32
    req_spec_rank:              int             = 0                     # INT32
    req_achievement_id:         int             = 0                     # INT32
    stack_size:                 int             = 1                     # INT32
    color1:                     ColorType       = ColorType.WHITE       # INT32
    decal:                      Optional[int]   = None                  # INT32
    offset_group_id:            Optional[int]   = None                  # INT32
    build_types:                int             = 0                     # INT32
    req_precondition:           str             = "214"                 # TEXT4
    animation_flag:             Optional[int]   = None                  # INT32
    equip_effects:              Optional[int]   = None                  # INT32
    ready_for_qa:               bool            = False                 # INT_BOOL (0)
    item_rating:                int             = 0                     # INT32
    is_two_handed:              bool            = False                 # INT_BOOL (0)
    min_num_required:           Optional[int]   = None                  # INT32
    del_res_index:              Optional[int]   = None                  # INT32
    currency_lot:               Optional[int]   = None                  # INT32
    alt_currency_cost:          Optional[int]   = None                  # INT32
    sub_items:                  Optional[str]   = None                  # TEXT4
    audio_event_use:            Optional[str]   = None                  # TEXT4
    no_equip_animation:         bool            = False                 # INT_BOOL (0)
    commendation_lot:           Optional[int]   = None                  # INT32
    commendation_cost:          Optional[int]   = None                  # INT32
    audio_equip_meta_event_set: Optional[str]   = None                  # TEXT4
    currency_costs:             Optional[str]   = None                  # TEXT4
    ingredient_info:            Optional[str]   = None                  # TEXT4
    loc_status:                 Optional[int]   = None                  # INT32
    forge_type:                 Optional[int]   = None                  # INT32
    sell_multiplier:            Optional[float] = None                  # REAL

    dirty: bool = False

#------------------------------------------
# -------- GameObject (Objects)------------
@dataclass
class GameObject:
    def __init__(self, id: int, name: str, type: ObjectTypes, description: str):
        self.object_id = id
        self.name = name
        self.type = type
        self.description = description

    object_id:                  int             = INT_32_MAX            # INT32
    name:                       str             = PLACEHOLDER_TEXT      # TEXT4
    placeable:                  bool            = False                 # INT_BOOL (0)
    type:                       ObjectTypes     = None                  # TEXT4
    description:                str             = PLACEHOLDER_TEXT      # TEXT4
    localize:                   Optional[bool]  = True                  # INT_BOOL (1)
    npc_template_id:            Optional[int]   = None                  # INT32
    display_name:               Optional[str]   = PLACEHOLDER_TEXT      # TEXT4
    interaction_distance:       Optional[float] = None                  # REAL
    nametag:                    Optional[bool]  = False                 # INT_BOOL (0)
    internal_notes:             Optional[str]   = PLACEHOLDER_TEXT      # TEXT4
    loc_status:                 Optional[int]   = 2                     # INT32
    gate_version:               Optional[str]   = None                  # TEXT4
    hq_valid:                   Optional[bool]  = True                  # INT_BOOL (1)

    dirty: bool = False

    components: Dict[str, object] = field(default_factory=dict)


#####################################
# GameObject Subclasses
######################################

class Item(GameObject):
    def __init__(self, id: int, type: ObjectTypes, name: Optional[str] = None):
        if name:
            name = name
        else:
            name = f"Item: {id}"

        description = "An item in the game."

        super().__init__(id, name, type, description)




class NPC(GameObject):
    pass #TODO: Implement NPC-specific attributes and methods