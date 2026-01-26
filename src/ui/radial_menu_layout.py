"""
Radial menu layout data model.
Supports 8-directional slots, nested nodes, and customization.
"""


# 8 directional slots in clockwise order starting from North
DIRECTIONS = ["n", "ne", "e", "se", "s", "sw", "w", "nw"]

# Opposite direction mapping for return slots
OPPOSITE_DIRECTION = {
    "n": "s",
    "ne": "sw",
    "e": "w",
    "se": "nw",
    "s": "n",
    "sw": "ne",
    "w": "e",
    "nw": "se",
}


class RadialMenuNode:
    """
    A node in the radial menu structure.
    Can be the root menu or a nested submenu.
    """

    def __init__(self, node_id="root", name="Root"):
        self.node_id = node_id
        self.name = name

        # 8 slots, each can be: None, spell_id (str), or node_id (str prefixed with "node:")
        self.slots = {d: None for d in DIRECTIONS}

    def set_slot(self, direction, content):
        """
        Set a slot's content.
        content: None, spell_id string, or "node:node_id" string
        """
        if direction in DIRECTIONS:
            self.slots[direction] = content

    def get_slot(self, direction):
        """Get slot content."""
        return self.slots.get(direction)

    def clear_slot(self, direction):
        """Clear a slot."""
        if direction in DIRECTIONS:
            self.slots[direction] = None

    def is_node_slot(self, direction):
        """Check if a slot contains a node reference."""
        content = self.slots.get(direction)
        return content is not None and content.startswith("node:")

    def get_node_id_from_slot(self, direction):
        """Get node_id if slot contains a node, else None."""
        content = self.slots.get(direction)
        if content and content.startswith("node:"):
            return content[5:]  # Remove "node:" prefix
        return None

    def get_used_slots(self):
        """Get list of directions that have content."""
        return [d for d in DIRECTIONS if self.slots[d] is not None]

    def get_empty_slots(self):
        """Get list of directions that are empty."""
        return [d for d in DIRECTIONS if self.slots[d] is None]

    def serialize(self):
        """Convert to dict for saving."""
        return {
            "node_id": self.node_id,
            "name": self.name,
            "slots": self.slots.copy(),
        }

    @classmethod
    def deserialize(cls, data):
        """Create from saved dict."""
        node = cls(data.get("node_id", "root"), data.get("name", "Root"))
        node.slots = {d: data.get("slots", {}).get(d) for d in DIRECTIONS}
        return node


class RadialMenuLayout:
    """
    Complete radial menu layout configuration.
    Contains root menu and all nested nodes.
    """

    def __init__(self):
        # Root node (always exists)
        self.root = RadialMenuNode("root", "Spells")

        # All nodes by ID (including root)
        self.nodes = {"root": self.root}

        # Counter for generating unique node IDs
        self._next_node_id = 1

    def get_node(self, node_id):
        """Get a node by ID."""
        return self.nodes.get(node_id)

    def create_node(self, name=None):
        """
        Create a new nested node.
        Returns the new node.
        """
        node_id = f"node_{self._next_node_id}"
        self._next_node_id += 1

        if name is None:
            name = f"Menu {self._next_node_id - 1}"

        node = RadialMenuNode(node_id, name)
        self.nodes[node_id] = node
        return node

    def delete_node(self, node_id):
        """
        Delete a node and remove all references to it.
        Cannot delete root.
        """
        if node_id == "root":
            return False

        if node_id not in self.nodes:
            return False

        # Remove references to this node from all other nodes
        node_ref = f"node:{node_id}"
        for node in self.nodes.values():
            for direction in DIRECTIONS:
                if node.slots[direction] == node_ref:
                    node.slots[direction] = None

        # Delete the node
        del self.nodes[node_id]
        return True

    def assign_spell_to_slot(self, node_id, direction, spell_id):
        """Assign a spell to a slot in a node."""
        node = self.nodes.get(node_id)
        if node and direction in DIRECTIONS:
            node.set_slot(direction, spell_id)
            return True
        return False

    def assign_node_to_slot(self, parent_node_id, direction, child_node_id):
        """
        Assign a child node to a slot in a parent node.
        Validates that child exists and prevents circular references.
        """
        parent = self.nodes.get(parent_node_id)
        child = self.nodes.get(child_node_id)

        if not parent or not child:
            return False

        if parent_node_id == child_node_id:
            return False  # Can't put node in itself

        # Check for circular reference (child containing parent)
        if self._would_create_cycle(parent_node_id, child_node_id):
            return False

        parent.set_slot(direction, f"node:{child_node_id}")
        return True

    def _would_create_cycle(self, parent_id, child_id):
        """Check if adding child to parent would create a cycle."""
        # BFS through child's descendants to see if parent is reachable
        visited = set()
        queue = [child_id]

        while queue:
            current_id = queue.pop(0)
            if current_id in visited:
                continue
            visited.add(current_id)

            current_node = self.nodes.get(current_id)
            if not current_node:
                continue

            for direction in DIRECTIONS:
                slot_content = current_node.slots[direction]
                if slot_content and slot_content.startswith("node:"):
                    descendant_id = slot_content[5:]
                    if descendant_id == parent_id:
                        return True  # Found parent in descendants - would be cycle
                    queue.append(descendant_id)

        return False

    def clear_slot(self, node_id, direction):
        """Clear a slot in a node."""
        node = self.nodes.get(node_id)
        if node:
            node.clear_slot(direction)
            return True
        return False

    def get_return_direction(self, entry_direction):
        """Get the direction that should be the return slot."""
        return OPPOSITE_DIRECTION.get(entry_direction)

    def get_all_assigned_spells(self):
        """Get set of all spell IDs currently assigned in the layout."""
        spells = set()
        for node in self.nodes.values():
            for direction in DIRECTIONS:
                content = node.slots[direction]
                if content and not content.startswith("node:"):
                    spells.add(content)
        return spells

    def auto_populate_from_spells(self, spell_ids):
        """
        Auto-populate the root menu with spells.
        Used for initial setup or when player has no saved layout.
        """
        # Clear root slots
        for d in DIRECTIONS:
            self.root.slots[d] = None

        # Assign spells to slots in order
        for i, spell_id in enumerate(spell_ids):
            if i >= len(DIRECTIONS):
                break  # No more slots
            self.root.slots[DIRECTIONS[i]] = spell_id

    def serialize(self):
        """Convert entire layout to dict for saving."""
        return {
            "nodes": {nid: node.serialize() for nid, node in self.nodes.items()},
            "_next_node_id": self._next_node_id,
        }

    @classmethod
    def deserialize(cls, data):
        """Create layout from saved dict."""
        layout = cls()
        layout._next_node_id = data.get("_next_node_id", 1)

        # Deserialize all nodes
        layout.nodes = {}
        for node_id, node_data in data.get("nodes", {}).items():
            layout.nodes[node_id] = RadialMenuNode.deserialize(node_data)

        # Ensure root exists
        if "root" not in layout.nodes:
            layout.nodes["root"] = RadialMenuNode("root", "Spells")

        layout.root = layout.nodes["root"]
        return layout

    def copy(self):
        """Create a deep copy of this layout."""
        return RadialMenuLayout.deserialize(self.serialize())
