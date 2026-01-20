"""
Undo/Redo Manager Service

Manages the undo/redo stack with JSON persistence for PROGAIN.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
from PyQt6.QtWidgets import QMessageBox

from progain4.commands.base_command import Command

logger = logging.getLogger(__name__)


class UndoRedoManager:
    """
    Manages undo/redo operations with JSON persistence.
    
    Features:
    - Executes commands and maintains undo/redo stacks
    - Persists history to JSON file
    - Configurable stack size limit
    - Confirmation dialogs for batch operations
    """
    
    def __init__(self, firebase_client, config_manager, max_stack_size: int = 25):
        """
        Initialize UndoRedoManager.
        
        Args:
            firebase_client: FirebaseClient instance for database operations
            config_manager: ConfigManager instance for settings
            max_stack_size: Maximum number of actions to keep (default: 25)
        """
        self.firebase_client = firebase_client
        self.config_manager = config_manager
        
        # Get configured limit or use default
        self.max_stack_size = int(config_manager.get('undo_limit', max_stack_size))
        
        # Initialize stacks
        self.undo_stack: List[Command] = []
        self.redo_stack: List[Command] = []
        
        # Determine history file path (in project root)
        # Get the root directory (2 levels up from services/)
        services_dir = os.path.dirname(os.path.abspath(__file__))
        progain4_dir = os.path.dirname(services_dir)
        root_dir = os.path.dirname(progain4_dir)
        self.history_file = os.path.join(root_dir, "undo_history.json")
        
        logger.info(f"Undo/Redo history file: {self.history_file}")
        logger.info(f"Max stack size: {self.max_stack_size}")
        
        # Load existing history
        self.load_from_file()
    
    def execute_command(self, command: Command) -> bool:
        """
        Execute a command and add it to the undo stack.
        
        Args:
            command: Command to execute
            
        Returns:
            True if successful, False otherwise
        """
        if command.execute():
            self.undo_stack.append(command)
            self.redo_stack.clear()
            
            # Enforce stack size limit
            if len(self.undo_stack) > self.max_stack_size:
                self.undo_stack.pop(0)
            
            self.save_to_file()
            logger.info(f"Command executed: {command.get_description()}")
            return True
        else:
            logger.error(f"Command execution failed: {command.get_description()}")
            return False
    
    def undo(self, parent_widget=None) -> bool:
        """
        Undo the last action.
        
        Args:
            parent_widget: Parent widget for confirmation dialogs
            
        Returns:
            True if successful, False otherwise
        """
        if not self.can_undo():
            return False
        
        command = self.undo_stack.pop()
        
        # Confirmation for batch operations
        if command.is_batch and parent_widget:
            reply = QMessageBox.question(
                parent_widget,
                "Confirmar Deshacer",
                f"¿Deshacer operación masiva?\n\n{command.get_description()}\n\n"
                "Esta acción afectará múltiples registros.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                self.undo_stack.append(command)
                return False
        
        if command.undo():
            self.redo_stack.append(command)
            self.save_to_file()
            logger.info(f"Command undone: {command.get_description()}")
            return True
        else:
            # Restore to undo stack if undo failed
            self.undo_stack.append(command)
            logger.error(f"Command undo failed: {command.get_description()}")
            return False
    
    def redo(self, parent_widget=None) -> bool:
        """
        Redo the last undone action.
        
        Args:
            parent_widget: Parent widget for confirmation dialogs
            
        Returns:
            True if successful, False otherwise
        """
        if not self.can_redo():
            return False
        
        command = self.redo_stack.pop()
        
        # Confirmation for batch operations
        if command.is_batch and parent_widget:
            reply = QMessageBox.question(
                parent_widget,
                "Confirmar Rehacer",
                f"¿Rehacer operación masiva?\n\n{command.get_description()}\n\n"
                "Esta acción afectará múltiples registros.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                self.redo_stack.append(command)
                return False
        
        if command.redo():
            self.undo_stack.append(command)
            
            # Enforce stack size limit
            if len(self.undo_stack) > self.max_stack_size:
                self.undo_stack.pop(0)
            
            self.save_to_file()
            logger.info(f"Command redone: {command.get_description()}")
            return True
        else:
            # Restore to redo stack if redo failed
            self.redo_stack.append(command)
            logger.error(f"Command redo failed: {command.get_description()}")
            return False
    
    def can_undo(self) -> bool:
        """Check if undo is available."""
        return len(self.undo_stack) > 0
    
    def can_redo(self) -> bool:
        """Check if redo is available."""
        return len(self.redo_stack) > 0
    
    def get_undo_description(self) -> str:
        """Get description of the action that would be undone."""
        if self.can_undo():
            return self.undo_stack[-1].get_description()
        return ""
    
    def get_redo_description(self) -> str:
        """Get description of the action that would be redone."""
        if self.can_redo():
            return self.redo_stack[-1].get_description()
        return ""
    
    def get_history(self) -> List[Dict[str, Any]]:
        """
        Get history for display in dialog.
        
        Returns:
            List of command metadata dictionaries
        """
        return [
            {
                'description': cmd.get_description(),
                'timestamp': cmd.timestamp,
                'is_batch': cmd.is_batch,
                'type': cmd.__class__.__name__
            }
            for cmd in reversed(self.undo_stack)
        ]
    
    def clear(self):
        """Clear all undo/redo history (e.g., when changing projects)."""
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.save_to_file()
        logger.info("Undo/Redo history cleared")
    
    def save_to_file(self):
        """Persist undo/redo stacks to JSON file."""
        try:
            data = {
                'max_stack_size': self.max_stack_size,
                'undo_stack': [cmd.to_dict() for cmd in self.undo_stack],
                'redo_stack': [cmd.to_dict() for cmd in self.redo_stack]
            }
            
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Saved undo/redo history: {len(self.undo_stack)} undo, {len(self.redo_stack)} redo")
        except Exception as e:
            logger.error(f"Error saving undo/redo history: {e}")
    
    def load_from_file(self):
        """Load undo/redo stacks from JSON file."""
        if not os.path.exists(self.history_file):
            logger.info("No existing undo/redo history file found")
            return
        
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Deserialize commands
            self.undo_stack = [
                self._deserialize_command(cmd_data)
                for cmd_data in data.get('undo_stack', [])
                if self._deserialize_command(cmd_data) is not None
            ]
            self.redo_stack = [
                self._deserialize_command(cmd_data)
                for cmd_data in data.get('redo_stack', [])
                if self._deserialize_command(cmd_data) is not None
            ]
            
            logger.info(f"Loaded undo/redo history: {len(self.undo_stack)} undo, {len(self.redo_stack)} redo")
        except Exception as e:
            logger.error(f"Error loading undo/redo history: {e}")
            # Clear stacks on error to avoid corruption
            self.undo_stack.clear()
            self.redo_stack.clear()
    
    def _deserialize_command(self, cmd_data: Dict[str, Any]) -> Optional[Command]:
        """
        Deserialize a command from dictionary.
        
        Args:
            cmd_data: Command data dictionary
            
        Returns:
            Command instance or None if deserialization fails
        """
        try:
            cmd_type = cmd_data.get('type')
            
            if cmd_type == 'Batch':
                from progain4.commands.batch_command import BatchCommand
                return BatchCommand.from_dict(cmd_data, self.firebase_client)
            elif cmd_type == 'CreateTransaction':
                from progain4.commands.transaction_commands import CreateTransactionCommand
                return CreateTransactionCommand.from_dict(cmd_data, self.firebase_client)
            elif cmd_type == 'UpdateTransaction':
                from progain4.commands.transaction_commands import UpdateTransactionCommand
                return UpdateTransactionCommand.from_dict(cmd_data, self.firebase_client)
            elif cmd_type == 'DeleteTransaction':
                from progain4.commands.transaction_commands import DeleteTransactionCommand
                return DeleteTransactionCommand.from_dict(cmd_data, self.firebase_client)
            elif cmd_type == 'CreateAccount':
                from progain4.commands.account_commands import CreateAccountCommand
                return CreateAccountCommand.from_dict(cmd_data, self.firebase_client)
            elif cmd_type == 'UpdateAccount':
                from progain4.commands.account_commands import UpdateAccountCommand
                return UpdateAccountCommand.from_dict(cmd_data, self.firebase_client)
            elif cmd_type == 'DeleteAccount':
                from progain4.commands.account_commands import DeleteAccountCommand
                return DeleteAccountCommand.from_dict(cmd_data, self.firebase_client)
            elif cmd_type == 'CreateCategory':
                from progain4.commands.category_commands import CreateCategoryCommand
                return CreateCategoryCommand.from_dict(cmd_data, self.firebase_client)
            elif cmd_type == 'UpdateCategory':
                from progain4.commands.category_commands import UpdateCategoryCommand
                return UpdateCategoryCommand.from_dict(cmd_data, self.firebase_client)
            elif cmd_type == 'DeleteCategory':
                from progain4.commands.category_commands import DeleteCategoryCommand
                return DeleteCategoryCommand.from_dict(cmd_data, self.firebase_client)
            elif cmd_type == 'CreateBudget':
                from progain4.commands.budget_commands import CreateBudgetCommand
                return CreateBudgetCommand.from_dict(cmd_data, self.firebase_client)
            elif cmd_type == 'UpdateBudget':
                from progain4.commands.budget_commands import UpdateBudgetCommand
                return UpdateBudgetCommand.from_dict(cmd_data, self.firebase_client)
            elif cmd_type == 'DeleteBudget':
                from progain4.commands.budget_commands import DeleteBudgetCommand
                return DeleteBudgetCommand.from_dict(cmd_data, self.firebase_client)
            else:
                logger.warning(f"Unknown command type: {cmd_type}")
                return None
        except Exception as e:
            logger.error(f"Error deserializing command: {e}")
            return None
    
    def update_stack_size(self, new_size: int):
        """
        Update the maximum stack size.
        
        Args:
            new_size: New maximum stack size (10-100)
        """
        new_size = max(10, min(100, new_size))  # Clamp between 10-100
        self.max_stack_size = new_size
        
        # Trim undo stack if necessary
        if len(self.undo_stack) > self.max_stack_size:
            self.undo_stack = self.undo_stack[-self.max_stack_size:]
        
        self.save_to_file()
        logger.info(f"Updated max stack size to {new_size}")
