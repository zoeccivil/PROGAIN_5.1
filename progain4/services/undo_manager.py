"""
Undo/Redo Manager for PROGAIN 5.1
Manages command history and persistence
"""
import logging
import json
import os
from typing import List, Optional
from progain4.commands import Command

logger = logging.getLogger(__name__)


class UndoRedoManager:
    """Manages undo/redo stacks and command execution"""
    
    def __init__(self, firebase_client=None, config_manager=None, max_stack_size: int = 25):
        """
        Initialize undo/redo manager
        
        Args:
            firebase_client: Firebase client instance (for command execution)
            config_manager: Configuration manager (for settings)
            max_stack_size: Maximum number of commands to keep in history
        """
        self.firebase_client = firebase_client
        self.config_manager = config_manager
        self.max_stack_size = max_stack_size
        
        self.undo_stack: List[Command] = []
        self.redo_stack: List[Command] = []
        
        # Load persisted history if available
        # Note: Commands themselves can't be serialized, but we can track metadata
        logger.info(f"✅ UndoRedoManager inicializado (límite: {max_stack_size} acciones)")
    
    def execute_command(self, command: Command) -> bool:
        """
        Execute command and add to undo stack
        
        Args:
            command: Command to execute
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"🚀 Ejecutando comando: {command.get_description()}")
        
        if command.execute():
            self.undo_stack.append(command)
            self.redo_stack.clear()
            
            if len(self.undo_stack) > self.max_stack_size:
                removed = self.undo_stack.pop(0)
                logger.debug(f"Stack lleno, eliminado: {removed.get_description()}")
            
            self.save_to_file()
            
            logger.info(f"✅ Comando ejecutado y guardado (stack: {len(self.undo_stack)}/{self.max_stack_size})")
            return True
        else:
            logger.error(f"❌ Error ejecutando comando: {command.get_description()}")
            return False
    
    def undo(self) -> bool:
        """
        Undo last action
        
        Returns:
            True if successful, False otherwise
        """
        if not self.can_undo():
            logger.warning("⚠️ No hay acciones para deshacer")
            return False
        
        command = self.undo_stack.pop()
        
        logger.info(f"⏪ Deshaciendo: {command.get_description()}")
        
        # Confirmation only for batch operations
        if command.is_batch:
            from PyQt6.QtWidgets import QMessageBox
            reply = QMessageBox.question(
                None,
                "⚠️ Confirmar Deshacer",
                f"¿Deshacer operación masiva?\n\n{command.get_description()}\n\n"
                "Esta acción revertirá múltiples cambios.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                self.undo_stack.append(command)
                logger.info("❌ Undo cancelado por usuario")
                return False
        
        if command.undo():
            self.redo_stack.append(command)
            self.save_to_file()
            logger.info(f"✅ Undo exitoso (undo stack: {len(self.undo_stack)}, redo stack: {len(self.redo_stack)})")
            return True
        else:
            self.undo_stack.append(command)
            logger.error(f"❌ Error en undo, comando restaurado al stack")
            return False
    
    def redo(self) -> bool:
        """
        Redo last undone action
        
        Returns:
            True if successful, False otherwise
        """
        if not self.can_redo():
            logger.warning("⚠️ No hay acciones para rehacer")
            return False
        
        command = self.redo_stack.pop()
        
        logger.info(f"⏩ Rehaciendo: {command.get_description()}")
        
        if command.execute():
            self.undo_stack.append(command)
            self.save_to_file()
            logger.info(f"✅ Redo exitoso (undo stack: {len(self.undo_stack)}, redo stack: {len(self.redo_stack)})")
            return True
        else:
            self.redo_stack.append(command)
            logger.error(f"❌ Error en redo, comando restaurado al stack")
            return False
    
    def can_undo(self) -> bool:
        """Check if undo is available"""
        return len(self.undo_stack) > 0
    
    def can_redo(self) -> bool:
        """Check if redo is available"""
        return len(self.redo_stack) > 0
    
    def get_undo_description(self) -> str:
        """Get description of next undo action"""
        if self.can_undo():
            return self.undo_stack[-1].get_description()
        return "Nada para deshacer"
    
    def get_redo_description(self) -> str:
        """Get description of next redo action"""
        if self.can_redo():
            return self.redo_stack[-1].get_description()
        return "Nada para rehacer"
    
    def clear(self):
        """Clear both stacks"""
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.save_to_file()
        logger.info("🗑️ Historial de undo/redo limpiado")
    
    def save_to_file(self):
        """
        Save undo/redo metadata to file
        Note: We can't serialize Command objects, but we can save descriptions for UI
        """
        try:
            metadata = {
                'undo_count': len(self.undo_stack),
                'redo_count': len(self.redo_stack),
                'undo_descriptions': [cmd.get_description() for cmd in self.undo_stack[-10:]],
                'redo_descriptions': [cmd.get_description() for cmd in self.redo_stack[-10:]]
            }
            
            filepath = os.path.join(os.path.dirname(__file__), '..', 'undo_history.json')
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"💾 Historial guardado: {metadata['undo_count']} undo, {metadata['redo_count']} redo")
        except Exception as e:
            logger.warning(f"⚠️ No se pudo guardar historial: {e}")
    
    def get_history(self) -> dict:
        """Get undo/redo history for display"""
        return {
            'undo': [cmd.get_description() for cmd in self.undo_stack],
            'redo': [cmd.get_description() for cmd in self.redo_stack]
        }
