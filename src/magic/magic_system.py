"""
Core magic system - handles symbol resolution and spell creation.
"""
import json
import os
from .symbol import Symbol
from .spell_descriptor import SpellDescriptor


class MagicSystem:
    """
    Central magic system that handles:
    - Symbol registry
    - Symbol pair normalization
    - Spell resolution
    """

    # Symbol registry
    _symbols = {}

    # Spell combination lookup
    # Key: normalized tuple of symbol ids, Value: spell descriptor data
    _combinations = {}

    # Single symbol spell lookup
    _single_spells = {}

    @classmethod
    def initialize(cls, symbols_path=None, spells_path=None):
        """Initialize the magic system from data files."""
        # Load default symbols and spells if no path provided
        cls._load_default_data()

        # Load from files if paths provided
        if symbols_path and os.path.exists(symbols_path):
            cls._load_symbols_from_file(symbols_path)
        if spells_path and os.path.exists(spells_path):
            cls._load_spells_from_file(spells_path)

    @classmethod
    def _load_default_data(cls):
        """Load built-in default symbols and spell combinations."""
        # Default symbols
        default_symbols = {
            "fire": {
                "name": "Fire",
                "character": "\u706b",  # 火
                "description": "The symbol of flame and heat.",
                "category": "elemental",
                "element": "fire",
                "base_traits": ["burning", "heat"],
            },
            "water": {
                "name": "Water",
                "character": "\u6c34",  # 水
                "description": "The symbol of flow and moisture.",
                "category": "elemental",
                "element": "water",
                "base_traits": ["flowing", "wet"],
            },
            "earth": {
                "name": "Earth",
                "character": "\u571f",  # 土
                "description": "The symbol of stone and stability.",
                "category": "elemental",
                "element": "earth",
                "base_traits": ["solid", "heavy"],
            },
            "wind": {
                "name": "Wind",
                "character": "\u98a8",  # 風
                "description": "The symbol of cutting wind and pressure.",
                "category": "elemental",
                "element": "wind",
                "base_traits": ["cutting", "pressure"],
            },
            "force": {
                "name": "Force",
                "character": "\u529b",  # 力
                "description": "The symbol of raw physical power.",
                "category": "force",
                "element": "physical",
                "base_traits": ["pressure", "impact"],
            },
            "life": {
                "name": "Life",
                "character": "\u751f",  # 生
                "description": "The symbol of vitality and growth.",
                "category": "abstract",
                "element": "nature",
                "base_traits": ["healing", "growth"],
            },
            "light": {
                "name": "Light",
                "character": "\u5149",  # 光
                "description": "The symbol of illumination and clarity.",
                "category": "elemental",
                "element": "light",
                "base_traits": ["radiance", "revealing"],
            },
            "dark": {
                "name": "Darkness",
                "character": "\u95c7",  # 闇
                "description": "The symbol of corruptive shadow.",
                "category": "elemental",
                "element": "dark",
                "base_traits": ["shadow", "corruption"],
            },
            "electric": {
                "name": "Electric",
                "character": "\u96fb",  # 電
                "description": "The symbol of shock and static.",
                "category": "elemental",
                "element": "electric",
                "base_traits": ["shock", "static"],
            },
            "thunder": {
                "name": "Thunder",
                "character": "\u96f7",  # 雷
                "description": "The symbol of thunder, an upgraded form of electric.",
                "category": "elemental",
                "element": "electric",
                "base_traits": ["shock", "chain"],
            },
            "blaze": {
                "name": "Blaze",
                "character": "\u708e",  # 炎
                "description": "The symbol of inferno, an upgraded form of fire.",
                "category": "elemental",
                "element": "fire",
                "base_traits": ["inferno", "spread"],
            },
            "cut": {
                "name": "Cut",
                "character": "\u5207",  # 切
                "description": "The symbol of cutting, a combo modifier.",
                "category": "modifier",
                "element": "physical",
                "base_traits": ["slashing", "swift"],
            },
            "stone": {
                "name": "Stone",
                "character": "\u77f3",  # 石
                "description": "The symbol of rigid stone, for offensive physical magic.",
                "category": "elemental",
                "element": "earth",
                "base_traits": ["rigid", "crushing"],
            },
            "sword": {
                "name": "Sword",
                "character": "\u5200",  # 刀
                "description": "The symbol of the blade, swift and precise.",
                "category": "weapon",
                "element": "physical",
                "base_traits": ["slashing", "swift"],
            },
            "axe": {
                "name": "Axe",
                "character": "\u65a7",  # 斧
                "description": "The symbol of the axe, powerful and cleaving.",
                "category": "weapon",
                "element": "physical",
                "base_traits": ["slashing", "heavy"],
            },
            "great": {
                "name": "Great",
                "character": "\u5927",  # 大
                "description": "The symbol of magnitude and amplification.",
                "category": "modifier",
                "element": "none",
                "base_traits": ["amplify", "size"],
            },
            "bow": {
                "name": "Bow",
                "character": "\u5f13",  # 弓
                "description": "The symbol of the bow, striking from afar.",
                "category": "weapon",
                "element": "physical",
                "base_traits": ["piercing", "ranged"],
            },
            "bullet": {
                "name": "Bullet",
                "character": "\u5f3e",  # 弾
                "description": "The symbol of the projectile, a focused bolt of energy.",
                "category": "modifier",
                "element": "physical",
                "base_traits": ["projectile", "focused"],
            },
            "ice": {
                "name": "Ice",
                "character": "\u6c37",  # 氷
                "description": "The symbol of frost and stillness, a cold that seizes all motion.",
                "category": "elemental",
                "element": "ice",
                "base_traits": ["freezing", "cold"],
            },
        }

        for symbol_id, data in default_symbols.items():
            data["id"] = symbol_id
            cls._symbols[symbol_id] = Symbol(symbol_id, data)

        # Default single-symbol spells
        cls._single_spells = {
            "fire": {
                "name": "Ember",
                "category": "destructive",
                "element": "fire",
                "traits": ["burning", "heat"],
                "intensity": 0.5,
                "channel": {
                    "duration": 3.0,
                    "tick_interval": 0.15,
                    "rotation_speed": 5.0,
                    "range": 1.25,
                },
                "radius": 0,
                "damage": {"amount": 1.5, "type": "fire"},
                "status_effects": [{"name": "burning", "duration": 3.0, "intensity": 0.5}],
                "mana_cost": 10,
            },
            "water": {
                "name": "Splash",
                "category": "environmental",
                "element": "water",
                "traits": ["flowing", "wet"],
                "intensity": 0.5,
                "duration": 1.0,
                "radius": 0,
                "damage": None,
                "status_effects": [{"name": "wet", "duration": 5.0}],
                "mana_cost": 5,
            },
            "earth": {
                "name": "Null",
                "category": "none",
                "element": "earth",
                "traits": ["solid"],
                "intensity": 0,
                "duration": 0.1,
                "radius": 0,
                "is_dud": True,
                "mana_cost": 10,
            },
            "wind": {
                "name": "Gust",
                "category": "utility",
                "element": "wind",
                "traits": ["cutting", "pressure"],
                "intensity": 0.5,
                "duration": 0.5,
                "radius": 2,
                "damage": None,
                "mana_cost": 10,
            },
            "force": {
                "name": "Push",
                "category": "utility",
                "element": "physical",
                "traits": ["pressure", "impact"],
                "intensity": 1.0,
                "duration": 0.1,
                "radius": 0,
                "damage": {"amount": 10, "type": "physical"},
                "mana_cost": 10,
            },
            "life": {
                "name": "Null",
                "category": "none",
                "element": "nature",
                "traits": ["healing"],
                "intensity": 0,
                "duration": 0.1,
                "radius": 0,
                "is_dud": True,
                "mana_cost": 15,
            },
            "light": {
                "name": "Light",
                "category": "utility",
                "element": "light",
                "traits": ["radiance", "revealing"],
                "intensity": 0.5,
                "duration": 10.0,
                "radius": 2,
                "mana_cost": 15,
            },
            "dark": {
                "name": "Darkness",
                "category": "status",
                "element": "dark",
                "traits": ["shadow", "corruption"],
                "intensity": 0.5,
                "duration": 0.2,
                "radius": 0,
                "damage": None,
                "status_effects": [{"name": "decaying", "duration": 6.0, "intensity": 0.5}],
                "mana_cost": 20,
            },
            "electric": {
                "name": "Electric",
                "category": "destructive",
                "element": "electric",
                "traits": ["shock", "static"],
                "intensity": 0.8,
                "duration": 0.2,
                "radius": 2,
                "damage": {"amount": 15, "type": "electric"},
                "mana_cost": 10,
            },
            "thunder": {
                "name": "Thunder",
                "category": "destructive",
                "element": "electric",
                "traits": ["shock", "chain"],
                "intensity": 1.5,
                "duration": 0.3,
                "radius": 3,
                "damage": {"amount": 50, "type": "electric"},
                "status_effects": [{"name": "electrified", "duration": 2.0}],
                "mana_cost": 40,
            },
            "blaze": {
                "name": "Blaze",
                "category": "destructive",
                "element": "fire",
                "traits": ["inferno", "spread"],
                "intensity": 1.5,
                "duration": 2.0,
                "radius": 0,
                "damage": {"amount": 50, "type": "fire"},
                "status_effects": [{"name": "burning", "duration": 4.0, "intensity": 1.0}],
                "mana_cost": 40,
            },
            "cut": {
                "name": "Null",
                "category": "none",
                "element": "physical",
                "traits": ["slashing"],
                "intensity": 0,
                "duration": 0.1,
                "radius": 0,
                "is_dud": True,
                "mana_cost": 5,
            },
            "stone": {
                "name": "Null",
                "category": "none",
                "element": "earth",
                "traits": ["rigid"],
                "intensity": 0,
                "duration": 0.1,
                "radius": 0,
                "is_dud": True,
                "mana_cost": 5,
            },
            "sword": {
                "name": "Summon Sword",
                "category": "weapon_summon",
                "element": "physical",
                "traits": ["summoning", "slashing"],
                "intensity": 1.0,
                "duration": -1,
                "radius": 0,
                "weapon_type": "sword",
                "mana_cost": 40,
            },
            "axe": {
                "name": "Summon Axe",
                "category": "weapon_summon",
                "element": "physical",
                "traits": ["summoning", "slashing"],
                "intensity": 1.0,
                "duration": -1,
                "radius": 0,
                "weapon_type": "axe",
                "mana_cost": 40,
            },
            "great": {
                "name": "Null",
                "category": "none",
                "element": "none",
                "traits": ["amplify"],
                "intensity": 0,
                "duration": 0.1,
                "radius": 0,
                "is_dud": True,
                "mana_cost": 15,
            },
            "bow": {
                "name": "Summon Bow",
                "category": "weapon_summon",
                "element": "physical",
                "traits": ["summoning", "ranged"],
                "intensity": 1.0,
                "duration": -1,
                "radius": 0,
                "weapon_type": "bow",
                "mana_cost": 60,
            },
            "bullet": {
                "name": "Null",
                "category": "none",
                "is_dud": True,
                "mana_cost": 5,
            },
            "ice": {
                "name": "Frost",
                "category": "destructive",
                "element": "ice",
                "traits": ["cold", "freezing"],
                "intensity": 0.5,
                "duration": 1.5,
                "radius": 0,
                "damage": {"amount": 10, "type": "ice"},
                "status_effects": [{"name": "chilled", "duration": 4.0, "intensity": 0.5}],
                "mana_cost": 8,
            },
        }

        # Default combination spells (order-independent pairs)
        # Key format: tuple of sorted symbol ids
        cls._combinations = {
            # ============================================================
            # ELEMENTAL + ELEMENTAL
            # ============================================================
            ("fire", "water"): {
                "name": "Steam Cloud",
                "category": "environmental",
                "element": "water",
                "traits": ["heat", "obscuring", "wet"],
                "intensity": 1.0,
                "duration": 5.0,
                "radius": 2,
                "damage": {"amount": 5, "type": "fire"},
                "status_effects": [
                    {"name": "wet", "duration": 3.0},
                    {"name": "obscured", "duration": 5.0},
                ],
                "mana_cost": 15,
            },
            ("earth", "fire"): {
                "name": "Magma Burst",
                "category": "destructive",
                "element": "fire",
                "traits": ["burning", "heavy", "melting"],
                "intensity": 1.8,
                "duration": 3.0,
                "radius": 1,
                "damage": {"amount": 15, "type": "fire"},
                "status_effects": [{"name": "burning", "duration": 6.0}],
                "directional_shape": True,  # + for cardinal, X for diagonal
                "tick_damage": True,  # re-triggers each second
                "mana_cost": 40,
            },
            ("wind", "fire"): {
                "name": "Inferno Gust",
                "category": "destructive",
                "element": "fire",
                "traits": ["burning", "pressure", "spreading"],
                "intensity": 1.2,
                "duration": 2.0,
                "radius": 2,
                "damage": {"amount": 25, "type": "fire"},
                "status_effects": [{"name": "burning", "duration": 5.0}],
                "mana_cost": 20,
            },
            ("fire", "life"): {
                "name": "Null",
                "category": "none",
                "is_dud": True,
                "mana_cost": 5,
            },
            ("fire", "light"): {
                "name": "Solar Burst",
                "category": "destructive",
                "element": "fire",
                "traits": ["burning", "radiance", "cleansing"],
                "intensity": 1.3,
                "duration": 0.5,
                "radius": 2,
                "damage": {"amount": 15, "type": "fire"},
                "status_effects": [{"name": "burning", "duration": 3.0}],
                "cleanses": True,
                "mana_cost": 40,
            },
            ("earth", "water"): {
                "name": "Mud Spray",
                "category": "environmental",
                "element": "earth",
                "traits": ["slowing", "wet", "sticky"],
                "intensity": 1.0,
                "duration": 10.0,
                "radius": 3,
                "status_effects": [{"name": "slowed", "duration": 5.0}],
                "mana_cost": 15,
            },
            ("wind", "water"): {
                "name": "Mist",
                "category": "environmental",
                "element": "water",
                "traits": ["obscuring", "wet", "flowing"],
                "intensity": 0.8,
                "duration": 8.0,
                "radius": 3,
                "status_effects": [
                    {"name": "wet", "duration": 3.0},
                    {"name": "obscured", "duration": 8.0},
                ],
                "mana_cost": 12,
            },
            ("life", "water"): {
                "name": "Rejuvenation",
                "category": "utility",
                "element": "nature",
                "traits": ["healing", "cleansing", "wet"],
                "intensity": 1.5,
                "duration": 3.0,
                "radius": 0,
                "damage": {"amount": -12, "type": "healing"},
                "status_effects": [{"name": "wet", "duration": 2.0}],
                "tick_heal": True,  # heal over 3 ticks
                "mana_cost": 25,
            },
            ("light", "water"): {
                "name": "Cleansing Water",
                "category": "utility",
                "element": "light",
                "traits": ["healing", "cleansing", "wet"],
                "intensity": 1.0,
                "duration": 0.5,
                "radius": 0,
                "damage": {"amount": -5, "type": "healing"},
                "cleanses": True,
                "mana_cost": 50,
            },
            ("dark", "water"): {
                "name": "Null",
                "category": "none",
                "is_dud": True,
                "mana_cost": 5,
            },
            ("wind", "earth"): {
                "name": "Null",
                "category": "none",
                "is_dud": True,
                "mana_cost": 5,
            },
            ("earth", "life"): {
                "name": "Summon Boulder",
                "category": "utility",
                "element": "earth",
                "traits": ["solid", "heavy", "summoning"],
                "intensity": 1.5,
                "duration": -1,
                "radius": 0,
                "spawn_object": "rock",
                "mana_cost": 40,
            },
            ("earth", "light"): {
                "name": "Prismatic Light",
                "category": "utility",
                "element": "light",
                "traits": ["radiance", "earth", "confusion"],
                "intensity": 1.0,
                "duration": 4.0,
                "radius": 2,
                "status_effects": [{"name": "stunned", "duration": 2.0}],
                "mana_cost": 30,
            },
            ("wind", "life"): {
                "name": "Null",
                "category": "none",
                "is_dud": True,
                "mana_cost": 5,
            },
            ("wind", "light"): {
                "name": "Tailwind",
                "category": "utility",
                "element": "wind",
                "traits": ["pressure", "radiance", "speed"],
                "intensity": 1.0,
                "duration": 6.0,
                "radius": 0,
                "status_effects": [{"name": "hastened", "duration": 6.0}],
                "affects_caster": True,
                "mana_cost": 20,
            },
            ("life", "light"): {
                "name": "Purify",
                "category": "utility",
                "element": "light",
                "traits": ["healing", "cleansing", "radiance"],
                "intensity": 1.2,
                "duration": 1.0,
                "radius": 1,
                "damage": {"amount": -5, "type": "healing"},
                "cleanses": True,
                "mana_cost": 20,
            },

            # ============================================================
            # FORCE COMBINATIONS
            # ============================================================
            ("fire", "force"): {
                "name": "Mini Explosion",
                "category": "destructive",
                "element": "fire",
                "traits": ["burning", "impact", "explosion"],
                "intensity": 1.5,
                "duration": 0.5,
                "radius": 1.5,
                "damage": {"amount": 35, "type": "fire"},
                "status_effects": [{"name": "burning", "duration": 4.0}],
                "knockback": True,
                "mana_cost": 40,
            },
            ("force", "water"): {
                "name": "Water Jet",
                "category": "destructive",
                "element": "water",
                "traits": ["pressure", "piercing", "wet"],
                "intensity": 1.3,
                "duration": 0.3,
                "radius": 0,
                "damage": {"amount": 20, "type": "physical"},
                "status_effects": [{"name": "wet", "duration": 5.0}],
                "mana_cost": 20,
            },
            ("earth", "force"): {
                "name": "Boulder Throw",
                "category": "destructive",
                "element": "earth",
                "traits": ["heavy", "impact", "crushing"],
                "intensity": 2.0,
                "duration": 0.2,
                "radius": 0,
                "damage": {"amount": 50, "type": "physical"},
                "mana_cost": 25,
            },
            ("wind", "force"): {
                "name": "Blast",
                "category": "utility",
                "element": "wind",
                "traits": ["pressure", "knockback"],
                "intensity": 1.5,
                "duration": 0.2,
                "radius": 0,
                "push_force": 1,
                "path_effect": True,
                "mana_cost": 30,
            },
            ("force", "force"): {
                "name": "Shockwave",
                "category": "destructive",
                "element": "physical",
                "traits": ["pressure", "impact", "knockback"],
                "intensity": 2.0,
                "duration": 0.1,
                "radius": 2,
                "damage": {"amount": 25, "type": "physical"},
                "push_force": 2,
                "affects_caster": True,
                "mana_cost": 20,
            },
            ("force", "life"): {
                "name": "Null",
                "category": "none",
                "is_dud": True,
                "mana_cost": 5,
            },
            ("force", "light"): {
                "name": "Force Flash",
                "category": "destructive",
                "element": "physical",
                "traits": ["impact", "radiance", "knockback"],
                "intensity": 1.2,
                "duration": 0.3,
                "radius": 1,
                "damage": {"amount": 10, "type": "physical"},
                "status_effects": [{"name": "stunned", "duration": 1.0}],
                "push_force": 1,
                "mana_cost": 25,
            },

            # ============================================================
            # MODIFIER COMBINATIONS (大)
            # ============================================================
            ("fire", "great"): {
                "name": "Greater Ember",
                "category": "destructive",
                "element": "fire",
                "traits": ["burning", "heat", "amplify"],
                "intensity": 0.8,
                "duration": 2.0,
                "radius": 1,
                "damage": {"amount": 15, "type": "fire"},
                "status_effects": [{"name": "burning", "duration": 3.0}],
                "mana_cost": 20,
            },
            ("great", "water"): {
                "name": "Greater Splash",
                "category": "environmental",
                "element": "water",
                "traits": ["flowing", "wet", "amplify"],
                "intensity": 0.8,
                "duration": 1.0,
                "radius": 1,
                "status_effects": [{"name": "wet", "duration": 5.0}],
                "mana_cost": 15,
            },
            ("earth", "great"): {
                "name": "Null",
                "category": "none",
                "is_dud": True,
                "mana_cost": 20,
            },
            ("wind", "great"): {
                "name": "Greater Gust",
                "category": "utility",
                "element": "wind",
                "traits": ["cutting", "pressure", "amplify"],
                "intensity": 0.8,
                "duration": 0.5,
                "radius": 3,
                "mana_cost": 20,
            },
            ("force", "great"): {
                "name": "Greater Push",
                "category": "utility",
                "element": "physical",
                "traits": ["pressure", "impact", "amplify"],
                "intensity": 1.5,
                "duration": 0.1,
                "radius": 0,
                "damage": {"amount": 15, "type": "physical"},
                "push_force": 3,
                "mana_cost": 20,
            },
            ("great", "life"): {
                "name": "Null",
                "category": "none",
                "is_dud": True,
                "mana_cost": 5,
            },
            ("great", "light"): {
                "name": "Greater Flash",
                "category": "utility",
                "element": "light",
                "traits": ["radiance", "revealing", "amplify"],
                "intensity": 0.8,
                "duration": 15.0,
                "radius": 3,
                "mana_cost": 25,
            },
            ("great", "sword"): {
                "name": "Summon Great Sword",
                "category": "weapon_summon",
                "element": "physical",
                "traits": ["summoning", "slashing", "heavy"],
                "intensity": 2.0,
                "duration": -1,
                "radius": 0,
                "weapon_type": "big_sword",
                "mana_cost": 50,
            },
            ("axe", "great"): {
                "name": "Summon Great Axe",
                "category": "weapon_summon",
                "element": "physical",
                "traits": ["summoning", "slashing", "heavy"],
                "intensity": 2.5,
                "duration": -1,
                "radius": 0,
                "weapon_type": "big_axe",
                "mana_cost": 60,
            },
            ("bow", "great"): {
                "name": "Summon Great Bow",
                "category": "weapon_summon",
                "element": "physical",
                "traits": ["summoning", "ranged", "heavy"],
                "intensity": 2.0,
                "duration": -1,
                "radius": 0,
                "weapon_type": "great_bow",
                "mana_cost": 80,
            },

            # ============================================================
            # WEAPON ENCHANTMENTS (element + 刀/斧)
            # ============================================================
            ("fire", "sword"): {
                "name": "Summon Flame Sword",
                "category": "weapon_summon",
                "element": "fire",
                "traits": ["summoning", "slashing", "burning"],
                "duration": -1,
                "weapon_type": "flame_sword",
                "mana_cost": 50,
            },
            ("axe", "fire"): {
                "name": "Summon Flame Axe",
                "category": "weapon_summon",
                "element": "fire",
                "traits": ["summoning", "slashing", "burning"],
                "duration": -1,
                "weapon_type": "flame_axe",
                "mana_cost": 55,
            },
            ("sword", "water"): {
                "name": "Summon Tide Sword",
                "category": "weapon_summon",
                "element": "water",
                "traits": ["summoning", "slashing", "wet"],
                "duration": -1,
                "weapon_type": "tide_sword",
                "mana_cost": 50,
            },
            ("axe", "water"): {
                "name": "Summon Tide Axe",
                "category": "weapon_summon",
                "element": "water",
                "traits": ["summoning", "slashing", "wet"],
                "duration": -1,
                "weapon_type": "tide_axe",
                "mana_cost": 55,
            },
            ("earth", "sword"): {
                "name": "Summon Stone Sword",
                "category": "weapon_summon",
                "element": "earth",
                "traits": ["summoning", "bludgeoning"],
                "duration": -1,
                "weapon_type": "stone_sword",
                "mana_cost": 50,
            },
            ("axe", "earth"): {
                "name": "Summon Stone Axe",
                "category": "weapon_summon",
                "element": "earth",
                "traits": ["summoning", "bludgeoning"],
                "duration": -1,
                "weapon_type": "stone_axe",
                "mana_cost": 55,
            },
            ("wind", "sword"): {
                "name": "Summon Gale Blade",
                "category": "weapon_summon",
                "element": "wind",
                "traits": ["summoning", "slashing", "knockback"],
                "duration": -1,
                "weapon_type": "gale_sword",
                "mana_cost": 50,
            },
            ("wind", "axe"): {
                "name": "Summon Gale Axe",
                "category": "weapon_summon",
                "element": "wind",
                "traits": ["summoning", "slashing", "knockback"],
                "duration": -1,
                "weapon_type": "gale_axe",
                "mana_cost": 55,
            },
            ("force", "sword"): {
                "name": "Summon Power Blade",
                "category": "weapon_summon",
                "element": "physical",
                "traits": ["summoning", "slashing", "knockback"],
                "duration": -1,
                "weapon_type": "power_sword",
                "mana_cost": 50,
            },
            ("axe", "force"): {
                "name": "Summon Power Axe",
                "category": "weapon_summon",
                "element": "physical",
                "traits": ["summoning", "slashing", "knockback"],
                "duration": -1,
                "weapon_type": "power_axe",
                "mana_cost": 55,
            },
            ("life", "sword"): {
                "name": "Null",
                "category": "none",
                "is_dud": True,
                "mana_cost": 5,
            },
            ("axe", "life"): {
                "name": "Null",
                "category": "none",
                "is_dud": True,
                "mana_cost": 5,
            },
            ("light", "sword"): {
                "name": "Summon Radiant Blade",
                "category": "weapon_summon",
                "element": "light",
                "traits": ["summoning", "slashing", "cleansing"],
                "duration": -1,
                "weapon_type": "radiant_sword",
                "mana_cost": 50,
            },
            ("axe", "light"): {
                "name": "Summon Radiant Axe",
                "category": "weapon_summon",
                "element": "light",
                "traits": ["summoning", "slashing", "cleansing"],
                "duration": -1,
                "weapon_type": "radiant_axe",
                "mana_cost": 55,
            },

            # ============================================================
            # BOW ENCHANTMENTS (element + 弓)
            # ============================================================
            ("bow", "fire"): {
                "name": "Summon Fire Bow",
                "category": "weapon_summon",
                "element": "fire",
                "traits": ["summoning", "ranged", "burning"],
                "duration": -1,
                "weapon_type": "fire_bow",
                "mana_cost": 70,
            },
            ("bow", "water"): {
                "name": "Summon Water Bow",
                "category": "weapon_summon",
                "element": "water",
                "traits": ["summoning", "ranged", "wet"],
                "duration": -1,
                "weapon_type": "water_bow",
                "mana_cost": 70,
            },
            ("bow", "earth"): {
                "name": "Summon Stone Bow",
                "category": "weapon_summon",
                "element": "earth",
                "traits": ["summoning", "ranged", "bludgeoning"],
                "duration": -1,
                "weapon_type": "stone_bow",
                "mana_cost": 70,
            },
            ("wind", "bow"): {
                "name": "Summon Wind Bow",
                "category": "weapon_summon",
                "element": "wind",
                "traits": ["summoning", "ranged", "swift"],
                "duration": -1,
                "weapon_type": "wind_bow",
                "mana_cost": 65,
            },
            ("bow", "force"): {
                "name": "Summon Power Bow",
                "category": "weapon_summon",
                "element": "physical",
                "traits": ["summoning", "ranged", "knockback"],
                "duration": -1,
                "weapon_type": "power_bow",
                "mana_cost": 70,
            },
            ("bow", "life"): {
                "name": "Null",
                "category": "none",
                "is_dud": True,
                "mana_cost": 5,
            },
            ("bow", "light"): {
                "name": "Summon Light Bow",
                "category": "weapon_summon",
                "element": "light",
                "traits": ["summoning", "ranged", "cleansing"],
                "duration": -1,
                "weapon_type": "light_bow",
                "mana_cost": 70,
            },

            # ============================================================
            # CROSS-WEAPON COMBOS (all null)
            # ============================================================
            ("axe", "sword"): {
                "name": "Null",
                "category": "none",
                "is_dud": True,
                "mana_cost": 5,
            },
            ("bow", "sword"): {
                "name": "Null",
                "category": "none",
                "is_dud": True,
                "mana_cost": 5,
            },
            ("axe", "bow"): {
                "name": "Null",
                "category": "none",
                "is_dud": True,
                "mana_cost": 5,
            },
            ("bow", "bow"): {
                "name": "Null",
                "category": "none",
                "is_dud": True,
                "mana_cost": 5,
            },

            # ============================================================
            # BULLET COMBOS (element + 弾)
            # ============================================================
            ("bullet", "fire"): {
                "name": "Fireball",
                "category": "destructive",
                "element": "fire",
                "traits": ["burning", "projectile"],
                "intensity": 1.5,
                "duration": 0.1,
                "radius": 0,
                "damage": {"amount": 25, "type": "fire"},
                "status_effects": [{"name": "burning", "duration": 4.0}],
                "projectile_spell": True,
                "projectile_speed": 10.0,
                "projectile_range": 10.0,
                "impact_radius": 0.75,
                "mana_cost": 25,
            },
            ("bullet", "water"): {
                "name": "Water Ball",
                "category": "destructive",
                "element": "water",
                "traits": ["wet", "projectile"],
                "intensity": 1.0,
                "duration": 0.1,
                "radius": 0,
                "damage": {"amount": 15, "type": "water"},
                "status_effects": [{"name": "wet", "duration": 5.0}],
                "projectile_spell": True,
                "projectile_speed": 10.0,
                "projectile_range": 10.0,
                "impact_radius": 0.75,
                "mana_cost": 20,
            },
            ("bullet", "earth"): {
                "name": "Rock Shot",
                "category": "destructive",
                "element": "earth",
                "traits": ["heavy", "projectile"],
                "intensity": 2.0,
                "duration": 0.1,
                "radius": 0,
                "damage": {"amount": 35, "type": "physical"},
                "projectile_spell": True,
                "projectile_speed": 8.0,
                "projectile_range": 8.0,
                "impact_radius": 0.5,
                "mana_cost": 25,
            },
            ("wind", "bullet"): {
                "name": "Wind Shot",
                "category": "destructive",
                "element": "wind",
                "traits": ["swift", "projectile"],
                "intensity": 1.0,
                "duration": 0.1,
                "radius": 0,
                "damage": {"amount": 15, "type": "physical"},
                "projectile_spell": True,
                "projectile_speed": 14.0,
                "projectile_range": 12.0,
                "impact_radius": 0.625,
                "mana_cost": 20,
            },
            ("bullet", "force"): {
                "name": "Force Bolt",
                "category": "destructive",
                "element": "physical",
                "traits": ["impact", "projectile"],
                "intensity": 1.5,
                "duration": 0.1,
                "radius": 0,
                "damage": {"amount": 20, "type": "physical"},
                "status_effects": [],
                "push_force": 1,
                "projectile_spell": True,
                "projectile_speed": 12.0,
                "projectile_range": 10.0,
                "impact_radius": 0.625,
                "mana_cost": 25,
            },
            ("bullet", "light"): {
                "name": "Light Bolt",
                "category": "destructive",
                "element": "light",
                "traits": ["radiance", "projectile"],
                "intensity": 1.2,
                "duration": 0.1,
                "radius": 0,
                "damage": {"amount": 20, "type": "light"},
                "status_effects": [{"name": "stunned", "duration": 1.0}],
                "projectile_spell": True,
                "projectile_speed": 12.0,
                "projectile_range": 10.0,
                "impact_radius": 0.5,
                "mana_cost": 25,
            },
            ("bullet", "dark"): {
                "name": "Shadow Bolt",
                "category": "destructive",
                "element": "dark",
                "traits": ["shadow", "projectile"],
                "intensity": 1.5,
                "duration": 0.1,
                "radius": 0,
                "damage": {"amount": 25, "type": "dark"},
                "status_effects": [{"name": "cursed", "duration": 4.0}],
                "projectile_spell": True,
                "projectile_speed": 10.0,
                "projectile_range": 10.0,
                "impact_radius": 0.5,
                "mana_cost": 30,
            },
            ("bullet", "electric"): {
                "name": "Spark Shot",
                "category": "destructive",
                "element": "electric",
                "traits": ["shock", "projectile"],
                "intensity": 1.5,
                "duration": 0.1,
                "radius": 0,
                "damage": {"amount": 25, "type": "electric"},
                "status_effects": [{"name": "electrified", "duration": 2.0}],
                "projectile_spell": True,
                "projectile_speed": 14.0,
                "projectile_range": 12.0,
                "impact_radius": 0.625,
                "mana_cost": 25,
            },
            ("bullet", "life"): {
                "name": "Null",
                "category": "none",
                "is_dud": True,
                "mana_cost": 5,
            },
            ("bullet", "great"): {
                "name": "Null",
                "category": "none",
                "is_dud": True,
                "mana_cost": 5,
            },
            ("bullet", "cut"): {
                "name": "Null",
                "category": "none",
                "is_dud": True,
                "mana_cost": 5,
            },
            ("bullet", "stone"): {
                "name": "Stone Shot",
                "category": "destructive",
                "element": "earth",
                "traits": ["rigid", "projectile"],
                "intensity": 2.5,
                "duration": 0.1,
                "radius": 0,
                "damage": {"amount": 40, "type": "physical"},
                "projectile_spell": True,
                "projectile_speed": 7.0,
                "projectile_range": 8.0,
                "impact_radius": 0.625,
                "mana_cost": 30,
            },
            ("blaze", "bullet"): {
                "name": "Blaze Ball",
                "category": "destructive",
                "element": "fire",
                "traits": ["inferno", "projectile"],
                "intensity": 2.0,
                "duration": 0.1,
                "radius": 0,
                "damage": {"amount": 45, "type": "fire"},
                "status_effects": [{"name": "burning", "duration": 5.0}],
                "projectile_spell": True,
                "projectile_speed": 9.0,
                "projectile_range": 10.0,
                "impact_radius": 1.25,
                "mana_cost": 45,
            },
            ("bullet", "thunder"): {
                "name": "Thunder Shot",
                "category": "destructive",
                "element": "electric",
                "traits": ["shock", "chain", "projectile"],
                "intensity": 2.0,
                "duration": 0.1,
                "radius": 0,
                "damage": {"amount": 45, "type": "electric"},
                "status_effects": [{"name": "electrified", "duration": 3.0}],
                "projectile_spell": True,
                "projectile_speed": 12.0,
                "projectile_range": 12.0,
                "impact_radius": 1.0,
                "mana_cost": 45,
            },
            ("bullet", "sword"): {
                "name": "Null",
                "category": "none",
                "is_dud": True,
                "mana_cost": 5,
            },
            ("axe", "bullet"): {
                "name": "Null",
                "category": "none",
                "is_dud": True,
                "mana_cost": 5,
            },
            ("bow", "bullet"): {
                "name": "Null",
                "category": "none",
                "is_dud": True,
                "mana_cost": 5,
            },
            ("bullet", "bullet"): {
                "name": "Null",
                "category": "none",
                "is_dud": True,
                "mana_cost": 5,
            },

            # ============================================================
            # ICE COMBOS (氷 + elements)
            # ============================================================
            ("fire", "ice"): {
                "name": "Steam Burst",
                "category": "destructive",
                "element": "water",
                "traits": ["steam", "pressure", "heat"],
                "intensity": 1.2,
                "duration": 0.3,
                "radius": 1,
                "damage": {"amount": 20, "type": "water"},
                "status_effects": [{"name": "wet", "duration": 3.0}],
                "mana_cost": 18,
            },
            ("ice", "water"): {
                "name": "Frozen Wave",
                "category": "environmental",
                "element": "ice",
                "traits": ["freezing", "wet", "cold"],
                "intensity": 1.0,
                "duration": 3.0,
                "radius": 1,
                "damage": {"amount": 12, "type": "ice"},
                "status_effects": [{"name": "frozen", "duration": 3.0}],
                "mana_cost": 15,
            },
            ("earth", "ice"): {
                "name": "Permafrost",
                "category": "environmental",
                "element": "ice",
                "traits": ["freezing", "heavy", "solid"],
                "intensity": 1.2,
                "duration": 5.0,
                "radius": 1,
                "status_effects": [{"name": "slowed", "duration": 5.0}],
                "mana_cost": 18,
            },
            ("wind", "ice"): {
                "name": "Blizzard",
                "category": "environmental",
                "element": "ice",
                "traits": ["freezing", "cutting", "obscuring"],
                "intensity": 1.0,
                "duration": 4.0,
                "radius": 2,
                "damage": {"amount": 8, "type": "ice"},
                "status_effects": [{"name": "chilled", "duration": 5.0}, {"name": "obscured", "duration": 4.0}],
                "tick_damage": True,
                "mana_cost": 22,
            },
            ("force", "ice"): {
                "name": "Shatter",
                "category": "destructive",
                "element": "ice",
                "traits": ["impact", "freezing", "knockback"],
                "intensity": 1.5,
                "duration": 0.1,
                "radius": 1,
                "damage": {"amount": 30, "type": "ice"},
                "status_effects": [{"name": "chilled", "duration": 3.0}],
                "push_force": 1,
                "mana_cost": 22,
            },
            ("ice", "life"): {
                "name": "Null",
                "category": "none",
                "is_dud": True,
                "mana_cost": 5,
            },
            ("ice", "light"): {
                "name": "Crystal Prism",
                "category": "utility",
                "element": "ice",
                "traits": ["freezing", "radiance", "revealing"],
                "intensity": 0.8,
                "duration": 6.0,
                "radius": 2,
                "status_effects": [{"name": "stunned", "duration": 1.5}],
                "mana_cost": 20,
            },
            ("dark", "ice"): {
                "name": "Frostbite",
                "category": "destructive",
                "element": "ice",
                "traits": ["freezing", "corruption", "cold"],
                "intensity": 1.5,
                "duration": 0.2,
                "radius": 0,
                "damage": {"amount": 22, "type": "ice"},
                "status_effects": [{"name": "chilled", "duration": 4.0}, {"name": "decaying", "duration": 5.0}],
                "mana_cost": 25,
            },
            ("electric", "ice"): {
                "name": "Null",
                "category": "none",
                "is_dud": True,
                "mana_cost": 5,
            },

            # ICE + MODIFIERS
            ("great", "ice"): {
                "name": "Greater Frost",
                "category": "destructive",
                "element": "ice",
                "traits": ["freezing", "cold", "amplify"],
                "intensity": 1.0,
                "duration": 2.0,
                "radius": 1,
                "damage": {"amount": 20, "type": "ice"},
                "status_effects": [{"name": "frozen", "duration": 3.0}],
                "mana_cost": 20,
            },
            ("cut", "ice"): {
                "name": "Null",
                "category": "none",
                "is_dud": True,
                "mana_cost": 5,
            },

            # ICE + WEAPONS
            ("ice", "sword"): {
                "name": "Summon Frost Blade",
                "category": "weapon_summon",
                "element": "ice",
                "traits": ["summoning", "slashing", "freezing"],
                "duration": -1,
                "weapon_type": "frost_sword",
                "mana_cost": 50,
            },
            ("axe", "ice"): {
                "name": "Summon Frost Axe",
                "category": "weapon_summon",
                "element": "ice",
                "traits": ["summoning", "slashing", "freezing"],
                "duration": -1,
                "weapon_type": "frost_axe",
                "mana_cost": 55,
            },
            ("bow", "ice"): {
                "name": "Summon Frost Bow",
                "category": "weapon_summon",
                "element": "ice",
                "traits": ["summoning", "ranged", "freezing"],
                "duration": -1,
                "weapon_type": "frost_bow",
                "mana_cost": 70,
            },

            # ICE + BULLET
            ("bullet", "ice"): {
                "name": "Ice Shard",
                "category": "destructive",
                "element": "ice",
                "traits": ["freezing", "projectile"],
                "intensity": 1.2,
                "duration": 0.1,
                "radius": 0,
                "damage": {"amount": 20, "type": "ice"},
                "status_effects": [{"name": "chilled", "duration": 4.0}],
                "projectile_spell": True,
                "projectile_speed": 12.0,
                "projectile_range": 10.0,
                "impact_radius": 0.625,
                "mana_cost": 22,
            },

            # ICE + ADVANCED ELEMENTS
            ("blaze", "ice"): {
                "name": "Null",
                "category": "none",
                "is_dud": True,
                "mana_cost": 5,
            },
            ("ice", "thunder"): {
                "name": "Null",
                "category": "none",
                "is_dud": True,
                "mana_cost": 5,
            },
            ("ice", "stone"): {
                "name": "Null",
                "category": "none",
                "is_dud": True,
                "mana_cost": 5,
            },

            # ICE + ICE
            ("ice", "ice"): {
                "name": "Glacial Spike",
                "category": "destructive",
                "element": "ice",
                "traits": ["freezing", "cold", "piercing"],
                "intensity": 1.5,
                "duration": 0.2,
                "radius": 0,
                "damage": {"amount": 30, "type": "ice"},
                "status_effects": [{"name": "frozen", "duration": 4.0}],
                "mana_cost": 20,
            },

            # ============================================================
            # DOUBLE ELEMENT COMBOS
            # ============================================================
        }

    @classmethod
    def _load_symbols_from_file(cls, filepath):
        """Load symbols from a JSON file."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for symbol_data in data.get("symbols", []):
            symbol_id = symbol_data.get("id")
            if symbol_id:
                cls._symbols[symbol_id] = Symbol(symbol_id, symbol_data)

    @classmethod
    def _load_spells_from_file(cls, filepath):
        """Load spell combinations from a JSON file."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for spell_data in data.get("single_spells", []):
            symbol_id = spell_data.get("symbol")
            if symbol_id:
                cls._single_spells[symbol_id] = spell_data

        for combo_data in data.get("combinations", []):
            symbols = combo_data.get("symbols", [])
            if len(symbols) == 2:
                key = cls._normalize_pair(symbols[0], symbols[1])
                cls._combinations[key] = combo_data

    @classmethod
    def _normalize_pair(cls, symbol1, symbol2):
        """Normalize a symbol pair to ensure order independence."""
        return tuple(sorted([symbol1, symbol2]))

    @classmethod
    def get_symbol(cls, symbol_id):
        """Get a symbol by ID."""
        # Initialize if needed
        if not cls._symbols:
            cls._load_default_data()
        return cls._symbols.get(symbol_id)

    @classmethod
    def get_all_symbols(cls):
        """Get all registered symbols."""
        if not cls._symbols:
            cls._load_default_data()
        return cls._symbols.copy()

    @classmethod
    def resolve_spell(cls, symbols):
        """
        Resolve a list of symbols (1 or 2) into a spell descriptor.
        Returns a dictionary that can be passed to objects.
        """
        # Initialize if needed
        if not cls._symbols:
            cls._load_default_data()

        if not symbols:
            return None

        # Single symbol
        if len(symbols) == 1:
            symbol_id = symbols[0]
            if symbol_id in cls._single_spells:
                spell_data = cls._single_spells[symbol_id].copy()
                spell_data["source_symbols"] = [symbol_id]
                return spell_data
            return None

        # Two symbols
        if len(symbols) == 2:
            key = cls._normalize_pair(symbols[0], symbols[1])
            if key in cls._combinations:
                spell_data = cls._combinations[key].copy()
                spell_data["source_symbols"] = list(symbols)
                return spell_data

            # No combination found - try to create a weak combined effect
            # or return dud
            return {
                "name": "Unstable Mix",
                "category": "none",
                "element": "none",
                "traits": [],
                "intensity": 0.2,
                "duration": 0.1,
                "is_dud": True,
                "mana_cost": 5,
                "source_symbols": list(symbols),
            }

        # More than 2 symbols not supported yet
        return None

    @classmethod
    def get_spell_info(cls, symbols):
        """Get spell info without casting (for notebook/preview)."""
        return cls.resolve_spell(symbols)
