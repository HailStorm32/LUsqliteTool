import sqlite3
from Domain.domains import *
from Repository.exceptions import NotFoundError, DataIntegrityError, SaveError

def _b(x: bool) -> int: return 1 if x else 0 # Convert boolean to int for py -> SQLite
def _rb(x: Optional[int]) -> bool: return bool(x or 0) # Convert int to boolean for SQLite -> py, treating None as False

class baseRepository:
    def __init__(self, db_file: str):
        self.__db_file = db_file

    def _connect_to_db(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.__db_file)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def __get_row_count(self, table: str, value: int, column: str = "id") -> int:
        """Returns the number of rows in a table where a specific column matches a value"""
        conn = self._connect_to_db()
        try:
            count = conn.execute(
                f"SELECT COUNT(*) FROM {table} WHERE {column} = ?",
                (value,)
            ).fetchone()[0]
            return count
        finally:
            conn.close()


    ############################
    #-------- LOAD -------------
    ############################

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

            if len(components) == 0:
                print(f"WARNING: No components found for Object ID: {object_id}")

            return components

        finally:
            conn.close()

    def _load_object_table(self, object: GameObject) -> None:
        """Load the object data from the database."""
        conn = self._connect_to_db()

        try:
            #Ensure there is only one row for the object ID in the Objects table
            if self.__get_row_count("Objects", object.object_id) > 1:
                raise DataIntegrityError(f"Multiple rows found for object ID: {object.object_id} in Objects table, cannot load.",
                                         table="Objects", column="id", value=object.object_id)

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
                raise NotFoundError(f"Object data for object id: {object.object_id} not found in Objects table despite it existing previously.",
                                    table="Objects", column="id", value=object.object_id)

        finally:
            conn.close()

    def __load_item_component(self, conn: sqlite3.Connection, object_id: int, component_id: int) -> ItemComponent:

        #Ensure there is only one row for the component ID in the ItemComponent table
        if self.__get_row_count("ItemComponent", component_id, "id") > 1:
            raise DataIntegrityError(f"Multiple rows found for ItemComponent ID: {component_id} for object: {object_id}",
                                     table="ItemComponent", column="id", value=component_id)

        row = conn.execute(
            "SELECT * FROM ItemComponent WHERE id=?",
            (component_id,)
        ).fetchone()

        if not row:
            raise NotFoundError(f"ItemComponent with ID: {component_id} not found for object: {object_id}",
                                table="ItemComponent", column="id", value=component_id)

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

        #Ensure there is only one row for the component ID in the RenderComponent table
        if self.__get_row_count("RenderComponent", component_id, "id") > 1:
            raise DataIntegrityError(f"Multiple rows found for RenderComponent ID: {component_id} for object: {object_id}",
                                     table="RenderComponent", column="id", value=component_id)

        row = conn.execute(
            "SELECT * FROM RenderComponent WHERE id=?",
            (component_id,)
        ).fetchone()

        if not row:
            raise NotFoundError(f"RenderComponent with ID: {component_id} not found for object: {object_id}",
                               table="RenderComponent", column="id", value=component_id)

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
            raise NotFoundError(f"ObjectSkills of objectTemplate: {param} not found for object {object_id}",
                                table="ObjectSkills", column="objectTemplate", value=param)

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


    ############################
    #-------- SAVE -------------
    ############################

    def _save_components(self, conn: sqlite3.Connection, object_id: int, components: Dict[str, object]) -> None:
        """Save components for a given object ID."""

        # Cycle through the components and save them if they are dirty
        for component_type, component in components.items():
            if isinstance(component, ItemComponent) and component.dirty:
                self.__save_item_component(conn, component)

            elif isinstance(component, RenderComponent) and component.dirty:
                self.__save_render_component(conn, component)

            elif isinstance(component, ObjectSkills) and component.dirty:
                self.__save_skill_component(conn, component)

            else:
                print(f"Unknown component type: {component_type}")

        # Ensure the ComponentsRegistry is up-to-date
        self.__ensure_component_registry(conn, object_id, components)

    def _save_object_table(self, conn: sqlite3.Connection, object: GameObject) -> None:
        # Make sure only one row exists for the object ID in the Objects table
        if self.__get_row_count("Objects", object.object_id) > 1:
            raise DataIntegrityError(f"Multiple rows found for object ID: {object.object_id} in Objects table, cannot save.",
                                     table="Objects", column="id", value=object.object_id)

        # LU client database lacks UNIQUE constraints, so we need to handle this manually
        # If the object exists, we update it; otherwise, we insert a new row
        res = conn.execute("""
            UPDATE Objects SET
                name=?, placeable=?, description=?, type=?, localize=?, npcTemplateID=?, displayName=?,
                interactionDistance=?, nametag=?, _internalNotes=?, locStatus=?, gate_version=?, HQ_valid=?
            WHERE id=?""", (
                object.name, object.placeable, object.description, object.type, _b(object.localize), object.npc_template_id,
                object.display_name, object.interaction_distance, _b(object.nametag), object.internal_notes,
                object.loc_status, object.gate_version, _b(object.hq_valid), object.object_id
        ))

        #If no row was updated, INSERT a new one
        if res.rowcount == 0:
            conn.execute("""
                INSERT INTO Objects (
                    id, name, placeable, description, type, localize, npcTemplateID, displayName,
                    interactionDistance, nametag, _internalNotes, locStatus, gate_version, HQ_valid
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (
                    object.object_id, object.name, object.placeable, object.description, object.type, _b(object.localize),
                    object.npc_template_id, object.display_name, object.interaction_distance, _b(object.nametag),
                    object.internal_notes, object.loc_status, object.gate_version, _b(object.hq_valid)
            ))

    def __save_item_component(self, conn: sqlite3.Connection, item_component: ItemComponent) -> None:
        #TODO

        # Reset dirty flag after saving
        item_component.dirty = False

    def __save_render_component(self, conn: sqlite3.Connection, render_component: RenderComponent) -> None:
        #TODO

        # Reset dirty flag after saving
        render_component.dirty = False

    def __save_skill_component(self, conn: sqlite3.Connection, object_skills: ObjectSkills) -> None:
        #TODO

        # Reset dirty flag after saving
        object_skills.dirty = False

    def __ensure_component_registry(self, conn, object_id: int, components: Dict[str, object]) -> None:
        """Keeps ComponentsRegistry up-to-date."""

        # Delete existing entries so we can rebuild it
        conn.execute(
            "DELETE FROM ComponentsRegistry WHERE id=?",
            (object_id, )
        )

        # Insert new entries for each component
        for component_type, component in components.items():
            if isinstance(component, ItemComponent):
                conn.execute(
                    "INSERT INTO ComponentsRegistry (id, component_type, component_id) VALUES (?, ?, ?)",
                    (object_id, Components.ITEM, component.id)
                )

            elif isinstance(component, RenderComponent):
                conn.execute(
                    "INSERT INTO ComponentsRegistry (id, component_type, component_id) VALUES (?, ?, ?)",
                    (object_id, Components.RENDER, component.id)
                )

            elif isinstance(component, ObjectSkills):
                # Handle if ObjectSkills uses a non zero component ID
                if component.zero_component_id:
                    component_id = 0
                else:
                    print(f"WARNING: ObjectSkills for object: {object_id} uses non zero component ID in ComponentsRegistry, this is not standard!")
                    component_id = component.skills[0].skill_id if component.skills else 0

                conn.execute(
                    "INSERT INTO ComponentsRegistry (id, component_type, component_id) VALUES (?, ?, ?)",
                    (object_id, Components.SKILL, component_id)
                )
            else:
                print(f"ERROR: Unknown component type: {component_type}")



