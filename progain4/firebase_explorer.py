import sys
import os
import logging
from typing import Optional

from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QMessageBox,
    QSplitter,
    QWidget,
)
from PyQt6.QtCore import Qt

# --- AÑADIR ESTE BLOQUE JUSTO DESPUÉS DE LOS IMPORTS STANDARD ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))          # .../PROGRAIN-5.0/progain4
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)                       # .../PROGRAIN-5.0

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
# ---------------------------------------------------------------

from firebase_admin import firestore

from progain4.ui.dialogs.firebase_config_dialog import FirebaseConfigDialog
from progain4.services.config import ConfigManager
from progain4.services.firebase_client import FirebaseClient

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


class FirebaseExplorerDialog(QDialog):
    """
    Dialogo simple para explorar la estructura de Firestore usada por PROGRAIN.

    - Lista colecciones raíz.
    - Lista proyectos.
    - Para un proyecto seleccionado, lista subcolecciones reales.
    """

    def __init__(self, firebase_client: FirebaseClient, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Explorador de Firebase - PROGRAIN")
        self.resize(900, 600)

        self.firebase_client = firebase_client
        self.db: firestore.Client = firebase_client.db

        self._init_ui()
        self._load_root_collections()
        self._load_projects()

    def _init_ui(self):
        main_layout = QVBoxLayout()

        info_label = QLabel(
            "Este explorador muestra la estructura REAL de Firestore usada por PROGRAIN.\n"
            "Úsalo para ver dónde están las colecciones de cuentas, categorías, "
            "subcategorías y transacciones."
        )
        info_label.setWordWrap(True)
        main_layout.addWidget(info_label)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Panel izquierdo: colecciones raíz + proyectos
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(5, 5, 5, 5)

        left_layout.addWidget(QLabel("<b>Colecciones raíz</b>"))
        self.root_collections_list = QListWidget()
        left_layout.addWidget(self.root_collections_list)

        left_layout.addWidget(QLabel("<b>Proyectos (colección 'proyectos')</b>"))
        self.projects_list = QListWidget()
        self.projects_list.itemClicked.connect(self._on_project_clicked)
        left_layout.addWidget(self.projects_list)

        left_panel.setLayout(left_layout)
        splitter.addWidget(left_panel)

        # Panel derecho: detalle de proyecto / colección
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(5, 5, 5, 5)

        self.detail_title = QLabel("<b>Detalle</b>")
        right_layout.addWidget(self.detail_title)

        self.detail_list = QListWidget()
        right_layout.addWidget(self.detail_list)

        # Botón para explorar documentos de una colección raíz seleccionada
        explore_root_btn = QPushButton("Explorar colección raíz seleccionada...")
        explore_root_btn.clicked.connect(self._on_explore_root_collection)
        right_layout.addWidget(explore_root_btn)

        right_panel.setLayout(right_layout)
        splitter.addWidget(right_panel)

        splitter.setSizes([300, 600])

        main_layout.addWidget(splitter)

        # Botones inferiores
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton("Cerrar")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        main_layout.addLayout(btn_layout)

        self.setLayout(main_layout)

    # ---------------------- Carga de datos ----------------------

    def _load_root_collections(self):
        self.root_collections_list.clear()
        try:
            root_collections = list(self.db.collections())
            logger.info("Root collections: %s", [c.id for c in root_collections])
            for col in root_collections:
                item = QListWidgetItem(col.id)
                self.root_collections_list.addItem(item)
        except Exception as e:
            logger.error("Error loading root collections: %s", e)
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudieron cargar las colecciones raíz:\n{e}",
            )

    def _load_projects(self):
        self.projects_list.clear()
        try:
            proyectos = self.firebase_client.get_proyectos()
            for p in proyectos:
                name = p.get("nombre", "")
                pid = p.get("id", "")
                display = f"{pid} - {name}"
                item = QListWidgetItem(display)
                item.setData(Qt.ItemDataRole.UserRole, pid)
                self.projects_list.addItem(item)
        except Exception as e:
            logger.error("Error loading projects: %s", e)
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudieron cargar los proyectos:\n{e}",
            )

    # ---------------------- Handlers ----------------------

    def _on_project_clicked(self, item: QListWidgetItem):
        """Cuando se selecciona un proyecto, listar sus subcolecciones reales."""
        proyecto_id = item.data(Qt.ItemDataRole.UserRole)
        if not proyecto_id:
            return

        self.detail_title.setText(f"<b>Subcolecciones de proyectos/{proyecto_id}</b>")
        self.detail_list.clear()
        try:
            proj_ref = self.db.collection("proyectos").document(proyecto_id)
            subs = list(proj_ref.collections())
            if not subs:
                self.detail_list.addItem("(Sin subcolecciones visibles)")
                return

            for c in subs:
                sub_item = QListWidgetItem(c.id)
                # Intentar mostrar un ejemplo de documento
                example = None
                try:
                    for doc in c.stream():
                        example = doc.to_dict()
                        doc_id = doc.id
                        break
                except Exception as inner_e:
                    example = f"Error al leer documentos: {inner_e}"

                if isinstance(example, dict):
                    sub_item.setToolTip(
                        f"Ejemplo doc id: {doc_id}\n"
                        f"Campos: {', '.join(list(example.keys())[:10])}"
                    )
                else:
                    sub_item.setToolTip(str(example))

                self.detail_list.addItem(sub_item)

        except Exception as e:
            logger.error("Error listing subcollections for project %s: %s", proyecto_id, e)
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudieron obtener las subcolecciones del proyecto {proyecto_id}:\n{e}",
            )

    def _on_explore_root_collection(self):
        """Explora la colección raíz seleccionada y muestra algunos documentos."""
        item = self.root_collections_list.currentItem()
        if not item:
            QMessageBox.information(
                self,
                "Seleccione una colección",
                "Seleccione una colección raíz en la lista de la izquierda.",
            )
            return

        col_name = item.text()
        self.detail_title.setText(f"<b>Documentos de la colección raíz '{col_name}' (máx 20)</b>")
        self.detail_list.clear()

        try:
            col_ref = self.db.collection(col_name)
            count = 0
            for doc in col_ref.stream():
                data = doc.to_dict()
                display = f"id={doc.id}  |  keys={list(data.keys())}"
                list_item = QListWidgetItem(display)
                list_item.setData(Qt.ItemDataRole.UserRole, data)
                self.detail_list.addItem(list_item)
                count += 1
                if count >= 20:
                    break

            if count == 0:
                self.detail_list.addItem("(Colección vacía)")

        except Exception as e:
            logger.error("Error exploring root collection %s: %s", col_name, e)
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudieron leer documentos de la colección {col_name}:\n{e}",
            )


def main():
    app = QApplication(sys.argv)

    # 1. Reutilizar ConfigManager y/o FirebaseConfigDialog para obtener credenciales
    cfg = ConfigManager()
    creds, bucket = cfg.get_firebase_config()

    # Si no hay config persistente, abre el mismo diálogo que la app principal
    if not creds or not bucket:
        dlg = FirebaseConfigDialog()
        if dlg.exec() != FirebaseConfigDialog.DialogCode.Accepted:
            print("Configuración cancelada.")
            sys.exit(0)
        creds, bucket = dlg.get_config()
        # Guardar para la próxima vez
        cfg.save_firebase_config(creds, bucket)

    # 2. Inicializar FirebaseClient con esas credenciales
    fc = FirebaseClient()
    if not fc.initialize(creds, bucket):
        QMessageBox.critical(
            None,
            "Error de Firebase",
            "No se pudo inicializar Firebase. Verifique credenciales y bucket.",
        )
        sys.exit(1)

    # 3. Mostrar el explorador
    dlg = FirebaseExplorerDialog(firebase_client=fc)
    dlg.exec()

    sys.exit(0)


if __name__ == "__main__":
    main()