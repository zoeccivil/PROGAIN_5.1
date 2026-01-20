"""
Configuration Manager for PROGRAIN 4.0/5.0

Handles application settings persistence using INI files.
"""

import os
import sys
import logging
from typing import Optional, Tuple, Any
from PyQt6.QtCore import QSettings

logger = logging.getLogger(__name__)


class ConfigManager:
    """
    Manages persistent application configuration. 
    Uses local . ini file for cross-platform compatibility.
    """
    
    # Configuration keys
    KEY_FIREBASE_CREDENTIALS = "firebase/credentials_path"
    KEY_FIREBASE_BUCKET = "firebase/storage_bucket"
    KEY_THEME = "ui/theme"
    KEY_LAST_PROJECT_ID = "app/last_project_id"
    KEY_LAST_PROJECT_NAME = "app/last_project_name"
    
    def __init__(self):
        """Initialize configuration manager using a local INI file."""
        
        # 1. Determinar la ruta base (donde está el . exe o el script principal)
        if getattr(sys, 'frozen', False):
            # Si es un ejecutable (PyInstaller)
            base_dir = os.path.dirname(sys.executable)
        else:
            # Si es script (estamos en progain4/services/config.py -> subir 2 niveles)
            # Ruta:  . ../PROGRAIN-5.0/progain4/services/config.py
            current_dir = os.path.dirname(os.path.abspath(__file__))
            base_dir = os.path.dirname(os.path.dirname(current_dir))  # . ../PROGRAIN-5.0

        # 2. Definir ruta del archivo . ini
        ini_path = os.path.join(base_dir, "progain_app.ini")
        
        # 3. Forzar QSettings a usar ese archivo específico
        self.settings = QSettings(ini_path, QSettings.Format.IniFormat)
        
        # Log para confirmar que está leyendo el archivo correcto
        logger.info(f"Configuration file: {self.settings.fileName()}")
        
    # ==================== FIREBASE CONFIG ====================
    
    def get_firebase_config(self) -> Tuple[Optional[str], Optional[str]]: 
        """
        Get the saved Firebase configuration.
        
        Returns:
            Tuple of (credentials_path, storage_bucket)
            Returns (None, None) if configuration is missing or invalid. 
        """
        cred_path = self.settings. value(self.KEY_FIREBASE_CREDENTIALS, None)
        bucket_name = self.settings.value(self.KEY_FIREBASE_BUCKET, None)
        
        # Validar que el archivo de credenciales exista
        if cred_path: 
            if not os.path.exists(cred_path):
                logger. warning(f"Saved credentials file not found: {cred_path}")
                return None, None
        else:
            logger.info("No Firebase credentials configured")
            return None, None
        
        # Validar bucket
        if not bucket_name:
            logger. warning("No storage bucket configured")
            return None, None
        
        logger.info(f"Loaded Firebase config: {cred_path}, {bucket_name}")
        return str(cred_path), str(bucket_name)
    
    def set_firebase_config(self, credentials_path: str, storage_bucket: str) -> bool:
        """
        Save Firebase configuration to persistent storage.
        
        Args:
            credentials_path: Path to Firebase credentials JSON file
            storage_bucket: Firebase Storage bucket name
            
        Returns: 
            True if saved successfully, False otherwise
        """
        try: 
            # Validate inputs
            if not credentials_path or not storage_bucket:
                logger.error("Cannot save empty Firebase configuration")
                return False
                
            # Validate credentials file exists
            if not os. path.exists(credentials_path):
                logger.error(f"Credentials file not found: {credentials_path}")
                return False
            
            # Validate that it's a valid path
            credentials_path = os.path.abspath(credentials_path)
                
            # Save to settings
            self.settings.setValue(self. KEY_FIREBASE_CREDENTIALS, credentials_path)
            self.settings.setValue(self.KEY_FIREBASE_BUCKET, storage_bucket)
            
            # Force sync to disk
            self.settings.sync()
            
            logger.info(f"Firebase config saved:  {credentials_path}, {storage_bucket}")
            return True
            
        except Exception as e: 
            logger.error(f"Error saving Firebase configuration: {e}")
            return False
    
    # Alias for compatibility with older code
    def save_firebase_config(self, credentials_path: str, storage_bucket: str) -> bool:
        """
        Alias for set_firebase_config for backward compatibility.
        
        Args:
            credentials_path: Path to Firebase credentials JSON file
            storage_bucket: Firebase Storage bucket name
            
        Returns:
            True if saved successfully, False otherwise
        """
        return self.set_firebase_config(credentials_path, storage_bucket)
            
    def clear_firebase_config(self) -> None:
        """Clear Firebase configuration from persistent storage."""
        self.settings.remove(self.KEY_FIREBASE_CREDENTIALS)
        self.settings.remove(self.KEY_FIREBASE_BUCKET)
        self.settings.sync()
        logger.info("Cleared Firebase configuration")
        
    def has_firebase_config(self) -> bool:
        """
        Check if Firebase configuration exists and is valid. 
        
        Returns:
            True if valid configuration exists, False otherwise
        """
        credentials_path, storage_bucket = self.get_firebase_config()
        return credentials_path is not None and storage_bucket is not None

    # ==================== THEME CONFIG ====================
    
    def get_theme(self) -> Optional[str]:
        """
        Get the saved theme name from persistent storage.
        
        Returns:
            Theme name (e.g., "light", "dark", "blue", "green", "midnight") or None if not set
        """
        theme_name = self.settings.value(self.KEY_THEME, None)
        
        if theme_name: 
            logger.info(f"Loaded theme from settings: {theme_name}")
        else:
            logger.info("No saved theme found in settings, will use default")
        
        return theme_name
    
    def set_theme(self, theme_name: str) -> bool:
        """
        Save the theme name to persistent storage.
        
        Args:
            theme_name:  Name of the theme to save (e.g., "light", "dark", "blue", "green", "midnight")
            
        Returns: 
            True if saved successfully, False otherwise
        """
        try: 
            if not theme_name: 
                logger.error("Cannot save empty theme name")
                return False
            
            # Save to settings
            self.settings.setValue(self.KEY_THEME, theme_name)
            
            # Force sync to disk
            self. settings.sync()
            
            logger.info(f"Saved theme to settings: {theme_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving theme configuration: {e}")
            return False
    
    # ==================== GENERIC CONFIG (get/set) ====================
    
    def get(self, key:  str, default: Any = None) -> Any:
        """
        Get a configuration value using QSettings.
        
        Args:
            key: Configuration key (can use "/" for hierarchy, e.g., "app/last_project_id")
            default: Default value if not found
            
        Returns:
            Configuration value or default
        """
        try:
            value = self.settings.value(key, default)
            return value
            
        except Exception as e: 
            logger.error(f"Error reading config key '{key}': {e}")
            return default

    def set(self, key:  str, value: Any) -> bool:
        """
        Set a configuration value using QSettings.
        
        Args:
            key:  Configuration key (can use "/" for hierarchy, e.g., "app/last_project_id")
            value: Value to set
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.settings.setValue(key, value)
            self.settings.sync()
            
            logger.debug(f"Saved config:  {key} = {value}")
            return True
            
        except Exception as e:
            logger. error(f"Error writing config key '{key}': {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        Delete a configuration value. 
        
        Args:
            key: Configuration key to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.settings. remove(key)
            self.settings.sync()
            
            logger.debug(f"Deleted config key: {key}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting config key '{key}': {e}")
            return False
    
    # ==================== UTILITY METHODS ====================
    
    def get_config_file_path(self) -> str:
        """
        Get the full path to the configuration file.
        
        Returns:
            Full path to the .ini file
        """
        return self.settings.fileName()
    
    def get_firebase_credentials_path(self) -> Optional[str]:
        """
        Get saved Firebase credentials path.
        
        Returns:
            Path to credentials file or None
        """
        cred_path, _ = self.get_firebase_config()
        return cred_path
    
    def get_firebase_storage_bucket(self) -> Optional[str]:
        """
        Get saved Firebase storage bucket. 
        
        Returns:
            Storage bucket name or None
        """
        _, bucket = self.get_firebase_config()
        return bucket