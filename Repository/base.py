import sqlite3
from Domain.domains import *
from Repository.exceptions import NotFoundError, DataIntegrityError, SaveError

def _b(x: bool) -> int: return 1 if x else 0 # Convert boolean to int for py -> SQLite
def _rb(x: Optional[int]) -> bool: return bool(x or 0) # Convert int to boolean for SQLite -> py, treating None as False

# Convert ColorType enum to the int id stored in the DB; pass through existing ints/None
def _color_id(x: Optional[int | ColorType]) -> Optional[int]:
    # ColorType is imported at module scope; bind to its integer id for SQLite
    if isinstance(x, ColorType):
        return int(x)
    return x  # Already an int or None

class baseRepository:
    def __init__(self, db_file: str):
        self.__db_file = db_file

    def _connect_to_db(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.__db_file)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    ############################
    #-------- COMMON UTILS -----
    ############################
    def generate_new_id(self) -> int:
        """Generate a new unique object ID from the Objects table.

        Strategy: MAX(id)+1 with a guard for 32-bit signed range. This approach matches
        how the LU client DB behaves (no autoincrement) and is shared across object types
        (Items, NPCs, etc.), so it lives in the base repo for reuse.
        """
        conn = self._connect_to_db()
        try:
            row = conn.execute("SELECT MAX(id) AS max_id FROM Objects").fetchone()
            max_id = row["max_id"] if row is not None else None
            new_id = (int(max_id) + 1) if max_id is not None else 1
            # Basic overflow guard for 32-bit signed range
            if new_id > 2_147_483_647:
                raise SaveError("Exhausted id space; cannot create new object id.")
            return new_id
        finally:
            conn.close()

    def generate_new_component_id(self, preferred_id: int, table: str) -> int:
        """Generate a new unique component id for a table, preferring a starting id.

        Logic requested: try the object's id first; if that id already exists in the
        component table, choose the next available id by incrementing until free.
        Guards against exceeding 32-bit signed integer max.
        """
        if not isinstance(preferred_id, int) or preferred_id <= 0:
            raise ValueError("preferred_id must be a positive integer")
        if not table or not isinstance(table, str):
            raise ValueError("table must be a non-empty string")

        conn = self._connect_to_db()
        try:
            candidate = int(preferred_id)
            while True:
                row = conn.execute(f"SELECT 1 FROM {table} WHERE id=? LIMIT 1", (candidate,)).fetchone()
                if row is None:
                    # Free id found
                    return candidate
                candidate += 1
                if candidate > 2_147_483_647:
                    raise SaveError(f"Exhausted id space while generating new id for {table} starting from {preferred_id}")
        finally:
            conn.close()

    def list_objects_by_type(self, type_value: str, limit: int | None = None) -> list[dict[str, int | str]]:
        """List object ids and names for a given Objects.type value.

        Parameters:
            type_value: The exact value stored in Objects.type (e.g., ObjectTypes.ITEM.value).
            limit: Optional maximum number of rows to return.

        Returns: List of dicts with keys: id (int), name (str)
        """
        conn = self._connect_to_db()
        try:
            query = "SELECT id, name FROM Objects WHERE type=?"
            params: tuple = (type_value,)
            if limit is not None:
                query += " LIMIT ?"
                params += (limit,)
            rows = conn.execute(query, params).fetchall()
            return [{"id": row["id"], "name": row["name"]} for row in rows]
        finally:
            conn.close()

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
    #-------- DELETE -----------
    ############################
    def delete(self, object_id: int) -> None:
        """Public deletion API: remove an object and all of its related data.

        This simply delegates to delete_object for clarity/compatibility so
        concrete repositories don't need to re-declare a passthrough.
        """
        self.delete_object(object_id)

    def delete_object(self, object_id: int) -> None:
        """Permanently delete an object and all related components.

        This removes:
        - ComponentsRegistry entries for the object
        - Corresponding ItemComponent and RenderComponent rows referenced by the registry
        - Any ObjectSkills rows for the object (objectTemplate)
        - The Objects row itself
        """
        conn = self._connect_to_db()
        try:
            conn.execute("BEGIN")
            # Fetch component ids from registry
            reg_rows = conn.execute(
                "SELECT component_type, component_id FROM ComponentsRegistry WHERE id=?",
                (object_id,)
            ).fetchall()

            # Delete skill rows (by objectTemplate); skill component ids may be zero
            conn.execute("DELETE FROM ObjectSkills WHERE objectTemplate=?", (object_id,))

            # Delete component rows for known components
            for row in reg_rows:
                ctype = row['component_type']
                cid = row['component_id']
                if ctype == Components.ITEM:
                    conn.execute("DELETE FROM ItemComponent WHERE id=?", (cid,))
                elif ctype == Components.RENDER:
                    conn.execute("DELETE FROM RenderComponent WHERE id=?", (cid,))
                # Components.SKILL covered by ObjectSkills deletion above

            # Delete registry entries
            conn.execute("DELETE FROM ComponentsRegistry WHERE id=?", (object_id,))

            # Finally, delete object itself
            conn.execute("DELETE FROM Objects WHERE id=?", (object_id,))

            conn.commit()
        except Exception:
            conn.rollback(); raise
        finally:
            conn.close()

    def delete_item_component(self, component_id: int) -> None:
        """Delete an ItemComponent and clear registry references."""
        conn = self._connect_to_db()
        try:
            conn.execute("BEGIN")
            conn.execute(
                "DELETE FROM ComponentsRegistry WHERE component_id=? AND component_type=?",
                (component_id, Components.ITEM)
            )
            conn.execute("DELETE FROM ItemComponent WHERE id=?", (component_id,))
            conn.commit()
        except Exception:
            conn.rollback(); raise
        finally:
            conn.close()

    def delete_render_component(self, component_id: int) -> None:
        """Delete a RenderComponent and clear registry references."""
        conn = self._connect_to_db()
        try:
            conn.execute("BEGIN")
            conn.execute(
                "DELETE FROM ComponentsRegistry WHERE component_id=? AND component_type=?",
                (component_id, Components.RENDER)
            )
            conn.execute("DELETE FROM RenderComponent WHERE id=?", (component_id,))
            conn.commit()
        except Exception:
            conn.rollback(); raise
        finally:
            conn.close()

    def delete_skill_component(self, object_id: int) -> None:
        """Delete all skills for an object and its registry entry (skill component)."""
        conn = self._connect_to_db()
        try:
            conn.execute("BEGIN")
            conn.execute("DELETE FROM ObjectSkills WHERE objectTemplate=?", (object_id,))
            conn.execute(
                "DELETE FROM ComponentsRegistry WHERE id=? AND component_type=?",
                (object_id, Components.SKILL)
            )
            conn.commit()
        except Exception:
            conn.rollback(); raise
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
                object.placeable             = _rb(item_data['placeable'])
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
            print(f"WARNING: Object {object_id} has skill entry in ComponentsRegistry but no rows found in ObjectSkills table.")
            # raise NotFoundError(f"ObjectSkills of objectTemplate: {param} not found for object {object_id}",
            #                     table="ObjectSkills", column="objectTemplate", value=param)

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
    #Note: save methods are not intended to handle a deletion of a table or row, only insertion or updating of existing rows.

    def _save_components(self, conn: sqlite3.Connection, object_id: int, components: Dict[str, object]) -> None:
        """Save components for a given object ID."""

        # Cycle through the components and save them if they are dirty
        for component_type, component in components.items():
            if component.dirty == False:
                print(f"DEBUG: Component {component_type} not dirty, skipping save.")
                continue

            if isinstance(component, ItemComponent) and component.dirty:
                self.__save_item_component(conn, component)

            elif isinstance(component, RenderComponent) and component.dirty:
                self.__save_render_component(conn, component)

            elif isinstance(component, ObjectSkills) and component.dirty:
                self.__save_skill_component(conn, object_id, component)

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
                object.name, _b(object.placeable), object.description, object.type, _b(object.localize), object.npc_template_id,
                object.display_name, object.interaction_distance, _b(object.nametag), object.internal_notes,
                object.loc_status, object.gate_version, _b(object.hq_valid), object.object_id
            )
        )

        #If no row was updated, INSERT a new one
        if res.rowcount == 0:
            conn.execute("""
                INSERT INTO Objects (
                    id, name, placeable, description, type, localize, npcTemplateID, displayName,
                    interactionDistance, nametag, _internalNotes, locStatus, gate_version, HQ_valid
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (
                    object.object_id, object.name, _b(object.placeable), object.description, object.type, _b(object.localize),
                    object.npc_template_id, object.display_name, object.interaction_distance, _b(object.nametag),
                    object.internal_notes, object.loc_status, object.gate_version, _b(object.hq_valid)
                )
            )

        # Reset dirty flag after saving
        object.dirty = False

    def __save_item_component(self, conn: sqlite3.Connection, item_component: ItemComponent) -> None:
        # Make sure only one row exists for the item_component.id in the ItemComponent table
        if self.__get_row_count("ItemComponent", item_component.id, "id") > 1:
            raise DataIntegrityError(
                f"Multiple rows found for ItemComponent ID: {item_component.id}",
                table="ItemComponent", column="id", value=item_component.id
            )

        # LU client database lacks UNIQUE constraints, so we need to handle this manually
        # If the item exists, we update it; otherwise, we insert a new row
        res = conn.execute(
            """
            UPDATE ItemComponent SET
            equipLocation=?, baseValue=?, isKitPiece=?, rarity=?, itemType=?, itemInfo=?, inLootTable=?, inVendor=?, isUnique=?, isBOP=?, isBOE=?,
            reqFlagID=?, reqSpecialtyID=?, reqSpecRank=?, reqAchievementID=?, stackSize=?, color1=?, decal=?, offsetGroupID=?, buildTypes=?,
            reqPrecondition=?, animationFlag=?, equipEffects=?, readyForQA=?, itemRating=?, isTwoHanded=?, minNumRequired=?, delResIndex=?,
            currencyLOT=?, altCurrencyCost=?, subItems=?, audioEventUse=?, noEquipAnimation=?, commendationLOT=?, commendationCost=?,
            audioEquipMetaEventSet=?, currencyCosts=?, ingredientInfo=?, locStatus=?, forgeType=?, SellMultiplier=?
            WHERE id=? """, (
                item_component.equip_location, item_component.base_value, _b(item_component.is_kit_piece), item_component.rarity,
                item_component.item_type, item_component.item_info, _b(item_component.in_loot_table), _b(item_component.in_vendor),
                _b(item_component.is_unique), _b(item_component.is_bop), _b(item_component.is_boe), item_component.req_flag_id,
                item_component.req_specialty_id, item_component.req_spec_rank, item_component.req_achievement_id, item_component.stack_size,
                _color_id(item_component.color1), item_component.decal, item_component.offset_group_id, item_component.build_types,
                item_component.req_precondition, item_component.animation_flag, item_component.equip_effects, _b(item_component.ready_for_qa),
                item_component.item_rating, _b(item_component.is_two_handed), item_component.min_num_required, item_component.del_res_index,
                item_component.currency_lot, item_component.alt_currency_cost, item_component.sub_items, item_component.audio_event_use,
                _b(item_component.no_equip_animation), item_component.commendation_lot, item_component.commendation_cost,
                item_component.audio_equip_meta_event_set, item_component.currency_costs, item_component.ingredient_info,
                item_component.loc_status, item_component.forge_type, item_component.sell_multiplier, item_component.id
            )
        )

        # If no row was updated, insert a new one
        if res.rowcount == 0:
            conn.execute(
                """
                INSERT INTO ItemComponent (
                    id, equipLocation, baseValue, isKitPiece, rarity, itemType, itemInfo, inLootTable, inVendor, isUnique, isBOP, isBOE,
                    reqFlagID, reqSpecialtyID, reqSpecRank, reqAchievementID, stackSize, color1, decal, offsetGroupID, buildTypes,
                    reqPrecondition, animationFlag, equipEffects, readyForQA, itemRating, isTwoHanded, minNumRequired, delResIndex,
                    currencyLOT, altCurrencyCost, subItems, audioEventUse, noEquipAnimation, commendationLOT, commendationCost,
                    audioEquipMetaEventSet, currencyCosts, ingredientInfo, locStatus, forgeType, SellMultiplier
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item_component.id, item_component.equip_location, item_component.base_value, _b(item_component.is_kit_piece),
                    item_component.rarity, item_component.item_type, item_component.item_info, _b(item_component.in_loot_table),
                    _b(item_component.in_vendor), _b(item_component.is_unique), _b(item_component.is_bop), _b(item_component.is_boe),
                    item_component.req_flag_id, item_component.req_specialty_id, item_component.req_spec_rank, item_component.req_achievement_id,
                    item_component.stack_size, _color_id(item_component.color1), item_component.decal, item_component.offset_group_id,
                    item_component.build_types, item_component.req_precondition, item_component.animation_flag, item_component.equip_effects,
                    _b(item_component.ready_for_qa), item_component.item_rating, _b(item_component.is_two_handed), item_component.min_num_required,
                    item_component.del_res_index, item_component.currency_lot, item_component.alt_currency_cost, item_component.sub_items,
                    item_component.audio_event_use, _b(item_component.no_equip_animation), item_component.commendation_lot,
                    item_component.commendation_cost, item_component.audio_equip_meta_event_set, item_component.currency_costs,
                    item_component.ingredient_info, item_component.loc_status, item_component.forge_type, item_component.sell_multiplier
                )
            )

        # Reset dirty flag after saving
        item_component.dirty = False

    def __save_render_component(self, conn: sqlite3.Connection, render_component: RenderComponent) -> None:
        # Make sure only one row exists for the render_component.id in the RenderComponent table
        if self.__get_row_count("RenderComponent", render_component.id, "id") > 1:
            raise DataIntegrityError(
            f"Multiple rows found for RenderComponent ID: {render_component.id}",
            table="RenderComponent", column="id", value=render_component.id
            )

        # LU client database lacks UNIQUE constraints, so we need to handle this manually
        # If the render component exists, we update it; otherwise, we insert a new row
        res = conn.execute(
            """
            UPDATE RenderComponent SET
            render_asset=?, icon_asset=?, IconID=?, shader_id=?, effect1=?, effect2=?, effect3=?, effect4=?, effect5=?, effect6=?,
            animationGroupIDs=?, fade=?, usedropshadow=?, preloadAnimations=?, fadeInTime=?, maxShadowDistance=?, ignoreCameraCollision=?,
            renderComponentLOD1=?, renderComponentLOD2=?, gradualSnap=?, animationFlag=?, AudioMetaEventSet=?, billboardHeight=?,
            chatBubbleOffset=?, staticBillboard=?, LXFMLFolder=?, attachIndicatorsToNode=?
            WHERE id=? """, (
            render_component.render_asset, render_component.icon_asset, render_component.icon_id, render_component.shader_id,
            render_component.effect1, render_component.effect2, render_component.effect3, render_component.effect4,
            render_component.effect5, render_component.effect6, render_component.animation_group_ids, _b(render_component.fade),
            _b(render_component.use_drop_shadow), _b(render_component.preload_animations), render_component.fade_in_time,
            render_component.max_shadow_distance, _b(render_component.ignore_camera_collision), render_component.render_component_lod1,
            render_component.render_component_lod2, _b(render_component.gradual_snap), render_component.animation_flag,
            render_component.audio_meta_event_set, render_component.billboard_height, render_component.chat_bubble_offset,
            _b(render_component.static_billboard), render_component.lxfml_folder, _b(render_component.attach_indicators_to_node),
            render_component.id
            )
        )

        # If no row was updated, insert a new one
        if res.rowcount == 0:
            conn.execute(
            """
            INSERT INTO RenderComponent (
                id, render_asset, icon_asset, IconID, shader_id, effect1, effect2, effect3, effect4, effect5, effect6,
                animationGroupIDs, fade, usedropshadow, preloadAnimations, fadeInTime, maxShadowDistance, ignoreCameraCollision,
                renderComponentLOD1, renderComponentLOD2, gradualSnap, animationFlag, AudioMetaEventSet, billboardHeight,
                chatBubbleOffset, staticBillboard, LXFMLFolder, attachIndicatorsToNode
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                render_component.id, render_component.render_asset, render_component.icon_asset, render_component.icon_id,
                render_component.shader_id, render_component.effect1, render_component.effect2, render_component.effect3,
                render_component.effect4, render_component.effect5, render_component.effect6, render_component.animation_group_ids,
                _b(render_component.fade), _b(render_component.use_drop_shadow), _b(render_component.preload_animations),
                render_component.fade_in_time, render_component.max_shadow_distance, _b(render_component.ignore_camera_collision),
                render_component.render_component_lod1, render_component.render_component_lod2, _b(render_component.gradual_snap),
                render_component.animation_flag, render_component.audio_meta_event_set, render_component.billboard_height,
                render_component.chat_bubble_offset, _b(render_component.static_billboard), render_component.lxfml_folder,
                _b(render_component.attach_indicators_to_node)
            )
            )

        # Reset dirty flag after saving
        render_component.dirty = False

    def __save_skill_component(self, conn: sqlite3.Connection, object_id: int, object_skills: ObjectSkills) -> None:
        # Delete all existing skills for this object ID
        if object_skills.zero_component_id:
            conn.execute(
            "DELETE FROM ObjectSkills WHERE objectTemplate=?",
            (object_id,)
            )
        else:
            print(f"WARNING: Saving ObjectSkills for object: {object_id} using non zero component ID, this is not standard!")
            for skill in object_skills.skills:
                # Delete all existing skills for this object ID
                conn.execute(
                "DELETE FROM ObjectSkills WHERE objectTemplate=?",
                (skill.object_Template,)
                )

        # Insert all current skills
        for skill_row in object_skills.skills:
            conn.execute(
                """
                INSERT INTO ObjectSkills (
                objectTemplate, skillID, castOnType, AICombatWeight
                ) VALUES (?, ?, ?, ?)
                """,
                (
                skill_row.object_Template,
                skill_row.skill_id,
                skill_row.cast_on_type,
                skill_row.ai_combat_weight
                )
            )

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


    ############################
    #-------- SAVE -------------
    ############################

    def _delete_object_skill(self, conn: sqlite3.Connection, object_template: int) -> None:
        """Delete all skills for a given object template."""
        conn.execute(
            "DELETE FROM ObjectSkills WHERE objectTemplate=?",
            (object_template,)
        )

    def id_exists(self, table: str, id_value: int, column: str = "id") -> bool:
        """Return True if a row with the given id exists in table."""
        if not table or not isinstance(table, str):
            raise ValueError("table must be a non-empty string")
        conn = self._connect_to_db()
        try:
            row = conn.execute(
                f"SELECT 1 FROM {table} WHERE {column}=? LIMIT 1",
                (id_value,)
            ).fetchone()
            return row is not None
        finally:
            conn.close()
