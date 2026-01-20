from typing import List, Dict, Any, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QMessageBox,
    QHBoxLayout,
    QInputDialog,
)

CHECK_MARK = "✔"
CHECK_SPACE = " " * len(CHECK_MARK)


class GestionCategoriasProyectoDialog(QDialog):
    """
    Gestionar cuáles categorías maestras están activas en un proyecto.

    - Muestra TODAS las categorías maestras (colección global 'categorias')
      con una marca '✔' en el texto para indicar selección.
    - Marca las que ya estén asociadas al proyecto.
    - Permite agregar/renombrar/borrar categorías maestras (afecta catálogo global).
    - Guarda la selección en proyectos/{proyecto_id}/categorias_proyecto.
    """

    def __init__(self, firebase_client, proyecto_id: str, proyecto_nombre: str, parent=None):
        super().__init__(parent)
        self.firebase_client = firebase_client
        self.proyecto_id = proyecto_id
        self.proyecto_nombre = proyecto_nombre

        self.setWindowTitle(f"Gestionar Categorías del Proyecto: {proyecto_nombre}")
        self.setFixedSize(480, 600)

        layout = QVBoxLayout(self)

        label_intro = QLabel(
            "Selecciona las categorías que estarán activas en este proyecto:"
        )
        label_intro.setWordWrap(True)
        layout.addWidget(label_intro)

        self.lista_categorias = QListWidget()
        self.lista_categorias.setSelectionMode(
            QListWidget.SelectionMode.SingleSelection
        )
        layout.addWidget(self.lista_categorias)

        # Resumen de cuántas están seleccionadas
        self.label_resumen = QLabel("0 categorías seleccionadas")
        self.label_resumen.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.label_resumen)

        # Botones de gestión de categorías maestras
        btn_cat_layout = QHBoxLayout()
        self.btn_agregar_cat = QPushButton("Agregar")
        self.btn_editar_cat = QPushButton("Renombrar")
        self.btn_borrar_cat = QPushButton("Borrar")
        btn_cat_layout.addWidget(self.btn_agregar_cat)
        btn_cat_layout.addWidget(self.btn_editar_cat)
        btn_cat_layout.addWidget(self.btn_borrar_cat)
        layout.addLayout(btn_cat_layout)

        # Botones guardar/cancelar
        btn_layout = QHBoxLayout()
        self.btn_guardar = QPushButton("Guardar Cambios")
        self.btn_cancelar = QPushButton("Cancelar")
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_guardar)
        btn_layout.addWidget(self.btn_cancelar)
        layout.addLayout(btn_layout)

        # Estado
        self.categorias: List[Dict[str, Any]] = []
        self.ids_categorias_activas: set[str] = set()

        # Conexiones
        self.btn_guardar.clicked.connect(self._guardar)
        self.btn_cancelar.clicked.connect(self.reject)
        self.btn_agregar_cat.clicked.connect(self._agregar_categoria)
        self.btn_editar_cat.clicked.connect(self._renombrar_categoria)
        self.btn_borrar_cat.clicked.connect(self._borrar_categoria)

        # Evento de clic en fila: togglear selección
        self.lista_categorias.itemClicked.connect(self._toggle_item)

        # Carga inicial
        self._cargar_categorias()

    # ------------------------------------------------------------------ Carga

    def _cargar_categorias(self):
        """Carga categorías maestras y marca las activas para este proyecto."""
        try:
            todas = self.firebase_client.get_categorias_maestras() or []
            activas = self.firebase_client.get_categorias_por_proyecto(
                self.proyecto_id
            ) or []
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudieron cargar las categorías:\n{e}",
            )
            return

        self.categorias = todas
        self.ids_categorias_activas = {str(cat["id"]) for cat in activas}

        self.lista_categorias.clear()

        for cat in todas:
            cat_id = str(cat["id"])
            nombre_puro = cat.get("nombre", f"Categoría {cat_id}")
            seleccionada = cat_id in self.ids_categorias_activas
            texto = f"{CHECK_MARK if seleccionada else CHECK_SPACE}  {nombre_puro}"

            item = QListWidgetItem(texto)
            item.setData(Qt.ItemDataRole.UserRole, cat_id)
            item.setData(Qt.ItemDataRole.UserRole + 1, nombre_puro)  # nombre base
            item.setFlags(
                Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsEnabled
            )
            self.lista_categorias.addItem(item)

        if self.lista_categorias.count() > 0:
            self.lista_categorias.setCurrentRow(0)

        self._actualizar_resumen()

    # ------------------------------------------------------------------ Helpers

    def _get_checked_categoria_ids(self) -> set[str]:
        """Devuelve el conjunto de IDs de categorías marcadas (según ids_categorias_activas)."""
        return set(self.ids_categorias_activas)

    def _get_current_categoria(self) -> Optional[Dict[str, Any]]:
        """Devuelve la categoría (dict) seleccionada en la lista, o None."""
        row = self.lista_categorias.currentRow()
        if row < 0 or row >= len(self.categorias):
            return None
        return self.categorias[row]

    def _actualizar_item_texto(self, item: QListWidgetItem, seleccionado: bool):
        """Actualiza el texto visible del item con o sin ✔."""
        nombre_puro = item.data(Qt.ItemDataRole.UserRole + 1) or ""
        item.setText(f"{CHECK_MARK if seleccionado else CHECK_SPACE}  {nombre_puro}")

    def _actualizar_resumen(self):
        """Actualiza texto 'X categorías seleccionadas' y refresca todos los textos."""
        for i in range(self.lista_categorias.count()):
            item = self.lista_categorias.item(i)
            cat_id = str(item.data(Qt.ItemDataRole.UserRole))
            seleccionado = cat_id in self.ids_categorias_activas
            self._actualizar_item_texto(item, seleccionado)

        n = len(self.ids_categorias_activas)
        if n == 1:
            texto = "1 categoría seleccionada"
        else:
            texto = f"{n} categorías seleccionadas"
        self.label_resumen.setText(texto)

    def _toggle_item(self, item: QListWidgetItem):
        """
        Cuando el usuario hace clic en una fila, alternamos si la categoría
        está activa o no en self.ids_categorias_activas, y actualizamos el texto.
        """
        cat_id = str(item.data(Qt.ItemDataRole.UserRole))
        if cat_id in self.ids_categorias_activas:
            self.ids_categorias_activas.remove(cat_id)
        else:
            self.ids_categorias_activas.add(cat_id)
        self._actualizar_resumen()

    # ------------------------------------------------------------------ CRUD maestras

    def _agregar_categoria(self):
        nombre, ok = QInputDialog.getText(
            self,
            "Nueva Categoría",
            "Nombre de la categoría:",
        )
        if not (ok and nombre.strip()):
            return

        try:
            self.firebase_client.create_categoria_maestra(nombre.strip())
            self._cargar_categorias()
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudo agregar la categoría:\n{e}",
            )

    def _renombrar_categoria(self):
        cat = self._get_current_categoria()
        if not cat:
            QMessageBox.warning(
                self,
                "Sin selección",
                "Selecciona una categoría para renombrar.",
            )
            return

        nuevo_nombre, ok = QInputDialog.getText(
            self,
            "Renombrar Categoría",
            "Nuevo nombre:",
            text=cat["nombre"],
        )
        if not (ok and nuevo_nombre.strip()):
            return

        try:
            self.firebase_client.update_categoria_maestra(
                cat["id"], nuevo_nombre.strip()
            )
            self._cargar_categorias()
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudo renombrar la categoría:\n{e}",
            )

    def _borrar_categoria(self):
        cat = self._get_current_categoria()
        if not cat:
            QMessageBox.warning(
                self,
                "Sin selección",
                "Selecciona una categoría para borrar.",
            )
            return

        if (
            QMessageBox.question(
                self,
                "Confirmar",
                f"¿Borrar la categoría '{cat['nombre']}' y sus subcategorías?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            != QMessageBox.StandardButton.Yes
        ):
            return

        try:
            self.firebase_client.delete_categoria_maestra(cat["id"])
            self._cargar_categorias()
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudo borrar la categoría:\n{e}",
            )

    # ------------------------------------------------------------------ Guardar

    def _guardar(self):
        ids_seleccionadas = self._get_checked_categoria_ids()
        if not ids_seleccionadas:
            QMessageBox.warning(
                self,
                "Error",
                "Debes seleccionar al menos una categoría para el proyecto.",
            )
            return

        try:
            exito = self.firebase_client.asignar_categorias_a_proyecto(
                self.proyecto_id, list(ids_seleccionadas)
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudieron guardar las categorías del proyecto:\n{e}",
            )
            return

        if exito:
            QMessageBox.information(
                self,
                "Guardado",
                "Categorías del proyecto actualizadas correctamente.",
            )
            self.accept()
        else:
            QMessageBox.warning(
                self,
                "Error",
                "No se pudieron guardar los cambios.",
            )