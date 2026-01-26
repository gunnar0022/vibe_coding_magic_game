"""
Player notebook system - tracks discovered symbols and player notes.
"""
import json
import os
import re
from datetime import datetime


class NotebookEntry:
    """A single entry in the notebook (symbol reference or note)."""

    def __init__(self, entry_type="note", data=None):
        data = data or {}
        self.entry_type = entry_type  # "symbol", "note", "folder"
        self.id = data.get("id", f"entry_{datetime.now().timestamp()}")
        self.title = data.get("title", "Untitled")
        self.content = data.get("content", "")
        self.created_at = data.get("created_at", datetime.now().isoformat())
        self.modified_at = data.get("modified_at", self.created_at)
        self.tags = data.get("tags", [])
        self.parent_folder = data.get("parent_folder", None)

        # For symbol entries
        self.symbol_id = data.get("symbol_id", None)
        self.discovery_context = data.get("discovery_context", "")
        self.discovery_location = data.get("discovery_location", "")

    def update_content(self, new_content):
        """Update entry content with input sanitization."""
        # Sanitize input to prevent injection attacks
        sanitized = self._sanitize_input(new_content)
        self.content = sanitized
        self.modified_at = datetime.now().isoformat()

    def _sanitize_input(self, text):
        """Sanitize user input for safety."""
        if not isinstance(text, str):
            return ""

        # Limit length
        max_length = 10000
        text = text[:max_length]

        # Remove any potentially dangerous characters/sequences
        # Allow basic text, punctuation, and newlines
        # Remove control characters except newline and tab
        text = ''.join(char for char in text if char == '\n' or char == '\t' or (ord(char) >= 32 and ord(char) < 127) or ord(char) > 127)

        return text

    def add_tag(self, tag):
        """Add a tag to the entry."""
        tag = self._sanitize_input(tag).strip().lower()
        if tag and tag not in self.tags:
            self.tags.append(tag)
            self.modified_at = datetime.now().isoformat()

    def remove_tag(self, tag):
        """Remove a tag from the entry."""
        if tag in self.tags:
            self.tags.remove(tag)
            self.modified_at = datetime.now().isoformat()

    def to_dict(self):
        """Serialize to dictionary."""
        return {
            "entry_type": self.entry_type,
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
            "tags": self.tags,
            "parent_folder": self.parent_folder,
            "symbol_id": self.symbol_id,
            "discovery_context": self.discovery_context,
            "discovery_location": self.discovery_location,
        }

    @staticmethod
    def from_dict(data):
        """Create entry from dictionary."""
        return NotebookEntry(data.get("entry_type", "note"), data)


class NotebookFolder:
    """A folder for organizing notebook entries."""

    def __init__(self, data=None):
        data = data or {}
        self.id = data.get("id", f"folder_{datetime.now().timestamp()}")
        self.name = data.get("name", "New Folder")
        self.parent_folder = data.get("parent_folder", None)
        self.created_at = data.get("created_at", datetime.now().isoformat())

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "parent_folder": self.parent_folder,
            "created_at": self.created_at,
        }

    @staticmethod
    def from_dict(data):
        return NotebookFolder(data)


class Notebook:
    """
    The player's magic notebook.
    Tracks discovered symbols, player notes, and provides organization.
    """

    def __init__(self):
        # All entries (symbol references and notes)
        self.entries = {}  # id -> NotebookEntry

        # Folders for organization
        self.folders = {}  # id -> NotebookFolder

        # Symbol discovery records
        self.discovered_symbols = {}  # symbol_id -> entry_id

        # Quick access / loadout configurations
        self.loadouts = {}  # name -> list of symbol_ids

        # Search index
        self._search_index = {}

    def record_symbol_discovery(self, symbol_id, context="", location="", symbol_data=None):
        """
        Record a newly discovered symbol.
        Creates an auto-generated entry with discovery context.
        """
        if symbol_id in self.discovered_symbols:
            return None  # Already discovered

        symbol_data = symbol_data or {}

        entry = NotebookEntry("symbol", {
            "id": f"symbol_{symbol_id}",
            "title": symbol_data.get("name", symbol_id.title()),
            "content": symbol_data.get("description", "A newly discovered symbol."),
            "symbol_id": symbol_id,
            "discovery_context": context,
            "discovery_location": location,
            "tags": ["symbol", symbol_data.get("category", "unknown")],
        })

        self.entries[entry.id] = entry
        self.discovered_symbols[symbol_id] = entry.id
        self._update_search_index(entry)

        return entry

    def create_note(self, title="New Note", content="", folder_id=None, tags=None):
        """Create a new freeform note."""
        entry = NotebookEntry("note", {
            "title": title,
            "content": content,
            "parent_folder": folder_id,
            "tags": tags or [],
        })

        self.entries[entry.id] = entry
        self._update_search_index(entry)
        return entry

    def create_folder(self, name, parent_folder=None):
        """Create a new folder."""
        folder = NotebookFolder({
            "name": name,
            "parent_folder": parent_folder,
        })

        self.folders[folder.id] = folder
        return folder

    def delete_entry(self, entry_id):
        """Delete an entry (but not symbol discovery records)."""
        if entry_id in self.entries:
            entry = self.entries[entry_id]
            # Don't allow deleting symbol entries
            if entry.entry_type == "symbol":
                return False
            del self.entries[entry_id]
            self._rebuild_search_index()
            return True
        return False

    def delete_folder(self, folder_id):
        """Delete a folder and orphan its contents."""
        if folder_id in self.folders:
            # Move children to root
            for entry in self.entries.values():
                if entry.parent_folder == folder_id:
                    entry.parent_folder = None
            for folder in self.folders.values():
                if folder.parent_folder == folder_id:
                    folder.parent_folder = None

            del self.folders[folder_id]
            return True
        return False

    def move_entry(self, entry_id, folder_id):
        """Move an entry to a folder (None for root)."""
        if entry_id in self.entries:
            self.entries[entry_id].parent_folder = folder_id
            return True
        return False

    def get_symbol_entry(self, symbol_id):
        """Get the notebook entry for a symbol."""
        if symbol_id in self.discovered_symbols:
            entry_id = self.discovered_symbols[symbol_id]
            return self.entries.get(entry_id)
        return None

    def get_folder_contents(self, folder_id=None):
        """Get all entries and subfolders in a folder (None = root)."""
        entries = [e for e in self.entries.values() if e.parent_folder == folder_id]
        subfolders = [f for f in self.folders.values() if f.parent_folder == folder_id]
        return {
            "entries": entries,
            "folders": subfolders,
        }

    def search(self, query):
        """Search entries by keyword."""
        query = query.lower().strip()
        if not query:
            return []

        results = []
        for entry in self.entries.values():
            score = 0
            # Check title
            if query in entry.title.lower():
                score += 10
            # Check content
            if query in entry.content.lower():
                score += 5
            # Check tags
            for tag in entry.tags:
                if query in tag.lower():
                    score += 3

            if score > 0:
                results.append((entry, score))

        # Sort by relevance
        results.sort(key=lambda x: x[1], reverse=True)
        return [r[0] for r in results]

    def search_by_tag(self, tag):
        """Get all entries with a specific tag."""
        tag = tag.lower()
        return [e for e in self.entries.values() if tag in e.tags]

    def create_loadout(self, name, symbol_ids):
        """Create a quick-access spell loadout."""
        name = NotebookEntry._sanitize_input(None, name)[:50]
        self.loadouts[name] = list(symbol_ids)

    def get_loadout(self, name):
        """Get a loadout by name."""
        return self.loadouts.get(name, [])

    def delete_loadout(self, name):
        """Delete a loadout."""
        if name in self.loadouts:
            del self.loadouts[name]
            return True
        return False

    def _update_search_index(self, entry):
        """Update search index for an entry."""
        # Simple index - could be expanded
        words = set()
        words.update(entry.title.lower().split())
        words.update(entry.content.lower().split())
        words.update(tag.lower() for tag in entry.tags)

        self._search_index[entry.id] = words

    def _rebuild_search_index(self):
        """Rebuild the entire search index."""
        self._search_index.clear()
        for entry in self.entries.values():
            self._update_search_index(entry)

    def serialize(self):
        """Serialize notebook to dictionary."""
        return {
            "entries": {k: v.to_dict() for k, v in self.entries.items()},
            "folders": {k: v.to_dict() for k, v in self.folders.items()},
            "discovered_symbols": self.discovered_symbols.copy(),
            "loadouts": {k: list(v) for k, v in self.loadouts.items()},
        }

    def deserialize(self, data):
        """Load notebook from dictionary."""
        self.entries.clear()
        self.folders.clear()
        self.discovered_symbols.clear()
        self.loadouts.clear()

        for entry_id, entry_data in data.get("entries", {}).items():
            self.entries[entry_id] = NotebookEntry.from_dict(entry_data)

        for folder_id, folder_data in data.get("folders", {}).items():
            self.folders[folder_id] = NotebookFolder.from_dict(folder_data)

        self.discovered_symbols = data.get("discovered_symbols", {}).copy()
        self.loadouts = {k: list(v) for k, v in data.get("loadouts", {}).items()}

        self._rebuild_search_index()

    def get_statistics(self):
        """Get notebook statistics."""
        return {
            "total_entries": len(self.entries),
            "symbol_entries": len(self.discovered_symbols),
            "note_entries": sum(1 for e in self.entries.values() if e.entry_type == "note"),
            "folders": len(self.folders),
            "loadouts": len(self.loadouts),
        }
