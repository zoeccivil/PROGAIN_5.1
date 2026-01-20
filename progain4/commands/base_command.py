"""
Base Command Abstract Class for UNDO/REDO System

Defines the interface that all commands must implement.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any


class Command(ABC):
    """
    Abstract base class for all commands in the UNDO/REDO system.
    
    All commands must implement execute, undo, redo, get_description,
    to_dict, and from_dict methods.
    """
    
    def __init__(self):
        """Initialize command with timestamp."""
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.is_batch = False
    
    @abstractmethod
    def execute(self) -> bool:
        """
        Execute the command action.
        
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def undo(self) -> bool:
        """
        Undo the command action.
        
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def redo(self) -> bool:
        """
        Redo the command action (usually same as execute).
        
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """
        Get human-readable description for UI display.
        
        Returns:
            Description string (e.g., 'Crear transacción: Compra...')
        """
        pass
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize command to dictionary for JSON persistence.
        
        Returns:
            Dictionary representation of the command
        """
        pass
    
    @staticmethod
    @abstractmethod
    def from_dict(data: Dict[str, Any], firebase_client) -> 'Command':
        """
        Deserialize command from dictionary.
        
        Args:
            data: Dictionary representation of the command
            firebase_client: FirebaseClient instance for database operations
            
        Returns:
            Command instance
        """
        pass
