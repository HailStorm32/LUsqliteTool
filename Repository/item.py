import sqlite3
from Domain.domains import *

def _b(x: bool) -> int: return 1 if x else 0
def _rb(x: Optional[int]) -> bool: return bool(x or 0)

class ItemRepository:
    """Repository for managing items in the database."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    ##########################
    #-------- LOAD -----------
    ##########################
    def get(self, object_id: int) -> Item:
        try:
            conn = self._conn()

            # Fetch the required columns from the Objects table to create an Item object
            base = conn.execute(
                    "SELECT id, name, placeable, type FROM Objects WHERE id=?",
                    (object_id,)
                ).fetchone()
            if not base:
                raise KeyError(f"Item {object_id} not found")

            item = Item(id=base['id'], name=base['name'], placeable=base['placeable'], type=base['type'])

            # Get the components of the item
            component_rows = conn.execute(
                "SELECT component_type, component_id FROM ComponentsRegistry WHERE id=?",
                (object_id,)
            ).fetchall()

            for row in component_rows:
                if row["component_type"] == Components.ITEM:
                    item.components["ItemComponent"] = self._load_item_component(conn, object_id, row["component_id"])
                elif row["component_type"] == Components.RENDER:
                    item.components["RenderComponent"] = self._load_render_component(conn, object_id, row["component_id"])
                elif row["component_type"] == Components.SKILL:
                    item.components["ObjectSkill"] = self._load_skill_component(conn, object_id, row["component_id"])

            # Load all columns from the Objects table
            item_data = conn.execute(
                "SELECT * FROM Objects WHERE id=?",
                (object_id,)
            ).fetchone()

            if item_data:
                item.description           = item_data['description']
                item.localize              = _rb(item_data['localize'])
                item.npc_template_id       = item_data['npcTemplateID']
                item.display_name          = item_data['displayName']
                item.interaction_distance  = item_data['interactionDistance']
                item.nametag               = _rb(item_data['nametag'])
                item.internal_notes        = item_data['_internalNotes']
                item.loc_status            = item_data['locStatus']
                item.gate_version          = item_data['gate_version']
                item.hq_valid              = _rb(item_data['HQ_valid'])
            else:
                raise KeyError(f"Item data for {object_id} not found in Objects table despite it existing previously.")

            return item

        finally:
            conn.close()


    def _load_item_component(self, conn: sqlite3.Connection, object_id: int, component_id: int) -> ItemComponent:
        row = conn.execute(
            "SELECT * FROM ItemComponent WHERE id=?",
            (component_id,)
        ).fetchone()

        if not row:
            raise KeyError(f"ItemComponent {component_id} not found for object {object_id}")

        return ItemComponent(
            object_id                   = row['id'],
            equip_location              = row['equipLocation'],
            base_value                  = row['baseValue'],
            is_kit_piece                = _rb(row['isKitPiece']),
            rarity                      = row['rarity'],
            item_type                   = row['itemType'],
            item_info                   = row['itemInfo'],
            in_loot_table               = _rb(row['inLootTable']),
            in_vendor                   = _rb(row['inVendor']),
            is_unique                   = _rb(row['isUnique']),
            is_bop                      = _rb(row['isBOP']),
            is_boe                      = _rb(row['isBOE']),
            req_flag_id                 = row['reqFlagID'],
            req_specialty_id            = row['reqSpecialtyID'],
            req_spec_rank               = row['reqSpecRank'],
            req_achievement_id          = row['reqAchievementID'],
            stack_size                  = row['stackSize'],
            color1                      = row['color1'],
            decal                       = row['decal'],
            offset_group_id             = row['offsetGroupID'],
            build_types                 = row['buildTypes'],
            req_precondition            = row['reqPrecondition'],
            animation_flag              = row['animationFlag'],
            equip_effects               = row['equipEffects'],
            ready_for_qa                = _rb(row['readyForQA']),
            item_rating                 = row['itemRating'],
            is_two_handed               = _rb(row['isTwoHanded']),
            min_num_required            = row['minNumRequired'],
            del_res_index               = row['delResIndex'],
            currency_lot                = row['currencyLOT'],
            alt_currency_cost           = row['altCurrencyCost'],
            sub_items                   = row['subItems'],
            audio_event_use             = row['audioEventUse'],
            no_equip_animation          = _rb(row['noEquipAnimation']),
            commendation_lot            = row['commendationLOT'],
            commendation_cost           = row['commendationCost'],
            audio_equip_meta_event_set  = row['audioEquipMetaEventSet'],
            currency_costs              = row['currencyCosts'],
            ingredient_info             = row['ingredientInfo'],
            loc_status                  = row['locStatus'],
            forge_type                  = row['forgeType'],
            sell_multiplier             = row['SellMultiplier'],
        )


    def _load_render_component(self, conn: sqlite3.Connection, object_id: int, component_id: int) -> RenderComponent:
        row = conn.execute(
            "SELECT * FROM RenderComponent WHERE id=?",
            (component_id,)
        ).fetchone()

        if not row:
            raise KeyError(f"RenderComponent {component_id} not found for object {object_id}")

        return RenderComponent(
            object_id                   = row['id'],
            render_asset                = row['render_asset'],
            icon_asset                  = row['icon_asset'],
            icon_id                     = row['IconID'],
            shader_id                   = row['shader_id'],
            effect1                     = row['effect1'],
            effect2                     = row['effect2'],
            effect3                     = row['effect3'],
            effect4                     = row['effect4'],
            effect5                     = row['effect5'],
            effect6                     = row['effect6'],
            animation_group_ids         = row['animationGroupIDs'],
            fade                        = _rb(row['fade']),
            use_drop_shadow             = _rb(row['usedropshadow']),
            preload_animations          = _rb(row['preloadAnimations']),
            fade_in_time                = row['fadeInTime'],
            max_shadow_distance         = row['maxShadowDistance'],
            ignore_camera_collision     = _rb(row['ignoreCameraCollision']),
            render_component_lod1       = row['renderComponentLOD1'],
            render_component_lod2       = row['renderComponentLOD2'],
            gradual_snap                = _rb(row['gradualSnap']),
            animation_flag              = row['animationFlag'],
            audio_meta_event_set        = row['AudioMetaEventSet'],
            billboard_height            = row['billboardHeight'],
            chat_bubble_offset          = row['chatBubbleOffset'],
            static_billboard            = _rb(row['staticBillboard']),
            lxfml_folder                = row['LXFMLFolder'],
            attach_indicators_to_node   = _rb(row['attachIndicatorsToNode']),
        )


    def _load_skill_component(self, conn: sqlite3.Connection, object_id: int, component_id: int) -> ObjectSkills:

        # Typically, the component_id is 0 for ObjectSkills, which means we need to use the object_id for objectTemplate
        # However, in some cases, the component_id is not 0, and we need to handle that.
        if component_id == 0:
            param = object_id
        else:
            print("Using non standard method to load ObjectSkill")
            param = component_id

        # Fetch all the skill rows for the given objectTemplate
        rows = conn.execute(
            "SELECT * FROM ObjectSkills WHERE objectTemplate=?",
            (param,)
        ).fetchall()

        if not rows:
            raise KeyError(f"ObjectSkills of objectTemplate: {param} not found for object {object_id}")

        skill_list = []

        # Iterate through the rows and create ObjectSkillRow instances for each skill
        for row in rows:
            skill_list.append(
                ObjectSkillRow(
                    object_Template     = row['objectTemplate'],
                    skill_id            = row['skillID'],
                    cast_on_type        = row['castOnType'],
                    ai_combat_weight    = row['AICombatWeight']
                )
            )

        # Return an ObjectSkill instance containing the list of skills
        return ObjectSkills(
            skills = skill_list,
        )

    
    # def close(self):
    #     pass
