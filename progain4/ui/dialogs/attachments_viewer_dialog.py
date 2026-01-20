from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QListWidget, QListWidgetItem, 
    QPushButton, QHBoxLayout, QLabel, QMessageBox
)
from PyQt6.QtCore import Qt, QUrl, QSize
from PyQt6.QtGui import QIcon, QDesktopServices
import os

class AttachmentsViewerDialog(QDialog):
    """
    Diálogo para visualizar y abrir archivos adjuntos de una transacción.
    """
    def __init__(self, adjuntos: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Archivos Adjuntos")
        self.resize(500, 400)
        
        # Aseguramos que sea una lista, incluso si llega None o string
        if not adjuntos:
            self.adjuntos = []
        elif isinstance(adjuntos, str):
            self.adjuntos = [adjuntos]
        else:
            self.adjuntos = adjuntos
            
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        lbl_info = QLabel("Archivos adjuntos (Doble clic para abrir):")
        lbl_info.setStyleSheet("font-weight: bold; color: #555;")
        layout.addWidget(lbl_info)

        # Lista de archivos
        self.list_widget = QListWidget()
        self.list_widget.setIconSize(QSize(24, 24))
        self.list_widget.itemDoubleClicked.connect(self._open_item)
        
        # Poblar lista
        if not self.adjuntos:
            item = QListWidgetItem("No hay archivos adjuntos.")
            item.setFlags(Qt.ItemFlag.NoItemFlags) # Deshabilitar interacción
            self.list_widget.addItem(item)
        else:
            for url in self.adjuntos:
                # Intentar extraer un nombre legible de la URL de Firebase
                # Las URLs de Firebase suelen ser largas con tokens
                try:
                    # Decodificar nombre si es posible, si no usar parte final
                    from urllib.parse import unquote
                    clean_url = unquote(url)
                    # Buscar el nombre real antes de los parámetros ?alt=...
                    base_name = clean_url.split('/')[-1].split('?')[0]
                except:
                    base_name = "Archivo adjunto"

                item = QListWidgetItem(f"📄 {base_name}")
                item.setData(Qt.ItemDataRole.UserRole, url)
                item.setToolTip(url) 
                self.list_widget.addItem(item)
            
        layout.addWidget(self.list_widget)

        # Botones
        btn_layout = QHBoxLayout()
        
        btn_open = QPushButton("Abrir Seleccionado")
        btn_open.clicked.connect(lambda: self._open_item(self.list_widget.currentItem()))
        if not self.adjuntos:
            btn_open.setEnabled(False)
            
        btn_close = QPushButton("Cerrar")
        btn_close.clicked.connect(self.accept)
        
        btn_layout.addStretch()
        btn_layout.addWidget(btn_open)
        btn_layout.addWidget(btn_close)
        
        layout.addLayout(btn_layout)

    def _open_item(self, item):
        if not item: 
            return
            
        url = item.data(Qt.ItemDataRole.UserRole)
        if url:
            # QDesktopServices abre la URL con la app predeterminada del OS (Navegador, Visor de fotos, etc.)
            success = QDesktopServices.openUrl(QUrl(url))
            if not success:
                QMessageBox.warning(self, "Error", "No se pudo abrir el archivo. Verifique su conexión a internet.")
        else:
            # Caso de item vacío o placeholder
            pass