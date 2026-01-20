"""
test_themes.py
Script de prueba standalone para visualizar el nuevo sistema de temas.
CORREGIDO: Ahora actualiza el color de los iconos dinámicamente.
"""

import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QTableWidget, 
                             QTableWidgetItem, QLineEdit, QComboBox, QFrame, 
                             QHeaderView)
from PyQt6.QtCore import Qt
from theme_manager_improved import theme_manager
from icon_manager import IconManager
from theme_constants import THEMES

class ThemePreviewWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PROGRAIN 5.0 - UI System Preview")
        self.resize(1200, 800)
        
        # Widget principal
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # Layout principal
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # --- 1. SIDEBAR ---
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar") 
        self.sidebar.setFixedWidth(260)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 20, 0, 20)
        sidebar_layout.setSpacing(5)
        
        # Logo
        lbl_logo = QLabel("PROGRAIN 5.0")
        lbl_logo.setStyleSheet("font-size: 20px; font-weight: bold; padding-left: 20px; margin-bottom: 20px;")
        sidebar_layout.addWidget(lbl_logo)
        
        # Botones de navegación
        menu_items = [
            ("Dashboard", "dashboard"),
            ("Transacciones", "transactions"),
            ("Flujo de Caja", "cashflow"),
            ("Cuentas", "accounts"),
            ("Reportes", "reports"),
            ("Configuración", "settings")
        ]
        
        self.nav_buttons = []
        for text, icon_key in menu_items:
            btn = QPushButton(text)
            btn.setObjectName("sidebarNavButton")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            
            # --- CLAVE: Guardamos el nombre del icono en el botón para usarlo luego ---
            btn.setProperty("icon_name", icon_key)
            
            sidebar_layout.addWidget(btn)
            self.nav_buttons.append(btn)
            
        sidebar_layout.addStretch()
        
        # User Profile
        lbl_user = QLabel("Admin User")
        lbl_user.setStyleSheet("padding: 20px; color: grey;")
        sidebar_layout.addWidget(lbl_user)
        
        main_layout.addWidget(self.sidebar)
        
        # --- 2. CONTENIDO ---
        content_area = QWidget()
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(30, 30, 30, 30)
        content_layout.setSpacing(20)
        
        # Header
        header_layout = QHBoxLayout()
        lbl_title = QLabel("Dashboard General")
        lbl_title.setStyleSheet("font-size: 24px; font-weight: bold;")
        
        self.combo_themes = QComboBox()
        self.combo_themes.setFixedWidth(200)
        self.combo_themes.addItems(theme_manager.get_available_themes())
        self.combo_themes.currentTextChanged.connect(self.change_theme)
        
        header_layout.addWidget(lbl_title)
        header_layout.addStretch()
        header_layout.addWidget(QLabel("Cambiar Tema:"))
        header_layout.addWidget(self.combo_themes)
        content_layout.addLayout(header_layout)
        
        # Stats Cards
        stats_layout = QHBoxLayout()
        for i in range(3):
            card = QFrame()
            # Usamos un estilo inline temporal para las tarjetas de ejemplo
            card.setStyleSheet("background-color: rgba(0,0,0,0.05); border-radius: 8px; padding: 10px;")
            card_layout = QVBoxLayout(card)
            card_layout.addWidget(QLabel(f"Indicador {i+1}"))
            lbl_val = QLabel(f"$ {12000 * (i+1):,.2f}")
            lbl_val.setStyleSheet("font-size: 20px; font-weight: bold;")
            card_layout.addWidget(lbl_val)
            stats_layout.addWidget(card)
        content_layout.addLayout(stats_layout)
        
        # Tabla
        self.table = QTableWidget(10, 5)
        self.table.setHorizontalHeaderLabels(["ID", "Fecha", "Descripción", "Categoría", "Monto"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        
        for row in range(10):
            self.table.setItem(row, 0, QTableWidgetItem(f"TRX-{100+row}"))
            self.table.setItem(row, 1, QTableWidgetItem("2024-05-20"))
            self.table.setItem(row, 2, QTableWidgetItem("Pago de Servicios"))
            self.table.setItem(row, 3, QTableWidgetItem("Operativo"))
            self.table.setItem(row, 4, QTableWidgetItem(f"$ {row * 150}.00"))
        
        content_layout.addWidget(QLabel("Transacciones Recientes"))
        content_layout.addWidget(self.table)
        
        # Botones de Acción
        form_layout = QHBoxLayout()
        
        self.btn_primary = QPushButton("Nuevo Registro")
        self.btn_primary.setProperty("class", "primary")
        self.btn_primary.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_primary.setProperty("icon_name", "add") # Guardar nombre icono
        
        self.btn_secondary = QPushButton("Exportar")
        self.btn_secondary.setProperty("icon_name", "import_export") # Guardar nombre icono
        
        form_layout.addWidget(QLineEdit("Buscar transacción..."))
        form_layout.addWidget(self.btn_secondary)
        form_layout.addWidget(self.btn_primary)
        
        content_layout.addLayout(form_layout)
        main_layout.addWidget(content_area)
        
        # Estado inicial
        self.nav_buttons[0].setChecked(True)

    def change_theme(self, theme_name):
        """Aplica el tema y actualiza los iconos con el color correcto"""
        # 1. Aplicar CSS global
        theme_manager.apply_theme(QApplication.instance(), theme_name)
        
        # 2. Obtener colores específicos del tema seleccionado
        palette = THEMES[theme_name]
        sidebar_text_color = palette.get("sidebar_text", "#000000")
        accent_text_color = palette.get("accent_text", "#FFFFFF")
        fg_primary = palette.get("fg_primary", "#000000")
        
        # 3. Refrescar iconos del Sidebar (Color normal)
        # Nota: Para un sidebar avanzado, el icono "checked" debería cambiar de color
        # pero para empezar, usaremos el color de texto base del sidebar.
        for btn in self.nav_buttons:
            icon_name = btn.property("icon_name")
            if icon_name:
                IconManager.apply_icon_to_button(btn, icon_name, sidebar_text_color)
                
        # 4. Refrescar otros botones
        IconManager.apply_icon_to_button(self.btn_primary, "add", accent_text_color)
        IconManager.apply_icon_to_button(self.btn_secondary, "import_export", fg_primary)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Aplicar tema inicial
    theme_manager.apply_theme(app, "light")
    
    window = ThemePreviewWindow()
    # Forzar actualización inicial de iconos
    window.change_theme("light") 
    
    window.show()
    sys.exit(app.exec())