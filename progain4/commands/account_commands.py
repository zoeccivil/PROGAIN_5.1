"""
Account Commands for UNDO/REDO System

Implements Create, Update, and Delete commands for accounts.
"""

import logging
from typing import Dict, Any
from progain4.commands.base_command import Command

logger = logging.getLogger(__name__)


class CreateAccountCommand(Command):
    """Command to create a new account."""
    
    def __init__(self, firebase_client, data: Dict[str, Any]):
        """
        Initialize create account command.
        
        Args:
            firebase_client: FirebaseClient instance
            data: Account data dictionary (must include 'id')
        """
        super().__init__()
        self.firebase_client = firebase_client
        self.data = data
        self.account_id = str(data.get('id'))
    
    def execute(self) -> bool:
        """Create the account in Firestore."""
        try:
            account_ref = self.firebase_client.db.collection('cuentas').document(self.account_id)
            account_ref.set(self.data)
            logger.info(f"Created account {self.account_id}")
            return True
        except Exception as e:
            logger.error(f"Error creating account: {e}")
            return False
    
    def undo(self) -> bool:
        """Delete the account from Firestore."""
        try:
            account_ref = self.firebase_client.db.collection('cuentas').document(self.account_id)
            account_ref.delete()
            logger.info(f"Deleted account {self.account_id} (undo)")
            return True
        except Exception as e:
            logger.error(f"Error deleting account: {e}")
            return False
    
    def redo(self) -> bool:
        """Recreate the account."""
        return self.execute()
    
    def get_description(self) -> str:
        """Get human-readable description."""
        nombre = self.data.get('nombre', '')
        return f"Crear cuenta: {nombre}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'type': 'CreateAccount',
            'timestamp': self.timestamp,
            'account_id': self.account_id,
            'data': self.data
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any], firebase_client) -> 'CreateAccountCommand':
        """Deserialize from dictionary."""
        cmd = CreateAccountCommand(firebase_client, data['data'])
        cmd.timestamp = data.get('timestamp', cmd.timestamp)
        return cmd


class UpdateAccountCommand(Command):
    """Command to update an existing account."""
    
    def __init__(self, firebase_client, account_id: str,
                 old_data: Dict[str, Any], new_data: Dict[str, Any]):
        """
        Initialize update account command.
        
        Args:
            firebase_client: FirebaseClient instance
            account_id: Account ID
            old_data: Original account data (for undo)
            new_data: New account data (for execute/redo)
        """
        super().__init__()
        self.firebase_client = firebase_client
        self.account_id = str(account_id)
        self.old_data = old_data
        self.new_data = new_data
    
    def execute(self) -> bool:
        """Update the account with new data."""
        try:
            account_ref = self.firebase_client.db.collection('cuentas').document(self.account_id)
            account_ref.update(self.new_data)
            logger.info(f"Updated account {self.account_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating account: {e}")
            return False
    
    def undo(self) -> bool:
        """Restore the account to old data."""
        try:
            account_ref = self.firebase_client.db.collection('cuentas').document(self.account_id)
            account_ref.update(self.old_data)
            logger.info(f"Restored account {self.account_id} (undo)")
            return True
        except Exception as e:
            logger.error(f"Error restoring account: {e}")
            return False
    
    def redo(self) -> bool:
        """Reapply the update."""
        return self.execute()
    
    def get_description(self) -> str:
        """Get human-readable description."""
        nombre = self.old_data.get('nombre', '')
        return f"Editar cuenta: {nombre}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'type': 'UpdateAccount',
            'timestamp': self.timestamp,
            'account_id': self.account_id,
            'old_data': self.old_data,
            'new_data': self.new_data
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any], firebase_client) -> 'UpdateAccountCommand':
        """Deserialize from dictionary."""
        cmd = UpdateAccountCommand(
            firebase_client,
            data['account_id'],
            data['old_data'],
            data['new_data']
        )
        cmd.timestamp = data.get('timestamp', cmd.timestamp)
        return cmd


class DeleteAccountCommand(Command):
    """Command to delete an account."""
    
    def __init__(self, firebase_client, account_id: str, snapshot: Dict[str, Any]):
        """
        Initialize delete account command.
        
        Args:
            firebase_client: FirebaseClient instance
            account_id: Account ID
            snapshot: Account data snapshot (for undo)
        """
        super().__init__()
        self.firebase_client = firebase_client
        self.account_id = str(account_id)
        self.snapshot = snapshot
    
    def execute(self) -> bool:
        """Delete the account from Firestore."""
        try:
            account_ref = self.firebase_client.db.collection('cuentas').document(self.account_id)
            account_ref.delete()
            logger.info(f"Deleted account {self.account_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting account: {e}")
            return False
    
    def undo(self) -> bool:
        """Restore the deleted account."""
        try:
            account_ref = self.firebase_client.db.collection('cuentas').document(self.account_id)
            account_ref.set(self.snapshot)
            logger.info(f"Restored account {self.account_id} (undo)")
            return True
        except Exception as e:
            logger.error(f"Error restoring account: {e}")
            return False
    
    def redo(self) -> bool:
        """Delete the account again."""
        return self.execute()
    
    def get_description(self) -> str:
        """Get human-readable description."""
        nombre = self.snapshot.get('nombre', '')
        return f"Eliminar cuenta: {nombre}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'type': 'DeleteAccount',
            'timestamp': self.timestamp,
            'account_id': self.account_id,
            'snapshot': self.snapshot
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any], firebase_client) -> 'DeleteAccountCommand':
        """Deserialize from dictionary."""
        cmd = DeleteAccountCommand(
            firebase_client,
            data['account_id'],
            data['snapshot']
        )
        cmd.timestamp = data.get('timestamp', cmd.timestamp)
        return cmd
