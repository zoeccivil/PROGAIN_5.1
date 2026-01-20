"""
Undo History Dialog

Displays the complete history of undo/redo actions in a modal dialog.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QPushButton, QHeaderView
)
from PyQt6.QtCore import Qt


class UndoHistoryDialog(QDialog):
    """
    Modal dialog showing the complete undo/redo history.
    """
    
    def __init__(self, undo_manager, parent=None):
        """
        Initialize the dialog.
        
        Args:
            undo_manager: UndoRedoManager instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.undo_manager = undo_manager
        
        self.setWindowTitle("Historial de Cambios")
        self.resize(900, 600)
        
        self._init_ui()
        self._load_history()
    
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("📜 Historial de acciones (más recientes primero)")
        title.setStyleSheet("font-weight: bold; font-size: 12pt; padding: 10px;")
        layout.addWidget(title)
        
        # Table
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Timestamp", "Tipo", "Descripción", "Masiva"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        
        # Configure column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        
        layout.addWidget(self.table)
        
        # Info label
        self.info_label = QLabel()
        self.info_label.setStyleSheet("padding: 5px; color: #666;")
        layout.addWidget(self.info_label)
        
        # Close button
        btn_close = QPushButton("Cerrar")
        btn_close.clicked.connect(self.accept)
        btn_close.setDefault(True)
        layout.addWidget(btn_close)
    
    def _load_history(self):
        """Load and display the history."""
        history = self.undo_manager.get_history()
        self.table.setRowCount(len(history))
        
        for row, item in enumerate(history):
            # Timestamp
            timestamp_item = QTableWidgetItem(item['timestamp'])
            self.table.setItem(row, 0, timestamp_item)
            
            # Type (remove 'Command' suffix for cleaner display)
            type_name = item['type'].replace('Command', '')
            type_item = QTableWidgetItem(type_name)
            self.table.setItem(row, 1, type_item)
            
            # Description
            desc_item = QTableWidgetItem(item['description'])
            self.table.setItem(row, 2, desc_item)
            
            # Batch indicator
            masiva = "✅ Sí" if item['is_batch'] else ""
            masiva_item = QTableWidgetItem(masiva)
            masiva_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 3, masiva_item)
        
        # Update info label
        undo_count = len(self.undo_manager.undo_stack)
        redo_count = len(self.undo_manager.redo_stack)
        max_size = self.undo_manager.max_stack_size
        self.info_label.setText(
            f"Total de acciones: {undo_count} | "
            f"Disponibles para deshacer: {undo_count} | "
            f"Disponibles para rehacer: {redo_count} | "
            f"Límite: {max_size}"
        )
