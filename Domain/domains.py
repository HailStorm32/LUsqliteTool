from dataclasses import dataclass, field
from enum import IntEnum, StrEnum
from typing import List, Dict, Optional

#####################################
# Types
#####################################
INT_32_MAX = 2_147_483_647  # Maximum value for a 32-bit signed integer

class NPCProfession(IntEnum):
    VENDOR          = 1
    MISSION_GIVER   = 2

class ItemType(IntEnum):
    UNKNOWN             = -1   # An unknown item type
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

class EquipLocation(StrEnum):
    HAIR        = "hair"
    HEAD        = "head"
    NECK        = "clavicle"
    CHEST       = "chest"
    LEFT_HAND   = "special_l"
    RIGHT_HAND  = "special_r"
    LEGS        = "legs"
    ACCESSORY   = "accessory"


####################################
# Dataclass Definitions
####################################

#------------------------------------------
# ---------- RenderComponent --------------
@dataclass
class RenderComponent:
    object_id:                  int             = INT_32_MAX            # INT32_MAX
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
class ObjectSkill:
    # object_id:                  int
    skills:                     List[ObjectSkillRow] = field(default_factory=list)
    dirty:                      bool            = False

#------------------------------------------
# ---------- ItemComponent ----------------
@dataclass
class ItemComponent:
    object_id:                  int             = INT_32_MAX            # INT32
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
    color1:                     int             = 10                    # INT32 (TODO: map properly)
    decal:                      Optional[int]   = None                  # INT32
    offset_group_id:            Optional[int]   = None                  # INT32
    build_types:                int             = 0                     # INT32
    req_precondition:           Optional[int]   = 214                   # TEXT4 (cast to int here)
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

@dataclass
class GameObject:
    object_id: int
    name: str
    components: Dict[str, object] = field(default_factory=dict)
    
    dirty: bool = False


#####################################
# GameObject Subclasses
######################################

class NPC(GameObject): ...
class Item(GameObject): ...