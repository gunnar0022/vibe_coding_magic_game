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
        "buy_price": 25,
        "sell_price": 10,
        # Weapon stats
        "damage": 18,
        "damage_type": "piercing",
        "cooldown": 0.5,
        "hands_required": 1,
        "slashing_power": 1,
        "range": 1.5,
        "push_force": 0,
    },

    # === CONSUMABLES ===
    "health_potion": {
        "name": "Health Potion",
        "description": "A red vial that restores 20 health when consumed.",
        "item_type": "consumable",
        "weight": 0.5,
        "stackable": True,
        "max_stack": 99,
        "color": (220, 60, 60),
        "buy_price": 15,
        "sell_price": 5,
        # Consumable effect
        "effect_type": "heal_health",
        "effect_amount": 20,
    },

    "mana_potion": {
        "name": "Mana Potion",
        "description": "A blue vial that restores 50 mana when consumed.",
        "item_type": "consumable",
        "weight": 0.5,
        "stackable": True,
        "max_stack": 99,
        "color": (60, 100, 220),
        "buy_price": 20,
        "sell_price": 8,
        # Consumable effect
        "effect_type": "heal_mana",
        "effect_amount": 50,
    },

    # === VALUABLES ===
    "trinket": {
        "name": "Trinket",
        "description": "A small curiosity with no practical use, but it might fetch a price.",
        "item_type": "valuable",
        "weight": 0.2,
        "stackable": True,
        "max_stack": 99,
        "color": (200, 180, 100),
        "buy_price": 75,
        "sell_price": 50,
    },
}
