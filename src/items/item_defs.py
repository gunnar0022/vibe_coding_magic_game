"""
Item definitions - data dict for all physical items.
Parallel to WEAPON_TYPES and ENEMY_DEFS.
"""

ITEM_DEFS = {
    "wooden_spear": {
        "name": "Wooden Spear",
        "description": "A simple spear carved from hardwood. Good reach.",
        "item_type": "weapon",
        "weight": 3.0,
        "stackable": False,
        "max_stack": 1,
        "color": (160, 120, 60),
        # Weapon stats
        "damage": 18,
        "damage_type": "piercing",
        "cooldown": 0.5,
        "hands_required": 1,
        "slashing_power": 1,
        "range": 1.5,
        "push_force": 0,
    },
}
