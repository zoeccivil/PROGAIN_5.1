"""
Batch command for executing multiple commands as a single unit
"""
import logging
from typing import List
from progain4.commands import Command

logger = logging.getLogger(__name__)


class BatchCommand(Command):
    """Command that executes multiple commands as a single unit"""
    
    def __init__(self, commands: List[Command], description: str = ""):
        """
        Initialize batch command
        
        Args:
            commands: List of commands to execute
            description: Human-readable description
        """
        self.commands = commands
        self.is_batch = True
        
        if not description:
            description = f"Operación masiva ({len(commands)} acciones)"
        
        super().__init__(description)
    
    def execute(self) -> bool:
        """Execute all commands in order"""
        executed_commands = []
        
        for i, cmd in enumerate(self.commands):
            logger.debug(f"Ejecutando comando {i+1}/{len(self.commands)}: {cmd.get_description()}")
            
            if not cmd.execute():
                logger.error(f"❌ Error ejecutando comando {i+1}, revertiendo cambios...")
                
                # Rollback: undo all previously executed commands
                for executed_cmd in reversed(executed_commands):
                    executed_cmd.undo()
                
                return False
            
            executed_commands.append(cmd)
        
        logger.info(f"✅ Batch command ejecutado: {len(self.commands)} comandos")
        return True
    
    def undo(self) -> bool:
        """Undo all commands in reverse order"""
        failed_count = 0
        
        for i, cmd in enumerate(reversed(self.commands)):
            logger.debug(f"Deshaciendo comando {i+1}/{len(self.commands)}: {cmd.get_description()}")
            
            if not cmd.undo():
                logger.error(f"❌ Error deshaciendo comando {i+1}")
                failed_count += 1
        
        if failed_count > 0:
            logger.warning(f"⚠️ {failed_count} comandos fallaron en undo")
            return False
        
        logger.info(f"✅ Batch undo completado: {len(self.commands)} comandos")
        return True
