from typing import List, Dict, Any, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QMessageBox,
    QInputDialog,
)


class GestionCategoriasMaestrasDialog(QDialog):
    """
    Gestión de Categorías y Subcategorías Maestras (versión Firebase).
    
    ✅ Emite señal 'data_changed' cuando se modifica algo.
    """
    
    # ✅ SEÑAL PARA NOTIFICAR CAMBIOS
    data_changed = pyqtSignal()

    def __init__(self, firebase_client, parent=None):
        super().__init__(parent)
        self.firebase_client = firebase_client
        self._cambios_realizados = False  # ✅ Flag para saber si hubo cambios

        self.setWindowTitle("Gestionar Categorías y Subcategorías Maestras")
        self.setFixedSize(700, 450)

        layout = QHBoxLayout(self)

        # --- Categorías maestras ---
        cat_layout = QVBoxLayout()
        cat_layout. addWidget(QLabel("Categorías maestras"))
        self.lista_categorias = QListWidget()
        cat_layout.addWidget(self.lista_categorias)

        btn_cat_layout = QHBoxLayout()
        btn_agregar_cat = QPushButton("Agregar")
        btn_editar_cat = QPushButton("Renombrar")
        btn_borrar_cat = QPushButton("Borrar")
        btn_cat_layout.addWidget(btn_agregar_cat)
        btn_cat_layout.addWidget(btn_editar_cat)
        btn_cat_layout.addWidget(btn_borrar_cat)
        cat_layout.addLayout(btn_cat_layout)
        layout.addLayout(cat_layout)

        # --- Subcategorías maestras ---
        sub_layout = QVBoxLayout()
        sub_layout.addWidget(QLabel("Subcategorías maestras de la categoría seleccionada"))
        self.lista_subcategorias = QListWidget()
        sub_layout.addWidget(self.lista_subcategorias)

        btn_sub_layout = QHBoxLayout()
        btn_agregar_sub = QPushButton("Agregar")
        btn_editar_sub = QPushButton("Renombrar")
        btn_borrar_sub = QPushButton("Borrar")
        btn_sub_layout.addWidget(btn_agregar_sub)
        btn_sub_layout.addWidget(btn_editar_sub)
        btn_sub_layout.addWidget(btn_borrar_sub)
        sub_layout.addLayout(btn_sub_layout)
        
        # ✅ BOTÓN CERRAR
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.clicked.connect(self.accept)
        sub_layout.addWidget(btn_cerrar)
        
        layout.addLayout(sub_layout)

        # --- Estado ---
        self.categorias: List[Dict[str, Any]] = []
        self.subcategorias: List[Dict[str, Any]] = []
        self.categoria_seleccionada_id:  Optional[str] = None

        # --- Conexiones ---
        self.lista_categorias.currentItemChanged.connect(self._refrescar_subcategorias)
        btn_agregar_cat. clicked.connect(self._agregar_categoria)
        btn_editar_cat.clicked.connect(self._renombrar_categoria)
        btn_borrar_cat.clicked.connect(self._borrar_categoria)
        btn_agregar_sub.clicked.connect(self._agregar_subcategoria)
        btn_editar_sub.clicked.connect(self._renombrar_subcategoria)
        btn_borrar_sub.clicked.connect(self._borrar_subcategoria)

        # Carga inicial
        self._refrescar_categorias()

    # ✅ OVERRIDE:  Al cerrar, emitir señal si hubo cambios
    def accept(self):
        if self._cambios_realizados:
            self.data_changed.emit()
        super().accept()

    def reject(self):
        if self._cambios_realizados:
            self.data_changed. emit()
        super().reject()

    # ------------------------------------------------------------------ Datos

    def _refrescar_categorias(self):
        """Carga todas las categorías maestras desde Firebase."""
        try:
            self.categorias = self.firebase_client.get_categorias_maestras() or []
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudieron cargar las categorías maestras desde Firebase:\n{e}",
            )
            self.categorias = []

        self.lista_categorias.clear()
        for cat in self.categorias:
            item = QListWidgetItem(cat["nombre"])
            item.setData(Qt.ItemDataRole.UserRole, cat["id"])
            self.lista_categorias.addItem(item)

        # Selecciona la primera por defecto
        if self.lista_categorias.count() > 0:
            self.lista_categorias.setCurrentRow(0)
        else:
            self._refrescar_subcategorias()

    def _refrescar_subcategorias(self):
        """Carga subcategorías maestras para la categoría seleccionada."""
        sel_row = self.lista_categorias. currentRow()
        if sel_row < 0 or not self.categorias:
            self. subcategorias = []
            self.lista_subcategorias.clear()
            self.categoria_seleccionada_id = None
            return

        cat = self. categorias[sel_row]
        cat_id = cat["id"]
        self.categoria_seleccionada_id = cat_id

        try:
            self.subcategorias = (
                self.firebase_client.get_subcategorias_maestras_by_categoria(cat_id)
                or []
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudieron cargar las subcategorías maestras:\n{e}",
            )
            self.subcategorias = []

        self.lista_subcategorias.clear()
        for sub in self.subcategorias:
            item = QListWidgetItem(sub["nombre"])
            item.setData(Qt.ItemDataRole.UserRole, sub["id"])
            self.lista_subcategorias.addItem(item)

    # ------------------------------------------------------------------ Categorías

    def _agregar_categoria(self):
        nombre, ok = QInputDialog.getText(self, "Nueva Categoría", "Nombre de la categoría:")
        if not (ok and nombre.strip()):
            return

        try: 
            self.firebase_client.create_categoria_maestra(nombre. strip())
            self._cambios_realizados = True
            
            # ✅ RECARGAR DATOS FRESCOS DE FIREBASE
            self.categorias = self.firebase_client.get_categorias_maestras() or []
            
            # ✅ ACTUALIZAR LA LISTA VISUAL
            self.lista_categorias.clear()
            for cat in self.categorias:
                item = QListWidgetItem(cat["nombre"])
                item.setData(Qt.ItemDataRole.UserRole, cat["id"])
                self.lista_categorias.addItem(item)
            
            # Seleccionar la primera
            if self.lista_categorias.count() > 0:
                self.lista_categorias. setCurrentRow(0)
            
            QMessageBox.information(self, "Éxito", f"Categoría '{nombre. strip()}' creada correctamente.")
            
        except Exception as e: 
            QMessageBox. critical(self, "Error", f"No se pudo agregar la categoría:\n{e}")

    def _renombrar_categoria(self):
        sel = self. lista_categorias.currentRow()
        if sel < 0:
            QMessageBox.warning(
                self,
                "Sin selección",
                "Selecciona una categoría para renombrar.",
            )
            return

        cat = self.categorias[sel]
        cat_id = cat["id"]

        nuevo_nombre, ok = QInputDialog.getText(
            self,
            "Renombrar Categoría",
            "Nuevo nombre:",
            text=cat["nombre"],
        )
        if not (ok and nuevo_nombre.strip()):
            return

        try:
            self.firebase_client.update_categoria_maestra(cat_id, nuevo_nombre. strip())
            self._cambios_realizados = True  # ✅ Marcar cambios
            self._refrescar_categorias()
            QMessageBox.information(self, "Éxito", "Categoría renombrada correctamente.")
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudo renombrar la categoría:\n{e}",
            )

    def _borrar_categoria(self):
        sel = self.lista_categorias.currentRow()
        if sel < 0:
            QMessageBox.warning(
                self,
                "Sin selección",
                "Selecciona una categoría para borrar.",
            )
            return

        cat = self.categorias[sel]
        cat_id = cat["id"]

        if (
            QMessageBox.question(
                self,
                "Confirmar",
                f"¿Borrar la categoría '{cat['nombre']}' y sus subcategorías maestras?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            != QMessageBox.StandardButton.Yes
        ):
            return

        try:
            self. firebase_client.delete_categoria_maestra(cat_id)
            self._cambios_realizados = True  # ✅ Marcar cambios
            self._refrescar_categorias()
            QMessageBox.information(self, "Éxito", "Categoría eliminada correctamente.")
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudo borrar la categoría:\n{e}",
            )

    # ------------------------------------------------------------------ Subcategorías

    def _agregar_subcategoria(self):
        if self.categoria_seleccionada_id is None: 
            QMessageBox.warning(self, "Sin categoría", "Selecciona una categoría primero.")
            return

        nombre, ok = QInputDialog.getText(self, "Nueva Subcategoría", "Nombre de la subcategoría:")
        if not (ok and nombre.strip()):
            return

        try:
            self.firebase_client.create_subcategoria_maestra(nombre. strip(), self.categoria_seleccionada_id)
            self._cambios_realizados = True
            
            # ✅ RECARGAR DATOS FRESCOS DE FIREBASE
            self. subcategorias = (
                self.firebase_client. get_subcategorias_maestras_by_categoria(self.categoria_seleccionada_id)
                or []
            )
            
            # ✅ ACTUALIZAR LA LISTA VISUAL
            self. lista_subcategorias.clear()
            for sub in self.subcategorias:
                item = QListWidgetItem(sub["nombre"])
                item.setData(Qt.ItemDataRole.UserRole, sub["id"])
                self.lista_subcategorias.addItem(item)
            
            QMessageBox.information(self, "Éxito", f"Subcategoría '{nombre.strip()}' creada correctamente.")
            
        except Exception as e: 
            QMessageBox.critical(self, "Error", f"No se pudo agregar la subcategoría:\n{e}")

    def _renombrar_subcategoria(self):
        sel = self.lista_subcategorias.currentRow()
        if sel < 0:
            QMessageBox.warning(
                self,
                "Sin selección",
                "Selecciona una subcategoría para renombrar.",
            )
            return

        sub = self.subcategorias[sel]
        sub_id = sub["id"]

        nuevo_nombre, ok = QInputDialog.getText(
            self,
            "Renombrar Subcategoría",
            "Nuevo nombre:",
            text=sub["nombre"],
        )
        if not (ok and nuevo_nombre.strip()):
            return

        try: 
            self.firebase_client. update_subcategoria_maestra(sub_id, nuevo_nombre.strip())
            self._cambios_realizados = True  # ✅ Marcar cambios
            self._refrescar_subcategorias()
            QMessageBox.information(self, "Éxito", "Subcategoría renombrada correctamente.")
        except Exception as e: 
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudo renombrar la subcategoría:\n{e}",
            )

    def _borrar_subcategoria(self):
        sel = self.lista_subcategorias.currentRow()
        if sel < 0:
            QMessageBox.warning(
                self,
                "Sin selección",
                "Selecciona una subcategoría para borrar.",
            )
            return

        sub = self.subcategorias[sel]
        sub_id = sub["id"]

        if (
            QMessageBox.question(
                self,
                "Confirmar",
                f"¿Borrar la subcategoría '{sub['nombre']}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton. No,
            )
            != QMessageBox.StandardButton.Yes
        ):
            return

        try:
            self.firebase_client.delete_subcategoria_maestra(sub_id)
            self._cambios_realizados = True  # ✅ Marcar cambios
            self._refrescar_subcategorias()
            QMessageBox.information(self, "Éxito", "Subcategoría eliminada correctamente.")
        except Exception as e:
            QMessageBox. critical(
                self,
                "Error",
                f"No se pudo borrar la subcategoría:\n{e}",
            )