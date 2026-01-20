"""
Transaction Commands for UNDO/REDO System

Implements Create, Update, and Delete commands for transactions.
"""

import logging
from typing import Dict, Any
from progain4.commands.base_command import Command

logger = logging.getLogger(__name__)


class CreateTransactionCommand(Command):
    """Command to create a new transaction."""
    
    def __init__(self, firebase_client, proyecto_id: str, data: Dict[str, Any]):
        """
        Initialize create transaction command.
        
        Args:
            firebase_client: FirebaseClient instance
            proyecto_id: Project ID
            data: Transaction data dictionary (must include 'id')
        """
        super().__init__()
        self.firebase_client = firebase_client
        self.proyecto_id = str(proyecto_id)
        self.data = data
        self.transaction_id = data.get('id')
    
    def execute(self) -> bool:
        """Create the transaction in Firestore."""
        try:
            trans_ref = (
                self.firebase_client.db.collection('proyectos')
                .document(self.proyecto_id)
                .collection('transacciones')
                .document(self.transaction_id)
            )
            trans_ref.set(self.data)
            logger.info(f"Created transaction {self.transaction_id}")
            return True
        except Exception as e:
            logger.error(f"Error creating transaction: {e}")
            return False
    
    def undo(self) -> bool:
        """Delete the transaction from Firestore."""
        try:
            trans_ref = (
                self.firebase_client.db.collection('proyectos')
                .document(self.proyecto_id)
                .collection('transacciones')
                .document(self.transaction_id)
            )
            trans_ref.delete()
            logger.info(f"Deleted transaction {self.transaction_id} (undo)")
            return True
        except Exception as e:
            logger.error(f"Error deleting transaction: {e}")
            return False
    
    def redo(self) -> bool:
        """Recreate the transaction."""
        return self.execute()
    
    def get_description(self) -> str:
        """Get human-readable description."""
        desc = self.data.get('descripcion', self.data.get('concepto', ''))
        if len(desc) > 30:
            desc = desc[:30] + '...'
        return f"Crear transacción: {desc}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'type': 'CreateTransaction',
            'timestamp': self.timestamp,
            'proyecto_id': self.proyecto_id,
            'transaction_id': self.transaction_id,
            'data': self.data
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any], firebase_client) -> 'CreateTransactionCommand':
        """Deserialize from dictionary."""
        cmd = CreateTransactionCommand(
            firebase_client,
            data['proyecto_id'],
            data['data']
        )
        cmd.timestamp = data.get('timestamp', cmd.timestamp)
        return cmd


class UpdateTransactionCommand(Command):
    """Command to update an existing transaction."""
    
    def __init__(self, firebase_client, proyecto_id: str, transaction_id: str,
                 old_data: Dict[str, Any], new_data: Dict[str, Any]):
        """
        Initialize update transaction command.
        
        Args:
            firebase_client: FirebaseClient instance
            proyecto_id: Project ID
            transaction_id: Transaction ID
            old_data: Original transaction data (for undo)
            new_data: New transaction data (for execute/redo)
        """
        super().__init__()
        self.firebase_client = firebase_client
        self.proyecto_id = str(proyecto_id)
        self.transaction_id = str(transaction_id)
        self.old_data = old_data
        self.new_data = new_data
    
    def execute(self) -> bool:
        """Update the transaction with new data."""
        try:
            trans_ref = (
                self.firebase_client.db.collection('proyectos')
                .document(self.proyecto_id)
                .collection('transacciones')
                .document(self.transaction_id)
            )
            trans_ref.update(self.new_data)
            logger.info(f"Updated transaction {self.transaction_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating transaction: {e}")
            return False
    
    def undo(self) -> bool:
        """Restore the transaction to old data."""
        try:
            trans_ref = (
                self.firebase_client.db.collection('proyectos')
                .document(self.proyecto_id)
                .collection('transacciones')
                .document(self.transaction_id)
            )
            trans_ref.update(self.old_data)
            logger.info(f"Restored transaction {self.transaction_id} (undo)")
            return True
        except Exception as e:
            logger.error(f"Error restoring transaction: {e}")
            return False
    
    def redo(self) -> bool:
        """Reapply the update."""
        return self.execute()
    
    def get_description(self) -> str:
        """Get human-readable description."""
        desc = self.old_data.get('descripcion', self.old_data.get('concepto', ''))
        if len(desc) > 30:
            desc = desc[:30] + '...'
        return f"Editar transacción: {desc}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'type': 'UpdateTransaction',
            'timestamp': self.timestamp,
            'proyecto_id': self.proyecto_id,
            'transaction_id': self.transaction_id,
            'old_data': self.old_data,
            'new_data': self.new_data
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any], firebase_client) -> 'UpdateTransactionCommand':
        """Deserialize from dictionary."""
        cmd = UpdateTransactionCommand(
            firebase_client,
            data['proyecto_id'],
            data['transaction_id'],
            data['old_data'],
            data['new_data']
        )
        cmd.timestamp = data.get('timestamp', cmd.timestamp)
        return cmd


class DeleteTransactionCommand(Command):
    """Command to delete a transaction."""
    
    def __init__(self, firebase_client, proyecto_id: str, transaction_id: str,
                 snapshot: Dict[str, Any]):
        """
        Initialize delete transaction command.
        
        Args:
            firebase_client: FirebaseClient instance
            proyecto_id: Project ID
            transaction_id: Transaction ID
            snapshot: Transaction data snapshot (for undo)
        """
        super().__init__()
        self.firebase_client = firebase_client
        self.proyecto_id = str(proyecto_id)
        self.transaction_id = str(transaction_id)
        self.snapshot = snapshot
    
    def execute(self) -> bool:
        """Delete the transaction from Firestore."""
        try:
            trans_ref = (
                self.firebase_client.db.collection('proyectos')
                .document(self.proyecto_id)
                .collection('transacciones')
                .document(self.transaction_id)
            )
            trans_ref.delete()
            logger.info(f"Deleted transaction {self.transaction_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting transaction: {e}")
            return False
    
    def undo(self) -> bool:
        """Restore the deleted transaction."""
        try:
            trans_ref = (
                self.firebase_client.db.collection('proyectos')
                .document(self.proyecto_id)
                .collection('transacciones')
                .document(self.transaction_id)
            )
            trans_ref.set(self.snapshot)
            logger.info(f"Restored transaction {self.transaction_id} (undo)")
            return True
        except Exception as e:
            logger.error(f"Error restoring transaction: {e}")
            return False
    
    def redo(self) -> bool:
        """Delete the transaction again."""
        return self.execute()
    
    def get_description(self) -> str:
        """Get human-readable description."""
        desc = self.snapshot.get('descripcion', self.snapshot.get('concepto', ''))
        if len(desc) > 30:
            desc = desc[:30] + '...'
        return f"Eliminar transacción: {desc}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'type': 'DeleteTransaction',
            'timestamp': self.timestamp,
            'proyecto_id': self.proyecto_id,
            'transaction_id': self.transaction_id,
            'snapshot': self.snapshot
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any], firebase_client) -> 'DeleteTransactionCommand':
        """Deserialize from dictionary."""
        cmd = DeleteTransactionCommand(
            firebase_client,
            data['proyecto_id'],
            data['transaction_id'],
            data['snapshot']
        )
        cmd.timestamp = data.get('timestamp', cmd.timestamp)
        return cmd
