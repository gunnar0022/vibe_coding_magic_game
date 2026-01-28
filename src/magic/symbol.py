"""
Symbol definition - the fundamental unit of magic.
"""


class Symbol:
    """
    Represents a magical symbol.
    Symbols are the basic building blocks of magic - they can be cast alone
    or combined in pairs to create different effects.
    """

    def __init__(self, symbol_id, data=None):
        self.id = symbol_id
        data = data or {}

        # Display properties
        self.name = data.get("name", symbol_id.title())
        self.character = data.get("character", "?")  # The visual character/glyph
        self.description = data.get("description", "An unknown symbol.")

        # Classification
        self.category = data.get("category", "unknown")  # elemental, force, abstract, etc.
        self.element = data.get("element", None)  # fire, water, earth, wind, etc.

        # Base traits when cast alone
        self.base_traits = data.get("base_traits", [])

        # Discovery information
        self.discovery_hint = data.get("discovery_hint", "")
        self.rarity = data.get("rarity", "common")

    def to_dict(self):
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "character": self.character,
            "description": self.description,
            "category": self.category,
            "element": self.element,
            "base_traits": self.base_traits,
            "discovery_hint": self.discovery_hint,
            "rarity": self.rarity,
        }

    @staticmethod
    def from_dict(data):
        """Create Symbol from dictionary."""
        return Symbol(data["id"], data)

    def __repr__(self):
        return f"Symbol({self.id}, '{self.character}')"
