"""
Save/Load system for game state persistence.
"""
import json
import os
from datetime import datetime


class SaveSystem:
    """Handles saving and loading game state."""

    DEFAULT_SAVE_DIR = "saves"

    def __init__(self, save_dir=None):
        self.save_dir = save_dir or self.DEFAULT_SAVE_DIR
        self._ensure_save_dir()

    def _ensure_save_dir(self):
        """Create save directory if it doesn't exist."""
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)

    def _get_save_path(self, save_name):
        """Get full path for a save file."""
        # Sanitize save name
        safe_name = "".join(c for c in save_name if c.isalnum() or c in "._- ")
        safe_name = safe_name.strip()[:50] or "save"
        return os.path.join(self.save_dir, f"{safe_name}.json")

    def save_game(self, save_name, game_data):
        """
        Save game state to file.

        game_data should contain:
        - player: Player state (position, stats, known_symbols, etc.)
        - world: World state (modified objects, etc.)
        - notebook: Notebook state
        - metadata: Save metadata
        """
        save_path = self._get_save_path(save_name)

        save_data = {
            "version": "1.0",
            "timestamp": datetime.now().isoformat(),
            "save_name": save_name,
            "data": game_data
        }

        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=2, ensure_ascii=False)
            return True, save_path
        except Exception as e:
            return False, str(e)

    def load_game(self, save_name):
        """Load game state from file."""
        save_path = self._get_save_path(save_name)

        if not os.path.exists(save_path):
            return None, "Save file not found"

        try:
            with open(save_path, 'r', encoding='utf-8') as f:
                save_data = json.load(f)

            # Validate version
            version = save_data.get("version", "0.0")
            if not self._is_compatible_version(version):
                return None, f"Incompatible save version: {version}"

            return save_data.get("data"), None
        except json.JSONDecodeError as e:
            return None, f"Corrupted save file: {e}"
        except Exception as e:
            return None, str(e)

    def _is_compatible_version(self, version):
        """Check if save version is compatible."""
        # For now, accept version 1.x
        try:
            major = int(version.split(".")[0])
            return major == 1
        except:
            return False

    def list_saves(self):
        """List all available save files."""
        saves = []
        if not os.path.exists(self.save_dir):
            return saves

        for filename in os.listdir(self.save_dir):
            if filename.endswith(".json"):
                save_path = os.path.join(self.save_dir, filename)
                try:
                    with open(save_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    saves.append({
                        "name": data.get("save_name", filename[:-5]),
                        "timestamp": data.get("timestamp", "Unknown"),
                        "filename": filename,
                        "path": save_path
                    })
                except:
                    # Skip corrupted files
                    pass

        # Sort by timestamp, newest first
        saves.sort(key=lambda x: x["timestamp"], reverse=True)
        return saves

    def delete_save(self, save_name):
        """Delete a save file."""
        save_path = self._get_save_path(save_name)
        if os.path.exists(save_path):
            try:
                os.remove(save_path)
                return True
            except:
                return False
        return False

    def auto_save(self, game_data):
        """Create an auto-save."""
        return self.save_game("autosave", game_data)


def create_save_data(player, world, notebook):
    """
    Helper function to create save data from game objects.
    """
    return {
        "player": {
            "x": player.x,
            "y": player.y,
            "facing": getattr(player, 'facing', 'down'),
            "stats": player.stats.serialize(),
            "status": player.status.serialize(),
            "inventory": player.inventory.serialize() if hasattr(player, 'inventory') else {},
            "known_symbols": list(player.known_symbols),
            "selected_symbols": player.selected_symbols.copy(),
        },
        "notebook": notebook.serialize() if notebook else {},
        "world_state": {
            # Only save dynamic state (modified objects)
            # Static world layout is loaded from map files
        },
        "play_time": 0,  # Would track total play time
    }


def apply_save_data(save_data, player, notebook):
    """
    Helper function to apply save data to game objects.
    """
    player_data = save_data.get("player", {})

    # Restore player position
    player.x = player_data.get("x", player.x)
    player.y = player_data.get("y", player.y)
    player.facing = player_data.get("facing", "down")

    # Restore transform component
    if hasattr(player, 'transform'):
        player.transform.set_position(player.x, player.y)
        player.transform.facing = player.facing

    # Restore stats
    if "stats" in player_data:
        player.stats.deserialize(player_data["stats"])

    # Restore status
    if "status" in player_data:
        player.status.deserialize(player_data["status"])

    # Restore inventory
    if "inventory" in player_data and hasattr(player, 'inventory'):
        player.inventory.deserialize(player_data["inventory"])

    # Restore magic knowledge
    player.known_symbols = set(player_data.get("known_symbols", []))
    player.selected_symbols = player_data.get("selected_symbols", [])

    # Restore notebook
    if notebook and "notebook" in save_data:
        notebook.deserialize(save_data["notebook"])
