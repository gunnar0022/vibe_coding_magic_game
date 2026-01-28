"""
NPC entity - non-player characters that can teach, trade, and interact.
"""
from .actor import Actor


class NPC(Actor):
    """
    A non-player character.
    NPCs can teach symbols, provide information, and offer services.
    """

    def __init__(self, x=0, y=0, npc_id="generic_npc", data=None):
        super().__init__(x, y, tags=["npc"])
        data = data or {}

        self.npc_id = npc_id
        self.controller = "ai"

        # NPC properties
        self.name = data.get("name", "Stranger")
        self.title = data.get("title", "")  # e.g., "Village Elder", "Wandering Mage"
        self.color = data.get("color", (200, 150, 100))

        # Dialogue
        self.dialogue_id = data.get("dialogue_id", None)
        self.interaction.set_dialogue(self.dialogue_id)
        self.interaction.can_talk = True
        self.interaction.can_examine = True

        # Examination text
        examine = data.get("examine_text", f"{self.name} stands here.")
        if self.title:
            examine = f"{self.name}, {self.title}. " + examine
        self.interaction.set_examine_text(examine)

        # Teaching capability
        self.can_teach = data.get("can_teach", False)
        self.teachable_symbols = data.get("teachable_symbols", [])
        self.taught_symbols = set()  # Symbols already taught to player

        # Trading capability
        self.can_trade = data.get("can_trade", False)
        self.trade_inventory = data.get("trade_inventory", [])

        # Movement behavior
        self.wanders = data.get("wanders", False)
        self.wander_radius = data.get("wander_radius", 3)
        self.home_x = x
        self.home_y = y

        # AI state
        self.ai_state = "idle"
        self.ai_timer = 0

    def get_display_name(self):
        """Get full display name with title."""
        if self.title:
            return f"{self.name}, {self.title}"
        return self.name

    def can_teach_symbol(self, symbol_id):
        """Check if NPC can teach a specific symbol."""
        return (self.can_teach and
                symbol_id in self.teachable_symbols and
                symbol_id not in self.taught_symbols)

    def teach_symbol(self, symbol_id, player):
        """
        Teach a symbol to the player.
        Returns (success, message, symbol_data).
        """
        if not self.can_teach_symbol(symbol_id):
            return False, "I have nothing more to teach you about that.", None

        if player.learn_symbol(symbol_id):
            self.taught_symbols.add(symbol_id)
            return True, f"Let me show you the symbol of {symbol_id}...", {
                "symbol_id": symbol_id,
                "teacher": self.name,
                "context": f"Taught by {self.get_display_name()}",
            }
        else:
            return False, "You already know this symbol.", None

    def get_teachable_for_player(self, player):
        """Get list of symbols this NPC can teach to this player."""
        return [s for s in self.teachable_symbols
                if s not in self.taught_symbols and s not in player.known_symbols]

    def update(self, dt):
        super().update(dt)

        # Simple wandering AI
        if self.wanders and self.ai_state == "idle":
            self.ai_timer -= dt
            if self.ai_timer <= 0:
                self._wander_step()
                self.ai_timer = 2.0 + (hash(self.npc_id) % 30) / 10  # 2-5 seconds

    def _wander_step(self):
        """Take a wandering step (if world reference available)."""
        # This would need world reference to check collision
        # For now, just change facing randomly
        import random
        self.facing = random.choice(["up", "down", "left", "right"])

    def get_greeting(self, player=None):
        """Get a greeting message for interaction."""
        # Check if we've taught everything we can
        if player and self.can_teach:
            teachable = self.get_teachable_for_player(player)
            if not teachable and self.taught_symbols:
                # Already taught what we know
                return f"Welcome back, young one. Practice the symbol of {', '.join(self.taught_symbols)} well."

        greetings = [
            f"Hello, traveler. I am {self.name}.",
            f"Greetings. What brings you here?",
            f"Ah, a visitor. I am {self.get_display_name()}.",
        ]
        import random
        return random.choice(greetings)

    def serialize(self):
        data = super().serialize()
        data.update({
            "npc_id": self.npc_id,
            "name": self.name,
            "title": self.title,
            "taught_symbols": list(self.taught_symbols),
            "ai_state": self.ai_state,
        })
        return data

    def deserialize(self, data):
        super().deserialize(data)
        self.taught_symbols = set(data.get("taught_symbols", []))
        self.ai_state = data.get("ai_state", "idle")


# Predefined NPC templates
NPC_TEMPLATES = {
    "village_elder": {
        "name": "Elder Mira",
        "title": "Village Elder",
        "color": (180, 160, 140),
        "can_teach": True,
        "teachable_symbols": ["force"],
        "examine_text": "An elderly woman with kind eyes and weathered hands. She has seen much.",
        "wanders": False,
    },
    "wandering_mage": {
        "name": "Kael",
        "title": "Wandering Scholar",
        "color": (100, 120, 180),
        "can_teach": True,
        "teachable_symbols": ["wind", "earth", "light"],
        "examine_text": "A traveler in worn robes, carrying a staff covered in strange markings.",
        "wanders": True,
        "wander_radius": 5,
    },
    "hermit": {
        "name": "The Hermit",
        "title": "",
        "color": (120, 100, 80),
        "can_teach": True,
        "teachable_symbols": ["life"],
        "examine_text": "A mysterious figure who rarely speaks. Their eyes hold ancient knowledge.",
        "wanders": False,
    },
    "merchant": {
        "name": "Bram",
        "title": "Traveling Merchant",
        "color": (160, 140, 100),
        "can_teach": False,
        "can_trade": True,
        "examine_text": "A jovial merchant with a cart full of curious goods.",
        "wanders": False,
    },
}


def create_npc_from_template(template_id, x, y):
    """Create an NPC from a predefined template."""
    if template_id not in NPC_TEMPLATES:
        return NPC(x, y, template_id)

    template = NPC_TEMPLATES[template_id].copy()
    return NPC(x, y, template_id, template)
