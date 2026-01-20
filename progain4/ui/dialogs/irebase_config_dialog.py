# progain4/ui/dialogs/firebase_config_dialog. py
"""
Diálogo de Configuración de Firebase para PROGRAIN 5.0

Permite al usuario seleccionar el archivo de credenciales JSON de Firebase
y configurar el bucket de Storage.
"""

import os
import json
from typing import Optional, Tuple

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QFileDialog, QMessageBox, QGroupBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import logging

logger = logging.getLogger(__name__)


class FirebaseConfigDialog(QDialog):
    """
    Diálogo para configurar las credenciales de Firebase. 
    
    Permite:
    - Seleccionar archivo JSON de credenciales (service account)
    - Configurar el bucket de Storage
    - Validar credenciales antes de guardar
    """
    
    def __init__(self, parent=None, config_manager=None):
        """
        Initialize dialog. 
        
        Args:
            parent: Parent widget
            config_manager: ConfigManager instance for loading/saving config
        """
        super().__init__(parent)
        self.setWindowTitle("Configuración de Firebase - PROGRAIN 5.0")
        self.setModal(True)
        self.setMinimumWidth(600)
        self.setMinimumHeight(350)
        
        self. config_manager = config_manager
        self._credentials_path = ""
        self._storage_bucket = ""
        
        self._init_ui()
        self._load_existing_config()
    
    def _init_ui(self):
        """Construye la interfaz del diálogo."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Título
        title = QLabel("🔥 Configuración de Firebase")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Descripción
        desc = QLabel(
            "Para conectar PROGRAIN con Firebase, necesitas un archivo de credenciales\n"
            "(Service Account JSON) de tu proyecto Firebase.\n\n"
            "Este archivo se puede descargar desde:\n"
            "Firebase Console → Configuración del Proyecto → Service Accounts → "
            "Generar nueva clave privada"
        )
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignmentFlag. AlignCenter)
        desc.setStyleSheet("color: gray; padding: 10px;")
        layout.addWidget(desc)
        
        # Grupo de credenciales
        cred_group = QGroupBox("📄 Credenciales")
        cred_layout = QVBoxLayout()
        cred_layout.setSpacing(10)
        
        # Ruta del archivo JSON
        cred_label = QLabel("Archivo de credenciales (JSON):")
        cred_label.setStyleSheet("font-weight: bold;")
        cred_layout. addWidget(cred_label)
        
        cred_row = QHBoxLayout()
        self.cred_edit = QLineEdit()
        self.cred_edit.setPlaceholderText("Selecciona el archivo de credenciales de Firebase...")
        self.cred_edit.setReadOnly(True)
        cred_row.addWidget(self.cred_edit)
        
        btn_browse = QPushButton("📂 Seleccionar...")
        btn_browse.setMinimumWidth(120)
        btn_browse.clicked.connect(self._browse_credentials)
        cred_row.addWidget(btn_browse)
        cred_layout.addLayout(cred_row)
        
        cred_group.setLayout(cred_layout)
        layout.addWidget(cred_group)
        
        # Grupo de Storage
        storage_group = QGroupBox("☁️ Storage")
        storage_layout = QVBoxLayout()
        storage_layout.setSpacing(10)
        
        bucket_label = QLabel("Bucket de Storage:")
        bucket_label.setStyleSheet("font-weight: bold;")
        storage_layout. addWidget(bucket_label)
        
        self.bucket_edit = QLineEdit()
        self.bucket_edit.setPlaceholderText("proyecto-id. firebasestorage.app")
        storage_layout.addWidget(self.bucket_edit)
        
        bucket_hint = QLabel(
            "💡 Se autocompleta al seleccionar las credenciales.\n"
            "Formato:  {project_id}.firebasestorage.app o {project_id}.appspot.com"
        )
        bucket_hint.setStyleSheet("color: gray; font-size: 9pt;")
        bucket_hint.setWordWrap(True)
        storage_layout.addWidget(bucket_hint)
        
        storage_group.setLayout(storage_layout)
        layout.addWidget(storage_group)
        
        layout.addStretch()
        
        # Botones de acción
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_cancel = QPushButton("❌ Cancelar")
        btn_cancel.setMinimumWidth(100)
        btn_cancel.clicked.connect(self. reject)
        btn_layout. addWidget(btn_cancel)
        
        btn_test = QPushButton("🔍 Validar")
        btn_test.setMinimumWidth(100)
        btn_test.clicked.connect(self._test_connection)
        btn_layout.addWidget(btn_test)
        
        btn_save = QPushButton("💾 Guardar")
        btn_save.setMinimumWidth(100)
        btn_save.clicked.connect(self._save_and_accept)
        btn_save.setDefault(True)
        btn_layout.addWidget(btn_save)
        
        layout.addLayout(btn_layout)
    
    def _load_existing_config(self):
        """Carga la configuración existente si la hay."""
        if not self.config_manager:
            return
        
        try: 
            cred_path, bucket = self.config_manager. get_firebase_config()
            
            if cred_path: 
                self.cred_edit. setText(cred_path)
                self._credentials_path = cred_path
                logger.info(f"Loaded existing credentials path: {cred_path}")
            
            if bucket:
                self.bucket_edit.setText(bucket)
                self._storage_bucket = bucket
                logger.info(f"Loaded existing bucket: {bucket}")
                
        except Exception as e: 
            logger.error(f"Error loading existing config: {e}")
    
    def _browse_credentials(self):
        """Abre diálogo para seleccionar archivo de credenciales."""
        start_dir = os.path. expanduser("~")
        
        # Si ya hay una ruta, usar su directorio
        if self._credentials_path and os.path.exists(os. path.dirname(self._credentials_path)):
            start_dir = os.path.dirname(self._credentials_path)
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar credenciales de Firebase",
            start_dir,
            "Archivos JSON (*.json);;Todos los archivos (*.*)"
        )
        
        if not file_path:
            return
        
        self.cred_edit.setText(file_path)
        self._credentials_path = file_path
        logger.info(f"Selected credentials file: {file_path}")
        
        # Intentar extraer project_id y autocompletar bucket
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                cred_data = json.load(f)
                project_id = cred_data.get('project_id', '')
                
                if project_id:
                    # Intentar determinar el bucket correcto
                    suggested_bucket = f"{project_id}.firebasestorage.app"
                    
                    # Solo autocompletar si el campo está vacío
                    if not self.bucket_edit.text().strip():
                        self.bucket_edit.setText(suggested_bucket)
                        self._storage_bucket = suggested_bucket
                    
                    logger.info(f"Detected project:  {project_id}")
                    
                    QMessageBox.information(
                        self,
                        "✓ Credenciales detectadas",
                        f"<b>Proyecto detectado:</b> {project_id}<br><br>"
                        f"<b>Bucket sugerido:</b> {suggested_bucket}<br><br>"
                        f"Si el bucket es diferente, puedes editarlo manualmente."
                    )
                    
        except json.JSONDecodeError:
            QMessageBox. warning(
                self, 
                "⚠️ Archivo inválido", 
                "El archivo seleccionado no es un JSON válido.\n\n"
                "Asegúrate de descargar el archivo correcto desde Firebase Console."
            )
        except Exception as e:
            logger.error(f"Error reading credentials: {e}")
            QMessageBox.warning(
                self,
                "⚠️ Error",
                f"No se pudo leer el archivo:\n{str(e)}"
            )
    
    def _test_connection(self):
        """Valida la conexión con Firebase."""
        cred_path = self.cred_edit. text().strip()
        bucket = self.bucket_edit.text().strip()
        
        if not cred_path:
            QMessageBox.warning(
                self, 
                "⚠️ Campos incompletos", 
                "Por favor, selecciona un archivo de credenciales."
            )
            return
        
        if not os.path.exists(cred_path):
            QMessageBox.warning(
                self, 
                "⚠️ Archivo no encontrado", 
                f"El archivo de credenciales no existe:\n{cred_path}"
            )
            return
        
        if not bucket:
            QMessageBox.warning(
                self, 
                "⚠️ Campos incompletos", 
                "Por favor, ingresa el nombre del bucket de Storage."
            )
            return
        
        try:
            # Intentar cargar y validar las credenciales
            with open(cred_path, 'r', encoding='utf-8') as f:
                cred_data = json.load(f)
            
            # Validar campos requeridos
            required_fields = ['type', 'project_id', 'private_key', 'client_email']
            missing = [f for f in required_fields if f not in cred_data]
            
            if missing:
                QMessageBox.warning(
                    self,
                    "⚠️ Credenciales incompletas",
                    f"El archivo de credenciales no contiene los campos requeridos:\n"
                    f"<b>{', '.join(missing)}</b><br><br>"
                    "Asegúrate de usar un archivo de <b>Service Account</b> válido "
                    "descargado desde Firebase Console."
                )
                return
            
            if cred_data.get('type') != 'service_account': 
                QMessageBox.warning(
                    self,
                    "⚠️ Tipo de credencial inválido",
                    "El archivo debe ser de tipo '<b>service_account</b>'. <br><br>"
                    "Descarga las credenciales desde: <br>"
                    "<i>Firebase Console → Configuración → Service Accounts → "
                    "Generar nueva clave privada</i>"
                )
                return
            
            # Validaciones exitosas
            project_id = cred_data. get('project_id', 'N/A')
            client_email = cred_data. get('client_email', 'N/A')
            
            QMessageBox.information(
                self,
                "✅ Credenciales válidas",
                f"<b>Las credenciales son válidas</b><br><br>"
                f"<b>Proyecto: </b> {project_id}<br>"
                f"<b>Service Account:</b> {client_email}<br><br>"
                f"<i>Haz clic en 'Guardar' para aplicar la configuración.</i>"
            )
            
            logger.info(f"Credentials validated successfully for project: {project_id}")
            
        except json.JSONDecodeError:
            QMessageBox.critical(
                self, 
                "❌ Error de formato", 
                "El archivo no es un JSON válido.\n\n"
                "Verifica que el archivo no esté corrupto."
            )
        except Exception as e:
            logger.error(f"Error validating credentials: {e}")
            QMessageBox. critical(
                self, 
                "❌ Error", 
                f"Error al validar las credenciales:\n\n{str(e)}"
            )
    
    def _save_and_accept(self):
        """Guarda la configuración y cierra el diálogo."""
        cred_path = self.cred_edit.text().strip()
        bucket = self.bucket_edit.text().strip()
        
        # Validaciones
        if not cred_path:
            QMessageBox.warning(
                self, 
                "⚠️ Campos incompletos", 
                "Por favor, selecciona un archivo de credenciales."
            )
            return
        
        if not os.path.exists(cred_path):
            QMessageBox.warning(
                self, 
                "⚠️ Archivo no encontrado", 
                f"El archivo de credenciales no existe:\n{cred_path}"
            )
            return
        
        if not bucket:
            QMessageBox. warning(
                self, 
                "⚠️ Campos incompletos", 
                "Por favor, ingresa el nombre del bucket de Storage."
            )
            return
        
        # Guardar valores
        self._credentials_path = cred_path
        self._storage_bucket = bucket
        
        # Guardar en ConfigManager
        if self.config_manager:
            try:
                success = self.config_manager.set_firebase_config(cred_path, bucket)
                if success:
                    logger.info(f"Firebase config saved:  {cred_path}, {bucket}")
                    
                    QMessageBox.information(
                        self,
                        "✅ Configuración guardada",
                        "La configuración de Firebase se guardó correctamente.\n\n"
                        "La aplicación se reiniciará para aplicar los cambios."
                    )
                else:
                    logger.error("Failed to save Firebase config")
                    QMessageBox.warning(
                        self,
                        "⚠️ Advertencia",
                        "No se pudo guardar la configuración.\n"
                        "Los cambios se aplicarán solo para esta sesión."
                    )
            except Exception as e:
                logger.error(f"Error saving config: {e}")
                QMessageBox.warning(
                    self,
                    "⚠️ Error al guardar",
                    f"Error al guardar la configuración:\n{str(e)}\n\n"
                    "Los cambios se aplicarán solo para esta sesión."
                )
        
        self.accept()
    
    def get_config(self) -> Tuple[str, str]:
        """
        Retorna la configuración seleccionada.
        
        Returns:
            Tuple of (credentials_path, storage_bucket)
        """
        return (self._credentials_path, self._storage_bucket)
    
    def get_credentials_path(self) -> str:
        """Retorna la ruta del archivo de credenciales."""
        return self._credentials_path
    
    def get_storage_bucket(self) -> str:
        """Retorna el nombre del bucket de Storage."""
        return self._storage_bucket


def show_firebase_config_dialog(parent=None, config_manager=None) -> Optional[Tuple[str, str]]: 
    """
    Muestra el diálogo de configuración de Firebase.
    
    Args:
        parent: Widget padre
        config_manager: ConfigManager instance
    
    Returns:
        Tuple of (credentials_path, bucket) if accepted, None if cancelled
    """
    dialog = FirebaseConfigDialog(parent, config_manager)
    result = dialog.exec()
    
    if result == QDialog.DialogCode.Accepted:
        return dialog.get_config()
    
    return None