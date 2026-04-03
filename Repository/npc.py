from __future__ import annotations

import logging
import sqlite3
from typing import Any, Iterable

from Domain.domains import (
    Components,
    CurrencyTableRow,
    DestructibleComponent,
    InventoryComponentRow,
    LootMatrixIndexRow,
    LootMatrixRow,
    LootTableRow,
    LootTableIndexRow,
    MinifigComponent,
    MissionEmailRow,
    MissionNPCComponentRow,
    MissionRow,
    MissionTaskRow,
    MissionTextRow,
    NPC,
    ObjectTypes,
    PhysicsComponent,
    RenderComponent,
    RowCollection,
    ScriptComponent,
    VendorComponent,
)
from Repository.base import _b, _rb, baseRepository
from Repository.exceptions import NotFoundError

log = logging.getLogger(__name__)


_RENDER_MAP = {
    "id": "id",
    "render_asset": "render_asset",
    "icon_asset": "icon_asset",
    "icon_id": "IconID",
    "shader_id": "shader_id",
    "effect1": "effect1",
    "effect2": "effect2",
    "effect3": "effect3",
    "effect4": "effect4",
    "effect5": "effect5",
    "effect6": "effect6",
    "animation_group_ids": "animationGroupIDs",
    "fade": "fade",
    "use_drop_shadow": "usedropshadow",
    "preload_animations": "preloadAnimations",
    "fade_in_time": "fadeInTime",
    "max_shadow_distance": "maxShadowDistance",
    "ignore_camera_collision": "ignoreCameraCollision",
    "render_component_lod1": "renderComponentLOD1",
    "render_component_lod2": "renderComponentLOD2",
    "gradual_snap": "gradualSnap",
    "animation_flag": "animationFlag",
    "audio_meta_event_set": "AudioMetaEventSet",
    "billboard_height": "billboardHeight",
    "chat_bubble_offset": "chatBubbleOffset",
    "static_billboard": "staticBillboard",
    "lxfml_folder": "LXFMLFolder",
    "attach_indicators_to_node": "attachIndicatorsToNode",
}

_MINIFIG_MAP = {
    "id": "id",
    "head": "head",
    "chest": "chest",
    "legs": "legs",
    "hairstyle": "hairstyle",
    "haircolor": "haircolor",
    "chestdecal": "chestdecal",
    "headcolor": "headcolor",
    "lefthand": "lefthand",
    "righthand": "righthand",
    "eyebrowstyle": "eyebrowstyle",
    "eyesstyle": "eyesstyle",
    "mouthstyle": "mouthstyle",
}

_PHYSICS_MAP = {
    "id": "id",
    "static": "static",
    "physics_asset": "physics_asset",
    "jump": "jump",
    "doublejump": "doublejump",
    "speed": "speed",
    "rot_speed": "rotSpeed",
    "player_height": "playerHeight",
    "player_radius": "playerRadius",
    "pc_shape_type": "pcShapeType",
    "collision_group": "collisionGroup",
    "air_speed": "airSpeed",
    "boundary_asset": "boundaryAsset",
    "jump_air_speed": "jumpAirSpeed",
    "friction": "friction",
    "gravity_volume_asset": "gravityVolumeAsset",
}

_DESTRUCTIBLE_MAP = {
    "id": "id",
    "faction": "faction",
    "faction_list": "factionList",
    "life": "life",
    "imagination": "imagination",
    "loot_matrix_index": "LootMatrixIndex",
    "currency_index": "CurrencyIndex",
    "level": "level",
    "armor": "armor",
    "death_behavior": "death_behavior",
    "is_npc": "isnpc",
    "attack_priority": "attack_priority",
    "is_smashable": "isSmashable",
    "difficulty_level": "difficultyLevel",
}

_VENDOR_MAP = {
    "id": "id",
    "buy_scalar": "buyScalar",
    "sell_scalar": "sellScalar",
    "refresh_time_seconds": "refreshTimeSeconds",
    "loot_matrix_index": "LootMatrixIndex",
}

_SCRIPT_MAP = {
    "id": "id",
    "script_name": "script_name",
    "client_script_name": "client_script_name",
}

_LOOT_MATRIX_INDEX_MAP = {
    "loot_matrix_index": "LootMatrixIndex",
    "in_npc_editor": "inNpcEditor",
}

_LOOT_TABLE_INDEX_MAP = {
    "loot_table_index": "LootTableIndex",
}

_BOOL_FIELDS = {
    "RenderComponent": {"fade", "use_drop_shadow", "preload_animations", "ignore_camera_collision", "gradual_snap", "static_billboard", "attach_indicators_to_node"},
    "DestructibleComponent": {"is_npc", "is_smashable"},
    "LootMatrixIndexRow": {"in_npc_editor"},
    "InventoryComponentRow": {"equip"},
    "MissionNPCComponentRow": {"offers_mission", "accepts_mission"},
    "LootTableRow": {"mission_drop"},
    "MissionRow": {"is_choice_reward", "repeatable", "is_mission", "localize", "in_motd", "is_random"},
    "MissionTaskRow": {"localize"},
    "MissionTextRow": {"localize"},
    "MissionEmailRow": {"localize"},
}

_MISSION_MAP = {
    "id": "id",
    "defined_type": "defined_type",
    "defined_subtype": "defined_subtype",
    "ui_sort_order": "UISortOrder",
    "offer_object_id": "offer_objectID",
    "target_object_id": "target_objectID",
    "reward_currency": "reward_currency",
    "lego_score": "LegoScore",
    "reward_reputation": "reward_reputation",
    "is_choice_reward": "isChoiceReward",
    "reward_item1": "reward_item1",
    "reward_item1_count": "reward_item1_count",
    "reward_item2": "reward_item2",
    "reward_item2_count": "reward_item2_count",
    "reward_item3": "reward_item3",
    "reward_item3_count": "reward_item3_count",
    "reward_item4": "reward_item4",
    "reward_item4_count": "reward_item4_count",
    "reward_emote": "reward_emote",
    "reward_emote2": "reward_emote2",
    "reward_emote3": "reward_emote3",
    "reward_emote4": "reward_emote4",
    "reward_max_imagination": "reward_maximagination",
    "reward_max_health": "reward_maxhealth",
    "reward_max_inventory": "reward_maxinventory",
    "reward_max_model": "reward_maxmodel",
    "reward_max_widget": "reward_maxwidget",
    "reward_max_wallet": "reward_maxwallet",
    "repeatable": "repeatable",
    "reward_currency_repeatable": "reward_currency_repeatable",
    "reward_item1_repeatable": "reward_item1_repeatable",
    "reward_item1_repeat_count": "reward_item1_repeat_count",
    "reward_item2_repeatable": "reward_item2_repeatable",
    "reward_item2_repeat_count": "reward_item2_repeat_count",
    "reward_item3_repeatable": "reward_item3_repeatable",
    "reward_item3_repeat_count": "reward_item3_repeat_count",
    "reward_item4_repeatable": "reward_item4_repeatable",
    "reward_item4_repeat_count": "reward_item4_repeat_count",
    "time_limit": "time_limit",
    "is_mission": "isMission",
    "mission_icon_id": "missionIconID",
    "prereq_mission_id": "prereqMissionID",
    "localize": "localize",
    "in_motd": "inMOTD",
    "cooldown_time": "cooldownTime",
    "is_random": "isRandom",
    "random_pool": "randomPool",
    "ui_prereq_id": "UIPrereqID",
    "gate_version": "gate_version",
    "hud_states": "HUDStates",
    "loc_status": "locStatus",
    "reward_bank_inventory": "reward_bankinventory",
}

_MISSION_TASK_MAP = {
    "id": "id",
    "loc_status": "locStatus",
    "task_type": "taskType",
    "target": "target",
    "target_group": "targetGroup",
    "target_value": "targetValue",
    "task_param1": "taskParam1",
    "large_task_icon": "largeTaskIcon",
    "icon_id": "IconID",
    "uid": "uid",
    "large_task_icon_id": "largeTaskIconID",
    "localize": "localize",
    "gate_version": "gate_version",
}

_MISSION_TEXT_MAP = {
    "id": "id",
    "story_icon": "story_icon",
    "mission_icon": "missionIcon",
    "offer_npc_icon": "offerNPCIcon",
    "icon_id": "IconID",
    "state_1_anim": "state_1_anim",
    "state_2_anim": "state_2_anim",
    "state_3_anim": "state_3_anim",
    "state_4_anim": "state_4_anim",
    "state_3_turnin_anim": "state_3_turnin_anim",
    "state_4_turnin_anim": "state_4_turnin_anim",
    "onclick_anim": "onclick_anim",
    "cinematic_accepted": "CinematicAccepted",
    "cinematic_accepted_leadin": "CinematicAcceptedLeadin",
    "cinematic_completed": "CinematicCompleted",
    "cinematic_completed_leadin": "CinematicCompletedLeadin",
    "cinematic_repeatable": "CinematicRepeatable",
    "cinematic_repeatable_leadin": "CinematicRepeatableLeadin",
    "cinematic_repeatable_completed": "CinematicRepeatableCompleted",
    "cinematic_repeatable_completed_leadin": "CinematicRepeatableCompletedLeadin",
    "audio_event_guid_interact": "AudioEventGUID_Interact",
    "audio_event_guid_offer_accept": "AudioEventGUID_OfferAccept",
    "audio_event_guid_offer_deny": "AudioEventGUID_OfferDeny",
    "audio_event_guid_completed": "AudioEventGUID_Completed",
    "audio_event_guid_turn_in": "AudioEventGUID_TurnIn",
    "audio_event_guid_failed": "AudioEventGUID_Failed",
    "audio_event_guid_progress": "AudioEventGUID_Progress",
    "audio_music_cue_offer_accept": "AudioMusicCue_OfferAccept",
    "audio_music_cue_turn_in": "AudioMusicCue_TurnIn",
    "turn_in_icon_id": "turnInIconID",
    "localize": "localize",
    "loc_status": "locStatus",
    "gate_version": "gate_version",
}

_MISSION_EMAIL_MAP = {
    "id": "ID",
    "message_type": "messageType",
    "notification_group": "notificationGroup",
    "mission_id": "missionID",
    "attachment_lot": "attachmentLOT",
    "localize": "localize",
    "loc_status": "locStatus",
    "gate_version": "gate_version",
}


class NPCRepository(baseRepository):
    """Repository for NPC objects and their linked tables."""

    def __init__(self, db_path: str):
        super().__init__(db_path)
        self._log = logging.getLogger(__name__)

    def _has_linked_index(self, value: Any) -> bool:
        return isinstance(value, int) and value > 0

    def list_npcs(self, limit: int | None = None) -> list[dict[str, int | str]]:
        conn = self._connect_to_db()
        try:
            query = (
                "SELECT id, name FROM Objects "
                "WHERE type IN (?, ?) "
                "ORDER BY id"
            )
            params: list[Any] = [ObjectTypes.NPC_2.value, ObjectTypes.NPC.value]
            if limit is not None:
                query += " LIMIT ?"
                params.append(limit)
            rows = conn.execute(query, tuple(params)).fetchall()
            return [{"id": row["id"], "name": row["name"]} for row in rows]
        finally:
            conn.close()

    def get_lookup_options(self, lookup_name: str) -> list[dict[str, Any]]:
        conn = self._connect_to_db()
        try:
            if lookup_name == "icons":
                rows = conn.execute(
                    "SELECT IconID, IconName, IconPath FROM Icons ORDER BY IconID"
                ).fetchall()
                return [
                    {
                        "id": row["IconID"],
                        "label": (row["IconName"] or row["IconPath"] or ""),
                    }
                    for row in rows
                ]
            if lookup_name == "minifig_torsos":
                rows = conn.execute(
                    "SELECT ID, High_path FROM MinifigDecals_Torsos ORDER BY ID"
                ).fetchall()
                return [{"id": row["ID"], "label": row["High_path"] or ""} for row in rows]
            return []
        finally:
            conn.close()

    def generate_new_mission_id(self) -> int:
        return self._next_int("Missions", "id")

    def generate_new_loot_matrix_index(self) -> int:
        return self._next_int("LootMatrixIndex", "LootMatrixIndex")

    def generate_new_loot_table_index(self) -> int:
        return self._next_int("LootTableIndex", "LootTableIndex")

    def generate_new_loot_table_row_id(self) -> int:
        return self._next_int("LootTable", "id")

    def generate_new_currency_index(self) -> int:
        return self._next_int("CurrencyTable", "currencyIndex")

    def generate_new_currency_row_id(self) -> int:
        return self._next_int("CurrencyTable", "id")

    def generate_new_task_uid(self) -> int:
        return self._next_int("MissionTasks", "uid")

    def generate_new_mission_email_id(self) -> int:
        return self._next_int("MissionEmail", "ID")

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------
    def get(self, object_id: int) -> NPC:
        conn = self._connect_to_db()
        try:
            base = conn.execute(
                "SELECT id, name, type FROM Objects WHERE id=?",
                (object_id,),
            ).fetchone()
            if not base:
                raise NotFoundError(
                    f"NPC {object_id} not found",
                    table="Objects",
                    column="id",
                    value=object_id,
                )

            npc = NPC(id=base["id"], name=base["name"], type=base["type"])
            self._load_object_table(npc)

            registry_rows = conn.execute(
                "SELECT component_type, component_id FROM ComponentsRegistry WHERE id=?",
                (object_id,),
            ).fetchall()

            for row in registry_rows:
                ctype = row["component_type"]
                cid = row["component_id"]
                if ctype == Components.RENDER:
                    npc.components["RenderComponent"] = self._load_single_component(
                        conn,
                        object_id,
                        cid,
                        "RenderComponent",
                        RenderComponent,
                        _RENDER_MAP,
                    )
                elif ctype == Components.MINIFIG:
                    npc.components["MinifigComponent"] = self._load_single_component(
                        conn,
                        object_id,
                        cid,
                        "MinifigComponent",
                        MinifigComponent,
                        _MINIFIG_MAP,
                    )
                elif ctype == Components.SIMPLE_PHYSICS:
                    npc.components["PhysicsComponent"] = self._load_single_component(
                        conn,
                        object_id,
                        cid,
                        "PhysicsComponent",
                        PhysicsComponent,
                        _PHYSICS_MAP,
                    )
                elif ctype == Components.DESTROYABLE:
                    npc.components["DestructibleComponent"] = self._load_single_component(
                        conn,
                        object_id,
                        cid,
                        "DestructibleComponent",
                        DestructibleComponent,
                        _DESTRUCTIBLE_MAP,
                    )
                elif ctype == Components.VENDOR:
                    npc.components["VendorComponent"] = self._load_single_component(
                        conn,
                        object_id,
                        cid,
                        "VendorComponent",
                        VendorComponent,
                        _VENDOR_MAP,
                    )
                elif ctype == Components.SCRIPT:
                    npc.components["ScriptComponent"] = self._load_single_component(
                        conn,
                        object_id,
                        cid,
                        "ScriptComponent",
                        ScriptComponent,
                        _SCRIPT_MAP,
                    )
                elif ctype == Components.INVENTORY:
                    npc.components["InventoryComponent"] = self._load_inventory_rows(conn, cid, object_id)
                elif ctype == Components.MISSION_OFFER:
                    npc.components["MissionNPCComponent"] = self._load_mission_npc_rows(conn, cid, object_id)

            self._attach_vendor_rows(conn, npc)
            self._attach_destructible_rows(conn, npc)
            self._attach_mission_rows(conn, npc)
            return npc
        except Exception:
            self._log.exception("NPCRepository.get(%s) failed", object_id)
            raise
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------
    def save(self, npc: NPC) -> None:
        conn = self._connect_to_db()
        try:
            conn.execute("BEGIN")

            if getattr(npc, "dirty", False):
                self._save_object_table(conn, npc)

            self._save_direct_component(conn, npc, "RenderComponent", "RenderComponent", _RENDER_MAP)
            self._save_direct_component(conn, npc, "MinifigComponent", "MinifigComponent", _MINIFIG_MAP)
            self._save_direct_component(conn, npc, "PhysicsComponent", "PhysicsComponent", _PHYSICS_MAP)
            self._save_direct_component(conn, npc, "ScriptComponent", "ScriptComponent", _SCRIPT_MAP)
            self._save_vendor_index_rows(conn, npc)
            self._save_destructible_index_rows(conn, npc)
            self._save_direct_component(conn, npc, "DestructibleComponent", "DestructibleComponent", _DESTRUCTIBLE_MAP)
            self._save_direct_component(conn, npc, "VendorComponent", "VendorComponent", _VENDOR_MAP)

            self._save_inventory_rows(conn, npc)
            self._save_mission_npc_rows(conn, npc)
            self._save_vendor_rows(conn, npc)
            self._save_destructible_rows(conn, npc)
            self._save_mission_rows(conn, npc)
            self._rebuild_component_registry(conn, npc)

            conn.commit()
            self._mark_all_clean(npc)
        except Exception:
            self._log.exception(
                "NPCRepository.save(%s) failed; rolling back",
                getattr(npc, "object_id", "?"),
            )
            conn.rollback()
            raise
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------
    def delete(self, object_id: int) -> None:
        self.delete_object(object_id)

    def delete_object(self, object_id: int) -> None:
        npc = self.get(object_id)
        conn = self._connect_to_db()
        try:
            conn.execute("BEGIN")
            self._delete_vendor_rows(conn, npc)
            self._delete_destructible_rows(conn, npc)
            self._delete_mission_rows(conn, npc)
            inventory = npc.components.get("InventoryComponent")
            inventory_component_id = self._resolve_row_collection_component_id(inventory, fallback=object_id)
            conn.execute("DELETE FROM InventoryComponent WHERE id=?", (inventory_component_id,))
            mission_component = npc.components.get("MissionNPCComponent")
            mission_component_id = self._resolve_row_collection_component_id(mission_component, fallback=object_id)
            conn.execute("DELETE FROM MissionNPCComponent WHERE id=?", (mission_component_id,))
            self._delete_single_component(conn, npc.components.get("RenderComponent"), "RenderComponent")
            self._delete_single_component(conn, npc.components.get("MinifigComponent"), "MinifigComponent")
            self._delete_single_component(conn, npc.components.get("PhysicsComponent"), "PhysicsComponent")
            self._delete_single_component(conn, npc.components.get("VendorComponent"), "VendorComponent")
            self._delete_vendor_index_rows(conn, npc)
            self._delete_single_component(conn, npc.components.get("DestructibleComponent"), "DestructibleComponent")
            self._delete_destructible_index_rows(conn, npc)
            self._delete_single_component(conn, npc.components.get("ScriptComponent"), "ScriptComponent")
            conn.execute("DELETE FROM ComponentsRegistry WHERE id=?", (object_id,))
            conn.execute("DELETE FROM Objects WHERE id=?", (object_id,))
            conn.commit()
            self._log.info("Deleted NPC object_id=%s", object_id)
        except Exception:
            self._log.exception("Failed to delete NPC object_id=%s", object_id)
            conn.rollback()
            raise
        finally:
            conn.close()

    def delete_component(
        self,
        component_key: str,
        component_id: int | None = None,
        object_id: int | None = None,
    ) -> None:
        if object_id is None:
            raise ValueError("object_id is required for NPC component deletion")

        conn = self._connect_to_db()
        try:
            conn.execute("BEGIN")

            if component_key == "InventoryComponent":
                if component_id is None:
                    row = conn.execute(
                        "SELECT component_id FROM ComponentsRegistry WHERE id=? AND component_type=?",
                        (object_id, Components.INVENTORY),
                    ).fetchone()
                    component_id = row["component_id"] if row else object_id
                conn.execute("DELETE FROM InventoryComponent WHERE id=?", (component_id,))
                conn.execute(
                    "DELETE FROM ComponentsRegistry WHERE id=? AND component_type=?",
                    (object_id, Components.INVENTORY),
                )
            elif component_key == "MissionNPCComponent":
                npc = self.get(object_id)
                self._delete_mission_rows(conn, npc)
                if component_id is None:
                    row = conn.execute(
                        "SELECT component_id FROM ComponentsRegistry WHERE id=? AND component_type=?",
                        (object_id, Components.MISSION_OFFER),
                    ).fetchone()
                    component_id = row["component_id"] if row else object_id
                conn.execute("DELETE FROM MissionNPCComponent WHERE id=?", (component_id,))
                conn.execute(
                    "DELETE FROM ComponentsRegistry WHERE id=? AND component_type=?",
                    (object_id, Components.MISSION_OFFER),
                )
            elif component_key == "VendorComponent":
                npc = self.get(object_id)
                self._delete_vendor_rows(conn, npc)
                if component_id is not None:
                    conn.execute("DELETE FROM VendorComponent WHERE id=?", (component_id,))
                self._delete_vendor_index_rows(conn, npc)
                conn.execute(
                    "DELETE FROM ComponentsRegistry WHERE id=? AND component_type=?",
                    (object_id, Components.VENDOR),
                )
            elif component_key == "DestructibleComponent":
                npc = self.get(object_id)
                self._delete_destructible_rows(conn, npc)
                if component_id is not None:
                    conn.execute("DELETE FROM DestructibleComponent WHERE id=?", (component_id,))
                self._delete_destructible_index_rows(conn, npc)
                conn.execute(
                    "DELETE FROM ComponentsRegistry WHERE id=? AND component_type=?",
                    (object_id, Components.DESTROYABLE),
                )
            elif component_key == "RenderComponent" and component_id is not None:
                conn.execute("DELETE FROM RenderComponent WHERE id=?", (component_id,))
                conn.execute(
                    "DELETE FROM ComponentsRegistry WHERE id=? AND component_type=?",
                    (object_id, Components.RENDER),
                )
            elif component_key == "MinifigComponent" and component_id is not None:
                conn.execute("DELETE FROM MinifigComponent WHERE id=?", (component_id,))
                conn.execute(
                    "DELETE FROM ComponentsRegistry WHERE id=? AND component_type=?",
                    (object_id, Components.MINIFIG),
                )
            elif component_key == "PhysicsComponent" and component_id is not None:
                conn.execute("DELETE FROM PhysicsComponent WHERE id=?", (component_id,))
                conn.execute(
                    "DELETE FROM ComponentsRegistry WHERE id=? AND component_type=?",
                    (object_id, Components.SIMPLE_PHYSICS),
                )
            elif component_key == "ScriptComponent" and component_id is not None:
                conn.execute("DELETE FROM ScriptComponent WHERE id=?", (component_id,))
                conn.execute(
                    "DELETE FROM ComponentsRegistry WHERE id=? AND component_type=?",
                    (object_id, Components.SCRIPT),
                )
            else:
                raise ValueError(f"Unsupported NPC component delete key: {component_key}")

            conn.commit()
            self._log.info(
                "Deleted NPC component type=%s object_id=%s component_id=%s",
                component_key,
                object_id,
                component_id,
            )
        except Exception:
            self._log.exception(
                "Failed deleting NPC component type=%s object_id=%s component_id=%s",
                component_key,
                object_id,
                component_id,
            )
            conn.rollback()
            raise
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _next_int(self, table: str, column: str) -> int:
        conn = self._connect_to_db()
        try:
            row = conn.execute(f"SELECT MAX({column}) AS max_value FROM {table}").fetchone()
            max_value = row["max_value"] if row is not None else None
            return (int(max_value) + 1) if max_value is not None else 1
        finally:
            conn.close()

    def _load_single_component(
        self,
        conn: sqlite3.Connection,
        object_id: int,
        component_id: int,
        component_name: str,
        cls: type[Any],
        field_map: dict[str, str],
    ) -> Any:
        row = conn.execute(
            f"SELECT * FROM {component_name} WHERE id=?",
            (component_id,),
        ).fetchone()
        if not row:
            raise NotFoundError(
                f"{component_name} {component_id} not found for NPC {object_id}",
                table=component_name,
                column="id",
                value=component_id,
            )

        kwargs: dict[str, Any] = {}
        bool_fields = _BOOL_FIELDS.get(cls.__name__, set())
        for attr, column in field_map.items():
            value = row[column]
            if attr in bool_fields:
                value = _rb(value)
            kwargs[attr] = value
        return cls(**kwargs)

    def _save_direct_component(
        self,
        conn: sqlite3.Connection,
        npc: NPC,
        key: str,
        table: str,
        field_map: dict[str, str],
    ) -> None:
        component = npc.components.get(key)
        if component is None or not getattr(component, "dirty", False):
            return
        values = self._as_db_values(component, field_map)
        self._upsert_single_row(conn, table, values)
        component.dirty = False
        self._log.debug("Saved %s object_id=%s component_id=%s", key, npc.object_id, values.get("id"))

    def _as_db_values(self, obj: Any, field_map: dict[str, str]) -> dict[str, Any]:
        values: dict[str, Any] = {}
        bool_fields = _BOOL_FIELDS.get(obj.__class__.__name__, set())
        for attr, column in field_map.items():
            value = getattr(obj, attr)
            if attr in bool_fields:
                value = _b(bool(value))
            values[column] = value
        return values

    def _upsert_single_row(
        self,
        conn: sqlite3.Connection,
        table: str,
        values: dict[str, Any],
        id_column: str = "id",
    ) -> None:
        columns = list(values.keys())
        update_cols = [c for c in columns if c != id_column]
        update_sql = ", ".join(f"{col}=?" for col in update_cols)
        update_params = [values[col] for col in update_cols] + [values[id_column]]
        result = conn.execute(
            f"UPDATE {table} SET {update_sql} WHERE {id_column}=?",
            update_params,
        )
        if result.rowcount == 0:
            placeholders = ", ".join("?" for _ in columns)
            conn.execute(
                f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})",
                [values[col] for col in columns],
            )

    def _resolve_row_collection_component_id(self, collection: Any, *, fallback: int) -> int:
        component_id = getattr(collection, "component_id", None)
        if isinstance(component_id, int) and component_id > 0:
            return component_id
        if isinstance(collection, RowCollection):
            for row in collection.rows:
                row_id = getattr(row, "id", None)
                if isinstance(row_id, int) and row_id > 0:
                    collection.component_id = row_id
                    return row_id
        return fallback

    def _load_inventory_rows(self, conn: sqlite3.Connection, component_id: int, object_id: int) -> RowCollection:
        rows = conn.execute(
            "SELECT * FROM InventoryComponent WHERE id=? ORDER BY itemid",
            (component_id,),
        ).fetchall()
        collection_rows = [
            InventoryComponentRow(
                id=row["id"],
                itemid=row["itemid"],
                count=row["count"],
                equip=_rb(row["equip"]),
            )
            for row in rows
        ]
        self._log.debug(
            "Loaded InventoryComponent rows=%s object_id=%s component_id=%s",
            len(collection_rows),
            object_id,
            component_id,
        )
        return RowCollection(
            rows=collection_rows,
            key_field="itemid",
            label_prefix="Item",
            component_id=component_id,
            loaded_keys={component_id},
        )

    def _save_inventory_rows(self, conn: sqlite3.Connection, npc: NPC) -> None:
        collection = npc.components.get("InventoryComponent")
        if not isinstance(collection, RowCollection) or not collection.dirty:
            return
        component_id = self._resolve_row_collection_component_id(collection, fallback=npc.object_id)
        conn.execute("DELETE FROM InventoryComponent WHERE id=?", (component_id,))
        for row in collection.rows:
            conn.execute(
                """
                INSERT INTO InventoryComponent (id, itemid, count, equip)
                VALUES (?, ?, ?, ?)
                """,
                (component_id, row.itemid, row.count, _b(row.equip)),
            )
            row.id = component_id
            row.dirty = False
        collection.component_id = component_id
        collection.loaded_keys = {component_id}
        collection.dirty = False

    def _load_mission_npc_rows(self, conn: sqlite3.Connection, component_id: int, object_id: int) -> RowCollection:
        rows = conn.execute(
            "SELECT * FROM MissionNPCComponent WHERE id=? ORDER BY missionID",
            (component_id,),
        ).fetchall()
        collection_rows = [
            MissionNPCComponentRow(
                id=row["id"],
                mission_id=row["missionID"],
                offers_mission=_rb(row["offersMission"]),
                accepts_mission=_rb(row["acceptsMission"]),
                gate_version=row["gate_version"],
            )
            for row in rows
        ]
        self._log.debug(
            "Loaded MissionNPCComponent rows=%s object_id=%s component_id=%s",
            len(collection_rows),
            object_id,
            component_id,
        )
        return RowCollection(
            rows=collection_rows,
            key_field="mission_id",
            label_prefix="Mission",
            component_id=component_id,
            loaded_keys={component_id},
        )

    def _save_mission_npc_rows(self, conn: sqlite3.Connection, npc: NPC) -> None:
        collection = npc.components.get("MissionNPCComponent")
        if not isinstance(collection, RowCollection) or not collection.dirty:
            return
        component_id = self._resolve_row_collection_component_id(collection, fallback=npc.object_id)
        conn.execute("DELETE FROM MissionNPCComponent WHERE id=?", (component_id,))
        for row in collection.rows:
            conn.execute(
                """
                INSERT INTO MissionNPCComponent (id, missionID, offersMission, acceptsMission, gate_version)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    component_id,
                    row.mission_id,
                    _b(row.offers_mission),
                    _b(row.accepts_mission),
                    row.gate_version,
                ),
            )
            row.id = component_id
            row.dirty = False
        collection.component_id = component_id
        collection.loaded_keys = {component_id}
        collection.dirty = False

    def _save_keyed_row_collection(
        self,
        conn: sqlite3.Connection,
        collection: Any,
        *,
        table: str,
        scope_column: str,
        field_map: dict[str, str],
    ) -> None:
        if not isinstance(collection, RowCollection) or not collection.dirty:
            return
        current_keys = {
            getattr(row, collection.key_field, None)
            for row in collection.rows
            if getattr(row, collection.key_field, None) is not None
        }
        self._replace_rows_by_scope(
            conn,
            table,
            scope_column,
            set(collection.loaded_keys) | current_keys,
            collection.rows,
            field_map,
        )
        collection.loaded_keys = current_keys
        collection.dirty = False

    def _save_vendor_index_rows(self, conn: sqlite3.Connection, npc: NPC) -> None:
        self._sync_vendor_index_collections(npc)
        self._save_keyed_row_collection(
            conn,
            npc.components.get("VendorLootMatrixIndex"),
            table="LootMatrixIndex",
            scope_column="LootMatrixIndex",
            field_map=_LOOT_MATRIX_INDEX_MAP,
        )
        self._save_keyed_row_collection(
            conn,
            npc.components.get("VendorLootTableIndex"),
            table="LootTableIndex",
            scope_column="LootTableIndex",
            field_map=_LOOT_TABLE_INDEX_MAP,
        )

    def _save_destructible_index_rows(self, conn: sqlite3.Connection, npc: NPC) -> None:
        self._sync_destructible_index_collections(npc)
        self._save_keyed_row_collection(
            conn,
            npc.components.get("DestructibleLootMatrixIndex"),
            table="LootMatrixIndex",
            scope_column="LootMatrixIndex",
            field_map=_LOOT_MATRIX_INDEX_MAP,
        )
        self._save_keyed_row_collection(
            conn,
            npc.components.get("DestructibleLootTableIndex"),
            table="LootTableIndex",
            scope_column="LootTableIndex",
            field_map=_LOOT_TABLE_INDEX_MAP,
        )

    def _sync_single_matrix_index_collection(self, npc: NPC, component_key: str, collection_key: str) -> None:
        component = npc.components.get(component_key)
        if component is None:
            return
        loot_matrix_index = getattr(component, "loot_matrix_index", None)
        collection = npc.components.get(collection_key)
        if not isinstance(collection, RowCollection):
            collection = RowCollection(rows=[], key_field="loot_matrix_index", label_prefix="LootMatrixIndex")
            npc.components[collection_key] = collection
        current_rows = list(collection.rows)
        if not self._has_linked_index(loot_matrix_index):
            desired_rows: list[LootMatrixIndexRow] = []
        else:
            current_row = next(
                (row for row in current_rows if getattr(row, "loot_matrix_index", None) == loot_matrix_index),
                None,
            )
            desired_rows = [
                LootMatrixIndexRow(
                    loot_matrix_index=int(loot_matrix_index),
                    in_npc_editor=bool(getattr(current_row, "in_npc_editor", True)),
                )
            ]
        if current_rows != desired_rows:
            collection.rows = desired_rows
            collection.dirty = True

    def _sync_loot_table_index_collection(self, npc: NPC, matrix_key: str, table_key: str, collection_key: str) -> None:
        collection = npc.components.get(collection_key)
        if not isinstance(collection, RowCollection):
            collection = RowCollection(rows=[], key_field="loot_table_index", label_prefix="LootTableIndex")
            npc.components[collection_key] = collection
        current_rows = list(collection.rows)
        current_indices = {
            getattr(row, "loot_table_index", None)
            for row in current_rows
            if getattr(row, "loot_table_index", None) is not None
        }
        desired_indices = {
            getattr(row, "loot_table_index", None)
            for key in (matrix_key, table_key)
            for row in getattr(npc.components.get(key), "rows", []) or []
            if getattr(row, "loot_table_index", None) is not None
        }
        desired_rows = [LootTableIndexRow(loot_table_index=int(index)) for index in sorted(desired_indices)]
        if current_rows != desired_rows or current_indices != desired_indices:
            collection.rows = desired_rows
            collection.dirty = True

    def _sync_vendor_index_collections(self, npc: NPC) -> None:
        self._sync_single_matrix_index_collection(npc, "VendorComponent", "VendorLootMatrixIndex")
        self._sync_loot_table_index_collection(npc, "VendorLootMatrix", "VendorLootTable", "VendorLootTableIndex")

    def _sync_destructible_index_collections(self, npc: NPC) -> None:
        self._sync_single_matrix_index_collection(npc, "DestructibleComponent", "DestructibleLootMatrixIndex")
        self._sync_loot_table_index_collection(
            npc,
            "DestructibleLootMatrix",
            "DestructibleLootTable",
            "DestructibleLootTableIndex",
        )

    def _attach_vendor_rows(self, conn: sqlite3.Connection, npc: NPC) -> None:
        vendor = npc.components.get("VendorComponent")
        if not isinstance(vendor, VendorComponent):
            return

        loot_matrix_indices: set[int] = set()
        vendor_matrix: list[LootMatrixRow] = []
        if self._has_linked_index(vendor.loot_matrix_index):
            loot_matrix_indices = {int(vendor.loot_matrix_index)}
            matrix_rows = conn.execute(
                """
                SELECT rowid AS row_id, *
                FROM LootMatrix
                WHERE LootMatrixIndex=?
                ORDER BY rowid
                """,
                (vendor.loot_matrix_index,),
            ).fetchall()
            vendor_matrix = [
                LootMatrixRow(
                    row_id=row["row_id"],
                    loot_matrix_index=row["LootMatrixIndex"],
                    loot_table_index=row["LootTableIndex"],
                    rarity_table_index=row["RarityTableIndex"],
                    percent=row["percent"],
                    min_to_drop=row["minToDrop"],
                    max_to_drop=row["maxToDrop"],
                    id=row["id"],
                    flag_id=row["flagID"],
                    gate_version=row["gate_version"],
                )
                for row in matrix_rows
            ]
        loot_table_indices = {row.loot_table_index for row in vendor_matrix}
        npc.components["VendorLootMatrixIndex"] = RowCollection(
            rows=self._load_loot_matrix_index_rows(conn, loot_matrix_indices),
            key_field="loot_matrix_index",
            label_prefix="LootMatrixIndex",
            loaded_keys=loot_matrix_indices,
        )
        loot_table_rows = self._load_loot_tables_by_indices(conn, loot_table_indices)

        npc.components["VendorLootMatrix"] = RowCollection(
            rows=vendor_matrix,
            key_field="ui_key",
            label_prefix="LootMatrix",
            loaded_keys=loot_matrix_indices,
        )
        npc.components["VendorLootTableIndex"] = RowCollection(
            rows=self._load_loot_table_index_rows(conn, loot_table_indices),
            key_field="loot_table_index",
            label_prefix="LootTableIndex",
            loaded_keys=loot_table_indices,
        )
        npc.components["VendorLootTable"] = RowCollection(
            rows=loot_table_rows,
            key_field="id",
            label_prefix="LootTable",
            loaded_keys=loot_table_indices,
        )

    def _attach_destructible_rows(self, conn: sqlite3.Connection, npc: NPC) -> None:
        destructible = npc.components.get("DestructibleComponent")
        if not isinstance(destructible, DestructibleComponent):
            return

        matrix_rows: list[LootMatrixRow] = []
        loot_table_indices: set[int] = set()
        loot_matrix_indices: set[int] = set()
        if destructible.loot_matrix_index is not None:
            loot_matrix_indices = {destructible.loot_matrix_index}
            rows = conn.execute(
                """
                SELECT rowid AS row_id, *
                FROM LootMatrix
                WHERE LootMatrixIndex=?
                ORDER BY rowid
                """,
                (destructible.loot_matrix_index,),
            ).fetchall()
            matrix_rows = [
                LootMatrixRow(
                    row_id=row["row_id"],
                    loot_matrix_index=row["LootMatrixIndex"],
                    loot_table_index=row["LootTableIndex"],
                    rarity_table_index=row["RarityTableIndex"],
                    percent=row["percent"],
                    min_to_drop=row["minToDrop"],
                    max_to_drop=row["maxToDrop"],
                    id=row["id"],
                    flag_id=row["flagID"],
                    gate_version=row["gate_version"],
                )
                for row in rows
            ]
            loot_table_indices = {row.loot_table_index for row in matrix_rows}

        npc.components["DestructibleLootMatrixIndex"] = RowCollection(
            rows=self._load_loot_matrix_index_rows(conn, loot_matrix_indices),
            key_field="loot_matrix_index",
            label_prefix="LootMatrixIndex",
            loaded_keys=loot_matrix_indices,
        )
        npc.components["DestructibleLootMatrix"] = RowCollection(
            rows=matrix_rows,
            key_field="ui_key",
            label_prefix="LootMatrix",
            loaded_keys=loot_matrix_indices,
        )
        npc.components["DestructibleLootTableIndex"] = RowCollection(
            rows=self._load_loot_table_index_rows(conn, loot_table_indices),
            key_field="loot_table_index",
            label_prefix="LootTableIndex",
            loaded_keys=loot_table_indices,
        )
        npc.components["DestructibleLootTable"] = RowCollection(
            rows=self._load_loot_tables_by_indices(conn, loot_table_indices),
            key_field="id",
            label_prefix="LootTable",
            loaded_keys=loot_table_indices,
        )

        currency_rows: list[CurrencyTableRow] = []
        loaded_currency_keys: set[int] = set()
        if destructible.currency_index is not None:
            rows = conn.execute(
                """
                SELECT * FROM CurrencyTable
                WHERE currencyIndex=?
                ORDER BY id
                """,
                (destructible.currency_index,),
            ).fetchall()
            currency_rows = [
                CurrencyTableRow(
                    currency_index=row["currencyIndex"],
                    npcminlevel=row["npcminlevel"],
                    minvalue=row["minvalue"],
                    maxvalue=row["maxvalue"],
                    id=row["id"],
                )
                for row in rows
            ]
            loaded_currency_keys = {destructible.currency_index}

        npc.components["CurrencyTable"] = RowCollection(
            rows=currency_rows,
            key_field="id",
            label_prefix="CurrencyTable",
            loaded_keys=loaded_currency_keys,
        )

    def _load_loot_matrix_index_rows(
        self,
        conn: sqlite3.Connection,
        loot_matrix_indices: Iterable[int],
    ) -> list[LootMatrixIndexRow]:
        ids = sorted({int(idx) for idx in loot_matrix_indices if idx is not None})
        if not ids:
            return []
        return self._load_rows_by_ids(
            conn,
            "LootMatrixIndex",
            "LootMatrixIndex",
            set(ids),
            LootMatrixIndexRow,
            _LOOT_MATRIX_INDEX_MAP,
        )

    def _load_loot_tables_by_indices(
        self,
        conn: sqlite3.Connection,
        loot_table_indices: Iterable[int],
    ) -> list[LootTableRow]:
        ids = sorted({int(idx) for idx in loot_table_indices if idx is not None})
        if not ids:
            return []
        placeholders = ", ".join("?" for _ in ids)
        rows = conn.execute(
            f"""
            SELECT * FROM LootTable
            WHERE LootTableIndex IN ({placeholders})
            ORDER BY id
            """,
            tuple(ids),
        ).fetchall()
        return [
            LootTableRow(
                itemid=row["itemid"],
                loot_table_index=row["LootTableIndex"],
                id=row["id"],
                mission_drop=_rb(row["MissionDrop"]),
                sort_priority=row["sortPriority"],
            )
            for row in rows
        ]

    def _load_loot_table_index_rows(
        self,
        conn: sqlite3.Connection,
        loot_table_indices: Iterable[int],
    ) -> list[LootTableIndexRow]:
        ids = sorted({int(idx) for idx in loot_table_indices if idx is not None})
        if not ids:
            return []
        return self._load_rows_by_ids(
            conn,
            "LootTableIndex",
            "LootTableIndex",
            set(ids),
            LootTableIndexRow,
            _LOOT_TABLE_INDEX_MAP,
        )

    def _attach_mission_rows(self, conn: sqlite3.Connection, npc: NPC) -> None:
        mission_collection = npc.components.get("MissionNPCComponent")
        if not isinstance(mission_collection, RowCollection):
            return
        mission_ids = {row.mission_id for row in mission_collection.rows}

        npc.components["Missions"] = RowCollection(
            rows=self._load_rows_by_ids(conn, "Missions", "id", mission_ids, MissionRow, _MISSION_MAP),
            key_field="id",
            label_prefix="Mission",
            loaded_keys=set(mission_ids),
        )
        npc.components["MissionTasks"] = RowCollection(
            rows=self._load_rows_by_ids(conn, "MissionTasks", "id", mission_ids, MissionTaskRow, _MISSION_TASK_MAP),
            key_field="uid",
            label_prefix="Task",
            loaded_keys=set(mission_ids),
        )
        npc.components["MissionText"] = RowCollection(
            rows=self._load_rows_by_ids(conn, "MissionText", "id", mission_ids, MissionTextRow, _MISSION_TEXT_MAP),
            key_field="id",
            label_prefix="Text",
            loaded_keys=set(mission_ids),
        )
        npc.components["MissionEmail"] = RowCollection(
            rows=self._load_rows_by_ids(conn, "MissionEmail", "missionID", mission_ids, MissionEmailRow, _MISSION_EMAIL_MAP),
            key_field="id",
            label_prefix="Email",
            loaded_keys=set(mission_ids),
        )

    def _load_rows_by_ids(
        self,
        conn: sqlite3.Connection,
        table: str,
        where_column: str,
        ids: set[int],
        row_cls: type[Any],
        field_map: dict[str, str],
    ) -> list[Any]:
        if not ids:
            return []
        placeholders = ", ".join("?" for _ in ids)
        rows = conn.execute(
            f"SELECT * FROM {table} WHERE {where_column} IN ({placeholders}) ORDER BY 1",
            tuple(sorted(ids)),
        ).fetchall()
        bool_fields = _BOOL_FIELDS.get(row_cls.__name__, set())
        results = []
        for row in rows:
            kwargs: dict[str, Any] = {}
            for attr, column in field_map.items():
                value = row[column]
                if attr in bool_fields:
                    value = _rb(value)
                kwargs[attr] = value
            results.append(row_cls(**kwargs))
        return results

    def _save_vendor_rows(self, conn: sqlite3.Connection, npc: NPC) -> None:
        vendor = npc.components.get("VendorComponent")
        matrix_collection = npc.components.get("VendorLootMatrix")
        table_collection = npc.components.get("VendorLootTable")
        if not isinstance(vendor, VendorComponent):
            return

        if isinstance(matrix_collection, RowCollection) and matrix_collection.dirty:
            keys = set(matrix_collection.loaded_keys)
            if self._has_linked_index(vendor.loot_matrix_index):
                keys.add(int(vendor.loot_matrix_index))
            for key in keys:
                if key is None:
                    continue
                conn.execute("DELETE FROM LootMatrix WHERE LootMatrixIndex=?", (key,))
            if self._has_linked_index(vendor.loot_matrix_index):
                for row in matrix_collection.rows:
                    result = conn.execute(
                        """
                        INSERT INTO LootMatrix (
                            LootMatrixIndex, LootTableIndex, RarityTableIndex, percent,
                            minToDrop, maxToDrop, id, flagID, gate_version
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            vendor.loot_matrix_index,
                            row.loot_table_index,
                            row.rarity_table_index,
                            row.percent,
                            row.min_to_drop,
                            row.max_to_drop,
                            row.id,
                            row.flag_id,
                            row.gate_version,
                        ),
                    )
                    row.loot_matrix_index = vendor.loot_matrix_index
                    row.row_id = result.lastrowid
                    row.dirty = False
            matrix_collection.loaded_keys = {int(vendor.loot_matrix_index)} if self._has_linked_index(vendor.loot_matrix_index) else set()
            matrix_collection.dirty = False

        if isinstance(table_collection, RowCollection) and table_collection.dirty:
            self._save_loot_table_rows(conn, table_collection)

    def _save_destructible_rows(self, conn: sqlite3.Connection, npc: NPC) -> None:
        destructible = npc.components.get("DestructibleComponent")
        matrix_collection = npc.components.get("DestructibleLootMatrix")
        table_collection = npc.components.get("DestructibleLootTable")
        currency_collection = npc.components.get("CurrencyTable")
        if not isinstance(destructible, DestructibleComponent):
            return

        if isinstance(matrix_collection, RowCollection) and matrix_collection.dirty:
            keys = set(matrix_collection.loaded_keys)
            if destructible.loot_matrix_index is not None:
                keys.add(destructible.loot_matrix_index)
            for key in keys:
                if key is None:
                    continue
                conn.execute("DELETE FROM LootMatrix WHERE LootMatrixIndex=?", (key,))
            if destructible.loot_matrix_index is not None:
                for row in matrix_collection.rows:
                    result = conn.execute(
                        """
                        INSERT INTO LootMatrix (
                            LootMatrixIndex, LootTableIndex, RarityTableIndex, percent,
                            minToDrop, maxToDrop, id, flagID, gate_version
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            destructible.loot_matrix_index,
                            row.loot_table_index,
                            row.rarity_table_index,
                            row.percent,
                            row.min_to_drop,
                            row.max_to_drop,
                            row.id,
                            row.flag_id,
                            row.gate_version,
                        ),
                    )
                    row.loot_matrix_index = destructible.loot_matrix_index
                    row.row_id = result.lastrowid
                    row.dirty = False
            matrix_collection.loaded_keys = {destructible.loot_matrix_index} if destructible.loot_matrix_index is not None else set()
            matrix_collection.dirty = False

        if isinstance(table_collection, RowCollection) and table_collection.dirty:
            self._save_loot_table_rows(conn, table_collection)

        if isinstance(currency_collection, RowCollection) and currency_collection.dirty:
            keys = set(currency_collection.loaded_keys)
            if destructible.currency_index is not None:
                keys.add(destructible.currency_index)
            for key in keys:
                if key is None:
                    continue
                conn.execute("DELETE FROM CurrencyTable WHERE currencyIndex=?", (key,))
            if destructible.currency_index is not None:
                for row in currency_collection.rows:
                    conn.execute(
                        """
                        INSERT INTO CurrencyTable (currencyIndex, npcminlevel, minvalue, maxvalue, id)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            destructible.currency_index,
                            row.npcminlevel,
                            row.minvalue,
                            row.maxvalue,
                            row.id,
                        ),
                    )
                    row.currency_index = destructible.currency_index
                    row.dirty = False
            currency_collection.loaded_keys = {destructible.currency_index} if destructible.currency_index is not None else set()
            currency_collection.dirty = False

    def _save_loot_table_rows(self, conn: sqlite3.Connection, table_collection: RowCollection) -> None:
        keys = set(table_collection.loaded_keys)
        keys.update(row.loot_table_index for row in table_collection.rows)
        for key in keys:
            conn.execute("DELETE FROM LootTable WHERE LootTableIndex=?", (key,))
        for row in table_collection.rows:
            conn.execute(
                """
                INSERT INTO LootTable (itemid, LootTableIndex, id, MissionDrop, sortPriority)
                VALUES (?, ?, ?, ?, ?)
                """,
                (row.itemid, row.loot_table_index, row.id, _b(row.mission_drop), row.sort_priority),
            )
            row.dirty = False
        table_collection.loaded_keys = {row.loot_table_index for row in table_collection.rows}
        table_collection.dirty = False

    def _save_mission_rows(self, conn: sqlite3.Connection, npc: NPC) -> None:
        mission_component = npc.components.get("MissionNPCComponent")
        if not isinstance(mission_component, RowCollection):
            return
        current_ids = {row.mission_id for row in mission_component.rows}

        missions = npc.components.get("Missions")
        if isinstance(missions, RowCollection) and missions.dirty:
            self._replace_rows_by_scope(
                conn,
                "Missions",
                "id",
                set(missions.loaded_keys) | current_ids,
                missions.rows,
                _MISSION_MAP,
            )
            missions.loaded_keys = set(current_ids)
            missions.dirty = False

        tasks = npc.components.get("MissionTasks")
        if isinstance(tasks, RowCollection) and tasks.dirty:
            self._replace_rows_by_scope(
                conn,
                "MissionTasks",
                "id",
                set(tasks.loaded_keys) | current_ids,
                tasks.rows,
                _MISSION_TASK_MAP,
            )
            tasks.loaded_keys = set(current_ids)
            tasks.dirty = False

        mission_text = npc.components.get("MissionText")
        if isinstance(mission_text, RowCollection) and mission_text.dirty:
            self._replace_rows_by_scope(
                conn,
                "MissionText",
                "id",
                set(mission_text.loaded_keys) | current_ids,
                mission_text.rows,
                _MISSION_TEXT_MAP,
            )
            mission_text.loaded_keys = set(current_ids)
            mission_text.dirty = False

        mission_email = npc.components.get("MissionEmail")
        if isinstance(mission_email, RowCollection) and mission_email.dirty:
            self._replace_rows_by_scope(
                conn,
                "MissionEmail",
                "missionID",
                set(mission_email.loaded_keys) | current_ids,
                mission_email.rows,
                _MISSION_EMAIL_MAP,
            )
            mission_email.loaded_keys = set(current_ids)
            mission_email.dirty = False

    def _replace_rows_by_scope(
        self,
        conn: sqlite3.Connection,
        table: str,
        scope_column: str,
        scope_values: set[int],
        rows: list[Any],
        field_map: dict[str, str],
    ) -> None:
        if scope_values:
            placeholders = ", ".join("?" for _ in scope_values)
            conn.execute(
                f"DELETE FROM {table} WHERE {scope_column} IN ({placeholders})",
                tuple(sorted(scope_values)),
            )
        if not rows:
            return

        columns = list(field_map.values())
        placeholders = ", ".join("?" for _ in columns)
        bool_fields = _BOOL_FIELDS.get(rows[0].__class__.__name__, set())
        for row in rows:
            values = []
            for attr, column in field_map.items():
                value = getattr(row, attr)
                if attr in bool_fields:
                    value = _b(bool(value))
                values.append(value)
            conn.execute(
                f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})",
                values,
            )
            row.dirty = False

    def _rebuild_component_registry(self, conn: sqlite3.Connection, npc: NPC) -> None:
        conn.execute("DELETE FROM ComponentsRegistry WHERE id=?", (npc.object_id,))
        entries: list[tuple[int, int]] = []

        render = npc.components.get("RenderComponent")
        if isinstance(render, RenderComponent):
            entries.append((Components.RENDER, render.id))

        minifig = npc.components.get("MinifigComponent")
        if isinstance(minifig, MinifigComponent):
            entries.append((Components.MINIFIG, minifig.id))

        physics = npc.components.get("PhysicsComponent")
        if isinstance(physics, PhysicsComponent):
            entries.append((Components.SIMPLE_PHYSICS, physics.id))

        destructible = npc.components.get("DestructibleComponent")
        if isinstance(destructible, DestructibleComponent):
            entries.append((Components.DESTROYABLE, destructible.id))

        vendor = npc.components.get("VendorComponent")
        if isinstance(vendor, VendorComponent):
            entries.append((Components.VENDOR, vendor.id))

        script = npc.components.get("ScriptComponent")
        if isinstance(script, ScriptComponent):
            entries.append((Components.SCRIPT, script.id))

        inventory = npc.components.get("InventoryComponent")
        if isinstance(inventory, RowCollection):
            entries.append(
                (
                    Components.INVENTORY,
                    self._resolve_row_collection_component_id(inventory, fallback=npc.object_id),
                )
            )

        mission_component = npc.components.get("MissionNPCComponent")
        if isinstance(mission_component, RowCollection):
            entries.append(
                (
                    Components.MISSION_OFFER,
                    self._resolve_row_collection_component_id(mission_component, fallback=npc.object_id),
                )
            )

        for component_type, component_id in entries:
            conn.execute(
                "INSERT INTO ComponentsRegistry (id, component_type, component_id) VALUES (?, ?, ?)",
                (npc.object_id, component_type, component_id),
            )

    def _delete_single_component(self, conn: sqlite3.Connection, component: Any, table: str) -> None:
        if component is None:
            return
        component_id = getattr(component, "id", None)
        if component_id is None:
            return
        conn.execute(f"DELETE FROM {table} WHERE id=?", (component_id,))

    def _delete_vendor_rows(self, conn: sqlite3.Connection, npc: NPC) -> None:
        vendor = npc.components.get("VendorComponent")
        if not isinstance(vendor, VendorComponent):
            return
        if self._has_linked_index(vendor.loot_matrix_index):
            conn.execute("DELETE FROM LootMatrix WHERE LootMatrixIndex=?", (vendor.loot_matrix_index,))
        loot_table_collection = npc.components.get("VendorLootTable")
        indices = self._extract_loot_table_indices(loot_table_collection)
        for index in indices:
            conn.execute("DELETE FROM LootTable WHERE LootTableIndex=?", (index,))

    def _delete_vendor_index_rows(self, conn: sqlite3.Connection, npc: NPC) -> None:
        vendor = npc.components.get("VendorComponent")
        if isinstance(vendor, VendorComponent) and self._has_linked_index(vendor.loot_matrix_index):
            conn.execute("DELETE FROM LootMatrixIndex WHERE LootMatrixIndex=?", (vendor.loot_matrix_index,))
        loot_table_collection = npc.components.get("VendorLootTableIndex")
        for index in self._extract_index_collection_keys(loot_table_collection):
            conn.execute("DELETE FROM LootTableIndex WHERE LootTableIndex=?", (index,))

    def _delete_destructible_rows(self, conn: sqlite3.Connection, npc: NPC) -> None:
        destructible = npc.components.get("DestructibleComponent")
        if not isinstance(destructible, DestructibleComponent):
            return
        if destructible.loot_matrix_index is not None:
            conn.execute("DELETE FROM LootMatrix WHERE LootMatrixIndex=?", (destructible.loot_matrix_index,))
        loot_table_collection = npc.components.get("DestructibleLootTable")
        for index in self._extract_loot_table_indices(loot_table_collection):
            conn.execute("DELETE FROM LootTable WHERE LootTableIndex=?", (index,))
        if destructible.currency_index is not None:
            conn.execute("DELETE FROM CurrencyTable WHERE currencyIndex=?", (destructible.currency_index,))

    def _delete_destructible_index_rows(self, conn: sqlite3.Connection, npc: NPC) -> None:
        destructible = npc.components.get("DestructibleComponent")
        if isinstance(destructible, DestructibleComponent) and destructible.loot_matrix_index is not None:
            conn.execute("DELETE FROM LootMatrixIndex WHERE LootMatrixIndex=?", (destructible.loot_matrix_index,))
        loot_table_collection = npc.components.get("DestructibleLootTableIndex")
        for index in self._extract_index_collection_keys(loot_table_collection):
            conn.execute("DELETE FROM LootTableIndex WHERE LootTableIndex=?", (index,))

    def _delete_mission_rows(self, conn: sqlite3.Connection, npc: NPC) -> None:
        mission_component = npc.components.get("MissionNPCComponent")
        mission_ids: set[int] = set()
        component_id = npc.object_id
        if isinstance(mission_component, RowCollection):
            component_id = self._resolve_row_collection_component_id(mission_component, fallback=npc.object_id)
            mission_ids = {row.mission_id for row in mission_component.rows}
        if not mission_ids:
            rows = conn.execute(
                "SELECT missionID FROM MissionNPCComponent WHERE id=?",
                (component_id,),
            ).fetchall()
            mission_ids = {row["missionID"] for row in rows}
        if not mission_ids:
            return
        placeholders = ", ".join("?" for _ in mission_ids)
        params = tuple(sorted(mission_ids))
        conn.execute(f"DELETE FROM Missions WHERE id IN ({placeholders})", params)
        conn.execute(f"DELETE FROM MissionTasks WHERE id IN ({placeholders})", params)
        conn.execute(f"DELETE FROM MissionText WHERE id IN ({placeholders})", params)
        conn.execute(f"DELETE FROM MissionEmail WHERE missionID IN ({placeholders})", params)

    def _extract_loot_table_indices(self, collection: Any) -> set[int]:
        if not isinstance(collection, RowCollection):
            return set()
        return {row.loot_table_index for row in collection.rows}

    def _extract_index_collection_keys(self, collection: Any) -> set[int]:
        if not isinstance(collection, RowCollection):
            return set()
        key_field = collection.key_field
        return {
            int(getattr(row, key_field))
            for row in collection.rows
            if getattr(row, key_field, None) is not None
        }

    def _mark_all_clean(self, npc: NPC) -> None:
        npc.dirty = False
        for component in npc.components.values():
            if hasattr(component, "dirty"):
                component.dirty = False
            if isinstance(component, RowCollection):
                for row in component.rows:
                    if hasattr(row, "dirty"):
                        row.dirty = False
