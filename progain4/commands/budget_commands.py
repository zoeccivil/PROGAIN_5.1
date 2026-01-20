"""
Budget Commands for UNDO/REDO System

Implements Create, Update, and Delete commands for budgets.
"""

import logging
from typing import Dict, Any
from progain4.commands.base_command import Command

logger = logging.getLogger(__name__)


class CreateBudgetCommand(Command):
    """Command to create a new budget."""
    
    def __init__(self, firebase_client, proyecto_id: str, data: Dict[str, Any]):
        """
        Initialize create budget command.
        
        Args:
            firebase_client: FirebaseClient instance
            proyecto_id: Project ID
            data: Budget data dictionary (must include 'id')
        """
        super().__init__()
        self.firebase_client = firebase_client
        self.proyecto_id = str(proyecto_id)
        self.data = data
        self.budget_id = str(data.get('id'))
    
    def execute(self) -> bool:
        """Create the budget in Firestore."""
        try:
            budget_ref = (
                self.firebase_client.db.collection('proyectos')
                .document(self.proyecto_id)
                .collection('presupuestos')
                .document(self.budget_id)
            )
            budget_ref.set(self.data)
            logger.info(f"Created budget {self.budget_id}")
            return True
        except Exception as e:
            logger.error(f"Error creating budget: {e}")
            return False
    
    def undo(self) -> bool:
        """Delete the budget from Firestore."""
        try:
            budget_ref = (
                self.firebase_client.db.collection('proyectos')
                .document(self.proyecto_id)
                .collection('presupuestos')
                .document(self.budget_id)
            )
            budget_ref.delete()
            logger.info(f"Deleted budget {self.budget_id} (undo)")
            return True
        except Exception as e:
            logger.error(f"Error deleting budget: {e}")
            return False
    
    def redo(self) -> bool:
        """Recreate the budget."""
        return self.execute()
    
    def get_description(self) -> str:
        """Get human-readable description."""
        categoria = self.data.get('categoria_nombre', self.data.get('categoria_id', ''))
        return f"Crear presupuesto: {categoria}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'type': 'CreateBudget',
            'timestamp': self.timestamp,
            'proyecto_id': self.proyecto_id,
            'budget_id': self.budget_id,
            'data': self.data
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any], firebase_client) -> 'CreateBudgetCommand':
        """Deserialize from dictionary."""
        cmd = CreateBudgetCommand(
            firebase_client,
            data['proyecto_id'],
            data['data']
        )
        cmd.timestamp = data.get('timestamp', cmd.timestamp)
        return cmd


class UpdateBudgetCommand(Command):
    """Command to update an existing budget."""
    
    def __init__(self, firebase_client, proyecto_id: str, budget_id: str,
                 old_data: Dict[str, Any], new_data: Dict[str, Any]):
        """
        Initialize update budget command.
        
        Args:
            firebase_client: FirebaseClient instance
            proyecto_id: Project ID
            budget_id: Budget ID
            old_data: Original budget data (for undo)
            new_data: New budget data (for execute/redo)
        """
        super().__init__()
        self.firebase_client = firebase_client
        self.proyecto_id = str(proyecto_id)
        self.budget_id = str(budget_id)
        self.old_data = old_data
        self.new_data = new_data
    
    def execute(self) -> bool:
        """Update the budget with new data."""
        try:
            budget_ref = (
                self.firebase_client.db.collection('proyectos')
                .document(self.proyecto_id)
                .collection('presupuestos')
                .document(self.budget_id)
            )
            budget_ref.update(self.new_data)
            logger.info(f"Updated budget {self.budget_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating budget: {e}")
            return False
    
    def undo(self) -> bool:
        """Restore the budget to old data."""
        try:
            budget_ref = (
                self.firebase_client.db.collection('proyectos')
                .document(self.proyecto_id)
                .collection('presupuestos')
                .document(self.budget_id)
            )
            budget_ref.update(self.old_data)
            logger.info(f"Restored budget {self.budget_id} (undo)")
            return True
        except Exception as e:
            logger.error(f"Error restoring budget: {e}")
            return False
    
    def redo(self) -> bool:
        """Reapply the update."""
        return self.execute()
    
    def get_description(self) -> str:
        """Get human-readable description."""
        categoria = self.old_data.get('categoria_nombre', self.old_data.get('categoria_id', ''))
        return f"Editar presupuesto: {categoria}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'type': 'UpdateBudget',
            'timestamp': self.timestamp,
            'proyecto_id': self.proyecto_id,
            'budget_id': self.budget_id,
            'old_data': self.old_data,
            'new_data': self.new_data
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any], firebase_client) -> 'UpdateBudgetCommand':
        """Deserialize from dictionary."""
        cmd = UpdateBudgetCommand(
            firebase_client,
            data['proyecto_id'],
            data['budget_id'],
            data['old_data'],
            data['new_data']
        )
        cmd.timestamp = data.get('timestamp', cmd.timestamp)
        return cmd


class DeleteBudgetCommand(Command):
    """Command to delete a budget."""
    
    def __init__(self, firebase_client, proyecto_id: str, budget_id: str,
                 snapshot: Dict[str, Any]):
        """
        Initialize delete budget command.
        
        Args:
            firebase_client: FirebaseClient instance
            proyecto_id: Project ID
            budget_id: Budget ID
            snapshot: Budget data snapshot (for undo)
        """
        super().__init__()
        self.firebase_client = firebase_client
        self.proyecto_id = str(proyecto_id)
        self.budget_id = str(budget_id)
        self.snapshot = snapshot
    
    def execute(self) -> bool:
        """Delete the budget from Firestore."""
        try:
            budget_ref = (
                self.firebase_client.db.collection('proyectos')
                .document(self.proyecto_id)
                .collection('presupuestos')
                .document(self.budget_id)
            )
            budget_ref.delete()
            logger.info(f"Deleted budget {self.budget_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting budget: {e}")
            return False
    
    def undo(self) -> bool:
        """Restore the deleted budget."""
        try:
            budget_ref = (
                self.firebase_client.db.collection('proyectos')
                .document(self.proyecto_id)
                .collection('presupuestos')
                .document(self.budget_id)
            )
            budget_ref.set(self.snapshot)
            logger.info(f"Restored budget {self.budget_id} (undo)")
            return True
        except Exception as e:
            logger.error(f"Error restoring budget: {e}")
            return False
    
    def redo(self) -> bool:
        """Delete the budget again."""
        return self.execute()
    
    def get_description(self) -> str:
        """Get human-readable description."""
        categoria = self.snapshot.get('categoria_nombre', self.snapshot.get('categoria_id', ''))
        return f"Eliminar presupuesto: {categoria}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'type': 'DeleteBudget',
            'timestamp': self.timestamp,
            'proyecto_id': self.proyecto_id,
            'budget_id': self.budget_id,
            'snapshot': self.snapshot
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any], firebase_client) -> 'DeleteBudgetCommand':
        """Deserialize from dictionary."""
        cmd = DeleteBudgetCommand(
            firebase_client,
            data['proyecto_id'],
            data['budget_id'],
            data['snapshot']
        )
        cmd.timestamp = data.get('timestamp', cmd.timestamp)
        return cmd
