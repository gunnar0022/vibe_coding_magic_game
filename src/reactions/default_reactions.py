"""
Default elemental reactions based on the design document.
Registers all element+element and element+attribute reactions.
"""
from .elements import Element, Attribute
from .reaction_registry import ReactionRegistry
from .reaction_definition import ReactionDefinition


def register_default_reactions():
    """Register all default reactions from the design document."""
    _register_element_element_reactions()
    _register_element_attribute_reactions()
    _register_reactive_statuses()


def _register_reactive_statuses():
    """Register status effects that can trigger element reactions."""
    ReactionRegistry.register_reactive_status("burning")
    ReactionRegistry.register_reactive_status("wet")
    ReactionRegistry.register_reactive_status("frozen")
    ReactionRegistry.register_reactive_status("electrified")
    ReactionRegistry.register_reactive_status("chilled")


def _register_element_element_reactions():
    """Register all element + element reactions."""

    # ===== FIRE REACTIONS =====

    # Fire + Water = Steam (extinguishes fire, creates steam cloud)
    ReactionRegistry.register_element_reaction(Element.FIRE, Element.WATER, {
        "name": "Steam",
        "priority": 80,
        "removes_statuses": ["burning", "wet"],
        "produces_effect": "steam_cloud",
        "cancels_source": True,
    })

    # Fire + Ice = Melt (extinguishes fire, creates water/wet)
    ReactionRegistry.register_element_reaction(Element.FIRE, Element.ICE, {
        "name": "Melt",
        "priority": 75,
        "removes_statuses": ["frozen", "burning"],
        "applies_statuses": [{"name": "wet", "duration": 10.0}],
        "cancels_source": True,
    })

    # Fire + Wind = Spread (fire spreads faster/further)
    ReactionRegistry.register_element_reaction(Element.FIRE, Element.WIND, {
        "name": "Fan Flames",
        "priority": 60,
        "spread_type": "adjacent",
        "spread_range": 2,
        "spread_condition": "plant",
        "spread_element": Element.FIRE,
        "chain_reaction": True,
    })

    # Fire + Earth = No strong reaction (earth remains)
    # No registration needed - handled by default "no reaction"

    # Fire + Electric = Discharge (brief, high heat effect)
    ReactionRegistry.register_element_reaction(Element.FIRE, Element.ELECTRIC, {
        "name": "Discharge",
        "priority": 70,
        "damage": {"amount": 8, "type": "fire"},
        "removes_statuses": ["electrified"],
    })

    # Fire + Light = Fire overtakes light (fire remains)
    # Fire + Dark = Fire overtakes dark (fire remains)
    # Fire + Spirit = Fire overtakes spirit (fire remains)
    # These are "first element wins" - no special reaction needed

    # ===== WATER REACTIONS =====

    # Water + Ice = Freeze
    ReactionRegistry.register_element_reaction(Element.WATER, Element.ICE, {
        "name": "Freeze",
        "priority": 70,
        "removes_statuses": ["wet"],
        "applies_statuses": [{"name": "frozen", "duration": 8.0}],
    })

    # Water + Wind = Cleanse both
    ReactionRegistry.register_element_reaction(Element.WATER, Element.WIND, {
        "name": "Cleanse",
        "priority": 65,
        "removes_statuses": ["wet"],
    })

    # Water + Earth = Mud (slows movement)
    ReactionRegistry.register_element_reaction(Element.WATER, Element.EARTH, {
        "name": "Mud",
        "priority": 55,
        "applies_statuses": [{"name": "muddy", "duration": 6.0}],
    })

    # Water + Electric = Conductivity (spreads electric through water)
    ReactionRegistry.register_element_reaction(Element.WATER, Element.ELECTRIC, {
        "name": "Electrified Water",
        "priority": 90,
        "applies_statuses": [{"name": "electrified", "duration": 2.0}],
        "damage": {"amount": 15, "type": "electric"},
        "spread_type": "material",
        "spread_condition": "wet",
        "spread_element": Element.ELECTRIC,
        "chain_reaction": True,
    })

    # Water + Light = Water overtakes light
    # Water + Dark = Water overtakes dark
    # Water + Spirit = Water overtakes spirit
    # No special reactions

    # ===== ICE REACTIONS =====

    # Ice + Wind = Cold damage to living things
    ReactionRegistry.register_element_reaction(Element.ICE, Element.WIND, {
        "name": "Bitter Cold",
        "priority": 60,
        "applies_statuses": [{"name": "chilled", "duration": 4.0}],
        "damage": {"amount": 5, "type": "ice"},
    })

    # Ice + Earth = Ice remains
    # Ice + Electric = Ice remains
    # Ice + Light = Ice remains
    # No strong reactions

    # Ice + Dark = Dark remains
    ReactionRegistry.register_element_reaction(Element.ICE, Element.DARK, {
        "name": "Black Ice",
        "priority": 50,
        # Dark overtakes ice, but ice remains as status
    })

    # Ice + Spirit = Stun effect
    ReactionRegistry.register_element_reaction(Element.ICE, Element.SPIRIT, {
        "name": "Soul Freeze",
        "priority": 55,
        "applies_statuses": [{"name": "stunned", "duration": 2.0}],
    })

    # ===== WIND REACTIONS =====

    # Wind + Earth = Cleanse
    ReactionRegistry.register_element_reaction(Element.WIND, Element.EARTH, {
        "name": "Settle",
        "priority": 50,
        "removes_statuses": ["muddy"],
    })

    # Wind + Electric = Nothing special
    # Wind + Light = Light remains
    # Wind + Dark = Dark remains
    # Wind + Spirit = Spirit remains

    # ===== EARTH REACTIONS =====

    # Earth + Electric = Earth remains (grounding)
    ReactionRegistry.register_element_reaction(Element.EARTH, Element.ELECTRIC, {
        "name": "Ground",
        "priority": 60,
        "removes_statuses": ["electrified"],
    })

    # Earth + Light = Earth remains
    # Earth + Dark = Dark remains
    # Earth + Spirit = Spirit remains

    # ===== ELECTRIC REACTIONS =====

    # Electric + Light = Full cleanse
    ReactionRegistry.register_element_reaction(Element.ELECTRIC, Element.LIGHT, {
        "name": "Purge",
        "priority": 75,
        "removes_statuses": ["electrified", "burning", "frozen", "poisoned"],
    })

    # Electric + Dark = Second remains
    # Electric + Spirit = Second remains

    # ===== LIGHT REACTIONS =====

    # Light + Dark = Cleanse both (nullify)
    ReactionRegistry.register_element_reaction(Element.LIGHT, Element.DARK, {
        "name": "Nullify",
        "priority": 80,
        "removes_statuses": ["feared", "cursed", "blinded"],
        "cancels_source": True,
    })

    # Light + Spirit = Spirit remains

    # ===== DARK REACTIONS =====

    # Dark + Spirit = Fear status
    ReactionRegistry.register_element_reaction(Element.DARK, Element.SPIRIT, {
        "name": "Terror",
        "priority": 65,
        "applies_statuses": [{"name": "feared", "duration": 5.0}],
    })


def _register_element_attribute_reactions():
    """Register all element + attribute reactions."""

    # ===== FIRE + ATTRIBUTES =====

    # Fire + Organic = Burning (damage over time)
    ReactionRegistry.register_attribute_reaction(Element.FIRE, Attribute.ORGANIC, {
        "name": "Burn",
        "priority": 45,
        "applies_statuses": [{"name": "burning", "duration": 4.0, "intensity": 1.0}],
        "damage": {"amount": 3, "type": "fire"},
    })

    # Fire + Plant = Burns faster, spreads fire
    ReactionRegistry.register_attribute_reaction(Element.FIRE, Attribute.PLANT, {
        "name": "Ignite Vegetation",
        "priority": 50,
        "applies_statuses": [{"name": "burning", "duration": 6.0, "intensity": 1.5}],
        "damage": {"amount": 5, "type": "fire"},
        "spread_type": "adjacent",
        "spread_range": 1,
        "spread_condition": "plant",
        "spread_element": Element.FIRE,
        "chain_reaction": True,
    })

    # Fire + Metal = Heating (damages on touch)
    ReactionRegistry.register_attribute_reaction(Element.FIRE, Attribute.METAL, {
        "name": "Heat Metal",
        "priority": 40,
        "applies_statuses": [{"name": "heated", "duration": 8.0}],
        "damage": {"amount": 2, "type": "fire"},
    })

    # Fire + Liquid = Evaporation
    ReactionRegistry.register_attribute_reaction(Element.FIRE, Attribute.LIQUID, {
        "name": "Evaporate",
        "priority": 55,
        "removes_statuses": ["wet"],
        "produces_effect": "steam_cloud",
    })

    # Fire + Stone = Heating (dissipates faster than metal)
    ReactionRegistry.register_attribute_reaction(Element.FIRE, Attribute.STONE, {
        "name": "Heat Stone",
        "priority": 35,
        "applies_statuses": [{"name": "heated", "duration": 4.0}],
    })

    # ===== WATER + ATTRIBUTES =====

    # Water + Organic = Wet status (extinguishes burning)
    ReactionRegistry.register_attribute_reaction(Element.WATER, Attribute.ORGANIC, {
        "name": "Drench",
        "priority": 50,
        "removes_statuses": ["burning", "heated"],
        "applies_statuses": [{"name": "wet", "duration": 10.0}],
    })

    # Water + Plant = Growth (positive effect)
    ReactionRegistry.register_attribute_reaction(Element.WATER, Attribute.PLANT, {
        "name": "Nourish",
        "priority": 45,
        "removes_statuses": ["burning", "withered"],
        "applies_statuses": [{"name": "growing", "duration": 15.0}],
    })

    # Water + Metal = Nothing special
    # Water + Stone = Nothing special (maybe erosion long-term?)

    # ===== ICE + ATTRIBUTES =====

    # Ice + Organic = Slow
    ReactionRegistry.register_attribute_reaction(Element.ICE, Attribute.ORGANIC, {
        "name": "Chill",
        "priority": 45,
        "applies_statuses": [{"name": "chilled", "duration": 5.0}],
    })

    # Ice + Plant = Frost damage
    ReactionRegistry.register_attribute_reaction(Element.ICE, Attribute.PLANT, {
        "name": "Frost",
        "priority": 45,
        "applies_statuses": [{"name": "frozen", "duration": 6.0}],
        "damage": {"amount": 8, "type": "ice"},
    })

    # Ice + Metal = Nothing
    # Ice + Stone = Nothing

    # Ice + Liquid = Freezes into ice block
    ReactionRegistry.register_attribute_reaction(Element.ICE, Attribute.LIQUID, {
        "name": "Freeze Solid",
        "priority": 55,
        "applies_statuses": [{"name": "frozen", "duration": 12.0}],
    })

    # ===== ELECTRIC + ATTRIBUTES =====

    # Electric + Organic = Shock damage, stun
    ReactionRegistry.register_attribute_reaction(Element.ELECTRIC, Attribute.ORGANIC, {
        "name": "Shock",
        "priority": 50,
        "applies_statuses": [{"name": "electrified", "duration": 1.0}, {"name": "stunned", "duration": 0.5}],
        "damage": {"amount": 10, "type": "electric"},
    })

    # Electric + Plant = Nothing special

    # Electric + Metal = Chains to nearby metal
    ReactionRegistry.register_attribute_reaction(Element.ELECTRIC, Attribute.METAL, {
        "name": "Conduct",
        "priority": 60,
        "applies_statuses": [{"name": "electrified", "duration": 1.5}],
        "damage": {"amount": 12, "type": "electric"},
        "spread_type": "radius",
        "spread_range": 2,
        "spread_condition": "metal",
        "spread_element": Element.ELECTRIC,
        "chain_reaction": True,
    })

    # Electric + Liquid = Full body conduction
    ReactionRegistry.register_attribute_reaction(Element.ELECTRIC, Attribute.LIQUID, {
        "name": "Full Conduction",
        "priority": 65,
        "applies_statuses": [{"name": "electrified", "duration": 2.0, "intensity": 1.5}],
        "damage": {"amount": 20, "type": "electric"},
    })

    # Electric + Stone = No effect (grounded)

    # ===== WIND + ATTRIBUTES =====

    # Wind + Organic = Push (depends on object)
    ReactionRegistry.register_attribute_reaction(Element.WIND, Attribute.ORGANIC, {
        "name": "Gust",
        "priority": 40,
        # Push effect would be handled by specific object logic
    })

    # Wind + Plant = Similar to organic
    ReactionRegistry.register_attribute_reaction(Element.WIND, Attribute.PLANT, {
        "name": "Sway",
        "priority": 40,
        # Seeds could spread, etc. - handled by specific object logic
    })

    # Wind + Metal = No effect
    # Wind + Liquid = No effect
    # Wind + Stone = No effect (maybe erosion over long time)

    # ===== EARTH + ATTRIBUTES =====

    # Earth + Organic = Nothing
    # Earth + Plant = Nothing
    # Earth + Metal = Nothing

    # Earth + Liquid = Make mud
    ReactionRegistry.register_attribute_reaction(Element.EARTH, Attribute.LIQUID, {
        "name": "Muddy",
        "priority": 45,
        "applies_statuses": [{"name": "muddy", "duration": 8.0}],
    })

    # Earth + Stone = Nothing

    # ===== LIGHT + ATTRIBUTES =====
    # Light has minimal reactions with physical attributes
    # Most light effects are status-based (revealing, blessing, etc.)

    # ===== DARK + ATTRIBUTES =====

    # Dark + Organic = Wither
    ReactionRegistry.register_attribute_reaction(Element.DARK, Attribute.ORGANIC, {
        "name": "Wither",
        "priority": 50,
        "applies_statuses": [{"name": "withered", "duration": 8.0}],
        "damage": {"amount": 5, "type": "dark"},
    })

    # Dark + Plant = Wilt, decay
    ReactionRegistry.register_attribute_reaction(Element.DARK, Attribute.PLANT, {
        "name": "Decay",
        "priority": 50,
        "applies_statuses": [{"name": "decaying", "duration": 10.0}],
        "damage": {"amount": 8, "type": "dark"},
    })

    # Dark + Metal = Weaken (swords/armor less effective)
    ReactionRegistry.register_attribute_reaction(Element.DARK, Attribute.METAL, {
        "name": "Corrode",
        "priority": 45,
        "applies_statuses": [{"name": "weakened", "duration": 12.0}],
    })

    # Dark + Liquid = Tainted/Poisoned
    ReactionRegistry.register_attribute_reaction(Element.DARK, Attribute.LIQUID, {
        "name": "Taint",
        "priority": 50,
        "applies_statuses": [{"name": "tainted", "duration": 15.0}],
    })

    # Dark + Stone = Nothing

    # ===== SPIRIT + ATTRIBUTES =====
    # Spirit has minimal reactions with physical attributes
    # Spirit effects are more metaphysical (possession, enchantment, etc.)
