"""
Player entity - controlled by player input.
"""
from .actor import Actor
from ..components import InventoryComponent


class Player(Actor):
    """The player character."""

    def __init__(self, x=0, y=0):
        super().__init__(x, y, tags=["player"])
        self.controller = "player"

        # Add inventory for player
        self.inventory = self.add_component(InventoryComponent(capacity=30))

        # Known symbols (unlocked magic)
        self.known_symbols = set()

        # Currently selected symbols for casting (max 2)
        self.selected_symbols = []

        # Player color for rendering
        self.color = (100, 200, 255)

        # Interaction settings
        self.interaction.can_examine = True
        self.interaction.can_attack = True

    def learn_symbol(self, symbol_id):
        """Learn a new magical symbol."""
        if symbol_id not in self.known_symbols:
            self.known_symbols.add(symbol_id)
            return True
        return False

    def select_symbol(self, symbol_id):
        """Select a symbol for casting."""
        if symbol_id not in self.known_symbols:
            return False

        if len(self.selected_symbols) >= 2:
            # Replace oldest selection
            self.selected_symbols.pop(0)

        self.selected_symbols.append(symbol_id)
        return True

    def clear_symbol_selection(self):
        """Clear selected symbols."""
        self.selected_symbols.clear()

    def get_cast_ready_symbols(self):
        """Get currently selected symbols ready for casting."""
        return self.selected_symbols.copy()

    def can_cast(self):
        """Check if player can cast magic."""
        if self.status.has_flag("silenced"):
            return False
        if len(self.selected_symbols) == 0:
            return False
        return True

    def serialize(self):
        data = super().serialize()
        data["known_symbols"] = list(self.known_symbols)
        data["selected_symbols"] = self.selected_symbols.copy()
        return data

    def deserialize(self, data):
        super().deserialize(data)
        self.known_symbols = set(data.get("known_symbols", []))
        self.selected_symbols = data.get("selected_symbols", [])
