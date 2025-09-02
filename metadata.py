INT_32_MAX = 2_147_483_647
FLOAT_32_MAX = 3.4028235e+38

component_field_metadata = {
    "ItemComponent": {
        # Core identity / primary
        "id":                         { "tip": "Primary key / component id",             "type": int,        "min": 1,       "max": INT_32_MAX,     "readonly": True,   "advanced": False   },

        # Basic classification / value
        "equip_location":             { "tip": "Where this item is equipped",            "type": str,        "min": None,    "max": None,           "readonly": False,  "advanced": False   },
        "base_value":                 { "tip": "Base vendor value (placeholder)",        "type": int,        "min": 0,       "max": INT_32_MAX,     "readonly": False,  "advanced": False   },
        "is_kit_piece":               { "tip": "Part of a kit?",                         "type": bool,       "min": None,    "max": None,           "readonly": False,  "advanced": False   },
        "rarity":                     { "tip": "Rarity tier (placeholder)",              "type": int,        "min": 0,       "max": 10,             "readonly": False,  "advanced": False   },
        "item_type":                  { "tip": "Item type (enum)",                       "type": str,        "min": None,    "max": None,           "readonly": False,  "advanced": False   },
        "item_info":                  { "tip": "Opaque item info id",                    "type": int,        "min": 0,       "max": INT_32_MAX,     "readonly": False,  "advanced": True    },

        # Availability flags
        "in_loot_table":              { "tip": "Appears in loot tables",                 "type": bool,       "min": None,    "max": None,           "readonly": False,  "advanced": False   },
        "in_vendor":                  { "tip": "Sold by vendors",                        "type": bool,       "min": None,    "max": None,           "readonly": False,  "advanced": False   },
        "is_unique":                  { "tip": "Unique (one per player)",                "type": bool,       "min": None,    "max": None,           "readonly": False,  "advanced": False   },
        "is_bop":                     { "tip": "Bind on pickup",                         "type": bool,       "min": None,    "max": None,           "readonly": False,  "advanced": False   },
        "is_boe":                     { "tip": "Bind on equip",                          "type": bool,       "min": None,    "max": None,           "readonly": False,  "advanced": False   },

        # Requirements
        "req_flag_id":                { "tip": "Required flag id (placeholder)",         "type": int,        "min": 0,       "max": INT_32_MAX,     "readonly": False,  "advanced": True    },
        "req_specialty_id":           { "tip": "Required specialty id",                  "type": int,        "min": 0,       "max": INT_32_MAX,     "readonly": False,  "advanced": True    },
        "req_spec_rank":              { "tip": "Required specialty rank",                "type": int,        "min": 0,       "max": 100,            "readonly": False,  "advanced": True    },
        "req_achievement_id":         { "tip": "Required achievement id",                "type": int,        "min": 0,       "max": INT_32_MAX,     "readonly": False,  "advanced": True    },

        # Stack / appearance
        "stack_size":                 { "tip": "Max stack size",                         "type": int,        "min": 1,       "max": 256,            "readonly": False,  "advanced": False   },
        "color1":                     { "tip": "Primary color index (placeholder)",      "type": int,        "min": 0,       "max": 255,            "readonly": False,  "advanced": True    },
        "decal":                      { "tip": "Decal id (optional)",                    "type": int,        "min": 0,       "max": INT_32_MAX,     "readonly": False,  "advanced": True    },
        "offset_group_id":            { "tip": "Offset group id",                        "type": int,        "min": 0,       "max": INT_32_MAX,     "readonly": False,  "advanced": True    },
        "build_types":                { "tip": "Bitmask build types",                    "type": int,        "min": 0,       "max": INT_32_MAX,     "readonly": False,  "advanced": True    },

        # Misc functional
        "req_precondition":           { "tip": "Precondition id (placeholder)",          "type": int,        "min": 0,       "max": INT_32_MAX,     "readonly": False,  "advanced": True    },
        "animation_flag":             { "tip": "Animation flag id",                      "type": int,        "min": 0,       "max": INT_32_MAX,     "readonly": False,  "advanced": True    },
        "equip_effects":              { "tip": "Equip effects id",                       "type": int,        "min": 0,       "max": INT_32_MAX,     "readonly": False,  "advanced": True    },
        "ready_for_qa":               { "tip": "Marked ready for QA",                    "type": bool,       "min": None,    "max": None,           "readonly": False,  "advanced": True    },
        "item_rating":                { "tip": "Item rating (placeholder)",              "type": int,        "min": 0,       "max": 10_000,         "readonly": False,  "advanced": True    },
        "is_two_handed":              { "tip": "Requires two hands",                     "type": bool,       "min": None,    "max": None,           "readonly": False,  "advanced": False   },
        "min_num_required":           { "tip": "Minimum number required",                "type": int,        "min": 0,       "max": INT_32_MAX,     "readonly": False,  "advanced": True    },
        "del_res_index":              { "tip": "Delete resource index",                  "type": int,        "min": 0,       "max": INT_32_MAX,     "readonly": False,  "advanced": True    },
        "currency_lot":               { "tip": "Primary currency lot id",                "type": int,        "min": 0,       "max": INT_32_MAX,     "readonly": False,  "advanced": True    },
        "alt_currency_cost":          { "tip": "Alternate currency cost",                "type": int,        "min": 0,       "max": INT_32_MAX,     "readonly": False,  "advanced": True    },
        "sub_items":                  { "tip": "Sub items list (raw text)",              "type": str,        "min": None,    "max": None,           "readonly": False,  "advanced": True    },
        "audio_event_use":            { "tip": "Audio event on use",                     "type": str,        "min": None,    "max": None,           "readonly": False,  "advanced": True    },
        "no_equip_animation":         { "tip": "Skip equip animation",                   "type": bool,       "min": None,    "max": None,           "readonly": False,  "advanced": True    },
        "commendation_lot":           { "tip": "Commendation lot id",                    "type": int,        "min": 0,       "max": INT_32_MAX,     "readonly": False,  "advanced": True    },
        "commendation_cost":          { "tip": "Commendation cost",                      "type": int,        "min": 0,       "max": INT_32_MAX,     "readonly": False,  "advanced": True    },
        "audio_equip_meta_event_set": { "tip": "Equip meta event set",                   "type": str,        "min": None,    "max": None,           "readonly": False,  "advanced": True    },
        "currency_costs":             { "tip": "Serialized currency costs",              "type": str,        "min": None,    "max": None,           "readonly": False,  "advanced": True    },
        "ingredient_info":            { "tip": "Serialized ingredient info",             "type": str,        "min": None,    "max": None,           "readonly": False,  "advanced": True    },
        "loc_status":                 { "tip": "Localization status code",               "type": int,        "min": 0,       "max": INT_32_MAX,     "readonly": False,  "advanced": True    },
        "forge_type":                 { "tip": "Forge type id",                          "type": int,        "min": 0,       "max": INT_32_MAX,     "readonly": False,  "advanced": True    },
        "sell_multiplier":            { "tip": "Sell price multiplier",                  "type": float,      "min": 0.0,     "max": FLOAT_32_MAX,   "readonly": False,  "advanced": True    },

        # Internal state
        "dirty":                      { "tip": "Internal dirty flag (not editable)",     "type": bool,       "min": None,    "max": None,           "readonly": True,   "advanced": True    },
    }
}