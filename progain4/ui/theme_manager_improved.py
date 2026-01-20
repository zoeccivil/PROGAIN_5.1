"""
theme_manager_improved.py
Gestor de temas avanzado para PROGRAIN 5.0
Genera hojas de estilo QSS dinámicas basadas en configuraciones de paleta.
"""

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, pyqtSignal

# =============================================================================
# CORRECCIÓN DE IMPORTACIONES (Path Fix)
# Permite que funcione tanto desde main_ynab.py como en pruebas locales
# =============================================================================
try:
    # Intento 1: Importación absoluta (Ruta para cuando ejecutas main_ynab.py)
    from progain4.ui.theme_constants import THEMES, AppFonts, AppMargins
except ImportError:
    try:
        # Intento 2: Importación relativa (Por si Python lo trata como paquete)
        from .theme_constants import THEMES, AppFonts, AppMargins
    except ImportError:
        # Intento 3: Importación local (Para test_themes.py ejecutado en la carpeta ui)
        from theme_constants import THEMES, AppFonts, AppMargins
# =============================================================================

class ThemeManager(QObject):
    """
    Singleton-like manager para aplicar estilos a toda la aplicación.
    """
    theme_changed = pyqtSignal(str) # Señal emitida cuando cambia el tema

    def __init__(self):
        super().__init__()
        self.current_theme = "light"

    def get_available_themes(self):
        return list(THEMES.keys())

    def apply_theme(self, app: QApplication, theme_name: str):
        """
        Genera el QSS para el tema seleccionado y lo aplica a la QApplication.
        """
        if theme_name not in THEMES:
            print(f"Advertencia: Tema '{theme_name}' no encontrado. Usando 'light'.")
            theme_name = "light"
        
        self.current_theme = theme_name
        palette = THEMES[theme_name]
        
        # Construcción del QSS Maestro
        qss = f"""
        /* === MAIN WINDOW & GENERAL === */
        QMainWindow, QWidget {{
            background-color: {palette['bg_main']};
            color: {palette['fg_primary']};
            font-family: {AppFonts.MAIN_FONT};
            font-size: {AppFonts.BODY};
        }}

        /* === SIDEBAR (Navigation) === */
        #sidebar {{
            background-color: {palette['bg_sidebar']};
            border-right: 1px solid {palette['border']};
        }}
        
        /* Botones del Sidebar */
        QPushButton#sidebarNavButton {{
            background-color: transparent;
            color: {palette['sidebar_text']};
            text-align: left;
            padding: 12px 20px;
            border: none;
            border-radius: {AppMargins.RADIUS};
            font-weight: 500;
            margin: 2px 8px;
        }}
        
        QPushButton#sidebarNavButton:hover {{
            background-color: {palette['sidebar_hover']};
            color: {palette['fg_primary']};
        }}
        
        QPushButton#sidebarNavButton:checked {{
            background-color: {palette['sidebar_active']};
            color: {palette['sidebar_active_text']};
            border-left: 3px solid {palette['sidebar_active_text']};
            font-weight: bold;
        }}

        /* === STANDARD BUTTONS === */
        QPushButton {{
            background-color: {palette['bg_surface']};
            border: 1px solid {palette['border']};
            color: {palette['fg_primary']};
            padding: 6px 16px;
            border-radius: {AppMargins.RADIUS};
            font-weight: 500;
        }}
        
        QPushButton:hover {{
            background-color: {palette['bg_main']};
            border-color: {palette['accent']};
        }}
        
        QPushButton:pressed {{
            background-color: {palette['border']};
        }}

        /* Primary Action Button (class="primary") */
        QPushButton[class="primary"] {{
            background-color: {palette['accent']};
            color: {palette['accent_text']};
            border: none;
        }}
        
        QPushButton[class="primary"]:hover {{
            background-color: {palette['accent_hover']};
        }}

        /* === INPUT FIELDS === */
        QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox, QDateEdit {{
            background-color: {palette['bg_surface']};
            border: 1px solid {palette['border']};
            color: {palette['fg_primary']};
            padding: 6px;
            border-radius: {AppMargins.RADIUS};
            selection-background-color: {palette['accent']};
            selection-color: {palette['accent_text']};
        }}
        
        QLineEdit:focus, QComboBox:focus {{
            border: 1px solid {palette['accent']};
        }}

        /* === TABLES (QTableWidget) === */
        QTableWidget {{
            background-color: {palette['bg_surface']};
            gridline-color: {palette['border']};
            border: 1px solid {palette['border']};
            border-radius: {AppMargins.RADIUS};
            alternate-background-color: {palette['table_alt']};
        }}
        
        QHeaderView::section {{
            background-color: {palette['bg_main']};
            color: {palette['fg_secondary']};
            padding: 8px;
            border: none;
            border-bottom: 2px solid {palette['border']};
            font-weight: bold;
            text-transform: uppercase;
            font-size: {AppFonts.SMALL};
        }}
        
        QTableWidget::item {{
            padding: 6px;
        }}
        
        QTableWidget::item:selected {{
            background-color: {palette['sidebar_active']};
            color: {palette['fg_primary']};
        }}

        /* === SCROLLBARS === */
        QScrollBar:vertical {{
            border: none;
            background: {palette['bg_main']};
            width: 10px;
            margin: 0px;
        }}
        
        QScrollBar::handle:vertical {{
            background: {palette['border']};
            min-height: 20px;
            border-radius: 5px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background: {palette['fg_secondary']};
        }}
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}

        /* === GROUP BOX & CARDS === */
        QGroupBox {{
            border: 1px solid {palette['border']};
            border-radius: {AppMargins.RADIUS};
            margin-top: 24px;
            font-weight: bold;
            color: {palette['fg_secondary']};
        }}
        
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 5px;
            left: 10px;
        }}
        
        /* === TABS === */
        QTabWidget::pane {{
            border: 1px solid {palette['border']};
            border-radius: {AppMargins.RADIUS};
            background: {palette['bg_surface']};
        }}
        
        QTabBar::tab {{
            background: {palette['bg_main']};
            color: {palette['fg_secondary']};
            padding: 8px 16px;
            border-top-left-radius: {AppMargins.RADIUS};
            border-top-right-radius: {AppMargins.RADIUS};
            margin-right: 4px;
        }}
        
        QTabBar::tab:selected {{
            background: {palette['bg_surface']};
            color: {palette['accent']};
            border-bottom: 2px solid {palette['accent']};
            font-weight: bold;
        }}
        """
        
        app.setStyleSheet(qss)
        self.theme_changed.emit(theme_name)
        print(f"Tema '{theme_name}' aplicado correctamente.")

# Instancia global
theme_manager = ThemeManager()