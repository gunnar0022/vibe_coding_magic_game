"""
Elemental Reactions System

This module provides a data-driven system for handling element+element
and element+attribute reactions in the game world.

Usage:
    from src.reactions import ReactionProcessor, Element, Attribute

    # Process an element being applied to an entity
    processor = ReactionProcessor(world)
    results = processor.process_element_applied(entity, Element.FIRE, context)

    # Or use the singleton
    from src.reactions import get_reaction_processor
    processor = get_reaction_processor(world)
"""

from .elements import Element, Attribute, STATUS_TO_ELEMENT, ELEMENT_TO_STATUS
from .reaction_definition import ReactionDefinition
from .reaction_registry import ReactionRegistry
from .reaction_processor import ReactionProcessor, get_reaction_processor
from .default_reactions import register_default_reactions

# Register default reactions on import
register_default_reactions()

__all__ = [
    "Element",
    "Attribute",
    "STATUS_TO_ELEMENT",
    "ELEMENT_TO_STATUS",
    "ReactionDefinition",
    "ReactionRegistry",
    "ReactionProcessor",
    "get_reaction_processor",
    "register_default_reactions",
]
