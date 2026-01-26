"""
Base component class for the entity-component system.
"""
from abc import ABC, abstractmethod


class Component(ABC):
    """Base class for all components."""

    def __init__(self):
        self.owner = None

    def attach(self, entity):
        """Called when component is attached to an entity."""
        self.owner = entity

    def detach(self):
        """Called when component is removed from entity."""
        self.owner = None

    def update(self, dt):
        """Update component state. Override in subclasses."""
        pass

    def serialize(self):
        """Return serializable state for saving."""
        return {}

    def deserialize(self, data):
        """Load state from serialized data."""
        pass
