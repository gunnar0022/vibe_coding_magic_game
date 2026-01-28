"""
Rune Stone entity - magical stones that teach symbols when interacted with.
"""
from .base import Entity
from ..components import InteractionComponent


class RuneStone(Entity):
    """
    A magical rune stone that can teach the player a symbol.
    Once activated, the stone becomes dormant.
    """

    def __init__(self, x=0, y=0, symbol_id="earth", data=None):
        super().__init__(x, y, tags=["rune_stone", "interactable"])
        data = data or {}

        self.symbol_id = symbol_id
        self.solid = True

        # Visual properties
        self.color = data.get("color", (120, 100, 180))  # Purple-ish stone
        self.dormant_color = (80, 80, 90)  # Grey when used

        # State
        self.is_activated = False  # Whether the player has learned from this stone

        # Interaction component
        self.interaction = self.add_component(InteractionComponent())
        self.interaction.can_examine = True
        self._update_examine_text()

        # Teaching context
        self.teaching_context = data.get("context", f"Ancient knowledge from a rune stone")
        self.activation_message = data.get("activation_message",
            "The stone glows with ancient power as knowledge flows into your mind...")

    def _update_examine_text(self):
        """Update examine text and color based on activation state."""
        if self.is_activated:
            self.color = self.dormant_color
            self.interaction.set_examine_text(
                "A dormant rune stone. Its power has been absorbed."
            )
        else:
            self.interaction.set_examine_text(
                f"An ancient stone carved with a glowing rune. "
                f"You sense the symbol of {self.symbol_id} within."
            )

    def can_teach(self, player):
        """Check if this stone can teach the player."""
        if self.is_activated:
            return False
        if self.symbol_id in player.known_symbols:
            return False
        return True

    def teach(self, player):
        """
        Teach the symbol to the player.
        Returns (success, messages) where messages is a list of dialogue lines.
        """
        if not self.can_teach(player):
            if self.is_activated:
                return False, ["The stone is dormant. Its power has already been claimed."]
            else:
                return False, ["You already know this symbol."]

        # Teach the symbol
        if player.learn_symbol(self.symbol_id):
            self.is_activated = True
            self._update_examine_text()
            return True, [
                self.activation_message,
                f"You have learned the symbol of {self.symbol_id}!"
            ]
        else:
            return False, ["Something prevents you from learning."]

    def get_current_color(self):
        """Get the current color based on activation state."""
        return self.dormant_color if self.is_activated else self.color

    def serialize(self):
        data = super().serialize()
        data.update({
            "symbol_id": self.symbol_id,
            "is_activated": self.is_activated,
            "teaching_context": self.teaching_context,
        })
        return data

    def deserialize(self, data):
        super().deserialize(data)
        self.symbol_id = data.get("symbol_id", "earth")
        self.is_activated = data.get("is_activated", False)
        self.teaching_context = data.get("teaching_context", "")
        self._update_examine_text()


# Predefined rune stone templates
RUNE_STONE_TEMPLATES = {
    "earth_stone": {
        "symbol_id": "earth",
        "color": (140, 120, 80),  # Earthy brown
        "context": "Discovered in an ancient rune stone",
        "activation_message": "The earth beneath you trembles as ancient knowledge fills your mind...",
    },
    "air_stone": {
        "symbol_id": "air",
        "color": (180, 200, 220),  # Light blue-grey
        "context": "Whispered by the winds of a rune stone",
        "activation_message": "A gentle breeze swirls around you as the symbol becomes clear...",
    },
    "light_stone": {
        "symbol_id": "light",
        "color": (255, 240, 180),  # Warm golden
        "context": "Illuminated by a rune stone",
        "activation_message": "Brilliant light bursts from the stone, imprinting wisdom upon you...",
    },
    "void_stone": {
        "symbol_id": "void",
        "color": (40, 20, 60),  # Dark purple
        "context": "Absorbed from a void rune stone",
        "activation_message": "Darkness envelops you momentarily as forbidden knowledge seeps in...",
    },
    "sword_stone": {
        "symbol_id": "sword",
        "color": (180, 180, 200),  # Metallic silver
        "context": "Carved upon a warrior's memorial stone",
        "activation_message": "The spirit of a thousand blades whispers through your mind...",
    },
    "axe_stone": {
        "symbol_id": "axe",
        "color": (120, 100, 80),  # Bronze-brown
        "context": "Etched into an ancient logging stone",
        "activation_message": "The echo of falling trees resonates within you...",
    },
    "great_stone": {
        "symbol_id": "great",
        "color": (200, 180, 150),  # Pale gold
        "context": "Inscribed on a monument of grandeur",
        "activation_message": "A sense of magnitude and power swells within you...",
    },
    "bow_stone": {
        "symbol_id": "bow",
        "color": (160, 120, 60),  # Warm wood brown
        "context": "Carved upon an ancient archer's monument",
        "activation_message": "The whisper of a bowstring echoes through your mind...",
    },
    "dark_stone": {
        "symbol_id": "dark",
        "color": (60, 30, 80),  # Deep purple-black
        "context": "Found in the shadow of a forgotten shrine",
        "activation_message": "Shadows coil around you as dark knowledge seeps into your mind...",
    },
    "electric_stone": {
        "symbol_id": "electric",
        "color": (180, 220, 50),  # Electric yellow-green
        "context": "Struck by lightning upon an exposed hilltop",
        "activation_message": "Static crackles through your fingertips as the symbol ignites...",
    },
    "thunder_stone": {
        "symbol_id": "thunder",
        "color": (100, 80, 200),  # Storm purple
        "context": "Embedded in the heart of a thunderstruck boulder",
        "activation_message": "Thunder rumbles within you as raw power surges through your veins...",
    },
    "blaze_stone": {
        "symbol_id": "blaze",
        "color": (240, 120, 40),  # Intense orange
        "context": "Forged in the mouth of an ancient volcano",
        "activation_message": "An inferno blazes behind your eyes as the symbol sears into memory...",
    },
    "cut_stone": {
        "symbol_id": "cut",
        "color": (200, 200, 210),  # Sharp silver
        "context": "Etched by an impossibly sharp edge into living rock",
        "activation_message": "A razor-thin line of light slices through your consciousness...",
    },
    "stone_stone": {
        "symbol_id": "stone",
        "color": (160, 150, 130),  # Grey-brown stone
        "context": "Buried deep within solid bedrock",
        "activation_message": "The weight of mountains presses into your awareness...",
    },
}


def create_rune_stone(template_id, x, y):
    """Create a rune stone from a template or directly with a symbol ID."""
    if template_id in RUNE_STONE_TEMPLATES:
        template = RUNE_STONE_TEMPLATES[template_id].copy()
        return RuneStone(x, y, template.pop("symbol_id"), template)
    else:
        # Treat template_id as the symbol_id directly
        return RuneStone(x, y, template_id)
