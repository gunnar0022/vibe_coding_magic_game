"""
Inventory component for item storage.
"""
from .base import Component


class InventoryComponent(Component):
    """Manages item storage for entities."""

    def __init__(self, capacity=20):
        super().__init__()
        self.capacity = capacity
        self.items = []  # List of item instance IDs

    def is_full(self):
        return len(self.items) >= self.capacity

    def add_item(self, item_id):
        """Add item to inventory. Returns True if successful."""
        if self.is_full():
            return False
        self.items.append(item_id)
        return True

    def remove_item(self, item_id):
        """Remove item from inventory. Returns True if found."""
        if item_id in self.items:
            self.items.remove(item_id)
            return True
        return False

    def has_item(self, item_id):
        """Check if inventory contains item."""
        return item_id in self.items

    def get_count(self):
        """Get number of items in inventory."""
        return len(self.items)

    def clear(self):
        """Remove all items."""
        self.items.clear()

    def serialize(self):
        return {
            "capacity": self.capacity,
            "items": self.items.copy()
        }

    def deserialize(self, data):
        self.capacity = data.get("capacity", 20)
        self.items = data.get("items", []).copy()
