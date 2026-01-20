#!/usr/bin/env python3
"""
PROGRAIN 4.0 / 5.0 Main Application Entry Point

Firebase-based personal finance management application.
Run with: python progain4/main_ynab.py
"""

import sys
import os
import logging
from typing import Optional

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt

# ---------------------------------------------------------------------------
# Ensure project root is on sys.path so that `import progain4.*` works
# regardless of the current working directory.
# ---------------------------------------------------------------------------
CURRENT_DIR = os.path.dirname(os. path.abspath(__file__))          # .../PROGRAIN-5.0/progain4
PROJECT_ROOT = os.path. dirname(CURRENT_DIR)                       # .../PROGRAIN-5.0

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from progain4.services.firebase_client import FirebaseClient
from progain4.services.config import ConfigManager
from progain4.ui.dialogs.firebase_config_dialog import FirebaseConfigDialog
from progain4.ui.dialogs.project_dialog import ProjectDialog
from progain4.ui.main_window4 import MainWindow4

# Import theme manager
try:
    from progain4.ui.theme_manager_improved import theme_manager
    logger_temp = logging.getLogger(__name__)
    logger_temp.info("Using improved theme manager")
except ImportError: 
    from progain4.ui import theme_manager
    logger_temp = logging.getLogger(__name__)
    logger_temp.info("Using standard theme manager")


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class PROGRAIN4App: 
    """
    Main application class for PROGRAIN 4.0/5.0

    Handles:
    - Firebase initialization with validation
    - Project selection
    - Main window creation
    """

    def __init__(self):
        """Initialize the application"""
        self.app = QApplication(sys. argv)

        # High DPI:
        # Qt 6 maneja esto automáticamente en la mayoría de los casos.
        
        # Set application metadata
        self.app.setApplicationName("PROGRAIN 5.0")
        self.app.setApplicationVersion("5.0.0")
        self.app.setOrganizationName("PROGRAIN")
        self.app.setOrganizationDomain("prograin. com")

        self.firebase_client: Optional[FirebaseClient] = None
        self.main_window: Optional[MainWindow4] = None
        self.config_manager = ConfigManager()
        
        # --- APLICACIÓN DEL TEMA ---
        # Recuperamos la configuración guardada (ej: "light", "dark", "midnight", "coral")
        saved_theme = self.config_manager.get_theme()
        theme_to_apply = saved_theme if saved_theme else "light"
        
        # Aplicamos el tema
        try:
            theme_manager.apply_theme(self.app, theme_to_apply)
            logger.info(f"Applied theme at startup: {theme_to_apply}")
        except Exception as e: 
            logger.warning(f"Could not apply theme '{theme_to_apply}': {e}.  Using default.")
            try:
                theme_manager.apply_theme(self.app, "light")
            except: 
                logger.error("Could not apply default theme")

    def run(self) -> int:
        """
        Run the application. 

        Returns:
            Exit code
        """
        try:
            # Step 1: Initialize Firebase with validation
            if not self. initialize_firebase():
                logger.error("Failed to initialize Firebase")
                return 1

            # Step 2: Select or load last project (SIN DIÁLOGO INICIAL)
            proyecto_id, proyecto_nombre = self. select_project()
            if not proyecto_id:
                logger.info("No project available, exiting")
                return 0

            # Step 3: Create and show main window
            self.main_window = MainWindow4(
                self.firebase_client,
                proyecto_id,
                proyecto_nombre,
                self.config_manager,
            )
            
            # ✅ CORREGIDO: Guardar cuando CAMBIA de proyecto (no al cerrar)
            # Conectar señal de cambio de proyecto
            self.main_window.project_changed.connect(self._on_project_changed)
            
            self.main_window.show()

            logger.info(f"Application ready - Project: {proyecto_nombre} ({proyecto_id})")

            # Step 4: Run event loop
            exit_code = self.app.exec()
            
            # ✅ NUEVO: Guardar proyecto al salir (antes de que se destruya QSettings)
            if self.main_window and hasattr(self.main_window, 'current_proyecto_id'):
                self._save_last_project(
                    self. main_window.current_proyecto_id,
                    self.main_window.current_proyecto_nombre
                )
            
            return exit_code

        except Exception as e:
            logger.exception("Unexpected error:  %s", e)
            QMessageBox.critical(
                None,
                "Error Fatal",
                f"Error inesperado en la aplicación:\n{str(e)}",
            )
            return 1

    def _on_project_changed(self, proyecto_id: str, proyecto_nombre: str):
        """
        Callback cuando el usuario cambia de proyecto. 
        
        Args:
            proyecto_id: ID del nuevo proyecto
            proyecto_nombre:  Nombre del nuevo proyecto
        """
        logger.info(f"Project changed to: {proyecto_nombre} ({proyecto_id})")
        self._save_last_project(proyecto_id, proyecto_nombre)

    def initialize_firebase(self) -> bool:
        """
        Initialize Firebase connection with validation.
        
        Returns:
            True if initialization successful, False otherwise
        """
        logger.info("Initializing Firebase...")

        credentials_path = None
        storage_bucket = None
        
        # Intentar obtener credenciales desde múltiples fuentes
        
        # Priority 1: environment variables (útil para desarrollo/testing)
        env_credentials = os.environ.get("FIREBASE_CREDENTIALS", "")
        env_bucket = os.environ.get("FIREBASE_STORAGE_BUCKET", "")

        if env_credentials and env_bucket and os.path.exists(env_credentials):
            logger.info("Using Firebase credentials from environment variables")
            credentials_path = env_credentials
            storage_bucket = env_bucket
        else:
            # Priority 2: persistent configuration (archivo . ini)
            saved_credentials, saved_bucket = self.config_manager.get_firebase_config()

            if saved_credentials and saved_bucket:
                # Validar que el archivo exista
                if os.path.exists(saved_credentials):
                    logger.info("Using Firebase credentials from saved configuration")
                    credentials_path = saved_credentials
                    storage_bucket = saved_bucket
                else: 
                    logger.warning(f"Saved credentials file not found: {saved_credentials}")
                    # Limpiar configuración inválida
                    self.config_manager.clear_firebase_config()

        # Si no hay credenciales válidas, mostrar diálogo
        if not credentials_path or not storage_bucket:
            logger. info("No valid credentials found, showing configuration dialog")
            
            # Mostrar mensaje informativo
            QMessageBox.information(
                None,
                "Configuración de Firebase",
                "Bienvenido a PROGRAIN 5.0\n\n"
                "Para comenzar, necesitas configurar la conexión con Firebase.\n\n"
                "En el siguiente diálogo, selecciona el archivo de credenciales "
                "JSON descargado desde Firebase Console."
            )

            dialog = FirebaseConfigDialog(parent=None, config_manager=self.config_manager)

            if dialog.exec() != FirebaseConfigDialog.DialogCode. Accepted:
                logger.info("Firebase configuration cancelled by user")
                QMessageBox.warning(
                    None,
                    "Configuración requerida",
                    "PROGRAIN requiere configuración de Firebase para funcionar.\n\n"
                    "La aplicación se cerrará."
                )
                return False

            credentials_path, storage_bucket = dialog.get_config()
            
            if not credentials_path or not storage_bucket:
                logger.error("Invalid configuration returned from dialog")
                return False

        # Validar credenciales una última vez
        if not os.path.exists(credentials_path):
            QMessageBox.critical(
                None,
                "Error de configuración",
                f"El archivo de credenciales no existe:\n{credentials_path}\n\n"
                "Por favor, configura Firebase nuevamente."
            )
            self.config_manager.clear_firebase_config()
            return False

        # Intentar inicializar Firebase client
        try:
            logger.info(f"Initializing Firebase with credentials: {credentials_path}")
            logger.info(f"Storage bucket: {storage_bucket}")
            
            self.firebase_client = FirebaseClient()

            if not self.firebase_client.initialize(credentials_path, storage_bucket):
                raise Exception("Firebase initialization returned False")

            logger.info("Firebase initialized successfully")
            return True
            
        except Exception as e: 
            logger.error(f"Error initializing Firebase: {e}")
            
            # Mostrar error detallado y ofrecer reconfiguración
            reply = QMessageBox.critical(
                None,
                "Error de conexión con Firebase",
                f"No se pudo conectar con Firebase:\n\n{str(e)}\n\n"
                "Posibles causas:\n"
                "• Archivo de credenciales inválido\n"
                "• Nombre del bucket incorrecto\n"
                "• Sin conexión a Internet\n"
                "• Permisos insuficientes en Firebase\n\n"
                "¿Desea reconfigurar las credenciales? ",
                QMessageBox.StandardButton.Yes | QMessageBox. StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Limpiar configuración anterior
                self.config_manager. clear_firebase_config()
                
                # Mostrar diálogo de configuración
                dialog = FirebaseConfigDialog(parent=None, config_manager=self.config_manager)
                
                if dialog.exec() == FirebaseConfigDialog.DialogCode. Accepted:
                    credentials_path, storage_bucket = dialog.get_config()
                    
                    try:
                        # Reintentar inicialización
                        self.firebase_client = FirebaseClient()
                        
                        if self.firebase_client.initialize(credentials_path, storage_bucket):
                            logger.info("Firebase initialized successfully on retry")
                            return True
                        else:
                            raise Exception("Firebase initialization failed on retry")
                            
                    except Exception as e2:
                        logger.error(f"Error on retry: {e2}")
                        QMessageBox.critical(
                            None,
                            "Error",
                            f"No se pudo inicializar Firebase:\n{str(e2)}"
                        )
            
            return False

    def select_project(self) -> tuple[Optional[str], Optional[str]]:
        """
        Select or load last used project automatically.
        
        ✅ NUEVO COMPORTAMIENTO: 
        1. Intenta cargar el último proyecto usado
        2. Si no existe, carga el primero disponible
        3. Solo muestra diálogo si NO hay proyectos
        
        Returns:
            Tuple of (project_id, project_name) or (None, None) if cancelled
        """
        logger.info("Loading projects...")

        try:
            proyectos = self.firebase_client.get_proyectos()
            logger.info(f"Found {len(proyectos)} existing projects")
            
            if not proyectos: 
                logger.info("No existing projects found")
                
                # ✅ Solo preguntar si desea crear cuando NO hay proyectos
                reply = QMessageBox.question(
                    None,
                    "Sin proyectos",
                    "No se encontraron proyectos en Firebase.\n\n"
                    "¿Desea crear un nuevo proyecto?",
                    QMessageBox. StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )
                
                if reply == QMessageBox.StandardButton.No:
                    return None, None
                
                # Mostrar diálogo para crear proyecto
                dialog = ProjectDialog(proyectos=[])
                
                if dialog. exec() != ProjectDialog.DialogCode.Accepted:
                    return None, None
                
                result = dialog.get_selected_project()
                if not result or result[0] is not None:
                    return None, None
                
                # Crear nuevo proyecto
                _, nombre, descripcion = result
                logger.info(f"Creating new project: {nombre}")
                
                try: 
                    proyecto_id = self.firebase_client.create_proyecto(nombre, descripcion)
                    
                    if not proyecto_id:
                        raise Exception("create_proyecto returned None")
                    
                    logger. info(f"Project created successfully: {proyecto_id}")
                    
                    # ✅ Guardar como último proyecto
                    self._save_last_project(proyecto_id, nombre)
                    
                    return proyecto_id, nombre
                    
                except Exception as e:
                    logger.error(f"Error creating project: {e}")
                    QMessageBox.critical(
                        None,
                        "Error",
                        f"No se pudo crear el proyecto:\n{str(e)}"
                    )
                    return None, None
            
            # ✅ HAY PROYECTOS:  Intentar cargar el último usado
            last_project_id, last_project_name = self._load_last_project()
            
            if last_project_id:
                # Verificar que el proyecto aún existe
                proyecto_existe = any(
                    str(p. get('id')) == str(last_project_id) 
                    for p in proyectos
                )
                
                if proyecto_existe:
                    logger.info(f"Loading last used project: {last_project_name} ({last_project_id})")
                    return last_project_id, last_project_name
                else: 
                    logger.warning(f"Last project {last_project_id} no longer exists")
            
            # ✅ FALLBACK: Cargar el primer proyecto disponible
            primer_proyecto = proyectos[0]
            proyecto_id = str(primer_proyecto.get('id'))
            proyecto_nombre = primer_proyecto.get('nombre', f'Proyecto {proyecto_id}')
            
            logger.info(f"Loading first available project: {proyecto_nombre} ({proyecto_id})")
            
            # Guardar como último proyecto
            self._save_last_project(proyecto_id, proyecto_nombre)
            
            return proyecto_id, proyecto_nombre
            
        except Exception as e: 
            logger.error(f"Error loading projects: {e}")
            QMessageBox.critical(
                None,
                "Error",
                f"Error al cargar proyectos desde Firebase:\n{str(e)}"
            )
            return None, None

    def _load_last_project(self) -> tuple[Optional[str], Optional[str]]:
        """
        Carga el último proyecto usado desde la configuración.
        
        Returns:
            Tuple of (project_id, project_name) or (None, None) if not found
        """
        try:
            last_id = self.config_manager.get('last_project_id')
            last_name = self.config_manager.get('last_project_name')
            
            if last_id and last_name:
                return str(last_id), str(last_name)
            
            return None, None
            
        except Exception as e:
            logger. warning(f"Error loading last project:  {e}")
            return None, None

    def _save_last_project(self, proyecto_id: str, proyecto_nombre: str):
        """
        Guarda el último proyecto usado en la configuración.
        
        Args:
            proyecto_id:  ID del proyecto
            proyecto_nombre: Nombre del proyecto
        """
        try:
            self. config_manager.set('last_project_id', str(proyecto_id))
            self.config_manager.set('last_project_name', str(proyecto_nombre))
            logger.debug(f"Saved last project:  {proyecto_nombre} ({proyecto_id})")
        except Exception as e:
            logger.warning(f"Error saving last project:  {e}")

def main():
    """Main entry point"""
    logger.info("=" * 70)
    logger.info("PROGRAIN 5.0 Starting...")
    logger.info("=" * 70)
    
    try:
        app = PROGRAIN4App()
        exit_code = app.run()
        
        logger.info("=" * 70)
        logger.info(f"PROGRAIN 5.0 Exiting with code {exit_code}")
        logger.info("=" * 70)
        
        sys.exit(exit_code)
        
    except Exception as e:
        logger.exception("Fatal error in main(): %s", e)
        sys.exit(1)


if __name__ == "__main__": 
    main()