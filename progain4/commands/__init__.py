"""
Command Pattern Infrastructure for Undo/Redo System
"""
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class Command(ABC):
    """Base class for all commands"""
    
    def __init__(self, description: str = ""):
        self.description = description
        self.is_batch = False
    
    @abstractmethod
    def execute(self) -> bool:
        """Execute the command. Returns True if successful."""
        pass
    
    @abstractmethod
    def undo(self) -> bool:
        """Undo the command. Returns True if successful."""
        pass
    
    def get_description(self) -> str:
        """Get human-readable description of this command"""
        return self.description or "Comando sin descripción"
