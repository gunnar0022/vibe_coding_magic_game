"""
Enemy definitions - data-driven enemy type registry.
Parallel to WEAPON_TYPES in summoned_weapon.py.
"""

ENEMY_DEFS = {
    "slime": {
        "name": "Slime",
        "hp": 30,
        "color": (80, 180, 60),
        "resistances": {
            "physical": 0.3,
            "fire": -1.0,
            "poison": 1.0,
        },
        "ai": {
            "detection_range": 6.0,
            "chase_range": 8.0,
            "attack_range": 1.2,
            "flee_range": 0,
            "chase_speed": 1.5,
            "patrol_speed": 0.8,
            "maintains_distance": 0,
            "erratic": False,
            "flee_health_pct": 0,
        },
        "attacks": [
            {
                "name": "Slime Touch",
                "type": "contact",
                "damage": 8,
                "damage_type": "physical",
                "range": 1.2,
                "cooldown": 1.0,
                "windup": 0.0,
                "recovery": 0.0,
                "knockback_multiplier": 0.5,
                "status_effects": [],
                "telegraph_color": (80, 180, 60),
                "element": "physical",
            },
        ],
        "flags": {},
        "render_type": "slime",
    },

    "skeleton_archer": {
        "name": "Skeleton Archer",
        "hp": 40,
        "color": (220, 210, 180),
        "resistances": {
            "light": -0.5,
            "dark": 0.5,
            "physical": -0.2,
        },
        "ai": {
            "detection_range": 10.0,
            "chase_range": 14.0,
            "attack_range": 8.0,
            "flee_range": 3.0,
            "chase_speed": 2.0,
            "patrol_speed": 1.0,
            "maintains_distance": 6.0,
            "erratic": False,
            "flee_health_pct": 0,
        },
        "attacks": [
            {
                "name": "Bone Arrow",
                "type": "projectile",
                "damage": 12,
                "damage_type": "physical",
                "range": 10.0,
                "cooldown": 2.0,
                "windup": 0.5,
                "recovery": 0.3,
                "knockback_multiplier": 0.5,
                "status_effects": [],
                "projectile_speed": 7.0,
                "telegraph_color": (220, 210, 180),
                "element": "physical",
            },
        ],
        "flags": {
            "bone_shatter": True,  # takes 1.5x physical damage
        },
        "render_type": "skeleton_archer",
    },

    "ember_sprite": {
        "name": "Ember Sprite",
        "hp": 20,
        "color": (255, 140, 40),
        "resistances": {
            "fire": 1.0,
            "water": -5.0,
            "ice": -5.0,
        },
        "ai": {
            "detection_range": 7.0,
            "chase_range": 10.0,
            "attack_range": 1.2,
            "flee_range": 0,
            "chase_speed": 2.5,
            "patrol_speed": 1.5,
            "maintains_distance": 0,
            "erratic": True,
            "flee_health_pct": 0,
        },
        "attacks": [
            {
                "name": "Ember Touch",
                "type": "contact",
                "damage": 5,
                "damage_type": "fire",
                "range": 1.2,
                "cooldown": 0.5,
                "windup": 0.0,
                "recovery": 0.0,
                "knockback_multiplier": 0.3,
                "status_effects": [
                    {"name": "burning", "duration": 3.0, "intensity": 1.0},
                ],
                "telegraph_color": (255, 140, 40),
                "element": "fire",
            },
        ],
        "flags": {
            "innate_element": "fire",
            "ignites_nearby": True,  # sets nearby plants on fire
            "ignite_radius": 1.5,
        },
        "render_type": "ember_sprite",
    },

    "stone_guardian": {
        "name": "Stone Guardian",
        "hp": 150,
        "color": (140, 140, 150),
        "resistances": {
            "physical": 0.7,
            "earth": -0.5,
            "electric": -0.3,
        },
        "ai": {
            "detection_range": 5.0,
            "chase_range": 8.0,
            "attack_range": 2.0,
            "flee_range": 0,
            "chase_speed": 1.0,
            "patrol_speed": 0.5,
            "maintains_distance": 0,
            "erratic": False,
            "flee_health_pct": 0,
        },
        "attacks": [
            {
                "name": "Guardian Slam",
                "type": "melee",
                "damage": 25,
                "damage_type": "physical",
                "range": 2.0,
                "cooldown": 2.5,
                "windup": 1.0,
                "recovery": 1.0,
                "knockback_multiplier": 2.0,
                "status_effects": [],
                "telegraph_color": (180, 160, 120),
                "element": "physical",
            },
            {
                "name": "Ground Pound",
                "type": "aoe",
                "damage": 15,
                "damage_type": "earth",
                "range": 2.5,
                "cooldown": 5.0,
                "windup": 1.5,
                "recovery": 1.0,
                "knockback_multiplier": 1.5,
                "aoe_radius": 2.0,
                "status_effects": [
                    {"name": "stunned", "duration": 0.5, "intensity": 1.0},
                ],
                "telegraph_color": (160, 140, 100),
                "element": "earth",
            },
        ],
        "flags": {
            "damage_threshold": 10,  # ignores hits below this damage
            "electric_stun_duration": 2.0,  # extra stun from electric
        },
        "render_type": "stone_guardian",
        "size_multiplier": 1.5,
    },
}
