"""
Category Commands for UNDO/REDO System

Implements Create, Update, and Delete commands for categories and subcategories.
"""

import logging
from typing import Dict, Any
from progain4.commands.base_command import Command

logger = logging.getLogger(__name__)


class CreateCategoryCommand(Command):
    """Command to create a new category."""
    
    def __init__(self, firebase_client, data: Dict[str, Any]):
        """
        Initialize create category command.
        
        Args:
            firebase_client: FirebaseClient instance
            data: Category data dictionary (must include 'id')
        """
        super().__init__()
        self.firebase_client = firebase_client
        self.data = data
        self.category_id = str(data.get('id'))
    
    def execute(self) -> bool:
        """Create the category in Firestore."""
        try:
            cat_ref = self.firebase_client.db.collection('categorias').document(self.category_id)
            cat_ref.set(self.data)
            logger.info(f"Created category {self.category_id}")
            return True
        except Exception as e:
            logger.error(f"Error creating category: {e}")
            return False
    
    def undo(self) -> bool:
        """Delete the category from Firestore."""
        try:
            cat_ref = self.firebase_client.db.collection('categorias').document(self.category_id)
            cat_ref.delete()
            logger.info(f"Deleted category {self.category_id} (undo)")
            return True
        except Exception as e:
            logger.error(f"Error deleting category: {e}")
            return False
    
    def redo(self) -> bool:
        """Recreate the category."""
        return self.execute()
    
    def get_description(self) -> str:
        """Get human-readable description."""
        nombre = self.data.get('nombre', '')
        return f"Crear categoría: {nombre}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'type': 'CreateCategory',
            'timestamp': self.timestamp,
            'category_id': self.category_id,
            'data': self.data
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any], firebase_client) -> 'CreateCategoryCommand':
        """Deserialize from dictionary."""
        cmd = CreateCategoryCommand(firebase_client, data['data'])
        cmd.timestamp = data.get('timestamp', cmd.timestamp)
        return cmd


class UpdateCategoryCommand(Command):
    """Command to update an existing category."""
    
    def __init__(self, firebase_client, category_id: str,
                 old_data: Dict[str, Any], new_data: Dict[str, Any]):
        """
        Initialize update category command.
        
        Args:
            firebase_client: FirebaseClient instance
            category_id: Category ID
            old_data: Original category data (for undo)
            new_data: New category data (for execute/redo)
        """
        super().__init__()
        self.firebase_client = firebase_client
        self.category_id = str(category_id)
        self.old_data = old_data
        self.new_data = new_data
    
    def execute(self) -> bool:
        """Update the category with new data."""
        try:
            cat_ref = self.firebase_client.db.collection('categorias').document(self.category_id)
            cat_ref.update(self.new_data)
            logger.info(f"Updated category {self.category_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating category: {e}")
            return False
    
    def undo(self) -> bool:
        """Restore the category to old data."""
        try:
            cat_ref = self.firebase_client.db.collection('categorias').document(self.category_id)
            cat_ref.update(self.old_data)
            logger.info(f"Restored category {self.category_id} (undo)")
            return True
        except Exception as e:
            logger.error(f"Error restoring category: {e}")
            return False
    
    def redo(self) -> bool:
        """Reapply the update."""
        return self.execute()
    
    def get_description(self) -> str:
        """Get human-readable description."""
        nombre = self.old_data.get('nombre', '')
        return f"Editar categoría: {nombre}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'type': 'UpdateCategory',
            'timestamp': self.timestamp,
            'category_id': self.category_id,
            'old_data': self.old_data,
            'new_data': self.new_data
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any], firebase_client) -> 'UpdateCategoryCommand':
        """Deserialize from dictionary."""
        cmd = UpdateCategoryCommand(
            firebase_client,
            data['category_id'],
            data['old_data'],
            data['new_data']
        )
        cmd.timestamp = data.get('timestamp', cmd.timestamp)
        return cmd


class DeleteCategoryCommand(Command):
    """Command to delete a category."""
    
    def __init__(self, firebase_client, category_id: str, snapshot: Dict[str, Any]):
        """
        Initialize delete category command.
        
        Args:
            firebase_client: FirebaseClient instance
            category_id: Category ID
            snapshot: Category data snapshot (for undo)
        """
        super().__init__()
        self.firebase_client = firebase_client
        self.category_id = str(category_id)
        self.snapshot = snapshot
    
    def execute(self) -> bool:
        """Delete the category from Firestore."""
        try:
            cat_ref = self.firebase_client.db.collection('categorias').document(self.category_id)
            cat_ref.delete()
            logger.info(f"Deleted category {self.category_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting category: {e}")
            return False
    
    def undo(self) -> bool:
        """Restore the deleted category."""
        try:
            cat_ref = self.firebase_client.db.collection('categorias').document(self.category_id)
            cat_ref.set(self.snapshot)
            logger.info(f"Restored category {self.category_id} (undo)")
            return True
        except Exception as e:
            logger.error(f"Error restoring category: {e}")
            return False
    
    def redo(self) -> bool:
        """Delete the category again."""
        return self.execute()
    
    def get_description(self) -> str:
        """Get human-readable description."""
        nombre = self.snapshot.get('nombre', '')
        return f"Eliminar categoría: {nombre}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'type': 'DeleteCategory',
            'timestamp': self.timestamp,
            'category_id': self.category_id,
            'snapshot': self.snapshot
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any], firebase_client) -> 'DeleteCategoryCommand':
        """Deserialize from dictionary."""
        cmd = DeleteCategoryCommand(
            firebase_client,
            data['category_id'],
            data['snapshot']
        )
        cmd.timestamp = data.get('timestamp', cmd.timestamp)
        return cmd
