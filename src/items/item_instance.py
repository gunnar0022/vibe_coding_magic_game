"""
ItemInstance - runtime instance of an item with quantity and def lookup.
"""
from .item_defs import ITEM_DEFS


class ItemInstance:
    """A runtime item instance referencing an ITEM_DEFS entry."""

    _next_id = 1

    def __init__(self, item_def_id, quantity=1):
        self.instance_id = ItemInstance._next_id
        ItemInstance._next_id += 1
        self.item_def_id = item_def_id
        self.quantity = quantity

    def _def(self):
        return ITEM_DEFS.get(self.item_def_id, {})

    @property
    def name(self):
        return self._def().get("name", self.item_def_id)

    @property
    def description(self):
        return self._def().get("description", "")

    @property
    def item_type(self):
        return self._def().get("item_type", "material")

    @property
    def is_weapon(self):
        return self.item_type == "weapon"

    @property
    def damage(self):
        return self._def().get("damage", 0)

    @property
    def hands_required(self):
        return self._def().get("hands_required", 1)

    @property
    def cooldown(self):
        return self._def().get("cooldown", 0.5)

    @property
    def slashing_power(self):
        return self._def().get("slashing_power", 0)

    @property
    def stackable(self):
        return self._def().get("stackable", False)

    @property
    def max_stack(self):
        return self._def().get("max_stack", 1)

    @property
    def weight(self):
        return self._def().get("weight", 1.0)

    @property
    def color(self):
        return self._def().get("color", (200, 200, 200))

    @property
    def push_force(self):
        return self._def().get("push_force", 0)

    def serialize(self):
        return {
            "item_def_id": self.item_def_id,
            "quantity": self.quantity,
        }

    @staticmethod
    def deserialize(data):
        if not isinstance(data, dict) or "item_def_id" not in data:
            return None
        inst = ItemInstance(data["item_def_id"], data.get("quantity", 1))
        return inst

    def __repr__(self):
        return f"ItemInstance({self.item_def_id}, qty={self.quantity})"
