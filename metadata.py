INT_32_MAX = 2_147_483_647
FLOAT_32_MAX = 3.4028235e+38

component_field_metadata = {
    # ---------------------------------------------------------------
    # ItemComponent metadata
    # ---------------------------------------------------------------
    "ItemComponent": {
        # Core identity / primary
        "id":                         { "tip": "Primary key / component id",         "display_name": "",     "type": int,        "min": 1,       "max": INT_32_MAX,     "readonly": True,   "advanced": False   , "default": None },

        # Basic classification / value
        "equip_location":             { "tip": "Where this item is equipped",        "display_name": "",     "type": str,        "min": None,    "max": None,           "readonly": False,  "advanced": False   , "default": None },
        "base_value":                 { "tip": "Base vendor value (placeholder)",    "display_name": "",     "type": int,        "min": 0,       "max": INT_32_MAX,     "readonly": False,  "advanced": False   , "default": None },
        "is_kit_piece":               { "tip": "Part of a kit?",                     "display_name": "",     "type": bool,       "min": None,    "max": None,           "readonly": False,  "advanced": False   , "default": None },
        "rarity":                     { "tip": "Rarity tier (placeholder)",          "display_name": "",     "type": int,        "min": 0,       "max": 10,             "readonly": False,  "advanced": False   , "default": None },
        "item_type":                  { "tip": "Item type",                          "display_name": "",     "type": int,        "min": None,    "max": None,           "readonly": False,  "advanced": False   , "default": None },
        "item_info":                  { "tip": "Opaque item info id",                "display_name": "",     "type": int,        "min": 0,       "max": INT_32_MAX,     "readonly": False,  "advanced": True    , "default": None },

        # Availability flags
        "in_loot_table":              { "tip": "Appears in loot tables",             "display_name": "",     "type": bool,       "min": None,    "max": None,           "readonly": False,  "advanced": False   , "default": None },
        "in_vendor":                  { "tip": "Sold by vendors",                    "display_name": "",     "type": bool,       "min": None,    "max": None,           "readonly": False,  "advanced": False   , "default": None },
        "is_unique":                  { "tip": "Unique (one per player)",            "display_name": "",     "type": bool,       "min": None,    "max": None,           "readonly": False,  "advanced": False   , "default": None },
        "is_bop":                     { "tip": "Bind on pickup",                     "display_name": "",     "type": bool,       "min": None,    "max": None,           "readonly": False,  "advanced": False   , "default": None },
        "is_boe":                     { "tip": "Bind on equip",                      "display_name": "",     "type": bool,       "min": None,    "max": None,           "readonly": False,  "advanced": False   , "default": None },

        # Requirements
        "req_flag_id":                { "tip": "Required flag id (placeholder)",     "display_name": "",     "type": int,        "min": 0,       "max": INT_32_MAX,     "readonly": False,  "advanced": True    , "default": None },
        "req_specialty_id":           { "tip": "Required specialty id",              "display_name": "",     "type": int,        "min": 0,       "max": INT_32_MAX,     "readonly": False,  "advanced": True    , "default": None },
        "req_spec_rank":              { "tip": "Required specialty rank",            "display_name": "",     "type": int,        "min": 0,       "max": 100,            "readonly": False,  "advanced": True    , "default": None },
        "req_achievement_id":         { "tip": "Required achievement id",            "display_name": "",     "type": int,        "min": 0,       "max": INT_32_MAX,     "readonly": False,  "advanced": True    , "default": None },

        # Stack / appearance
        "stack_size":                 { "tip": "Max stack size",                     "display_name": "",     "type": int,        "min": 1,       "max": 256,            "readonly": False,  "advanced": False   , "default": None },
        "color1":                     { "tip": "Primary color index (placeholder)",  "display_name": "",     "type": int,        "min": 0,       "max": 255,            "readonly": False,  "advanced": True    , "default": None },
        "decal":                      { "tip": "Decal id (optional)",                "display_name": "",     "type": int,        "min": 0,       "max": INT_32_MAX,     "readonly": False,  "advanced": True    , "default": None },
        "offset_group_id":            { "tip": "Offset group id",                    "display_name": "",     "type": int,        "min": 0,       "max": INT_32_MAX,     "readonly": False,  "advanced": True    , "default": None },
        "build_types":                { "tip": "Bitmask build types",                "display_name": "",     "type": int,        "min": 0,       "max": INT_32_MAX,     "readonly": False,  "advanced": True    , "default": None },

        # Misc functional
        "req_precondition":           { "tip": "Precondition id (placeholder)",      "display_name": "",     "type": str,        "min": 0,       "max": None,           "readonly": False,  "advanced": True    , "default": None },
        "animation_flag":             { "tip": "Animation flag id",                  "display_name": "",     "type": int,        "min": 0,       "max": INT_32_MAX,     "readonly": False,  "advanced": True    , "default": None },
        "equip_effects":              { "tip": "Equip effects id",                   "display_name": "",     "type": int,        "min": 0,       "max": INT_32_MAX,     "readonly": False,  "advanced": True    , "default": None },
        "ready_for_qa":               { "tip": "Marked ready for QA",                "display_name": "",     "type": bool,       "min": None,    "max": None,           "readonly": False,  "advanced": True    , "default": None },
        "item_rating":                { "tip": "Item rating (placeholder)",          "display_name": "",     "type": int,        "min": 0,       "max": 10_000,         "readonly": False,  "advanced": True    , "default": None },
        "is_two_handed":              { "tip": "Requires two hands",                 "display_name": "",     "type": bool,       "min": None,    "max": None,           "readonly": False,  "advanced": False   , "default": None },
        "min_num_required":           { "tip": "Minimum number required",            "display_name": "",     "type": int,        "min": 0,       "max": INT_32_MAX,     "readonly": False,  "advanced": True    , "default": None },
        "del_res_index":              { "tip": "Delete resource index",              "display_name": "",     "type": int,        "min": 0,       "max": INT_32_MAX,     "readonly": False,  "advanced": True    , "default": None },
        "currency_lot":               { "tip": "Primary currency lot id",            "display_name": "",     "type": int,        "min": 0,       "max": INT_32_MAX,     "readonly": False,  "advanced": True    , "default": None },
        "alt_currency_cost":          { "tip": "Alternate currency cost",            "display_name": "",     "type": int,        "min": 0,       "max": INT_32_MAX,     "readonly": False,  "advanced": True    , "default": None },
        "sub_items":                  { "tip": "Sub items list (raw text)",          "display_name": "",     "type": str,        "min": None,    "max": None,           "readonly": False,  "advanced": True    , "default": None },
        "audio_event_use":            { "tip": "Audio event on use",                 "display_name": "",     "type": str,        "min": None,    "max": None,           "readonly": False,  "advanced": True    , "default": None },
        "no_equip_animation":         { "tip": "Skip equip animation",               "display_name": "",     "type": bool,       "min": None,    "max": None,           "readonly": False,  "advanced": True    , "default": None },
        "commendation_lot":           { "tip": "Commendation lot id",                "display_name": "",     "type": int,        "min": 0,       "max": INT_32_MAX,     "readonly": False,  "advanced": True    , "default": None },
        "commendation_cost":          { "tip": "Commendation cost",                  "display_name": "",     "type": int,        "min": 0,       "max": INT_32_MAX,     "readonly": False,  "advanced": True    , "default": None },
        "audio_equip_meta_event_set": { "tip": "Equip meta event set",               "display_name": "",     "type": str,        "min": None,    "max": None,           "readonly": False,  "advanced": True    , "default": None },
        "currency_costs":             { "tip": "Serialized currency costs",          "display_name": "",     "type": str,        "min": None,    "max": None,           "readonly": False,  "advanced": True    , "default": None },
        "ingredient_info":            { "tip": "Serialized ingredient info",         "display_name": "",     "type": str,        "min": None,    "max": None,           "readonly": False,  "advanced": True    , "default": None },
        "loc_status":                 { "tip": "Localization status code",           "display_name": "",     "type": int,        "min": 0,       "max": INT_32_MAX,     "readonly": False,  "advanced": True    , "default": None },
        "forge_type":                 { "tip": "Forge type id",                      "display_name": "",     "type": int,        "min": 0,       "max": INT_32_MAX,     "readonly": False,  "advanced": True    , "default": None },
        "sell_multiplier":            { "tip": "Sell price multiplier",              "display_name": "",     "type": float,      "min": 0.0,     "max": FLOAT_32_MAX,   "readonly": False,  "advanced": True    , "default": None },

        # Internal state
        "dirty":                      { "tip": "Internal dirty flag (not editable)", "display_name": "",     "type": bool,       "min": None,    "max": None,           "readonly": True,   "advanced": True    , "default": None },
    },

    # ---------------------------------------------------------------
    # RenderComponent visual representation metadata
    # ---------------------------------------------------------------
    "RenderComponent": {
        # Core identity
        "id":                          { "tip": "Primary key / component id",            "display_name": "",    "type": int,        "min": 1,        "max": INT_32_MAX,    "readonly": True,   "advanced": False , "default": None },

        # Assets
        "render_asset":                { "tip": "Path or identifier of render asset",    "display_name": "",    "type": str,        "min": None,     "max": None,          "readonly": False,  "advanced": False, "default": { "vendor": r"animations\minifig\mf_vendor.kfm", "mission": r"animations\minifig\mf_mission-givers.kfm" } },
        "icon_asset":                  { "tip": "Icon asset reference",                  "display_name": "",    "type": str,        "min": None,     "max": None,          "readonly": False,  "advanced": False , "default": None },
        "icon_id":                     { "tip": "Numeric icon id",                       "display_name": "",    "type": int,        "min": 0,        "max": INT_32_MAX,    "readonly": False,  "advanced": False, "lookup": "icons", "default": None },
        "shader_id":                   { "tip": "Shader identifier",                     "display_name": "",    "type": int,        "min": 0,        "max": INT_32_MAX,    "readonly": False,  "advanced": True  , "default": None },

        # Effects (optional int slots)
        "effect1":                     { "tip": "Effect slot 1 id",                      "display_name": "",    "type": int,        "min": 0,        "max": INT_32_MAX,    "readonly": False,  "advanced": True  , "default": None },
        "effect2":                     { "tip": "Effect slot 2 id",                      "display_name": "",    "type": int,        "min": 0,        "max": INT_32_MAX,    "readonly": False,  "advanced": True  , "default": None },
        "effect3":                     { "tip": "Effect slot 3 id",                      "display_name": "",    "type": int,        "min": 0,        "max": INT_32_MAX,    "readonly": False,  "advanced": True  , "default": None },
        "effect4":                     { "tip": "Effect slot 4 id",                      "display_name": "",    "type": int,        "min": 0,        "max": INT_32_MAX,    "readonly": False,  "advanced": True  , "default": None },
        "effect5":                     { "tip": "Effect slot 5 id",                      "display_name": "",    "type": int,        "min": 0,        "max": INT_32_MAX,    "readonly": False,  "advanced": True  , "default": None },
        "effect6":                     { "tip": "Effect slot 6 id",                      "display_name": "",    "type": int,        "min": 0,        "max": INT_32_MAX,    "readonly": False,  "advanced": True  , "default": None },
        "animation_group_ids":         { "tip": "Serialized animation group ids",        "display_name": "",    "type": str,        "min": None,     "max": None,          "readonly": False,  "advanced": True  , "default": None },

        # Booleans controlling rendering behavior
        "fade":                        { "tip": "Enable fade",                           "display_name": "",    "type": bool,       "min": None,     "max": None,          "readonly": False,  "advanced": False , "default": None },
        "use_drop_shadow":             { "tip": "Use drop shadow",                       "display_name": "",    "type": bool,       "min": None,     "max": None,          "readonly": False,  "advanced": False , "default": None },
        "preload_animations":          { "tip": "Preload animations",                    "display_name": "",    "type": bool,       "min": None,     "max": None,          "readonly": False,  "advanced": True  , "default": None },

        # Timing / distances
        "fade_in_time":                { "tip": "Fade in time (seconds)",                "display_name": "",    "type": float,      "min": 0.0,      "max": FLOAT_32_MAX,  "readonly": False,  "advanced": False , "default": None },
        "max_shadow_distance":         { "tip": "Max shadow distance",                   "display_name": "",    "type": float,      "min": 0.0,      "max": FLOAT_32_MAX,  "readonly": False,  "advanced": True  , "default": None },
        "ignore_camera_collision":     { "tip": "Ignore camera collision",               "display_name": "",    "type": bool,       "min": None,     "max": None,          "readonly": False,  "advanced": True  , "default": None },

        # LOD / snap
        "render_component_lod1":       { "tip": "LOD1 component id",                     "display_name": "",    "type": int,        "min": 0,        "max": INT_32_MAX,    "readonly": False,  "advanced": True  , "default": None },
        "render_component_lod2":       { "tip": "LOD2 component id",                     "display_name": "",    "type": int,        "min": 0,        "max": INT_32_MAX,    "readonly": False,  "advanced": True  , "default": None },
        "gradual_snap":                { "tip": "Enable gradual snap",                   "display_name": "",    "type": bool,       "min": None,     "max": None,          "readonly": False,  "advanced": True  , "default": None },

        # Animation / audio
        "animation_flag":              { "tip": "Animation flag id",                     "display_name": "",    "type": int,        "min": 0,        "max": INT_32_MAX,    "readonly": False,  "advanced": True  , "default": None },
        "audio_meta_event_set":        { "tip": "Audio meta event set",                  "display_name": "",    "type": str,        "min": None,     "max": None,          "readonly": False,  "advanced": True  , "default": None },

        # Billboard / UI
        "billboard_height":            { "tip": "Billboard height",                      "display_name": "",    "type": float,      "min": 0.0,      "max": FLOAT_32_MAX,  "readonly": False,  "advanced": True  , "default": None },
        "chat_bubble_offset":          { "tip": "Chat bubble vertical offset",           "display_name": "",    "type": float,      "min": 0.0,      "max": FLOAT_32_MAX,  "readonly": False,  "advanced": True  , "default": None },
        "static_billboard":            { "tip": "Static billboard",                      "display_name": "",    "type": bool,       "min": None,     "max": None,          "readonly": False,  "advanced": True  , "default": None },

        # Folders / misc
        "lxfml_folder":                { "tip": "LXFML folder path",                     "display_name": "",    "type": str,        "min": None,     "max": None,          "readonly": False,  "advanced": True  , "default": None },
        "attach_indicators_to_node":   { "tip": "Attach indicators to node",             "display_name": "",    "type": bool,       "min": None,     "max": None,          "readonly": False,  "advanced": True  , "default": None },

        # Internal state
        "dirty":                       { "tip": "Internal dirty flag (not editable)",    "display_name": "",    "type": bool,       "min": None,     "max": None,          "readonly": True,   "advanced": True  , "default": None },
    },

    # ---------------------------------------------------------------
    # MinifigComponent appearance metadata
    # ---------------------------------------------------------------
    "MinifigComponent": {
        "id":                          { "tip": "Primary key / component id",            "display_name": "",     "type": int,        "min": 1,         "max": INT_32_MAX,    "readonly": True,   "advanced": False , "default": None },
        "head":                        { "tip": "Head style id",                         "display_name": "",     "type": int,        "min": 0,         "max": INT_32_MAX,    "readonly": False,  "advanced": False, "default": 0  },
        "chest":                       { "tip": "Chest style id",                        "display_name": "",     "type": int,        "min": 0,         "max": INT_32_MAX,    "readonly": False,  "advanced": False, "default": 78 },
        "legs":                        { "tip": "Leg style id",                          "display_name": "",     "type": int,        "min": 0,         "max": INT_32_MAX,    "readonly": False,  "advanced": False, "default": 13 },
        "hairstyle":                   { "tip": "Hair style id",                         "display_name": "",     "type": int,        "min": 0,         "max": INT_32_MAX,    "readonly": False,  "advanced": False, "default": 2  },
        "haircolor":                   { "tip": "Hair color id",                         "display_name": "",     "type": int,        "min": 0,         "max": INT_32_MAX,    "readonly": False,  "advanced": False, "default": 9  },
        "chestdecal":                  { "tip": "Chest decal id",                        "display_name": "",     "type": int,        "min": 0,         "max": INT_32_MAX,    "readonly": False,  "advanced": False, "lookup": "minifig_torsos", "default": 33 },
        "headcolor":                   { "tip": "Head color id",                         "display_name": "",     "type": int,        "min": 0,         "max": INT_32_MAX,    "readonly": False,  "advanced": False, "default": 0  },
        "lefthand":                    { "tip": "Left hand item id",                     "display_name": "",     "type": int,        "min": 0,         "max": INT_32_MAX,    "readonly": False,  "advanced": False, "default": 0  },
        "righthand":                   { "tip": "Right hand item id",                    "display_name": "",     "type": int,        "min": 0,         "max": INT_32_MAX,    "readonly": False,  "advanced": False, "default": 0  },
        "eyebrowstyle":                { "tip": "Eyebrow style id",                      "display_name": "",     "type": int,        "min": 0,         "max": INT_32_MAX,    "readonly": False,  "advanced": False, "default": 4  },
        "eyesstyle":                   { "tip": "Eye style id",                          "display_name": "",     "type": int,        "min": 0,         "max": INT_32_MAX,    "readonly": False,  "advanced": False, "default": 12 },
        "mouthstyle":                  { "tip": "Mouth style id",                        "display_name": "",     "type": int,        "min": 0,         "max": INT_32_MAX,    "readonly": False,  "advanced": False, "default": 5  },
        "dirty":                       { "tip": "Internal dirty flag (not editable)",    "display_name": "",     "type": bool,       "min": None,      "max": None,          "readonly": True,   "advanced": True  , "default": None },
    },

    # ---------------------------------------------------------------
    # PhysicsComponent movement / collider metadata
    # ---------------------------------------------------------------
    "PhysicsComponent": {
        "id":                          { "tip": "Primary key / component id",            "display_name": "",     "type": int,        "min": 1,         "max": INT_32_MAX,    "readonly": True,   "advanced": False, "default": None },
            "static":                      { "tip": "Static physics flag / weight value",     "display_name": "",     "type": float,      "min": 0.0,       "max": FLOAT_32_MAX,  "readonly": False,  "advanced": False, "default": None },
            "physics_asset":               { "tip": "Physics asset path or identifier",       "display_name": "",     "type": str,        "min": None,      "max": None,          "readonly": False,  "advanced": False, "default": None },
            "jump":                        { "tip": "Jump strength",                          "display_name": "",     "type": float,      "min": 0.0,       "max": FLOAT_32_MAX,  "readonly": False,  "advanced": False, "default": None },
            "doublejump":                  { "tip": "Double-jump strength",                   "display_name": "",     "type": float,      "min": 0.0,       "max": FLOAT_32_MAX,  "readonly": False,  "advanced": False, "default": None },
            "speed":                       { "tip": "Movement speed",                         "display_name": "",     "type": float,      "min": 0.0,       "max": FLOAT_32_MAX,  "readonly": False,  "advanced": False, "default": 5 },
            "rot_speed":                   { "tip": "Rotation speed",                         "display_name": "",     "type": float,      "min": 0.0,       "max": FLOAT_32_MAX,  "readonly": False,  "advanced": True,  "default": 360 },
            "player_height":               { "tip": "Player collider height",                 "display_name": "",     "type": float,      "min": 0.0,       "max": FLOAT_32_MAX,  "readonly": False,  "advanced": False, "default": 4.400000095367432 },
            "player_radius":               { "tip": "Player collider radius",                 "display_name": "",     "type": float,      "min": 0.0,       "max": FLOAT_32_MAX,  "readonly": False,  "advanced": False, "default": 1.0 },
            "pc_shape_type":               { "tip": "Physics collider shape type",            "display_name": "",     "type": int,        "min": 0,         "max": INT_32_MAX,    "readonly": False,  "advanced": True,  "default": 2 },
            "collision_group":             { "tip": "Collision group id",                     "display_name": "",     "type": int,        "min": 0,         "max": INT_32_MAX,    "readonly": False,  "advanced": True,  "default": 3 },
            "air_speed":                   { "tip": "Movement speed while airborne",          "display_name": "",     "type": float,      "min": 0.0,       "max": FLOAT_32_MAX,  "readonly": False,  "advanced": True,  "default": 5.0 },
            "boundary_asset":              { "tip": "Boundary asset path or identifier",      "display_name": "",     "type": str,        "min": None,      "max": None,          "readonly": False,  "advanced": True,  "default": None },
            "jump_air_speed":              { "tip": "Air speed applied during jumps",         "display_name": "",     "type": float,      "min": 0.0,       "max": FLOAT_32_MAX,  "readonly": False,  "advanced": True,  "default": None },
            "friction":                    { "tip": "Surface friction value",                 "display_name": "",     "type": float,      "min": 0.0,       "max": FLOAT_32_MAX,  "readonly": False,  "advanced": True,  "default": None },
            "gravity_volume_asset":        { "tip": "Gravity volume asset reference",         "display_name": "",     "type": str,        "min": None,      "max": None,          "readonly": False,  "advanced": True,  "default": None },
            "dirty":                       { "tip": "Internal dirty flag (not editable)",     "display_name": "",     "type": bool,       "min": None,      "max": None,          "readonly": True,   "advanced": True,  "default": None },
    },

    # ---------------------------------------------------------------
    # DestructibleComponent combat / loot metadata
    # ---------------------------------------------------------------
    "DestructibleComponent": {
        "id":                          { "tip": "Primary key / component id",            "display_name": "",     "type": int,        "min": 1,         "max": INT_32_MAX,    "readonly": True,   "advanced": False, "default": None },
    },

    # ---------------------------------------------------------------
    # VendorComponent vendor behavior metadata
    # ---------------------------------------------------------------
    "VendorComponent": {
        "id":                          { "tip": "Primary key / component id",            "display_name": "",     "type": int,        "min": 1,         "max": INT_32_MAX,    "readonly": True,   "advanced": False, "default": None },
    },

    # ---------------------------------------------------------------
    # ScriptComponent script binding metadata
    # ---------------------------------------------------------------
    "ScriptComponent": {
        "id":                          { "tip": "Primary key / component id",            "display_name": "",     "type": int,        "min": 1,         "max": INT_32_MAX,    "readonly": True,   "advanced": False, "default": None },
    },

    # ---------------------------------------------------------------
    # GameObject (base object / template level metadata)
    # ---------------------------------------------------------------
    "GameObject": {
        "object_id":              { "tip": "Primary object / template id",              "display_name": "",     "type": int,        "min": 1,         "max": INT_32_MAX,    "readonly": True,   "advanced": False , "default": None },
        "name":                   { "tip": "Internal name",                             "display_name": "",     "type": str,        "min": None,      "max": None,          "readonly": False,  "advanced": False , "default": None },
        "placeable":              { "tip": "Can be placed in world",                    "display_name": "",     "type": bool,       "min": None,      "max": None,          "readonly": False,  "advanced": False,  "default": True  },
        "type":                   { "tip": "High-level object type enum",               "display_name": "",     "type": str,        "min": None,      "max": None,          "readonly": True,   "advanced": False , "default": None },
        "description":            { "tip": "Player-facing description",                 "display_name": "",     "type": str,        "min": None,      "max": None,          "readonly": False,  "advanced": False , "default": None },
        "localize":               { "tip": "Should be localized",                       "display_name": "",     "type": bool,       "min": None,      "max": None,          "readonly": False,  "advanced": True  , "default": None },
        "npc_template_id":        { "tip": "Associated NPC template id",                "display_name": "",     "type": int,        "min": 0,         "max": INT_32_MAX,    "readonly": False,  "advanced": True  , "default": None },
        "display_name":           { "tip": "Localized / display name",                  "display_name": "",     "type": str,        "min": None,      "max": None,          "readonly": False,  "advanced": False , "default": None },
        "interaction_distance":   { "tip": "Interaction distance (meters)",             "display_name": "",     "type": float,      "min": 0.0,       "max": FLOAT_32_MAX,  "readonly": False,  "advanced": True  , "default": None },
        "nametag":                { "tip": "Show name tag?",                            "display_name": "",     "type": bool,       "min": None,      "max": None,          "readonly": False,  "advanced": True,   "default": True  },
        "internal_notes":         { "tip": "Developer / internal notes",                "display_name": "",     "type": str,        "min": None,      "max": None,          "readonly": False,  "advanced": True  , "default": None },
        "loc_status":             { "tip": "Localization status code",                  "display_name": "",     "type": int,        "min": 0,         "max": INT_32_MAX,    "readonly": False,  "advanced": True  , "default": None },
        "gate_version":           { "tip": "Gate / version gating string",              "display_name": "",     "type": str,        "min": None,      "max": None,          "readonly": False,  "advanced": True  , "default": None },
        "hq_valid":               { "tip": "Valid for HQ?",                             "display_name": "",     "type": bool,       "min": None,      "max": None,          "readonly": False,  "advanced": True,   "default": False },

        # Internal
        "dirty":                  { "tip": "Internal dirty flag (not editable)",        "display_name": "",     "type": bool,       "min": None,      "max": None,          "readonly": True,   "advanced": True  , "default": None },
        "components":             { "tip": "Component mapping (managed internally)",    "display_name": "",     "type": dict,       "min": None,      "max": None,          "readonly": True,   "advanced": True  , "default": None },
    },

    # ---------------------------------------------------------------
    # Skill component metadata
    # ---------------------------------------------------------------
    "ObjectSkillRow": {
        "object_Template":        { "tip": "Parent object id",                        "display_name": "", "type": int,   "min": 1,    "max": INT_32_MAX, "readonly": True,  "advanced": True  , "default": None },
        "skill_id":               { "tip": "Skill behavior id",                       "display_name": "", "type": int,   "min": 1,    "max": INT_32_MAX, "readonly": False, "advanced": False , "default": None },
        "cast_on_type":           { "tip": "Cast on type flag",                       "display_name": "", "type": int,   "min": 0,    "max": INT_32_MAX, "readonly": False, "advanced": True  , "default": None },
        "ai_combat_weight":       { "tip": "AI combat weight / priority",             "display_name": "", "type": int,   "min": 0,    "max": INT_32_MAX, "readonly": False, "advanced": True  , "default": None },
        "dirty":                  { "tip": "Internal dirty flag (not editable)",      "display_name": "", "type": bool,  "min": None, "max": None,       "readonly": True,  "advanced": True  , "default": None },
    },

    # ---------------------------------------------------------------
    # Inventory row metadata
    # ---------------------------------------------------------------
    "InventoryComponentRow": {
        "id":                    { "tip": "Parent component id",                      "display_name": "", "type": int,   "min": 1,    "max": INT_32_MAX, "readonly": True,  "advanced": True,  "default": None },
        "itemid":                { "tip": "Item LOT id",                              "display_name": "", "type": int,   "min": 1,    "max": INT_32_MAX, "readonly": False, "advanced": False, "default": None },
        "count":                 { "tip": "Item count",                               "display_name": "", "type": int,   "min": 0,    "max": INT_32_MAX, "readonly": False, "advanced": False, "default": 1 },
        "equip":                 { "tip": "Equipped by default",                      "display_name": "", "type": bool,  "min": None, "max": None,       "readonly": False, "advanced": True,  "default": False },
        "dirty":                 { "tip": "Internal dirty flag (not editable)",       "display_name": "", "type": bool,  "min": None, "max": None,       "readonly": True,  "advanced": True,  "default": None },
    },

    # ---------------------------------------------------------------
    # Mission NPC row metadata
    # ---------------------------------------------------------------
    "MissionNPCComponentRow": {
        "id":                    { "tip": "Parent component id",                      "display_name": "", "type": int,   "min": 1,    "max": INT_32_MAX, "readonly": True,  "advanced": True,  "default": None },
        "mission_id":            { "tip": "Mission id",                               "display_name": "", "type": int,   "min": 1,    "max": INT_32_MAX, "readonly": False, "advanced": False, "default": None },
        "offers_mission":        { "tip": "NPC can offer mission",                    "display_name": "", "type": bool,  "min": None, "max": None,       "readonly": False, "advanced": False, "default": True },
        "accepts_mission":       { "tip": "NPC can accept turn-in",                   "display_name": "", "type": bool,  "min": None, "max": None,       "readonly": False, "advanced": False, "default": True },
        "gate_version":          { "tip": "Version gate string",                      "display_name": "", "type": str,   "min": None, "max": None,       "readonly": False, "advanced": True,  "default": None },
        "dirty":                 { "tip": "Internal dirty flag (not editable)",       "display_name": "", "type": bool,  "min": None, "max": None,       "readonly": True,  "advanced": True,  "default": None },
    },

    # ---------------------------------------------------------------
    # LootMatrix row metadata
    # ---------------------------------------------------------------
    "LootMatrixRow": {
        "row_id":                { "tip": "SQLite row id",                            "display_name": "", "type": int,   "min": None, "max": INT_32_MAX, "readonly": True,  "advanced": False, "default": None },
        "loot_matrix_index":     { "tip": "Loot matrix index",                        "display_name": "", "type": int,   "min": 0,    "max": INT_32_MAX, "readonly": False, "advanced": False, "default": 0 },
        "loot_table_index":      { "tip": "Loot table index",                         "display_name": "", "type": int,   "min": 0,    "max": INT_32_MAX, "readonly": False, "advanced": False, "default": 0 },
        "rarity_table_index":    { "tip": "Rarity table index",                       "display_name": "", "type": int,   "min": 0,    "max": INT_32_MAX, "readonly": False, "advanced": True,  "default": 1 },
        "percent":               { "tip": "Drop chance percentage",                    "display_name": "", "type": float, "min": 0.0,  "max": FLOAT_32_MAX, "readonly": False, "advanced": False, "default": 1.0 },
        "min_to_drop":           { "tip": "Minimum items to drop",                    "display_name": "", "type": int,   "min": 0,    "max": INT_32_MAX, "readonly": False, "advanced": False, "default": 0 },
        "max_to_drop":           { "tip": "Maximum items to drop",                    "display_name": "", "type": int,   "min": 0,    "max": INT_32_MAX, "readonly": False, "advanced": False, "default": 1 },
        "id":                    { "tip": "Associated object id",                      "display_name": "", "type": int,   "min": 0,    "max": INT_32_MAX, "readonly": False, "advanced": True,  "default": None },
        "flag_id":               { "tip": "Required flag id",                         "display_name": "", "type": int,   "min": 0,    "max": INT_32_MAX, "readonly": False, "advanced": True,  "default": None },
        "gate_version":          { "tip": "Version gate string",                      "display_name": "", "type": str,   "min": None, "max": None,       "readonly": False, "advanced": True,  "default": None },
        "dirty":                 { "tip": "Internal dirty flag (not editable)",       "display_name": "", "type": bool,  "min": None, "max": None,       "readonly": True,  "advanced": True,  "default": None },
    },

    # ---------------------------------------------------------------
    # Mission row metadata
    # ---------------------------------------------------------------
    "MissionRow": {
        "id":                    { "tip": "Mission id",                               "display_name": "", "type": int,   "min": 1,    "max": INT_32_MAX, "readonly": True,  "advanced": False, "default": None },
        "defined_type":          { "tip": "Defined mission type",                     "display_name": "", "type": str,   "min": None, "max": None,       "readonly": False, "advanced": True,  "default": None },
        "defined_subtype":       { "tip": "Defined mission subtype",                  "display_name": "", "type": str,   "min": None, "max": None,       "readonly": False, "advanced": True,  "default": None },
        "ui_sort_order":         { "tip": "UI sort order",                            "display_name": "", "type": int,   "min": 0,    "max": INT_32_MAX, "readonly": False, "advanced": True,  "default": None },
        "offer_object_id":       { "tip": "Mission offer object id",                  "display_name": "", "type": int,   "min": 0,    "max": INT_32_MAX, "readonly": False, "advanced": True,  "default": None },
        "target_object_id":      { "tip": "Mission target object id",                 "display_name": "", "type": int,   "min": 0,    "max": INT_32_MAX, "readonly": False, "advanced": True,  "default": None },
        "reward_currency":       { "tip": "Reward currency amount",                   "display_name": "", "type": int,   "min": 0,    "max": INT_32_MAX, "readonly": False, "advanced": False, "default": None },
        "lego_score":            { "tip": "LEGO score reward",                        "display_name": "", "type": int,   "min": 0,    "max": INT_32_MAX, "readonly": False, "advanced": False, "default": None },
        "reward_reputation":     { "tip": "Reputation reward",                        "display_name": "", "type": int,   "min": 0,    "max": INT_32_MAX, "readonly": False, "advanced": False, "default": None },
        "is_choice_reward":      { "tip": "Choose one reward item",                   "display_name": "", "type": bool,  "min": None, "max": None,       "readonly": False, "advanced": True,  "default": False },
        "reward_item1":          { "tip": "Primary reward item LOT",                  "display_name": "", "type": int,   "min": -1,   "max": INT_32_MAX, "readonly": False, "advanced": False, "default": -1 },
        "reward_item1_count":    { "tip": "Primary reward item count",                "display_name": "", "type": int,   "min": 0,    "max": INT_32_MAX, "readonly": False, "advanced": False, "default": 1 },
        "reward_item2":          { "tip": "Secondary reward item LOT",                "display_name": "", "type": int,   "min": -1,   "max": INT_32_MAX, "readonly": False, "advanced": False, "default": -1 },
        "reward_item2_count":    { "tip": "Secondary reward item count",              "display_name": "", "type": int,   "min": 0,    "max": INT_32_MAX, "readonly": False, "advanced": False, "default": 1 },
        "reward_item3":          { "tip": "Tertiary reward item LOT",                 "display_name": "", "type": int,   "min": -1,   "max": INT_32_MAX, "readonly": False, "advanced": True,  "default": -1 },
        "reward_item3_count":    { "tip": "Tertiary reward item count",               "display_name": "", "type": int,   "min": 0,    "max": INT_32_MAX, "readonly": False, "advanced": True,  "default": 1 },
        "reward_item4":          { "tip": "Quaternary reward item LOT",               "display_name": "", "type": int,   "min": -1,   "max": INT_32_MAX, "readonly": False, "advanced": True,  "default": -1 },
        "reward_item4_count":    { "tip": "Quaternary reward item count",             "display_name": "", "type": int,   "min": 0,    "max": INT_32_MAX, "readonly": False, "advanced": True,  "default": 1 },
        "reward_emote":          { "tip": "Primary reward emote id",                  "display_name": "", "type": int,   "min": -1,   "max": INT_32_MAX, "readonly": False, "advanced": True,  "default": -1 },
        "reward_emote2":         { "tip": "Secondary reward emote id",                "display_name": "", "type": int,   "min": -1,   "max": INT_32_MAX, "readonly": False, "advanced": True,  "default": -1 },
        "reward_emote3":         { "tip": "Tertiary reward emote id",                 "display_name": "", "type": int,   "min": -1,   "max": INT_32_MAX, "readonly": False, "advanced": True,  "default": -1 },
        "reward_emote4":         { "tip": "Quaternary reward emote id",               "display_name": "", "type": int,   "min": -1,   "max": INT_32_MAX, "readonly": False, "advanced": True,  "default": -1 },
        "reward_max_imagination": { "tip": "Max imagination reward",                  "display_name": "", "type": int,   "min": 0,    "max": INT_32_MAX, "readonly": False, "advanced": True,  "default": 0 },
        "reward_max_health":     { "tip": "Max health reward",                        "display_name": "", "type": int,   "min": 0,    "max": INT_32_MAX, "readonly": False, "advanced": True,  "default": 0 },
        "reward_max_inventory":  { "tip": "Max inventory reward",                     "display_name": "", "type": int,   "min": 0,    "max": INT_32_MAX, "readonly": False, "advanced": True,  "default": None },
        "reward_max_model":      { "tip": "Max model reward",                         "display_name": "", "type": int,   "min": 0,    "max": INT_32_MAX, "readonly": False, "advanced": True,  "default": None },
        "reward_max_widget":     { "tip": "Max widget reward",                        "display_name": "", "type": int,   "min": 0,    "max": INT_32_MAX, "readonly": False, "advanced": True,  "default": None },
        "reward_max_wallet":     { "tip": "Max wallet reward",                        "display_name": "", "type": int,   "min": 0,    "max": INT_32_MAX, "readonly": False, "advanced": True,  "default": None },
        "repeatable":            { "tip": "Mission is repeatable",                    "display_name": "", "type": bool,  "min": None, "max": None,       "readonly": False, "advanced": False, "default": False },
        "reward_currency_repeatable": { "tip": "Repeatable currency reward",          "display_name": "", "type": int,   "min": 0,    "max": INT_32_MAX, "readonly": False, "advanced": True,  "default": None },
        "reward_item1_repeatable": { "tip": "Repeatable reward item 1 LOT",           "display_name": "", "type": int,   "min": -1,   "max": INT_32_MAX, "readonly": False, "advanced": True,  "default": -1 },
        "reward_item1_repeat_count": { "tip": "Repeatable reward item 1 count",       "display_name": "", "type": int,   "min": 0,    "max": INT_32_MAX, "readonly": False, "advanced": True,  "default": 1 },
        "reward_item2_repeatable": { "tip": "Repeatable reward item 2 LOT",           "display_name": "", "type": int,   "min": -1,   "max": INT_32_MAX, "readonly": False, "advanced": True,  "default": -1 },
        "reward_item2_repeat_count": { "tip": "Repeatable reward item 2 count",       "display_name": "", "type": int,   "min": 0,    "max": INT_32_MAX, "readonly": False, "advanced": True,  "default": 1 },
        "reward_item3_repeatable": { "tip": "Repeatable reward item 3 LOT",           "display_name": "", "type": int,   "min": -1,   "max": INT_32_MAX, "readonly": False, "advanced": True,  "default": -1 },
        "reward_item3_repeat_count": { "tip": "Repeatable reward item 3 count",       "display_name": "", "type": int,   "min": 0,    "max": INT_32_MAX, "readonly": False, "advanced": True,  "default": 1 },
        "reward_item4_repeatable": { "tip": "Repeatable reward item 4 LOT",           "display_name": "", "type": int,   "min": -1,   "max": INT_32_MAX, "readonly": False, "advanced": True,  "default": -1 },
        "reward_item4_repeat_count": { "tip": "Repeatable reward item 4 count",       "display_name": "", "type": int,   "min": 0,    "max": INT_32_MAX, "readonly": False, "advanced": True,  "default": 1 },
        "time_limit":            { "tip": "Mission time limit",                        "display_name": "", "type": int,   "min": 0,    "max": INT_32_MAX, "readonly": False, "advanced": True,  "default": None },
        "is_mission":            { "tip": "Is mission (vs achievement)",              "display_name": "", "type": bool,  "min": None, "max": None,       "readonly": False, "advanced": True,  "default": True },
        "mission_icon_id":       { "tip": "Mission icon id",                          "display_name": "", "type": int,   "min": 0,    "max": INT_32_MAX, "readonly": False, "advanced": False, "lookup": "icons", "default": None },
        "prereq_mission_id":     { "tip": "Prerequisite mission ids",                  "display_name": "", "type": str,   "min": None, "max": None,       "readonly": False, "advanced": True,  "default": None },
        "localize":              { "tip": "Use localized text",                        "display_name": "", "type": bool,  "min": None, "max": None,       "readonly": False, "advanced": True,  "default": True },
        "in_motd":               { "tip": "Show in MOTD",                              "display_name": "", "type": bool,  "min": None, "max": None,       "readonly": False, "advanced": True,  "default": False },
        "cooldown_time":         { "tip": "Cooldown time in seconds",                  "display_name": "", "type": int,   "min": 0,    "max": INT_32_MAX, "readonly": False, "advanced": True,  "default": None },
        "is_random":             { "tip": "Randomized mission",                        "display_name": "", "type": bool,  "min": None, "max": None,       "readonly": False, "advanced": True,  "default": False },
        "random_pool":           { "tip": "Random mission pool",                       "display_name": "", "type": str,   "min": None, "max": None,       "readonly": False, "advanced": True,  "default": None },
        "ui_prereq_id":          { "tip": "UI prerequisite mission id",                "display_name": "", "type": int,   "min": 0,    "max": INT_32_MAX, "readonly": False, "advanced": True,  "default": None },
        "gate_version":          { "tip": "Version gate string",                       "display_name": "", "type": str,   "min": None, "max": None,       "readonly": False, "advanced": True,  "default": None },
        "hud_states":            { "tip": "HUD state overrides",                       "display_name": "", "type": str,   "min": None, "max": None,       "readonly": False, "advanced": True,  "default": None },
        "loc_status":            { "tip": "Localization status",                       "display_name": "", "type": int,   "min": 0,    "max": INT_32_MAX, "readonly": False, "advanced": True,  "default": 0 },
        "reward_bank_inventory": { "tip": "Bank inventory reward",                     "display_name": "", "type": int,   "min": 0,    "max": INT_32_MAX, "readonly": False, "advanced": True,  "default": None },
        "dirty":                 { "tip": "Internal dirty flag (not editable)",        "display_name": "", "type": bool,  "min": None, "max": None,       "readonly": True,  "advanced": True,  "default": None },
    },

    # ---------------------------------------------------------------
    # Mission task row metadata
    # ---------------------------------------------------------------
    "MissionTaskRow": {
        "id":                    { "tip": "Mission id",                               "display_name": "", "type": int,   "min": 1,    "max": INT_32_MAX, "readonly": True,  "advanced": False, "default": None },
        "loc_status":            { "tip": "Localization status",                       "display_name": "", "type": int,   "min": 0,    "max": INT_32_MAX, "readonly": False, "advanced": True,  "default": 0 },
        "task_type":             { "tip": "Task type enum",                            "display_name": "", "type": int,   "min": 0,    "max": INT_32_MAX, "readonly": False, "advanced": False, "default": None },
        "target":                { "tip": "Task target id",                            "display_name": "", "type": int,   "min": 0,    "max": INT_32_MAX, "readonly": False, "advanced": False, "default": None },
        "target_group":          { "tip": "Task target group",                         "display_name": "", "type": str,   "min": None, "max": None,       "readonly": False, "advanced": True,  "default": None },
        "target_value":          { "tip": "Task target value",                         "display_name": "", "type": int,   "min": 0,    "max": INT_32_MAX, "readonly": False, "advanced": False, "default": None },
        "task_param1":           { "tip": "Task parameter 1",                          "display_name": "", "type": str,   "min": None, "max": None,       "readonly": False, "advanced": True,  "default": None },
        "large_task_icon":       { "tip": "Large task icon asset",                     "display_name": "", "type": str,   "min": None, "max": None,       "readonly": False, "advanced": True,  "default": None },
        "icon_id":               { "tip": "Task icon id",                             "display_name": "", "type": int,   "min": 0,    "max": INT_32_MAX, "readonly": False, "advanced": False, "lookup": "icons", "default": None },
        "uid":                   { "tip": "Task unique id",                            "display_name": "", "type": int,   "min": 1,    "max": INT_32_MAX, "readonly": True,  "advanced": False, "default": None },
        "large_task_icon_id":    { "tip": "Large task icon id",                       "display_name": "", "type": int,   "min": 0,    "max": INT_32_MAX, "readonly": False, "advanced": False, "lookup": "icons", "default": None },
        "localize":              { "tip": "Use localized text",                        "display_name": "", "type": bool,  "min": None, "max": None,       "readonly": False, "advanced": True,  "default": True },
        "gate_version":          { "tip": "Version gate string",                       "display_name": "", "type": str,   "min": None, "max": None,       "readonly": False, "advanced": True,  "default": None },
        "dirty":                 { "tip": "Internal dirty flag (not editable)",        "display_name": "", "type": bool,  "min": None, "max": None,       "readonly": True,  "advanced": True,  "default": None },
    },

    # ---------------------------------------------------------------
    # Mission text row metadata
    # ---------------------------------------------------------------
    "MissionTextRow": {
        "id":                    { "tip": "Mission id",                               "display_name": "", "type": int,   "min": 1,    "max": INT_32_MAX, "readonly": True,  "advanced": False, "default": None },
        "story_icon":            { "tip": "Story icon asset",                          "display_name": "", "type": str,   "min": None, "max": None,       "readonly": False, "advanced": True,  "default": None },
        "mission_icon":          { "tip": "Mission icon asset",                        "display_name": "", "type": str,   "min": None, "max": None,       "readonly": False, "advanced": True,  "default": None },
        "offer_npc_icon":        { "tip": "Offer NPC icon asset",                      "display_name": "", "type": str,   "min": None, "max": None,       "readonly": False, "advanced": True,  "default": None },
        "icon_id":               { "tip": "Mission text icon id",                     "display_name": "", "type": int,   "min": 0,    "max": INT_32_MAX, "readonly": False, "advanced": False, "lookup": "icons", "default": None },
        "state_1_anim":          { "tip": "State 1 animation",                         "display_name": "", "type": str,   "min": None, "max": None,       "readonly": False, "advanced": True,  "default": None },
        "state_2_anim":          { "tip": "State 2 animation",                         "display_name": "", "type": str,   "min": None, "max": None,       "readonly": False, "advanced": True,  "default": None },
        "state_3_anim":          { "tip": "State 3 animation",                         "display_name": "", "type": str,   "min": None, "max": None,       "readonly": False, "advanced": True,  "default": None },
        "state_4_anim":          { "tip": "State 4 animation",                         "display_name": "", "type": str,   "min": None, "max": None,       "readonly": False, "advanced": True,  "default": None },
        "state_3_turnin_anim":   { "tip": "State 3 turn-in animation",                 "display_name": "", "type": str,   "min": None, "max": None,       "readonly": False, "advanced": True,  "default": None },
        "state_4_turnin_anim":   { "tip": "State 4 turn-in animation",                 "display_name": "", "type": str,   "min": None, "max": None,       "readonly": False, "advanced": True,  "default": None },
        "onclick_anim":          { "tip": "On-click animation",                         "display_name": "", "type": str,   "min": None, "max": None,       "readonly": False, "advanced": True,  "default": None },
        "cinematic_accepted":    { "tip": "Accepted cinematic",                         "display_name": "", "type": str,   "min": None, "max": None,       "readonly": False, "advanced": True,  "default": None },
        "cinematic_accepted_leadin": { "tip": "Accepted cinematic lead-in",             "display_name": "", "type": float, "min": 0.0,  "max": FLOAT_32_MAX, "readonly": False, "advanced": True,  "default": None },
        "cinematic_completed":   { "tip": "Completed cinematic",                        "display_name": "", "type": str,   "min": None, "max": None,       "readonly": False, "advanced": True,  "default": None },
        "cinematic_completed_leadin": { "tip": "Completed cinematic lead-in",           "display_name": "", "type": float, "min": 0.0,  "max": FLOAT_32_MAX, "readonly": False, "advanced": True,  "default": None },
        "cinematic_repeatable":  { "tip": "Repeatable cinematic",                       "display_name": "", "type": str,   "min": None, "max": None,       "readonly": False, "advanced": True,  "default": None },
        "cinematic_repeatable_leadin": { "tip": "Repeatable cinematic lead-in",         "display_name": "", "type": float, "min": 0.0,  "max": FLOAT_32_MAX, "readonly": False, "advanced": True,  "default": None },
        "cinematic_repeatable_completed": { "tip": "Repeatable completed cinematic",    "display_name": "", "type": str,   "min": None, "max": None,       "readonly": False, "advanced": True,  "default": None },
        "cinematic_repeatable_completed_leadin": { "tip": "Repeatable completed lead-in", "display_name": "", "type": float, "min": 0.0,  "max": FLOAT_32_MAX, "readonly": False, "advanced": True,  "default": None },
        "audio_event_guid_interact": { "tip": "Interact audio event GUID",             "display_name": "", "type": str,   "min": None, "max": None,       "readonly": False, "advanced": True,  "default": None },
        "audio_event_guid_offer_accept": { "tip": "Offer accept audio event GUID",     "display_name": "", "type": str,   "min": None, "max": None,       "readonly": False, "advanced": True,  "default": None },
        "audio_event_guid_offer_deny": { "tip": "Offer deny audio event GUID",         "display_name": "", "type": str,   "min": None, "max": None,       "readonly": False, "advanced": True,  "default": None },
        "audio_event_guid_completed": { "tip": "Completed audio event GUID",           "display_name": "", "type": str,   "min": None, "max": None,       "readonly": False, "advanced": True,  "default": None },
        "audio_event_guid_turn_in": { "tip": "Turn-in audio event GUID",               "display_name": "", "type": str,   "min": None, "max": None,       "readonly": False, "advanced": True,  "default": None },
        "audio_event_guid_failed":  { "tip": "Failed audio event GUID",                "display_name": "", "type": str,   "min": None, "max": None,       "readonly": False, "advanced": True,  "default": None },
        "audio_event_guid_progress": { "tip": "Progress audio event GUID",             "display_name": "", "type": str,   "min": None, "max": None,       "readonly": False, "advanced": True,  "default": None },
        "audio_music_cue_offer_accept": { "tip": "Offer accept music cue",             "display_name": "", "type": str,   "min": None, "max": None,       "readonly": False, "advanced": True,  "default": None },
        "audio_music_cue_turn_in": { "tip": "Turn-in music cue",                       "display_name": "", "type": str,   "min": None, "max": None,       "readonly": False, "advanced": True,  "default": None },
        "turn_in_icon_id":       { "tip": "Turn-in icon id",                          "display_name": "", "type": int,   "min": 0,    "max": INT_32_MAX, "readonly": False, "advanced": False, "lookup": "icons", "default": None },
        "localize":              { "tip": "Use localized text",                        "display_name": "", "type": bool,  "min": None, "max": None,       "readonly": False, "advanced": True,  "default": True },
        "loc_status":            { "tip": "Localization status",                       "display_name": "", "type": int,   "min": 0,    "max": INT_32_MAX, "readonly": False, "advanced": True,  "default": 0 },
        "gate_version":          { "tip": "Version gate string",                       "display_name": "", "type": str,   "min": None, "max": None,       "readonly": False, "advanced": True,  "default": None },
        "dirty":                 { "tip": "Internal dirty flag (not editable)",        "display_name": "", "type": bool,  "min": None, "max": None,       "readonly": True,  "advanced": True,  "default": None },
    },

    # ---------------------------------------------------------------
    # Mission email row metadata
    # ---------------------------------------------------------------
    "MissionEmailRow": {
        "id":                    { "tip": "Mission id",                               "display_name": "", "type": int,   "min": 1,    "max": INT_32_MAX, "readonly": True,  "advanced": False, "default": None },
        "message_type":          { "tip": "Mission email message type",               "display_name": "", "type": int,   "min": 0,    "max": INT_32_MAX, "readonly": False, "advanced": True,  "default": 0 },
        "notification_group":    { "tip": "Mission email notification group",         "display_name": "", "type": int,   "min": 0,    "max": INT_32_MAX, "readonly": False, "advanced": True,  "default": 0 },
        "mission_id":            { "tip": "Linked mission id",                        "display_name": "", "type": int,   "min": 1,    "max": INT_32_MAX, "readonly": False, "advanced": False, "default": None },
        "attachment_lot":        { "tip": "Attachment item LOT",                      "display_name": "", "type": int,   "min": 0,    "max": INT_32_MAX, "readonly": False, "advanced": True,  "default": None },
        "localize":              { "tip": "Use localized text",                        "display_name": "", "type": bool,  "min": None, "max": None,       "readonly": False, "advanced": True,  "default": True },
        "loc_status":            { "tip": "Localization status",                       "display_name": "", "type": int,   "min": 0,    "max": INT_32_MAX, "readonly": False, "advanced": True,  "default": 0 },
        "gate_version":          { "tip": "Version gate string",                       "display_name": "", "type": str,   "min": None, "max": None,       "readonly": False, "advanced": True,  "default": None },
        "dirty":                 { "tip": "Internal dirty flag (not editable)",        "display_name": "", "type": bool,  "min": None, "max": None,       "readonly": True,  "advanced": True,  "default": None },
    },
}

