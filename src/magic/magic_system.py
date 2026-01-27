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
                "character": "\u706b",  # Chinese character for fire
                "description": "The symbol of flame and heat.",
                "category": "elemental",
                "element": "fire",
                "base_traits": ["burning", "heat"],
            },
            "water": {
                "name": "Water",
                "character": "\u6c34",  # Chinese character for water
                "description": "The symbol of flow and moisture.",
                "category": "elemental",
                "element": "water",
                "base_traits": ["flowing", "wet"],
            },
            "earth": {
                "name": "Earth",
                "character": "\u571f",  # Chinese character for earth
                "description": "The symbol of stone and stability.",
                "category": "elemental",
                "element": "earth",
                "base_traits": ["solid", "heavy"],
            },
            "air": {
                "name": "Air",
                "character": "\u98a8",  # Chinese character for wind
                "description": "The symbol of wind and breath.",
                "category": "elemental",
                "element": "air",
                "base_traits": ["flowing", "pressure"],
            },
            "force": {
                "name": "Force",
                "character": "\u529b",  # Chinese character for force/power
                "description": "The symbol of raw physical power.",
                "category": "force",
                "element": "physical",
                "base_traits": ["pressure", "impact"],
            },
            "life": {
                "name": "Life",
                "character": "\u751f",  # Chinese character for life
                "description": "The symbol of vitality and growth.",
                "category": "abstract",
                "element": "nature",
                "base_traits": ["healing", "growth"],
            },
            "void": {
                "name": "Void",
                "character": "\u7a7a",  # Chinese character for empty/void
                "description": "The symbol of emptiness and absence.",
                "category": "abstract",
                "element": "dark",
                "base_traits": ["negation", "absorption"],
            },
            "light": {
                "name": "Light",
                "character": "\u5149",  # Chinese character for light
                "description": "The symbol of illumination and clarity.",
                "category": "elemental",
                "element": "light",
                "base_traits": ["radiance", "revealing"],
            },
            "sword": {
                "name": "Sword",
                "character": "\u5200",  # Chinese character for sword/blade (dao)
                "description": "The symbol of the blade, swift and precise.",
                "category": "weapon",
                "element": "physical",
                "base_traits": ["slashing", "swift"],
            },
            "axe": {
                "name": "Axe",
                "character": "\u65a7",  # Chinese character for axe (fu)
                "description": "The symbol of the axe, powerful and cleaving.",
                "category": "weapon",
                "element": "physical",
                "base_traits": ["slashing", "heavy"],
            },
            "great": {
                "name": "Great",
                "character": "\u5927",  # Chinese character for big/great (da)
                "description": "The symbol of magnitude and amplification.",
                "category": "modifier",
                "element": "none",
                "base_traits": ["amplify", "size"],
            },
            "bow": {
                "name": "Bow",
                "character": "\u5f13",  # Chinese character for bow (gong)
                "description": "The symbol of the bow, striking from afar.",
                "category": "weapon",
                "element": "physical",
                "base_traits": ["piercing", "ranged"],
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
                "duration": 2.0,
                "radius": 0,
                "damage": {"amount": 15, "type": "fire"},
                "status_effects": [{"name": "burning", "duration": 3.0, "intensity": 0.5}],
                "mana_cost": 8,
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
            "force": {
                "name": "Push",
                "category": "utility",
                "element": "physical",
                "traits": ["pressure", "impact"],
                "intensity": 1.0,
                "duration": 0.1,
                "radius": 0,
                "damage": {"amount": 10, "type": "physical"},
                "mana_cost": 6,
            },
            "earth": {
                "name": "Stone Shard",
                "category": "destructive",
                "element": "earth",
                "traits": ["solid", "piercing"],
                "intensity": 0.7,
                "duration": 0.1,
                "radius": 0,
                "damage": {"amount": 20, "type": "physical"},
                "mana_cost": 10,
            },
            "air": {
                "name": "Gust",
                "category": "utility",
                "element": "air",
                "traits": ["pressure", "flowing"],
                "intensity": 0.5,
                "duration": 0.5,
                "radius": 1,
                "damage": None,
                "mana_cost": 5,
            },
            "life": {
                "name": "Mend",
                "category": "utility",
                "element": "nature",
                "traits": ["healing", "growth"],
                "intensity": 0.5,
                "duration": 0.5,
                "radius": 0,
                "damage": {"amount": -15, "type": "healing"},  # Negative = healing
                "mana_cost": 12,
            },
            "light": {
                "name": "Flash",
                "category": "utility",
                "element": "light",
                "traits": ["radiance", "revealing"],
                "intensity": 0.5,
                "duration": 3.0,
                "radius": 2,
                "mana_cost": 5,
            },
            "void": {
                "name": "Drain",
                "category": "destructive",
                "element": "dark",
                "traits": ["negation", "absorption"],
                "intensity": 0.5,
                "duration": 1.0,
                "radius": 0,
                "damage": {"amount": 10, "type": "dark"},
                "mana_cost": 15,
            },
            "sword": {
                "name": "Summon Sword",
                "category": "weapon_summon",
                "element": "physical",
                "traits": ["summoning", "slashing"],
                "intensity": 1.0,
                "duration": -1,  # Permanent until dismissed
                "radius": 0,
                "weapon_type": "sword",
                "mana_cost": 15,
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
                "mana_cost": 18,
            },
            "great": {
                "name": "Amplify",
                "category": "utility",
                "element": "none",
                "traits": ["amplify"],
                "intensity": 0.3,
                "duration": 0.1,
                "radius": 0,
                "is_dud": True,  # Does nothing alone
                "mana_cost": 5,
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
                "mana_cost": 20,
            },
        }

        # Default combination spells (order-independent pairs)
        # Key format: tuple of sorted symbol ids
        cls._combinations = {
            ("fire", "force"): {
                "name": "Fireball",
                "category": "destructive",
                "element": "fire",
                "traits": ["burning", "impact", "explosion"],
                "intensity": 1.5,
                "duration": 0.5,
                "radius": 1,
                "damage": {"amount": 35, "type": "fire"},
                "status_effects": [{"name": "burning", "duration": 4.0}],
                "mana_cost": 20,
            },
            ("fire", "water"): {
                "name": "Steam Cloud",
                "category": "environmental",
                "element": "water",
                "traits": ["heat", "obscuring", "wet"],
                "intensity": 1.0,
                "duration": 5.0,
                "radius": 2,
                "damage": {"amount": 5, "type": "fire"},
                "status_effects": [{"name": "wet", "duration": 3.0}],
                "mana_cost": 15,
            },
            ("fire", "air"): {
                "name": "Inferno Gust",
                "category": "destructive",
                "element": "fire",
                "traits": ["burning", "pressure", "spreading"],
                "intensity": 1.2,
                "duration": 2.0,
                "radius": 2,
                "damage": {"amount": 25, "type": "fire"},
                "status_effects": [{"name": "burning", "duration": 5.0}],
                "mana_cost": 18,
            },
            ("water", "force"): {
                "name": "Water Jet",
                "category": "destructive",
                "element": "water",
                "traits": ["pressure", "piercing", "wet"],
                "intensity": 1.3,
                "duration": 0.3,
                "radius": 0,
                "damage": {"amount": 30, "type": "physical"},
                "status_effects": [{"name": "wet", "duration": 5.0}],
                "mana_cost": 15,
            },
            ("water", "air"): {
                "name": "Mist",
                "category": "environmental",
                "element": "water",
                "traits": ["obscuring", "wet", "flowing"],
                "intensity": 0.8,
                "duration": 8.0,
                "radius": 3,
                "status_effects": [{"name": "wet", "duration": 3.0}],
                "mana_cost": 12,
            },
            ("earth", "force"): {
                "name": "Boulder",
                "category": "destructive",
                "element": "earth",
                "traits": ["heavy", "impact", "crushing"],
                "intensity": 2.0,
                "duration": 0.2,
                "radius": 0,
                "damage": {"amount": 50, "type": "physical"},
                "mana_cost": 25,
            },
            ("earth", "water"): {
                "name": "Mud",
                "category": "environmental",
                "element": "earth",
                "traits": ["slowing", "wet", "sticky"],
                "intensity": 1.0,
                "duration": 10.0,
                "radius": 2,
                "status_effects": [{"name": "slowed", "duration": 5.0}],
                "mana_cost": 15,
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
                "affects_caster": True,
                "mana_cost": 20,
            },
            ("life", "water"): {
                "name": "Rejuvenation",
                "category": "utility",
                "element": "nature",
                "traits": ["healing", "cleansing", "wet"],
                "intensity": 1.5,
                "duration": 3.0,
                "radius": 0,
                "damage": {"amount": -40, "type": "healing"},
                "status_effects": [{"name": "wet", "duration": 2.0}],
                "mana_cost": 25,
            },
            ("life", "light"): {
                "name": "Purify",
                "category": "utility",
                "element": "light",
                "traits": ["healing", "cleansing", "radiance"],
                "intensity": 1.2,
                "duration": 1.0,
                "radius": 1,
                "damage": {"amount": -25, "type": "healing"},
                "mana_cost": 20,
            },
            ("void", "force"): {
                "name": "Gravity Well",
                "category": "utility",
                "element": "dark",
                "traits": ["pulling", "heavy", "negation"],
                "intensity": 1.5,
                "duration": 4.0,
                "radius": 2,
                "status_effects": [{"name": "slowed", "duration": 4.0}],
                "mana_cost": 22,
            },
            ("fire", "earth"): {
                "name": "Magma Burst",
                "category": "destructive",
                "element": "fire",
                "traits": ["burning", "heavy", "melting"],
                "intensity": 1.8,
                "duration": 3.0,
                "radius": 1,
                "damage": {"amount": 40, "type": "fire"},
                "status_effects": [{"name": "burning", "duration": 6.0}],
                "mana_cost": 28,
            },
            # Dud combinations - produce no useful effect
            ("void", "void"): {
                "name": "Nothing",
                "category": "none",
                "element": "none",
                "traits": [],
                "intensity": 0,
                "duration": 0.1,
                "is_dud": True,
                "mana_cost": 5,
            },
            # Weapon combinations with "great" modifier
            ("great", "sword"): {
                "name": "Summon Great Sword",
                "category": "weapon_summon",
                "element": "physical",
                "traits": ["summoning", "slashing", "heavy"],
                "intensity": 2.0,
                "duration": -1,
                "radius": 0,
                "weapon_type": "big_sword",
                "mana_cost": 25,
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
                "mana_cost": 30,
            },
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
