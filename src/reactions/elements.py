"""
Element and Attribute constants for the elemental reactions system.

Elements are active forces that can be applied via magic or environment.
Attributes are inherent properties of objects.
"""


class Element:
    """
    Elements are active forces that can be applied to entities.
    Used in spells and environmental effects.
    """
    FIRE = "fire"
    WATER = "water"
    ICE = "ice"
    ELECTRIC = "electric"
    WIND = "wind"
    EARTH = "earth"
    LIGHT = "light"
    DARK = "dark"
    SPIRIT = "spirit"
    NONE = "none"

    # All elements for iteration
    ALL = [FIRE, WATER, ICE, ELECTRIC, WIND, EARTH, LIGHT, DARK, SPIRIT]


class Attribute:
    """
    Attributes are inherent properties of objects.
    Stored as entity tags.
    """
    ORGANIC = "organic"    # Living tissue - creatures, player, fabric
    PLANT = "plant"        # Vegetation - trees, grass, flowers (subset of organic behavior)
    METAL = "metal"        # Metallic objects - weapons, armor, ore
    LIQUID = "liquid"      # Water bodies, potions
    STONE = "stone"        # Rocks, boulders, walls

    # All attributes for iteration
    ALL = [ORGANIC, PLANT, METAL, LIQUID, STONE]


# Mapping from status flags to their corresponding element
# Used when checking for element+element reactions based on current status
STATUS_TO_ELEMENT = {
    "burning": Element.FIRE,
    "wet": Element.WATER,
    "frozen": Element.ICE,
    "electrified": Element.ELECTRIC,
    "chilled": Element.ICE,  # Chilled is a weaker form of ice
    "decaying": Element.DARK,
    "cursed": Element.DARK,
}

# Mapping from elements to their primary status effect
ELEMENT_TO_STATUS = {
    Element.FIRE: "burning",
    Element.WATER: "wet",
    Element.ICE: "frozen",
    Element.ELECTRIC: "electrified",
    Element.DARK: "cursed",
}

# All status effects considered negative (used by cleanse mechanics)
NEGATIVE_STATUSES = [
    "burning", "poisoned", "stunned", "slowed", "frozen",
    "chilled", "feared", "cursed", "withered", "decaying",
    "weakened", "tainted", "obscured",
]

# Element priority for queue ordering when multiple elements conflict
# Higher number = processed first
ELEMENT_PRIORITY = {
    Element.ELECTRIC: 90,  # Dangerous, immediate
    Element.WATER: 80,     # Extinguishes, cleanses
    Element.FIRE: 75,      # Burning, spreading
    Element.ICE: 70,       # Freezing
    Element.LIGHT: 65,     # Cleansing
    Element.DARK: 60,      # Corrupting
    Element.WIND: 55,      # Spreading
    Element.EARTH: 50,     # Grounding
    Element.SPIRIT: 45,    # Ethereal
    Element.NONE: 0,
}

# Canonical element colors (RGB tuples) used for projectiles, effects, and UI
ELEMENT_COLORS = {
    Element.FIRE: (240, 120, 50),
    Element.WATER: (80, 160, 240),
    Element.EARTH: (160, 140, 100),
    Element.WIND: (180, 220, 200),
    Element.ICE: (140, 210, 235),
    Element.ELECTRIC: (255, 255, 100),
    Element.LIGHT: (255, 245, 200),
    Element.DARK: (80, 40, 120),
    Element.SPIRIT: (180, 140, 220),
    Element.NONE: (200, 200, 200),
    "physical": (220, 200, 120),
    "nature": (50, 200, 50),
}
