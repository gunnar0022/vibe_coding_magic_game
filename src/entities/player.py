"""
Player entity - controlled by player input.
"""
from .actor import Actor
from ..components import InventoryComponent, HandOccupancyComponent
from ..ui.radial_menu_layout import RadialMenuLayout


class Player(Actor):
    """The player character."""

    def __init__(self, x=0, y=0):
        super().__init__(x, y, tags=["player"])
        self.controller = "player"

        # Smaller collision box (6x6 sub-tiles instead of 8x8)
        self.collision_width = 0.75
        self.collision_height = 0.75

        # Add inventory for player
        self.inventory = self.add_component(InventoryComponent(capacity=30))

        # Add hand occupancy tracking for weapons and spellcasting
        self.hand_occupancy = self.add_component(HandOccupancyComponent())

        # Known symbols (unlocked magic)
        self.known_symbols = set()
        self.known_symbols_order = []  # Tracks order of learning for radial menu

        # Radial menu layout (customized spell menu structure)
        self.radial_menu_layout = None  # Initialized on first use

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
            self.known_symbols_order.append(symbol_id)
            return True
        return False

    def get_known_symbols_ordered(self):
        """Get known symbols in the order they were learned."""
        return self.known_symbols_order.copy()

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
        # Need at least one free hand to cast
        if not self.hand_occupancy.can_cast():
            return False
        return True

    def can_open_spell_menu(self):
        """Check if player can open the spell menu (needs a free hand)."""
        if self.status.has_flag("silenced"):
            return False
        return self.hand_occupancy.can_cast()

    def serialize(self):
        data = super().serialize()
        data["known_symbols"] = list(self.known_symbols)
        data["known_symbols_order"] = self.known_symbols_order.copy()
        data["selected_symbols"] = self.selected_symbols.copy()
        # Serialize radial menu layout if it exists
        if self.radial_menu_layout:
            data["radial_menu_layout"] = self.radial_menu_layout.serialize()
        return data

    def deserialize(self, data):
        super().deserialize(data)
        self.known_symbols = set(data.get("known_symbols", []))
        self.known_symbols_order = data.get("known_symbols_order", list(self.known_symbols))
        self.selected_symbols = data.get("selected_symbols", [])
        # Deserialize radial menu layout if present
        layout_data = data.get("radial_menu_layout")
        if layout_data:
            self.radial_menu_layout = RadialMenuLayout.deserialize(layout_data)
        else:
            self.radial_menu_layout = None
