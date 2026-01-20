"""
Batch Command for UNDO/REDO System

Wraps multiple commands into a single operation for bulk actions.
"""

import logging
from typing import List, Dict, Any
from progain4.commands.base_command import Command

logger = logging.getLogger(__name__)


class BatchCommand(Command):
    """
    Command that executes multiple commands as a single operation.
    Used for bulk operations like imports and cleanup.
    """
    
    def __init__(self, commands: List[Command], batch_description: str):
        """
        Initialize batch command.
        
        Args:
            commands: List of commands to execute as a batch
            batch_description: Human-readable description of the batch operation
        """
        super().__init__()
        self.commands = commands
        self.batch_description = batch_description
        self.is_batch = True
    
    def execute(self) -> bool:
        """Execute all commands in sequence."""
        success_count = 0
        for i, cmd in enumerate(self.commands):
            if not cmd.execute():
                logger.error(f"Batch command failed at index {i}")
                # Rollback successful commands with error handling
                for j in range(success_count):
                    try:
                        if not self.commands[j].undo():
                            logger.error(f"Failed to rollback command at index {j} during batch execute failure")
                    except Exception as e:
                        logger.error(f"Exception during rollback of command {j}: {e}")
                return False
            success_count += 1
        logger.info(f"Batch command executed: {len(self.commands)} commands")
        return True
    
    def undo(self) -> bool:
        """Undo all commands in reverse order."""
        for cmd in reversed(self.commands):
            if not cmd.undo():
                logger.error(f"Batch undo failed for command: {cmd.get_description()}")
                return False
        logger.info(f"Batch command undone: {len(self.commands)} commands")
        return True
    
    def redo(self) -> bool:
        """Redo all commands (same as execute)."""
        return self.execute()
    
    def get_description(self) -> str:
        """Get human-readable description."""
        return f"{self.batch_description} ({len(self.commands)} cambios)"
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'type': 'Batch',
            'timestamp': self.timestamp,
            'batch_description': self.batch_description,
            'commands': [cmd.to_dict() for cmd in self.commands]
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any], firebase_client) -> 'BatchCommand':
        """Deserialize from dictionary."""
        # Import here to avoid circular imports
        from progain4.commands.transaction_commands import (
            CreateTransactionCommand, UpdateTransactionCommand, DeleteTransactionCommand
        )
        from progain4.commands.account_commands import (
            CreateAccountCommand, UpdateAccountCommand, DeleteAccountCommand
        )
        from progain4.commands.category_commands import (
            CreateCategoryCommand, UpdateCategoryCommand, DeleteCategoryCommand
        )
        from progain4.commands.budget_commands import (
            CreateBudgetCommand, UpdateBudgetCommand, DeleteBudgetCommand
        )
        
        # Map command types to their classes
        command_map = {
            'CreateTransaction': CreateTransactionCommand,
            'UpdateTransaction': UpdateTransactionCommand,
            'DeleteTransaction': DeleteTransactionCommand,
            'CreateAccount': CreateAccountCommand,
            'UpdateAccount': UpdateAccountCommand,
            'DeleteAccount': DeleteAccountCommand,
            'CreateCategory': CreateCategoryCommand,
            'UpdateCategory': UpdateCategoryCommand,
            'DeleteCategory': DeleteCategoryCommand,
            'CreateBudget': CreateBudgetCommand,
            'UpdateBudget': UpdateBudgetCommand,
            'DeleteBudget': DeleteBudgetCommand,
        }
        
        inner_commands = []
        for cmd_data in data.get('commands', []):
            cmd_type = cmd_data.get('type')
            if cmd_type in command_map:
                cmd_class = command_map[cmd_type]
                inner_commands.append(cmd_class.from_dict(cmd_data, firebase_client))
            else:
                logger.warning(f"Unknown command type in batch: {cmd_type}")
        
        cmd = BatchCommand(inner_commands, data.get('batch_description', 'Batch'))
        cmd.timestamp = data.get('timestamp', cmd.timestamp)
        return cmd
