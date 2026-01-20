from typing import List, Dict, Any, Optional

from PyQt6.QtCore import Qt

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QLineEdit,
    QPushButton,
    QMessageBox,
    QInputDialog,
)


class GestionCuentasMaestrasDialog(QDialog):
    """
    Gestión de Cuentas Maestras (versión Firebase).

    Requiere que FirebaseClient implemente:
      - get_cuentas_maestras() -> List[Dict[str, Any]]
      - create_cuenta_maestra(nombre: str) -> str
      - update_cuenta_maestra(cuenta_id: str, nuevo_nombre: str) -> None
      - delete_cuenta_maestra(cuenta_id: str) -> None
    """

    def __init__(self, firebase_client, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Gestionar Cuentas Maestras")
        self.setFixedSize(420, 420)

        self.firebase_client = firebase_client

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Cuentas maestras:"))
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        self.nuevo_nombre = QLineEdit()
        self.nuevo_nombre.setPlaceholderText("Nombre de la nueva cuenta")
        layout.addWidget(self.nuevo_nombre)

        btn_layout = QHBoxLayout()
        btn_agregar = QPushButton("Agregar")
        btn_editar = QPushButton("Editar")
        btn_eliminar = QPushButton("Eliminar")
        btn_layout.addWidget(btn_agregar)
        btn_layout.addWidget(btn_editar)
        btn_layout.addWidget(btn_eliminar)
        layout.addLayout(btn_layout)

        btn_agregar.clicked.connect(self.agregar_cuenta)
        btn_editar.clicked.connect(self.editar_cuenta)
        btn_eliminar.clicked.connect(self.eliminar_cuenta)

        self._actualizar_lista()

    # ------------------------------------------------------------------ Helpers

    def _actualizar_lista(self):
        """Carga cuentas maestras desde Firebase y llena la lista."""
        self.list_widget.clear()
        try:
            cuentas: List[Dict[str, Any]] = self.firebase_client.get_cuentas_maestras() or []
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudieron cargar las cuentas maestras desde Firebase:\n{e}",
            )
            return

        for cuenta in cuentas:
            nombre = cuenta.get("nombre", "Sin nombre")
            cuenta_id = cuenta.get("id")
            item = QListWidgetItem(nombre)
            item.setData(Qt.ItemDataRole.UserRole, cuenta_id)
            self.list_widget.addItem(item)

    def _get_selected_item(self) -> Optional[QListWidgetItem]:
        items = self.list_widget.selectedItems()
        if not items:
            QMessageBox.warning(self, "Error", "Selecciona una cuenta primero.")
            return None
        return items[0]

    # ------------------------------------------------------------------ Actions

    def agregar_cuenta(self):
        nombre = self.nuevo_nombre.text().strip()
        if not nombre:
            QMessageBox.warning(self, "Error", "Debes escribir un nombre.")
            return

        try:
            self.firebase_client.create_cuenta_maestra(nombre)
            self._actualizar_lista()
            self.nuevo_nombre.clear()
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudo agregar la cuenta maestra:\n{e}",
            )

    def editar_cuenta(self):
        item = self._get_selected_item()
        if not item:
            return

        nombre_actual = item.text()
        cuenta_id = item.data(Qt.ItemDataRole.UserRole)

        nuevo_nombre, ok = QInputDialog.getText(
            self,
            "Editar cuenta",
            "Nuevo nombre:",
            text=nombre_actual,
        )
        if ok and nuevo_nombre.strip():
            try:
                self.firebase_client.update_cuenta_maestra(cuenta_id, nuevo_nombre.strip())
                self._actualizar_lista()
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"No se pudo editar la cuenta maestra:\n{e}",
                )

    def eliminar_cuenta(self):
        item = self._get_selected_item()
        if not item:
            return

        nombre = item.text()
        cuenta_id = item.data(Qt.ItemDataRole.UserRole)

        confirm = QMessageBox.question(
            self,
            "¿Eliminar?",
            f"¿Seguro que quieres borrar '{nombre}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            self.firebase_client.delete_cuenta_maestra(cuenta_id)
            self._actualizar_lista()
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudo eliminar la cuenta maestra:\n{e}",
            )