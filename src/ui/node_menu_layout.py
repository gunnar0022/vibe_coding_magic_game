"""
Node menu layout data model.
Stores spell node positions and connections for the freeform node-based spell menu.
"""
import math


# Canvas dimensions (shared between menu and editor)
CANVAS_WIDTH = 750
CANVAS_HEIGHT = 600


# Reserved ID for the permanent center anchor node
CENTER_NODE_ID = "__center__"


class NodeMenuLayout:
    """
    Layout configuration for the node-based spell menu.
    Stores which spells are placed, their positions on the canvas,
    and undirected connections between them.

    A permanent center anchor node (CENTER_NODE_ID) always exists at the
    canvas center.  It participates in physics and can be linked to spell
    nodes, but carries no spell and cannot be removed.
    """

    MAX_SPELLS = 20  # Configurable cap on how many *spell* nodes can be on the canvas

    def __init__(self):
        # spell_id -> {"x": float, "y": float} (pixel coords relative to canvas top-left)
        self.nodes = {}
        # List of (spell_id_a, spell_id_b) tuples, sorted alphabetically to avoid duplicates
        self.connections = []
        # Ensure center anchor always exists
        self._ensure_center_node()

    def _ensure_center_node(self):
        """Make sure the permanent center node is present."""
        if CENTER_NODE_ID not in self.nodes:
            self.nodes[CENTER_NODE_ID] = {
                "x": float(CANVAS_WIDTH / 2),
                "y": float(CANVAS_HEIGHT / 2),
            }

    def add_spell(self, spell_id, x=None, y=None):
        """Add a spell node at position. Returns False if at capacity or duplicate."""
        if spell_id == CENTER_NODE_ID:
            return False  # Can't add a spell with the reserved center ID
        if spell_id in self.nodes:
            return False
        # Count only spell nodes (exclude center anchor)
        spell_count = sum(1 for k in self.nodes if k != CENTER_NODE_ID)
        if spell_count >= self.MAX_SPELLS:
            return False

        if x is None:
            x = CANVAS_WIDTH / 2
        if y is None:
            y = CANVAS_HEIGHT / 2

        self.nodes[spell_id] = {"x": float(x), "y": float(y)}
        return True

    def remove_spell(self, spell_id):
        """Remove a spell node and all its connections. Center node cannot be removed."""
        if spell_id == CENTER_NODE_ID:
            return False
        if spell_id not in self.nodes:
            return False
        del self.nodes[spell_id]
        self.connections = [
            c for c in self.connections if spell_id not in c
        ]
        return True

    def move_spell(self, spell_id, x, y):
        """Update a spell node's position."""
        if spell_id not in self.nodes:
            return
        self.nodes[spell_id]["x"] = float(x)
        self.nodes[spell_id]["y"] = float(y)

    def add_connection(self, spell_id_a, spell_id_b):
        """Add undirected connection. Returns False if already exists, same node, or node missing."""
        if spell_id_a == spell_id_b:
            return False
        if spell_id_a not in self.nodes or spell_id_b not in self.nodes:
            return False

        pair = _sorted_pair(spell_id_a, spell_id_b)
        if pair in self.connections:
            return False

        self.connections.append(pair)
        return True

    def remove_connection(self, spell_id_a, spell_id_b):
        """Remove a connection between two spells."""
        pair = _sorted_pair(spell_id_a, spell_id_b)
        if pair in self.connections:
            self.connections.remove(pair)
            return True
        return False

    def get_connections_for(self, spell_id):
        """Get all spell IDs connected to a given spell."""
        connected = []
        for a, b in self.connections:
            if a == spell_id:
                connected.append(b)
            elif b == spell_id:
                connected.append(a)
        return connected

    def has_spell(self, spell_id):
        """Check if spell is on the canvas."""
        return spell_id in self.nodes and spell_id != CENTER_NODE_ID

    def get_all_assigned_spells(self):
        """Get set of all spell IDs on the canvas (excludes center anchor)."""
        return {k for k in self.nodes if k != CENTER_NODE_ID}

    def auto_populate_from_spells(self, spell_ids):
        """Auto-place spells in a circle pattern. Used for initial setup."""
        self.nodes.clear()
        self.connections.clear()
        self._ensure_center_node()

        count = min(len(spell_ids), self.MAX_SPELLS)
        if count == 0:
            return

        cx = CANVAS_WIDTH / 2
        cy = CANVAS_HEIGHT / 2
        radius = min(CANVAS_WIDTH, CANVAS_HEIGHT) * 0.35

        for i in range(count):
            angle = (2 * math.pi * i / count) - math.pi / 2  # Start from top
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle)
            self.nodes[spell_ids[i]] = {"x": x, "y": y}

    def serialize(self):
        """Convert to JSON-safe dict for save system."""
        return {
            "nodes": {sid: pos.copy() for sid, pos in self.nodes.items()},
            "connections": [list(c) for c in self.connections],
        }

    @classmethod
    def deserialize(cls, data):
        """Reconstruct from saved dict."""
        layout = cls()
        for sid, pos in data.get("nodes", {}).items():
            layout.nodes[sid] = {"x": float(pos["x"]), "y": float(pos["y"])}
        for pair in data.get("connections", []):
            if len(pair) == 2:
                layout.connections.append(_sorted_pair(pair[0], pair[1]))
        layout._ensure_center_node()
        return layout

    def copy(self):
        """Deep copy via serialize/deserialize."""
        return NodeMenuLayout.deserialize(self.serialize())


def _sorted_pair(a, b):
    """Return a tuple with the two IDs in sorted order."""
    return (min(a, b), max(a, b))
