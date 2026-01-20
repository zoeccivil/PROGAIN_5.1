"""
Project Selection Dialog for PROGRAIN 4.0/5.0

Allows user to select or create a project to work with.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QPushButton, QMessageBox, QInputDialog, QListWidgetItem
)
from PyQt6.QtCore import Qt
from typing import List, Dict, Any, Optional


class ProjectDialog(QDialog):
    """
    Dialog for selecting or creating a Firebase project.
    """
    
    def __init__(self, parent=None, proyectos: List[Dict[str, Any]] = None):
        """
        Initialize project dialog.
        
        Args:
            parent: Parent widget
            proyectos: List of existing projects from Firebase
        """
        super().__init__(parent)
        self.setWindowTitle("Seleccionar Proyecto")
        self.setModal(True)
        self.setMinimumSize(450, 350)
        
        self.proyectos = proyectos or []
        self.selected_proyecto_id: Optional[str] = None
        self.selected_proyecto_nombre: Optional[str] = None
        
        self._init_ui()
        self._load_projects()
        
    def _init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("<h2>Seleccionar Proyecto</h2>")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Instructions
        instructions = QLabel(
            "Seleccione un proyecto existente o cree uno nuevo."
        )
        instructions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        instructions.setStyleSheet("color: #666; margin-bottom: 10px;")
        layout.addWidget(instructions)
        
        # Project list
        self.project_list = QListWidget()
        self.project_list.itemDoubleClicked.connect(self._on_project_double_clicked)
        layout.addWidget(self.project_list)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        
        # New project button
        new_btn = QPushButton("Nuevo Proyecto")
        new_btn.clicked.connect(self._create_new_project)
        buttons_layout.addWidget(new_btn)
        
        buttons_layout.addStretch()
        
        # Cancel button
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)
        
        # Select button
        select_btn = QPushButton("Seleccionar")
        select_btn.setDefault(True)
        select_btn.clicked.connect(self._select_project)
        buttons_layout.addWidget(select_btn)
        
        layout.addLayout(buttons_layout)
        
        self.setLayout(layout)
        
    def _load_projects(self):
        """Load projects into the list"""
        self.project_list.clear()
        
        if not self.proyectos:
            # No projects available
            item = QListWidgetItem("No hay proyectos disponibles. Cree uno nuevo.")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.project_list.addItem(item)
        else:
            for proyecto in self.proyectos:
                item = QListWidgetItem(proyecto.get('nombre', 'Sin nombre'))
                item.setData(Qt.ItemDataRole.UserRole, proyecto)
                self.project_list.addItem(item)
                
            # Select first item by default
            if self.project_list.count() > 0:
                self.project_list.setCurrentRow(0)
                
    def _create_new_project(self):
        """Handle creating a new project"""
        # This will just set a flag that the caller should create the project
        nombre, ok = QInputDialog.getText(
            self,
            "Nuevo Proyecto",
            "Nombre del proyecto:"
        )
        
        if ok and nombre.strip():
            descripcion, ok = QInputDialog.getText(
                self,
                "Nuevo Proyecto",
                "Descripción (opcional):"
            )
            
            if not ok:
                descripcion = ""
                
            # Store the new project data
            self.selected_proyecto_id = None  # Signals a new project
            self.selected_proyecto_nombre = nombre.strip()
            self.selected_proyecto_descripcion = descripcion.strip()
            self.accept()
            
    def _select_project(self):
        """Handle selecting a project from the list"""
        current_item = self.project_list.currentItem()
        
        if not current_item:
            QMessageBox.warning(
                self,
                "Sin selección",
                "Por favor seleccione un proyecto o cree uno nuevo."
            )
            return
            
        proyecto_data = current_item.data(Qt.ItemDataRole.UserRole)
        
        if not proyecto_data:
            QMessageBox.warning(
                self,
                "Sin selección",
                "Por favor seleccione un proyecto válido o cree uno nuevo."
            )
            return
            
        self.selected_proyecto_id = proyecto_data.get('id')
        self.selected_proyecto_nombre = proyecto_data.get('nombre')
        
        self.accept()
        
    def _on_project_double_clicked(self, item):
        """Handle double-click on project item"""
        proyecto_data = item.data(Qt.ItemDataRole.UserRole)
        if proyecto_data:
            self.selected_proyecto_id = proyecto_data.get('id')
            self.selected_proyecto_nombre = proyecto_data.get('nombre')
            self.accept()
            
    def get_selected_project(self) -> Optional[tuple]:
        """
        Get the selected project.
        
        Returns:
            Tuple of (project_id, project_name, project_description) if creating new,
            or (project_id, project_name) if selecting existing.
            None if cancelled.
        """
        if self.selected_proyecto_id is None and hasattr(self, 'selected_proyecto_descripcion'):
            # New project
            return (None, self.selected_proyecto_nombre, self.selected_proyecto_descripcion)
        elif self.selected_proyecto_id:
            # Existing project
            return (self.selected_proyecto_id, self.selected_proyecto_nombre)
        else:
            return None
