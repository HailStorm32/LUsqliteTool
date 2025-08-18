import sqlite3
from Domain.domains import *

def _b(x: bool) -> int: return 1 if x else 0
def _rb(x: Optional[int]) -> bool: return bool(x or 0)

class baseRepository:
    def __init__(self, db_file: str):
        self.__db_file = db_file

    def _connect_to_db(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.__db_file)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _load_components(self, object_id: int) -> Dict[str, object]:
        """Load components for a given object ID."""
        components = {}

        conn = self._connect_to_db()

        try:
            # Get the components of the object
            component_rows = conn.execute(
                "SELECT component_type, component_id FROM ComponentsRegistry WHERE id=?",
                (object_id,)
            ).fetchall()

            for row in component_rows:
                if row["component_type"] == Components.ITEM:
                    components["ItemComponent"] = self.__load_item_component(conn, object_id, row["component_id"])

                elif row["component_type"] == Components.RENDER:
                    components["RenderComponent"] = self.__load_render_component(conn, object_id, row["component_id"])

                elif row["component_type"] == Components.SKILL:
                    components["ObjectSkill"] = self.__load_skill_component(conn, object_id, row["component_id"])

            return components

        finally:
            conn.close()

    def _load_object_table(self, object: GameObject) -> None:
        """Load the object data from the database."""
        conn = self._connect_to_db()

        try:
            # Load all columns from the Objects table
            item_data = conn.execute(
                "SELECT * FROM Objects WHERE id=?",
                (object.object_id,)
            ).fetchone()

            if item_data:
                object.description           = item_data['description']
                object.localize              = _rb(item_data['localize'])
                object.npc_template_id       = item_data['npcTemplateID']
                object.display_name          = item_data['displayName']
                object.interaction_distance  = item_data['interactionDistance']
                object.nametag               = _rb(item_data['nametag'])
                object.internal_notes        = item_data['_internalNotes']
                object.loc_status            = item_data['locStatus']
                object.gate_version          = item_data['gate_version']
                object.hq_valid              = _rb(item_data['HQ_valid'])
            else:
                raise KeyError(f"Object data for object id: {object.object_id} not found in Objects table despite it existing previously.")

        finally:
            conn.close()


    def __load_item_component(self, conn: sqlite3.Connection, object_id: int, component_id: int) -> ItemComponent:
        row = conn.execute(
            "SELECT * FROM ItemComponent WHERE id=?",
            (component_id,)
        ).fetchone()

        if not row:
            raise KeyError(f"ItemComponent with ID: {component_id} not found for object: {object_id}")

        return ItemComponent(
            id                          = row['id'],
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


    def __load_render_component(self, conn: sqlite3.Connection, object_id: int, component_id: int) -> RenderComponent:
        row = conn.execute(
            "SELECT * FROM RenderComponent WHERE id=?",
            (component_id,)
        ).fetchone()

        if not row:
            raise KeyError(f"RenderComponent ID: {component_id} not found for object: {object_id}")

        return RenderComponent(
            id                          = row['id'],
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


    def __load_skill_component(self, conn: sqlite3.Connection, object_id: int, component_id: int) -> ObjectSkills:

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
