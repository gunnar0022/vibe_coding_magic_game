"""
Area State Manager - tracks persistent per-area state across transitions and saves.

Stores:
- Which map-placed ground items have been removed (picked up)
- Player-dropped items and their positions
- Rune stone activation states
- Enemy spawner states (active, timers)
- Area-level metadata (max enemies, etc.)
"""
import math


class AreaState:
    """Persistent state for a single area."""

    def __init__(self, area_id):
        self.area_id = area_id

        # Ground items: map-placed items that were picked up (set of object IDs)
        self.removed_map_items = set()

        # Player-dropped items not from the original map
        # Each entry: {"item_id": str, "quantity": int, "x": float, "y": float}
        self.dropped_items = []

        # Rune stone states: {object_id: {"is_activated": bool}}
        self.rune_stone_states = {}

        # Enemy spawner states: {spawner_id: SpawnerState}
        self.spawner_states = {}

        # Event flags for one-time events (e.g., cutscene triggers)
        self.event_flags = {}

    def mark_item_removed(self, object_id):
        """Mark a map-placed ground item as picked up."""
        self.removed_map_items.add(object_id)

    def is_item_removed(self, object_id):
        """Check if a map-placed ground item was picked up."""
        return object_id in self.removed_map_items

    def add_dropped_item(self, item_id, quantity, x, y):
        """Record an item dropped by the player."""
        self.dropped_items.append({
            "item_id": item_id,
            "quantity": quantity,
            "x": x,
            "y": y,
        })

    def remove_dropped_item(self, index):
        """Remove a tracked dropped item (when picked up again)."""
        if 0 <= index < len(self.dropped_items):
            self.dropped_items.pop(index)

    def set_rune_stone_state(self, object_id, is_activated):
        """Record rune stone activation state."""
        self.rune_stone_states[object_id] = {"is_activated": is_activated}

    def get_rune_stone_state(self, object_id):
        """Get rune stone state, or None if not tracked."""
        return self.rune_stone_states.get(object_id)

    def set_spawner_state(self, spawner_id, state_dict):
        """Store spawner state (active, timer, etc.)."""
        self.spawner_states[spawner_id] = state_dict

    def get_spawner_state(self, spawner_id):
        """Get spawner state, or None if not tracked."""
        return self.spawner_states.get(spawner_id)

    def set_flag(self, name, value=True):
        """Set an event flag (e.g., 'forest_intro_played')."""
        self.event_flags[name] = value

    def get_flag(self, name, default=False):
        """Get an event flag value."""
        return self.event_flags.get(name, default)

    def serialize(self):
        """Serialize to dict for saving."""
        return {
            "area_id": self.area_id,
            "removed_map_items": list(self.removed_map_items),
            "dropped_items": list(self.dropped_items),
            "rune_stone_states": dict(self.rune_stone_states),
            "spawner_states": dict(self.spawner_states),
            "event_flags": dict(self.event_flags),
        }

    @staticmethod
    def deserialize(data):
        """Reconstruct from saved dict."""
        state = AreaState(data.get("area_id", "unknown"))
        state.removed_map_items = set(data.get("removed_map_items", []))
        state.dropped_items = list(data.get("dropped_items", []))
        state.rune_stone_states = dict(data.get("rune_stone_states", {}))
        state.spawner_states = dict(data.get("spawner_states", {}))
        state.event_flags = dict(data.get("event_flags", {}))
        return state


class AreaStateManager:
    """
    Manages persistent state for all areas the player has visited.
    Lives on the Game object and persists through save/load.
    """

    def __init__(self):
        # {area_id: AreaState}
        self._states = {}

    def get_state(self, area_id):
        """
        Get or create the persistent state for an area.
        Always returns an AreaState - creates a blank one if first visit.
        """
        if area_id not in self._states:
            self._states[area_id] = AreaState(area_id)
        return self._states[area_id]

    def has_state(self, area_id):
        """Check if we have any stored state for an area."""
        return area_id in self._states

    def serialize(self):
        """Serialize all area states for saving."""
        return {
            area_id: state.serialize()
            for area_id, state in self._states.items()
        }

    def deserialize(self, data):
        """Restore all area states from saved data."""
        self._states.clear()
        if data:
            for area_id, state_data in data.items():
                self._states[area_id] = AreaState.deserialize(state_data)

    @staticmethod
    def make_object_id(obj_type, x, y):
        """
        Generate a stable ID for a map-placed object from its type and position.
        This gives consistent identity without requiring IDs in the JSON.
        """
        return f"{obj_type}_{x}_{y}"
