"""
GroundItem entity - an item sitting on the ground, pickupable with E key.
"""
from .base import Entity
from ..components.interaction import InteractionComponent


class GroundItem(Entity):
    """An item placed on the ground that can be picked up."""

    def __init__(self, x, y, item_instance, map_object_id=None):
        super().__init__(x=x, y=y, tags=["ground_item", "interactable"])
        self.solid = False
        self.item_instance = item_instance
        self.color = item_instance.color

        # Tracking ID for persistence:
        # - map_object_id: set for items placed by the map JSON (e.g., "ground_item_15_20")
        # - None for items dropped by the player
        self.map_object_id = map_object_id

        # Add interaction component
        interaction = InteractionComponent()
        interaction.can_examine = True
        interaction.examine_text = f"{item_instance.name}: {item_instance.description}"
        self.add_component(interaction)

    def serialize(self):
        data = super().serialize()
        data["item_instance"] = self.item_instance.serialize()
        return data

    @staticmethod
    def deserialize_from(data):
        from ..items.item_instance import ItemInstance
        item_data = data.get("item_instance")
        if not item_data:
            return None
        item_inst = ItemInstance.deserialize(item_data)
        if not item_inst:
            return None
        gi = GroundItem(data.get("x", 0), data.get("y", 0), item_inst)
        return gi

    def __repr__(self):
        return f"GroundItem({self.item_instance.name} at {self.x},{self.y})"
