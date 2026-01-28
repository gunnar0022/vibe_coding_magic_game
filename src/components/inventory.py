"""
Inventory component for item storage.
Stores ItemInstance objects with stacking support and equipped weapon slot.
"""
from .base import Component


class InventoryComponent(Component):
    """Manages item storage for entities."""

    def __init__(self, capacity=20):
        super().__init__()
        self.capacity = capacity
        self.items = []  # List of ItemInstance objects
        self.equipped_weapon = None  # ItemInstance for equipped physical weapon

    def is_full(self):
        return len(self.items) >= self.capacity

    def add_item(self, item_instance):
        """Add an ItemInstance to inventory. Stacks if possible. Returns True if successful."""
        # Try stacking first
        if item_instance.stackable:
            for existing in self.items:
                if (existing.item_def_id == item_instance.item_def_id
                        and existing.quantity < existing.max_stack):
                    space = existing.max_stack - existing.quantity
                    transfer = min(space, item_instance.quantity)
                    existing.quantity += transfer
                    item_instance.quantity -= transfer
                    if item_instance.quantity <= 0:
                        return True

        # Add as new slot if there's remaining quantity
        if item_instance.quantity > 0:
            if self.is_full():
                return False
            self.items.append(item_instance)
        return True

    def remove_item_at(self, index):
        """Remove and return ItemInstance at index."""
        if 0 <= index < len(self.items):
            return self.items.pop(index)
        return None

    def remove_item(self, item_instance):
        """Remove a specific ItemInstance from inventory. Returns True if found."""
        for i, existing in enumerate(self.items):
            if existing.instance_id == item_instance.instance_id:
                self.items.pop(i)
                return True
        return False

    def has_item(self, item_def_id):
        """Check if inventory contains an item with the given def id."""
        for item in self.items:
            if item.item_def_id == item_def_id:
                return True
        return False

    def get_count(self):
        """Get number of item slots used."""
        return len(self.items)

    def clear(self):
        """Remove all items."""
        self.items.clear()
        self.equipped_weapon = None

    def serialize(self):
        serialized_items = []
        for item in self.items:
            serialized_items.append(item.serialize())
        data = {
            "capacity": self.capacity,
            "items": serialized_items,
        }
        if self.equipped_weapon is not None:
            data["equipped_weapon"] = self.equipped_weapon.serialize()
        return data

    def deserialize(self, data):
        from ..items.item_instance import ItemInstance

        self.capacity = data.get("capacity", 20)
        self.items = []
        self.equipped_weapon = None

        raw_items = data.get("items", [])
        for item_data in raw_items:
            if isinstance(item_data, dict) and "item_def_id" in item_data:
                inst = ItemInstance.deserialize(item_data)
                if inst:
                    self.items.append(inst)
            # Gracefully skip old string-ID format from legacy saves

        equipped_data = data.get("equipped_weapon")
        if equipped_data and isinstance(equipped_data, dict):
            self.equipped_weapon = ItemInstance.deserialize(equipped_data)
