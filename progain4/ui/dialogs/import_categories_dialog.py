"""
Dialog for importing categories and subcategories from another project. 
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QTreeWidget, QTreeWidgetItem, QCheckBox,
    QMessageBox, QGroupBox
)
from PyQt6.QtCore import Qt
import logging

logger = logging.getLogger(__name__)


class ImportCategoriesDialog(QDialog):
    """Dialog to import categories from another project."""
    
    def __init__(self, firebase_client, proyecto_actual_id:  str, parent=None):
        super().__init__(parent)
        self.firebase_client = firebase_client
        self.proyecto_actual_id = str(proyecto_actual_id)
        self.categorias_actuales = []
        self.proyectos_disponibles = []
        
        self.setWindowTitle("Importar Categorías desde Otro Proyecto")
        self.resize(600, 500)
        
        self._init_ui()
        self._load_data()
    
    def _init_ui(self):
        """Initialize user interface."""
        layout = QVBoxLayout(self)
        
        # === PROYECTO ORIGEN ===
        origen_group = QGroupBox("Proyecto Origen")
        origen_layout = QVBoxLayout()
        
        origen_label = QLabel("Seleccionar proyecto para copiar categorías:")
        self.combo_proyectos = QComboBox()
        self.combo_proyectos.currentIndexChanged.connect(self._on_proyecto_changed)
        
        origen_layout.addWidget(origen_label)
        origen_layout.addWidget(self.combo_proyectos)
        origen_group.setLayout(origen_layout)
        layout.addWidget(origen_group)
        
        # === ÁRBOL DE CATEGORÍAS ===
        tree_group = QGroupBox("Categorías Disponibles")
        tree_layout = QVBoxLayout()
        
        self.tree_categorias = QTreeWidget()
        self.tree_categorias.setHeaderLabels(["Categoría / Subcategoría", "Estado"])
        self.tree_categorias.setColumnWidth(0, 400)
        self.tree_categorias.itemChanged.connect(self._on_item_changed)
        
        tree_layout.addWidget(self. tree_categorias)
        tree_group.setLayout(tree_layout)
        layout.addWidget(tree_group)
        
        # === OPCIONES ===
        self.check_evitar_duplicados = QCheckBox("Evitar duplicados (no importar si ya existe)")
        self.check_evitar_duplicados.setChecked(True)
        layout.addWidget(self.check_evitar_duplicados)
        
        # === BOTONES DE SELECCIÓN ===
        btn_layout = QHBoxLayout()
        btn_select_all = QPushButton("Seleccionar Todo")
        btn_select_all.clicked.connect(self._select_all)
        btn_deselect_all = QPushButton("Deseleccionar Todo")
        btn_deselect_all.clicked.connect(self._deselect_all)
        
        btn_layout.addWidget(btn_select_all)
        btn_layout.addWidget(btn_deselect_all)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # === RESUMEN ===
        self.label_resumen = QLabel("Resumen:  0 categorías, 0 subcategorías")
        self.label_resumen.setStyleSheet("font-weight: bold; color: #2c3e50;")
        layout.addWidget(self.label_resumen)
        
        # === BOTONES DE ACCIÓN ===
        action_layout = QHBoxLayout()
        action_layout.addStretch()
        
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        
        self.btn_importar = QPushButton("Importar Seleccionadas")
        self.btn_importar.clicked. connect(self._importar_categorias)
        self.btn_importar.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        
        action_layout.addWidget(btn_cancelar)
        action_layout.addWidget(self. btn_importar)
        layout.addLayout(action_layout)
    
    def _load_data(self):
        """Load initial data:  projects and current categories."""
        try:
            # Cargar categorías activas del proyecto actual
            self. categorias_actuales = self. firebase_client.get_categorias_por_proyecto(
                self.proyecto_actual_id
            ) or []
            
            # Cargar lista de proyectos
            proyectos = self. firebase_client.get_proyectos()
            
            # Filtrar proyecto actual
            self. proyectos_disponibles = [
                p for p in proyectos 
                if str(p.get("id")) != self.proyecto_actual_id
            ]
            
            # Poblar combo
            self.combo_proyectos.addItem("-- Seleccionar Proyecto --", None)
            for p in self. proyectos_disponibles: 
                nombre = p.get("nombre", f"Proyecto {p. get('id')}")
                self.combo_proyectos.addItem(nombre, p.get("id"))
            
            logger. info(f"Loaded {len(self.proyectos_disponibles)} projects for import")
            
        except Exception as e: 
            logger.error(f"Error loading data: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Error al cargar datos:\n{str(e)}")
    
    def _on_proyecto_changed(self, index):
        """Handle project selection change."""
        proyecto_id = self. combo_proyectos.currentData()
        
        if proyecto_id is None:
            self. tree_categorias.clear()
            self._update_resumen()
            return
        
        try:
            # Cargar categorías activas del proyecto seleccionado
            categorias = self.firebase_client.get_categorias_por_proyecto(str(proyecto_id)) or []
            
            # Construir árbol
            self._build_tree(categorias)
            self._update_resumen()
            
        except Exception as e: 
            logger.error(f"Error loading categories:  {e}", exc_info=True)
            QMessageBox.warning(self, "Error", f"Error al cargar categorías:\n{str(e)}")
    
    def _build_tree(self, categorias):
        """Build category tree with checkboxes."""
        self.tree_categorias.clear()
        self.tree_categorias.blockSignals(True)  # Evitar triggers durante construcción
        
        # Las categorías ya están filtradas por proyecto
        # Ahora cargar subcategorías para cada categoría
        for cat in categorias:
            item = QTreeWidgetItem(self.tree_categorias)
            item.setText(0, cat. get("nombre", "Sin nombre"))
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(0, Qt.CheckState. Checked)
            
            # Guardar datos en el item
            item.setData(0, Qt.ItemDataRole.UserRole, cat)
            
            # Buscar subcategorías maestras de esta categoría
            cat_id = str(cat.get("id"))
            try:
                subcats = self. firebase_client.get_subcategorias_maestras_by_categoria(cat_id) or []
                
                # Filtrar solo las subcategorías que están activas en el proyecto origen
                proyecto_id_origen = self.combo_proyectos.currentData()
                if proyecto_id_origen: 
                    # Obtener subcategorías activas del proyecto
                    subcats_proyecto = self.firebase_client.get_subcategorias_por_proyecto(str(proyecto_id_origen)) or []
                    subcats_proyecto_ids = {str(sc.get("id")) for sc in subcats_proyecto if str(sc.get("categoria_id")) == cat_id}
                    
                    # Filtrar subcategorías:  solo las que están activas en el proyecto
                    subcats = [sc for sc in subcats if str(sc.get("id")) in subcats_proyecto_ids]
                
            except Exception as e:
                logger.error(f"Error loading subcategories for category {cat_id}: {e}")
                subcats = []
            
            # Agregar subcategorías
            for subcat in subcats:
                child_item = QTreeWidgetItem(item)
                child_item.setText(0, f"  └─ {subcat.get('nombre', 'Sin nombre')}")
                child_item.setFlags(child_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                child_item. setCheckState(0, Qt. CheckState.Checked)
                child_item.setData(0, Qt.ItemDataRole.UserRole, subcat)
            
            # Expandir si tiene hijos
            if subcats:
                item.setExpanded(True)
                item.setText(1, f"({len(subcats)} subcategorías)")
        
        self.tree_categorias.blockSignals(False)
        self._check_duplicates()
    
    def _check_duplicates(self):
        """Mark items that already exist in current project."""
        if not self.check_evitar_duplicados. isChecked():
            return
        
        # Crear set de IDs de categorías existentes en el proyecto actual
        cat_ids_existentes = {str(c.get("id")) for c in self.categorias_actuales}
        
        # Obtener subcategorías activas del proyecto actual
        try:
            subcats_actuales = self.firebase_client. get_subcategorias_por_proyecto(self.proyecto_actual_id) or []
            subcat_ids_existentes = {str(sc.get("id")) for sc in subcats_actuales}
        except Exception as e: 
            logger.error(f"Error loading current subcategories: {e}")
            subcat_ids_existentes = set()
        
        # Revisar items del árbol
        root = self.tree_categorias. invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            cat_data = item.data(0, Qt.ItemDataRole.UserRole)
            cat_id = str(cat_data.get("id"))
            
            # Verificar si la categoría ya existe
            if cat_id in cat_ids_existentes:
                item.setText(1, "⚠️ Ya existe")
                item.setForeground(1, Qt.GlobalColor.red)
                item.setCheckState(0, Qt.CheckState.Unchecked)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            
            # Revisar subcategorías
            for j in range(item.childCount()):
                child = item.child(j)
                subcat_data = child.data(0, Qt.ItemDataRole.UserRole)
                subcat_id = str(subcat_data.get("id"))
                
                # Verificar si la subcategoría ya existe
                if subcat_id in subcat_ids_existentes:
                    child.setText(1, "⚠️ Ya existe")
                    child.setForeground(1, Qt.GlobalColor. red)
                    child.setCheckState(0, Qt.CheckState.Unchecked)
                    child.setFlags(child.flags() & ~Qt.ItemFlag.ItemIsEnabled)
    
    def _on_item_changed(self, item, column):
        """Handle checkbox state change."""
        if column != 0:
            return
        
        self. tree_categorias.blockSignals(True)
        
        # Si es categoría padre, propagar a hijos
        if item.parent() is None:
            for i in range(item.childCount()):
                child = item. child(i)
                if child.flags() & Qt.ItemFlag.ItemIsEnabled:
                    child.setCheckState(0, item.checkState(0))
        
        self.tree_categorias.blockSignals(False)
        self._update_resumen()
    
    def _select_all(self):
        """Select all enabled items."""
        self._set_all_checks(Qt.CheckState.Checked)
    
    def _deselect_all(self):
        """Deselect all items."""
        self._set_all_checks(Qt.CheckState.Unchecked)
    
    def _set_all_checks(self, state):
        """Set all checkboxes to given state."""
        self.tree_categorias.blockSignals(True)
        
        root = self.tree_categorias. invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            if item.flags() & Qt.ItemFlag.ItemIsEnabled:
                item.setCheckState(0, state)
                
                for j in range(item.childCount()):
                    child = item.child(j)
                    if child.flags() & Qt.ItemFlag.ItemIsEnabled:
                        child.setCheckState(0, state)
        
        self.tree_categorias.blockSignals(False)
        self._update_resumen()
    
    def _update_resumen(self):
        """Update summary label."""
        num_cats = 0
        num_subcats = 0
        
        root = self.tree_categorias. invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            if item.checkState(0) == Qt.CheckState.Checked:
                num_cats += 1
                
                for j in range(item.childCount()):
                    child = item.child(j)
                    if child.checkState(0) == Qt.CheckState.Checked:
                        num_subcats += 1
        
        self.label_resumen.setText(f"Resumen: {num_cats} categorías, {num_subcats} subcategorías")
    
    def _importar_categorias(self):
        """Import selected categories."""
        # Recopilar seleccionadas
        categorias_seleccionadas = []
        subcategorias_seleccionadas = []
        
        root = self. tree_categorias.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            if item. checkState(0) == Qt.CheckState.Checked:
                cat_data = item.data(0, Qt.ItemDataRole. UserRole)
                categorias_seleccionadas.append(cat_data)
                
                for j in range(item.childCount()):
                    child = item.child(j)
                    if child.checkState(0) == Qt.CheckState.Checked:
                        subcat_data = child.data(0, Qt.ItemDataRole.UserRole)
                        subcategorias_seleccionadas.append(subcat_data)
        
        if not categorias_seleccionadas:
            QMessageBox.information(self, "Sin Selección", "No hay categorías seleccionadas para importar.")
            return
        
        # Confirmar
        reply = QMessageBox.question(
            self,
            "Confirmar Importación",
            f"¿Importar {len(categorias_seleccionadas)} categorías y {len(subcategorias_seleccionadas)} subcategorías?",
            QMessageBox.StandardButton.Yes | QMessageBox. StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try: 
            # Recopilar todos los IDs a asignar (categorías + subcategorías)
            ids_a_asignar = []
            
            # Agregar IDs de categorías padre
            for cat in categorias_seleccionadas:
                cat_id = str(cat.get("id"))
                ids_a_asignar.append(cat_id)
                logger.info(f"Prepared to assign category: {cat.get('nombre')} (ID {cat_id})")
            
            # Agregar IDs de subcategorías
            for subcat in subcategorias_seleccionadas:
                subcat_id = str(subcat.get("id"))
                ids_a_asignar.append(subcat_id)
                logger.info(f"Prepared to assign subcategory: {subcat.get('nombre')} (ID {subcat_id})")
            
            # Asignar todas las categorías y subcategorías al proyecto actual
            if ids_a_asignar: 
                self.firebase_client. asignar_categorias_a_proyecto(
                    self. proyecto_actual_id, 
                    ids_a_asignar
                )
                logger. info(f"Assigned {len(ids_a_asignar)} categories/subcategories to project {self.proyecto_actual_id}")
            
            QMessageBox. information(
                self,
                "Éxito",
                f"Importadas {len(categorias_seleccionadas)} categorías y {len(subcategorias_seleccionadas)} subcategorías."
            )
            
            self.accept()
            
        except Exception as e: 
            logger.error(f"Error importing categories: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Error al importar:\n{str(e)}")