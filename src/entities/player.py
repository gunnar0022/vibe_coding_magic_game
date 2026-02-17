"""
Player entity - controlled by player input.
"""
from .actor import Actor
from ..components import InventoryComponent, HandOccupancyComponent
from ..ui.radial_menu_layout import RadialMenuLayout
from ..systems.animation_controller import AnimationController, NPC_DIRECTION_ROW, PLAYER_ANIMATIONS


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

        # Node menu layout (freeform node-based spell menu)
        self.node_menu_layout = None  # Initialized on first use
        self.active_spell_mode = "dial"  # "dial" or "node"

        # Currently selected symbols for casting (max 2)
        self.selected_symbols = []

        # Player color for rendering
        self.color = (100, 200, 255)

        # Sprint state
        self.is_sprinting = False

        # Currency
        self.gold = 50  # Starting gold

        # Mana sense — unlocked via NPC dialogue, gates the ENV bar in HUD
        self.mana_sense_unlocked = False

        # Interaction settings
        self.interaction.can_examine = True
        self.interaction.can_attack = True

        # Sprite animation
        self.animation_controller = AnimationController(
            PLAYER_ANIMATIONS, direction_map=NPC_DIRECTION_ROW
        )
        self._is_moving = False

    def update(self, dt):
        super().update(dt)
        ac = self.animation_controller
        ac.set_facing(self.facing)
        if self._is_moving:
            ac.set_animation("walk")
        else:
            ac.set_animation("idle")
        ac.update(dt)
        self._is_moving = False

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
        """Check if player can open the spell menu (needs a free hand, not sprinting)."""
        if self.is_sprinting:
            return False
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
        # Serialize node menu layout if it exists
        if self.node_menu_layout:
            data["node_menu_layout"] = self.node_menu_layout.serialize()
        data["active_spell_mode"] = self.active_spell_mode
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
        # Deserialize node menu layout if present
        node_layout_data = data.get("node_menu_layout")
        if node_layout_data:
            from ..ui.node_menu_layout import NodeMenuLayout
            self.node_menu_layout = NodeMenuLayout.deserialize(node_layout_data)
        else:
            self.node_menu_layout = None
        self.active_spell_mode = data.get("active_spell_mode", "dial")
