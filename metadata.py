INT_32_MAX = 2_147_483_647
FLOAT_32_MAX = 3.4028235e+38

component_field_metadata = {
    # ---------------------------------------------------------------
    # ItemComponent metadata
    # ---------------------------------------------------------------
    "ItemComponent": {
        # Core identity / primary
        "id":                         { "tip": "Primary key / component id",         "display_name": "",     "type": int,        "min": 1,       "max": INT_32_MAX,     "readonly": True,   "advanced": False   },

        # Basic classification / value
        "equip_location":             { "tip": "Where this item is equipped",        "display_name": "",     "type": str,        "min": None,    "max": None,           "readonly": False,  "advanced": False   },
        "base_value":                 { "tip": "Base vendor value (placeholder)",    "display_name": "",     "type": int,        "min": 0,       "max": INT_32_MAX,     "readonly": False,  "advanced": False   },
        "is_kit_piece":               { "tip": "Part of a kit?",                     "display_name": "",     "type": bool,       "min": None,    "max": None,           "readonly": False,  "advanced": False   },
        "rarity":                     { "tip": "Rarity tier (placeholder)",          "display_name": "",     "type": int,        "min": 0,       "max": 10,             "readonly": False,  "advanced": False   },
        "item_type":                  { "tip": "Item type",                          "display_name": "",     "type": int,        "min": None,    "max": None,           "readonly": False,  "advanced": False   },
        "item_info":                  { "tip": "Opaque item info id",                "display_name": "",     "type": int,        "min": 0,       "max": INT_32_MAX,     "readonly": False,  "advanced": True    },

        # Availability flags
        "in_loot_table":              { "tip": "Appears in loot tables",             "display_name": "",     "type": bool,       "min": None,    "max": None,           "readonly": False,  "advanced": False   },
        "in_vendor":                  { "tip": "Sold by vendors",                    "display_name": "",     "type": bool,       "min": None,    "max": None,           "readonly": False,  "advanced": False   },
        "is_unique":                  { "tip": "Unique (one per player)",            "display_name": "",     "type": bool,       "min": None,    "max": None,           "readonly": False,  "advanced": False   },
        "is_bop":                     { "tip": "Bind on pickup",                     "display_name": "",     "type": bool,       "min": None,    "max": None,           "readonly": False,  "advanced": False   },
        "is_boe":                     { "tip": "Bind on equip",                      "display_name": "",     "type": bool,       "min": None,    "max": None,           "readonly": False,  "advanced": False   },

        # Requirements
        "req_flag_id":                { "tip": "Required flag id (placeholder)",     "display_name": "",     "type": int,        "min": 0,       "max": INT_32_MAX,     "readonly": False,  "advanced": True    },
        "req_specialty_id":           { "tip": "Required specialty id",              "display_name": "",     "type": int,        "min": 0,       "max": INT_32_MAX,     "readonly": False,  "advanced": True    },
        "req_spec_rank":              { "tip": "Required specialty rank",            "display_name": "",     "type": int,        "min": 0,       "max": 100,            "readonly": False,  "advanced": True    },
        "req_achievement_id":         { "tip": "Required achievement id",            "display_name": "",     "type": int,        "min": 0,       "max": INT_32_MAX,     "readonly": False,  "advanced": True    },

        # Stack / appearance
        "stack_size":                 { "tip": "Max stack size",                     "display_name": "",     "type": int,        "min": 1,       "max": 256,            "readonly": False,  "advanced": False   },
        "color1":                     { "tip": "Primary color index (placeholder)",  "display_name": "",     "type": int,        "min": 0,       "max": 255,            "readonly": False,  "advanced": True    },
        "decal":                      { "tip": "Decal id (optional)",                "display_name": "",     "type": int,        "min": 0,       "max": INT_32_MAX,     "readonly": False,  "advanced": True    },
        "offset_group_id":            { "tip": "Offset group id",                    "display_name": "",     "type": int,        "min": 0,       "max": INT_32_MAX,     "readonly": False,  "advanced": True    },
        "build_types":                { "tip": "Bitmask build types",                "display_name": "",     "type": int,        "min": 0,       "max": INT_32_MAX,     "readonly": False,  "advanced": True    },

        # Misc functional
        "req_precondition":           { "tip": "Precondition id (placeholder)",      "display_name": "",     "type": str,        "min": 0,       "max": None,           "readonly": False,  "advanced": True    },
        "animation_flag":             { "tip": "Animation flag id",                  "display_name": "",     "type": int,        "min": 0,       "max": INT_32_MAX,     "readonly": False,  "advanced": True    },
        "equip_effects":              { "tip": "Equip effects id",                   "display_name": "",     "type": int,        "min": 0,       "max": INT_32_MAX,     "readonly": False,  "advanced": True    },
        "ready_for_qa":               { "tip": "Marked ready for QA",                "display_name": "",     "type": bool,       "min": None,    "max": None,           "readonly": False,  "advanced": True    },
        "item_rating":                { "tip": "Item rating (placeholder)",          "display_name": "",     "type": int,        "min": 0,       "max": 10_000,         "readonly": False,  "advanced": True    },
        "is_two_handed":              { "tip": "Requires two hands",                 "display_name": "",     "type": bool,       "min": None,    "max": None,           "readonly": False,  "advanced": False   },
        "min_num_required":           { "tip": "Minimum number required",            "display_name": "",     "type": int,        "min": 0,       "max": INT_32_MAX,     "readonly": False,  "advanced": True    },
        "del_res_index":              { "tip": "Delete resource index",              "display_name": "",     "type": int,        "min": 0,       "max": INT_32_MAX,     "readonly": False,  "advanced": True    },
        "currency_lot":               { "tip": "Primary currency lot id",            "display_name": "",     "type": int,        "min": 0,       "max": INT_32_MAX,     "readonly": False,  "advanced": True    },
        "alt_currency_cost":          { "tip": "Alternate currency cost",            "display_name": "",     "type": int,        "min": 0,       "max": INT_32_MAX,     "readonly": False,  "advanced": True    },
        "sub_items":                  { "tip": "Sub items list (raw text)",          "display_name": "",     "type": str,        "min": None,    "max": None,           "readonly": False,  "advanced": True    },
        "audio_event_use":            { "tip": "Audio event on use",                 "display_name": "",     "type": str,        "min": None,    "max": None,           "readonly": False,  "advanced": True    },
        "no_equip_animation":         { "tip": "Skip equip animation",               "display_name": "",     "type": bool,       "min": None,    "max": None,           "readonly": False,  "advanced": True    },
        "commendation_lot":           { "tip": "Commendation lot id",                "display_name": "",     "type": int,        "min": 0,       "max": INT_32_MAX,     "readonly": False,  "advanced": True    },
        "commendation_cost":          { "tip": "Commendation cost",                  "display_name": "",     "type": int,        "min": 0,       "max": INT_32_MAX,     "readonly": False,  "advanced": True    },
        "audio_equip_meta_event_set": { "tip": "Equip meta event set",               "display_name": "",     "type": str,        "min": None,    "max": None,           "readonly": False,  "advanced": True    },
        "currency_costs":             { "tip": "Serialized currency costs",          "display_name": "",     "type": str,        "min": None,    "max": None,           "readonly": False,  "advanced": True    },
        "ingredient_info":            { "tip": "Serialized ingredient info",         "display_name": "",     "type": str,        "min": None,    "max": None,           "readonly": False,  "advanced": True    },
        "loc_status":                 { "tip": "Localization status code",           "display_name": "",     "type": int,        "min": 0,       "max": INT_32_MAX,     "readonly": False,  "advanced": True    },
        "forge_type":                 { "tip": "Forge type id",                      "display_name": "",     "type": int,        "min": 0,       "max": INT_32_MAX,     "readonly": False,  "advanced": True    },
        "sell_multiplier":            { "tip": "Sell price multiplier",              "display_name": "",     "type": float,      "min": 0.0,     "max": FLOAT_32_MAX,   "readonly": False,  "advanced": True    },

        # Internal state
        "dirty":                      { "tip": "Internal dirty flag (not editable)", "display_name": "",     "type": bool,       "min": None,    "max": None,           "readonly": True,   "advanced": True    },
    },

    # ---------------------------------------------------------------
    # RenderComponent visual representation metadata
    # ---------------------------------------------------------------
    "RenderComponent": {
        # Core identity
        "id":                          { "tip": "Primary key / component id",            "display_name": "",    "type": int,        "min": 1,        "max": INT_32_MAX,    "readonly": True,   "advanced": False },

        # Assets
        "render_asset":                { "tip": "Path or identifier of render asset",    "display_name": "",    "type": str,        "min": None,     "max": None,          "readonly": False,  "advanced": False },
        "icon_asset":                  { "tip": "Icon asset reference",                  "display_name": "",    "type": str,        "min": None,     "max": None,          "readonly": False,  "advanced": False },
        "icon_id":                     { "tip": "Numeric icon id",                       "display_name": "",    "type": int,        "min": 0,        "max": INT_32_MAX,    "readonly": False,  "advanced": False },
        "shader_id":                   { "tip": "Shader identifier",                     "display_name": "",    "type": int,        "min": 0,        "max": INT_32_MAX,    "readonly": False,  "advanced": True  },

        # Effects (optional int slots)
        "effect1":                     { "tip": "Effect slot 1 id",                      "display_name": "",    "type": int,        "min": 0,        "max": INT_32_MAX,    "readonly": False,  "advanced": True  },
        "effect2":                     { "tip": "Effect slot 2 id",                      "display_name": "",    "type": int,        "min": 0,        "max": INT_32_MAX,    "readonly": False,  "advanced": True  },
        "effect3":                     { "tip": "Effect slot 3 id",                      "display_name": "",    "type": int,        "min": 0,        "max": INT_32_MAX,    "readonly": False,  "advanced": True  },
        "effect4":                     { "tip": "Effect slot 4 id",                      "display_name": "",    "type": int,        "min": 0,        "max": INT_32_MAX,    "readonly": False,  "advanced": True  },
        "effect5":                     { "tip": "Effect slot 5 id",                      "display_name": "",    "type": int,        "min": 0,        "max": INT_32_MAX,    "readonly": False,  "advanced": True  },
        "effect6":                     { "tip": "Effect slot 6 id",                      "display_name": "",    "type": int,        "min": 0,        "max": INT_32_MAX,    "readonly": False,  "advanced": True  },
        "animation_group_ids":         { "tip": "Serialized animation group ids",        "display_name": "",    "type": str,        "min": None,     "max": None,          "readonly": False,  "advanced": True  },

        # Booleans controlling rendering behavior
        "fade":                        { "tip": "Enable fade",                           "display_name": "",    "type": bool,       "min": None,     "max": None,          "readonly": False,  "advanced": False },
        "use_drop_shadow":             { "tip": "Use drop shadow",                       "display_name": "",    "type": bool,       "min": None,     "max": None,          "readonly": False,  "advanced": False },
        "preload_animations":          { "tip": "Preload animations",                    "display_name": "",    "type": bool,       "min": None,     "max": None,          "readonly": False,  "advanced": True  },

        # Timing / distances
        "fade_in_time":                { "tip": "Fade in time (seconds)",                "display_name": "",    "type": float,      "min": 0.0,      "max": FLOAT_32_MAX,  "readonly": False,  "advanced": False },
        "max_shadow_distance":         { "tip": "Max shadow distance",                   "display_name": "",    "type": float,      "min": 0.0,      "max": FLOAT_32_MAX,  "readonly": False,  "advanced": True  },
        "ignore_camera_collision":     { "tip": "Ignore camera collision",               "display_name": "",    "type": bool,       "min": None,     "max": None,          "readonly": False,  "advanced": True  },

        # LOD / snap
        "render_component_lod1":       { "tip": "LOD1 component id",                     "display_name": "",    "type": int,        "min": 0,        "max": INT_32_MAX,    "readonly": False,  "advanced": True  },
        "render_component_lod2":       { "tip": "LOD2 component id",                     "display_name": "",    "type": int,        "min": 0,        "max": INT_32_MAX,    "readonly": False,  "advanced": True  },
        "gradual_snap":                { "tip": "Enable gradual snap",                   "display_name": "",    "type": bool,       "min": None,     "max": None,          "readonly": False,  "advanced": True  },

        # Animation / audio
        "animation_flag":              { "tip": "Animation flag id",                     "display_name": "",    "type": int,        "min": 0,        "max": INT_32_MAX,    "readonly": False,  "advanced": True  },
        "audio_meta_event_set":        { "tip": "Audio meta event set",                  "display_name": "",    "type": str,        "min": None,     "max": None,          "readonly": False,  "advanced": True  },

        # Billboard / UI
        "billboard_height":            { "tip": "Billboard height",                      "display_name": "",    "type": float,      "min": 0.0,      "max": FLOAT_32_MAX,  "readonly": False,  "advanced": True  },
        "chat_bubble_offset":          { "tip": "Chat bubble vertical offset",           "display_name": "",    "type": float,      "min": 0.0,      "max": FLOAT_32_MAX,  "readonly": False,  "advanced": True  },
        "static_billboard":            { "tip": "Static billboard",                      "display_name": "",    "type": bool,       "min": None,     "max": None,          "readonly": False,  "advanced": True  },

        # Folders / misc
        "lxfml_folder":                { "tip": "LXFML folder path",                     "display_name": "",    "type": str,        "min": None,     "max": None,          "readonly": False,  "advanced": True  },
        "attach_indicators_to_node":   { "tip": "Attach indicators to node",             "display_name": "",    "type": bool,       "min": None,     "max": None,          "readonly": False,  "advanced": True  },

        # Internal state
        "dirty":                       { "tip": "Internal dirty flag (not editable)",    "display_name": "",    "type": bool,       "min": None,     "max": None,          "readonly": True,   "advanced": True  },
    },

    # ---------------------------------------------------------------
    # GameObject (base object / template level metadata)
    # ---------------------------------------------------------------
    "GameObject": {
        "object_id":              { "tip": "Primary object / template id",              "display_name": "",     "type": int,        "min": 1,         "max": INT_32_MAX,    "readonly": True,   "advanced": False },
        "name":                   { "tip": "Internal name",                             "display_name": "",     "type": str,        "min": None,      "max": None,          "readonly": False,  "advanced": False },
        "placeable":              { "tip": "Can be placed in world",                    "display_name": "",     "type": bool,       "min": None,      "max": None,          "readonly": False,  "advanced": False },
        "type":                   { "tip": "High-level object type enum",               "display_name": "",     "type": str,        "min": None,      "max": None,          "readonly": False,  "advanced": False },
        "description":            { "tip": "Player-facing description",                 "display_name": "",     "type": str,        "min": None,      "max": None,          "readonly": False,  "advanced": False },
        "localize":               { "tip": "Should be localized",                       "display_name": "",     "type": bool,       "min": None,      "max": None,          "readonly": False,  "advanced": True  },
        "npc_template_id":        { "tip": "Associated NPC template id",                "display_name": "",     "type": int,        "min": 0,         "max": INT_32_MAX,    "readonly": False,  "advanced": True  },
        "display_name":           { "tip": "Localized / display name",                  "display_name": "",     "type": str,        "min": None,      "max": None,          "readonly": False,  "advanced": False },
        "interaction_distance":   { "tip": "Interaction distance (meters)",             "display_name": "",     "type": float,      "min": 0.0,       "max": FLOAT_32_MAX,  "readonly": False,  "advanced": True  },
        "nametag":                { "tip": "Show name tag?",                            "display_name": "",     "type": bool,       "min": None,      "max": None,          "readonly": False,  "advanced": True  },
        "internal_notes":         { "tip": "Developer / internal notes",                "display_name": "",     "type": str,        "min": None,      "max": None,          "readonly": False,  "advanced": True  },
        "loc_status":             { "tip": "Localization status code",                  "display_name": "",     "type": int,        "min": 0,         "max": INT_32_MAX,    "readonly": False,  "advanced": True  },
        "gate_version":           { "tip": "Gate / version gating string",              "display_name": "",     "type": str,        "min": None,      "max": None,          "readonly": False,  "advanced": True  },
        "hq_valid":               { "tip": "Valid for HQ?",                             "display_name": "",     "type": bool,       "min": None,      "max": None,          "readonly": False,  "advanced": True  },

        # Internal
        "dirty":                  { "tip": "Internal dirty flag (not editable)",        "display_name": "",     "type": bool,       "min": None,      "max": None,          "readonly": True,   "advanced": True  },
        "components":             { "tip": "Component mapping (managed internally)",    "display_name": "",     "type": dict,       "min": None,      "max": None,          "readonly": True,   "advanced": True  },
    },

    # ---------------------------------------------------------------
    # Skill component metadata
    # ---------------------------------------------------------------
    "ObjectSkillRow": {
        "object_Template":        { "tip": "Parent object id",                        "display_name": "", "type": int,   "min": 1,    "max": INT_32_MAX, "readonly": True,  "advanced": True  },
        "skill_id":               { "tip": "Skill behavior id",                       "display_name": "", "type": int,   "min": 1,    "max": INT_32_MAX, "readonly": False, "advanced": False },
        "cast_on_type":           { "tip": "Cast on type flag",                       "display_name": "", "type": int,   "min": 0,    "max": INT_32_MAX, "readonly": False, "advanced": True  },
        "ai_combat_weight":       { "tip": "AI combat weight / priority",             "display_name": "", "type": int,   "min": 0,    "max": INT_32_MAX, "readonly": False, "advanced": True  },
    }
}