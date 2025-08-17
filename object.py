import sqlite3

class Components:
    """Mapping of component tables to their respective IDs."""
    def __init__(self):                 #  TABLE NAME
        self.CONTROLLABLE_PHYSICS   = {"id": 1,  "table": " "                       }  # TODO: find name
        self.RENDER                 = {"id": 2,  "table": "RenderComponent"         }
        self.SIMPLE_PHYSICS         = {"id": 3,  "table": "PhysicsComponent"        }
        self.SCRIPT                 = {"id": 5,  "table": "ScriptComponent"         }
        self.DESTROYABLE            = {"id": 7,  "table": "DestructibleComponent"   }
        self.SKILL                  = {"id": 9,  "table": "ObjectSkills"            }
        self.ITEM                   = {"id": 11, "table": "ItemComponent"           }
        self.VENDOR                 = {"id": 16, "table": "VendorComponent"         }
        self.INVENTORY              = {"id": 17, "table": "InventoryComponent"      }
        self.MINIFIG                = {"id": 35, "table": "MinifigComponent"        }
        self.MISSION_OFFER          = {"id": 73, "table": "MissionNPCComponent"     }

        self.INVALID = None

    def get_component_by_id(self, id):
        """Return the component table name by its ID."""
        for key, value in self.__dict__.items():
            if isinstance(value, dict) and value.get("id") == id:
                return value
        return None

class NPCProfession:
    """Mapping of vendor professions to their respective IDs."""
    def __init__(self):
        self.NONE = 0
        self.VENDER = 1
        self.MISSION = 2

class ItemType:
    """Mapping of item types to their respective IDs."""
    def __init__(self):
        self.UNKNOWN = -1              # An unknown item type
        self.BRICK = 1                 # A brick
        self.HAT = 2                   # A hat / head item
        self.HAIR = 3                  # A hair item
        self.NECK = 4                  # A neck item
        self.LEFT_HAND = 5             # A left handed item
        self.RIGHT_HAND = 6            # A right handed item
        self.LEGS = 7                  # A pants item
        self.LEFT_TRINKET = 8          # A left handed trinket item
        self.RIGHT_TRINKET = 9         # A right handed trinket item
        self.BEHAVIOR = 10             # A behavior
        self.PROPERTY = 11             # A property
        self.MODEL = 12                # A model
        self.COLLECTIBLE = 13          # A collectible item
        self.CONSUMABLE = 14           # A consumable item
        self.CHEST = 15                # A chest item
        self.EGG = 16                  # An egg
        self.PET_FOOD = 17             # A pet food item
        self.QUEST_OBJECT = 18         # A quest item
        self.PET_INVENTORY_ITEM = 19   # A pet inventory item
        self.PACKAGE = 20              # A package
        self.LOOT_MODEL = 21           # A loot model
        self.VEHICLE = 22              # A vehicle
        self.CURRENCY = 23             # Currency
        self.MOUNT = 24                # A mount

        # Reverse mappings for easy lookup use: id_to_name[id]
        self.id_to_name = {v: k for k, v in self.name_to_id.items()}


# Singletons
COMPONENTS = Components()
NPC_PROFESSION = NPCProfession()
ITEM_TYPES = ItemType()

class Object:
    def __init__(self, id, cursor):
        self.id = id
        self.name = None

        self.cursor = cursor

        self.components = []

    def fetch_components(self):
        """Fetch components for this object from the database."""
        self.cursor.execute("SELECT * FROM ComponentsRegistry WHERE id = ?", (self.id,))
        rows = self.cursor.fetchall()
        if not rows:
            print(f"No components found for Object ID: {self.id}")
            return

        for row in rows:
            component = {
                "component_type": COMPONENTS.get_component_by_id(row["component_type"]),
                "component_id": row["component_id"],
            }
            self.components.append(component)

    def _init_tables(self):
        """Initialize the component tables for this NPC."""
        for component in self.components:
            if component["component_type"] is None or component["component_type"] == COMPONENTS.INVALID:
                print(f"Skipping initialization for component type: {component['component_type']}")
                continue

            if component["component_type"] is COMPONENTS.CONTROLLABLE_PHYSICS:
                pass
            elif component["component_type"] is COMPONENTS.RENDER:
                pass
            elif component["component_type"] is COMPONENTS.SIMPLE_PHYSICS:
                pass
            elif component["component_type"] is COMPONENTS.SCRIPT:
                pass
            elif component["component_type"] is COMPONENTS.DESTROYABLE:
                pass
            elif component["component_type"] is COMPONENTS.SKILL:
                pass
            elif component["component_type"] is COMPONENTS.ITEM:
                pass
            elif component["component_type"] is COMPONENTS.VENDOR:
                pass
            elif component["component_type"] is COMPONENTS.INVENTORY:
                pass
            elif component["component_type"] is COMPONENTS.MINIFIG:
                pass
            elif component["component_type"] is COMPONENTS.MISSION_OFFER:
                pass
            else:
                print(f"Unknown component type: {component['component_type']}")
                continue

    # def __eq__(self, other):
    #     if not isinstance(other, Object):
    #         return NotImplemented
    #     return self.id == other.id


class NPC(Object):
    def __init__(self,cursor, id, profession):
        super().__init__(cursor, id)

        self.profession = profession  # NPCProfession enum

        self.components = [
            {"component_type": COMPONENTS.MINIFIG, "component_id": None},
            #TODO: Finish
        ]

    def __init_tables(self):
        """Initialize the component tables for this NPC."""


class Item(Object):
    def __init__(self, cursor, id):
        super().__init__(cursor, id)

        self.components = [
            {"component_type": COMPONENTS.MINIFIG, "component_id": None},
            {"component_type": COMPONENTS.ITEM, "component_id": None},
            {"component_type": COMPONENTS.SKILL, "component_id": None},
        ]





if __name__ == "__main__":
    print(COMPONENTS.get_component_by_id(2))  # Example usage


"""
NOTES:

- The `Object` class represents a generic object in the database.
   - Can be NPC, Item, etc.


"""

"""
Table Maps

NPC (vendor):
- Objects
- ComponentsRegistry
  - RenderComponent (2)
  - MinifigComponent (35)
    - MinifigDecals_Torsos **
  - PhysicsComponent (3)
  - InventoryComponent (17)
  - DestructibleComponent (7) *
    - LootMatrix
      - LootTable
    - CurrencyTable *?
  - VendorComponent (16)
    - LootMatrix
      - LootTable
  - ScriptComponent (5) *



NPC (mission):
- Objects
- ComponentsRegistry
  - RenderComponent (2)
  - MinifigComponent (35)
    - MinifigDecals_Torsos **
  - PhysicsComponent (3)
  - InventoryComponent (17)
  - DestructibleComponent (7) *
    - LootMatrix
      - LootTable
    - CurrencyTable *?
  - MissionNPCComponent (73)
    - Missions
  - ScriptComponent (5) **


Item:
- Objects
- ComponentsRegistry
  - RenderComponent (2)
  - ItemComponent (11)
  - SkillComponent (9)

* Optional
** Copy from other NPC

"""


