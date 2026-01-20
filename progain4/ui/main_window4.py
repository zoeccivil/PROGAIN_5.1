from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QListWidget, QComboBox, QToolBar, QPushButton, QMessageBox,
    QListWidgetItem, QSplitter, QMenuBar, QMenu, QApplication, QDialog
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QAction
from typing import Optional, List, Dict, Any
import logging
import sys
import os

from progain4.services.firebase_client import FirebaseClient
from progain4.services. config import ConfigManager

# Widgets y Diálogos
from progain4.ui.widgets.transactions_widget import TransactionsWidget
from progain4.ui.widgets.sidebar_widget import SidebarWidget
from progain4.ui.dialogs.transaction_dialog import TransactionDialog
from progain4.ui.dialogs.transfer_dialog import TransferDialog
from progain4.ui.dialogs.firebase_inspector_dialog import FirebaseInspectorDialog
from progain4.ui.reports.resumen_por_cuenta_report import ResumenPorCuentaReport
from progain4.ui.reports.detailed_date_report import DetailedDateReport
from progain4.ui.dialogs.project_dialog import ProjectDialog
from progain4.ui.reports.gastos_categoria_report import GastosPorCategoriaWindowFirebase
from progain4.ui.dialogs.gestion_cuentas_maestras_dialog import GestionCuentasMaestrasDialog
from progain4.ui.dialogs.gestion_cuentas_proyecto_dialog import GestionCuentasProyectoDialog
from progain4.ui.dialogs. gestion_categorias_maestras_dialog import GestionCategoriasMaestrasDialog
from progain4.ui.dialogs.gestion_categorias_proyecto_dialog import GestionCategoriasProyectoDialog
from progain4.ui.dialogs.gestion_subcategorias_proyecto_dialog import GestionSubcategoriasProyectoDialog
from progain4.ui.dialogs.gestion_presupuestos_dialog import GestionPresupuestosDialog
from progain4.ui.dialogs.gestion_presupuestos_subcategorias_dialog import GestionPresupuestosSubcategoriasDialog
from progain4.ui.dialogs. import_categories_dialog import ImportCategoriesDialog

# Dashboards
from progain4.ui.dashboards.dashboard_gastos_avanzado_window_firebase import (
    DashboardGastosAvanzadoWindowFirebase,
)
from progain4.ui.dashboards.dashboard_ingresos_vs_gastos_window_firebase import (
    DashboardIngresosVsGastosWindowFirebase,
)
from progain4.ui. dashboards.dashboard_global_cuentas_window_firebase import (
    DashboardGlobalCuentasWindowFirebase,
)

from progain4.ui.dialogs.auditoria_categorias_firebase_dialog import (
    AuditoriaCategoriasFirebaseDialog,
)

from progain4.ui.dialogs.importer_window_firebase import ImporterWindowFirebaseQt
from progain4.ui.widgets.cashflow_window import CashflowWindow
from progain4.ui.widgets.accounts_window import AccountsWindow
from progain4.ui.dialogs.firebase_config_dialog import FirebaseConfigDialog

# Theme manager
try:
    from progain4.ui.theme_manager_improved import theme_manager
    from progain4.ui.icon_manager import IconManager
    from progain4.ui.theme_constants import THEMES
    IMPROVED_THEME_AVAILABLE = True
except ImportError: 
    from progain4.ui import theme_manager
    IMPROVED_THEME_AVAILABLE = False

logger = logging.getLogger(__name__)

from PyQt6.QtCore import Qt, QSize, pyqtSignal  # ✅ Añadir pyqtSignal al import

class MainWindow4(QMainWindow):
    """
    Main application window for PROGRAIN 4.0/5.0.
    """
    
    # ✅ NUEVA SEÑAL: Emitida cuando el usuario cambia de proyecto
    project_changed = pyqtSignal(str, str)  # (proyecto_id, proyecto_nombre)

    def __init__(
        self,
        firebase_client: FirebaseClient,
        proyecto_id: str,
        proyecto_nombre: str,
        config_manager
    ):
        super().__init__()

        self.firebase_client = firebase_client
        self.proyecto_id = proyecto_id
        self.proyecto_nombre = proyecto_nombre
        self.proyecto_nombre_actual = proyecto_nombre
        
        # ✅ NUEVO: Guardar para acceso desde main_ynab
        self.current_proyecto_id = proyecto_id
        self.current_proyecto_nombre = proyecto_nombre
        
        # ✅ NUEVO: ConfigManager (now required parameter)
        self.config_manager = config_manager

        # Data
        self.cuentas:  List[Dict[str, Any]] = []
        self.categorias: List[Dict[str, Any]] = []
        self. subcategorias: List[Dict[str, Any]] = []
        self.current_cuenta_id: Optional[str] = None
        
        # Windows (for reuse)
        self.cashflow_window: Optional[CashflowWindow] = None
        self.accounts_window: Optional[AccountsWindow] = None
        
        # Actions References (para actualizar iconos dinámicamente)
        self.action_refresh = None
        self.action_add = None
        self.action_transfer = None
        
        # ✅ NUEVO: Undo/Redo actions and buttons
        self.undo_action = None
        self.redo_action = None
        self.undo_button = None
        self.redo_button = None

        # UI setup
        self.setWindowTitle(f"PROGRAIN 5.0 - {proyecto_nombre}")
        self.setGeometry(100, 100, 1200, 700)

        self._init_ui()
        
        # ✅ NUEVO: Initialize undo/redo manager after UI
        from progain4.services.undo_manager import UndoRedoManager
        self.undo_manager = UndoRedoManager(
            self.firebase_client,
            self.config_manager
        )
        
        # ✅ NUEVO: Setup undo/redo UI
        self._setup_undo_redo()
        
        self._load_projects()  # Load projects into combo
        self._load_initial_data()
        
        # Aplicar iconos iniciales según el tema actual (solo si está disponible)
        if IMPROVED_THEME_AVAILABLE:  
            current_theme = theme_manager.current_theme
            self._update_toolbar_icons(current_theme)

    # ------------------------------------------------------------------ UI INIT

    def _init_ui(self):
        """Initialize the user interface"""
        self._create_menu_bar()
        self._create_toolbar()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout()

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.accounts_sidebar = self._create_accounts_sidebar()
        splitter.addWidget(self.accounts_sidebar)

        self.transactions_widget = TransactionsWidget()
        self.transactions_widget.transaction_double_clicked.connect(self._edit_transaction)
        self.transactions_widget.transaction_deleted.connect(self._on_delete_transaction)
        splitter.addWidget(self.transactions_widget)

        splitter.setSizes([200, 1000])

        main_layout.addWidget(splitter)
        central_widget.setLayout(main_layout)

        self.statusBar().showMessage("Listo")

    def _create_menu_bar(self):
        """Create the menu bar"""
        menu_bar:  QMenuBar = self.menuBar()

        # ========== ARCHIVO MENU ==========
        archivo_menu: QMenu = menu_bar.addMenu("Archivo")

        action_cambiar_proyecto = QAction("Cambiar de proyecto.. .", self)
        if IMPROVED_THEME_AVAILABLE: 
            action_cambiar_proyecto.setIcon(IconManager.get_icon("settings"))
        action_cambiar_proyecto.triggered. connect(self._change_project)
        archivo_menu.addAction(action_cambiar_proyecto)

        archivo_menu.addSeparator()
        
        # NUEVO:  Configuración de Firebase
        action_config_firebase = QAction("⚙️ Configurar Firebase...", self)
        if IMPROVED_THEME_AVAILABLE: 
            action_config_firebase.setIcon(IconManager. get_icon("settings"))
        action_config_firebase.triggered. connect(self._open_firebase_config)
        archivo_menu. addAction(action_config_firebase)

        archivo_menu.addSeparator()

        action_salir = QAction("Salir", self)
        if IMPROVED_THEME_AVAILABLE: 
            action_salir.setIcon(IconManager.get_icon("close"))
        action_salir. triggered.connect(self.close)
        archivo_menu.addAction(action_salir)

        # ========== EDITAR MENU ==========
        editar_menu: QMenu = menu_bar.addMenu("Editar")
        
        # ✅ NUEVO: Undo/Redo actions
        self.undo_action = QAction("Deshacer", self)
        self.undo_action.setShortcut("Ctrl+Z")
        self.undo_action.triggered.connect(self._perform_undo)
        self.undo_action.setEnabled(False)
        editar_menu.addAction(self.undo_action)
        
        self.redo_action = QAction("Rehacer", self)
        self.redo_action.setShortcuts(["Ctrl+Y", "Ctrl+Shift+Z"])
        self.redo_action.triggered.connect(self._perform_redo)
        self.redo_action.setEnabled(False)
        editar_menu.addAction(self.redo_action)
        
        editar_menu.addSeparator()
        
        # ✅ NUEVO: History dialog
        action_history = QAction("Ver historial de cambios...", self)
        action_history.triggered.connect(self._show_undo_history)
        editar_menu.addAction(action_history)
        
        editar_menu.addSeparator()

        # Gestionar cuentas maestras
        action_cuentas_maestras = QAction("Gestionar cuentas maestras...", self)
        action_cuentas_maestras. triggered.connect(self._open_gestion_cuentas_maestras)
        editar_menu. addAction(action_cuentas_maestras)

        # Gestionar cuentas del proyecto
        action_cuentas_proyecto = QAction("Gestionar cuentas del proyecto...", self)
        action_cuentas_proyecto.triggered.connect(self._open_gestion_cuentas_proyecto)
        editar_menu.addAction(action_cuentas_proyecto)

        editar_menu.addSeparator()

        # Categorías maestras
        action_categorias_maestras = QAction("Gestionar categorías maestras.. .", self)
        action_categorias_maestras.triggered.connect(self._open_gestion_categorias_maestras)
        editar_menu.addAction(action_categorias_maestras)

        # Categorías del proyecto
        action_categorias_proyecto = QAction("Gestionar categorías del proyecto...", self)
        action_categorias_proyecto. triggered.connect(self._open_gestion_categorias_proyecto)
        editar_menu.addAction(action_categorias_proyecto)

        # Gestionar subcategorías del proyecto
        action_subcategorias_proyecto = QAction("Gestionar subcategorías del proyecto...", self)
        action_subcategorias_proyecto.triggered.connect(self._open_gestion_subcategorias_proyecto)
        editar_menu.addAction(action_subcategorias_proyecto)

        editar_menu.addSeparator()

        # ✅ NUEVO: Importar Categorías desde Otro Proyecto
        action_import_cats = QAction("📥 Importar Categorías desde Otro Proyecto...", self)
        if IMPROVED_THEME_AVAILABLE:
            action_import_cats.setIcon(IconManager.get_icon("import_export"))
        action_import_cats.triggered.connect(self._open_import_categorias)
        editar_menu.addAction(action_import_cats)

        editar_menu.addSeparator()
 
        # Gestionar presupuestos por categoría
        action_presupuestos = QAction("Gestionar presupuestos del proyecto...", self)
        action_presupuestos.triggered.connect(self._open_gestion_presupuestos)
        editar_menu.addAction(action_presupuestos)

        # Gestionar presupuestos por subcategoría
        action_presupuestos_sub = QAction("Gestionar presupuestos por subcategoría...", self)
        action_presupuestos_sub.triggered.connect(self._open_gestion_presupuestos_subcategorias)
        editar_menu.addAction(action_presupuestos_sub)

        # ========== VER MENU ==========
        ver_menu: QMenu = menu_bar.addMenu("Ver")

        # Theme submenu
        tema_menu = ver_menu.addMenu("Tema")
        if IMPROVED_THEME_AVAILABLE:
            tema_menu.setIcon(IconManager.get_icon("theme"))
        
        # Add theme options
        for theme_name in theme_manager.get_available_themes():
            action = QAction(theme_name. capitalize(), self)
            action. triggered.connect(lambda checked, t=theme_name: self._change_theme(t))
            tema_menu.addAction(action)

        # ========== REPORTES MENU ==========
        reportes_menu: QMenu = menu_bar.addMenu("Reportes")

        action_reporte_fecha = QAction("Reporte Detallado por Fecha...", self)
        if IMPROVED_THEME_AVAILABLE: 
            action_reporte_fecha.setIcon(IconManager.get_icon("reports"))
        action_reporte_fecha.triggered. connect(self._open_detailed_date_report)
        reportes_menu.addAction(action_reporte_fecha)

        action_gastos_cat = QAction("Reporte Gastos por Categoría...", self)
        action_gastos_cat.triggered. connect(self._abrir_reporte_gastos_categoria)
        reportes_menu.addAction(action_gastos_cat)

        reportes_menu.addSeparator()

        action_resumen_cuenta = QAction("Resumen por Cuenta...", self)
        action_resumen_cuenta.triggered. connect(self._open_account_summary_report)
        reportes_menu.addAction(action_resumen_cuenta)
       
        reportes_menu.addSeparator()

        action_global_accounts = QAction("🌎 Explorador Global de Cuentas...", self)
        if IMPROVED_THEME_AVAILABLE:
            action_global_accounts.setIcon(IconManager.get_icon("accounts"))
        action_global_accounts.triggered.connect(self._open_global_accounts_window)
        reportes_menu.addAction(action_global_accounts)

        # ========== DASHBOARDS MENU ==========
        dashboards_menu: QMenu = menu_bar. addMenu("Dashboards")

        action_dash_gastos = QAction("Gastos por Categoría...", self)
        if IMPROVED_THEME_AVAILABLE:
            action_dash_gastos.setIcon(IconManager.get_icon("dashboard"))
        action_dash_gastos. triggered.connect(self._open_dashboard_gastos_avanzado)
        dashboards_menu. addAction(action_dash_gastos)

        action_dash_ing_gas = QAction("Ingresos vs.  Gastos...", self)
        action_dash_ing_gas.triggered.connect(self._open_dashboard_ingresos_vs_gastos)
        dashboards_menu.addAction(action_dash_ing_gas)

        dashboards_menu.addSeparator()

        action_dash_global = QAction("Dashboard Global de Cuentas...", self)
        action_dash_global. triggered.connect(self._open_dashboard_global_cuentas)
        dashboards_menu.addAction(action_dash_global)

        # ========== HERRAMIENTAS MENU ==========
        herramientas_menu:  QMenu = menu_bar.addMenu("Herramientas")

        action_auditoria = QAction("Auditoría de Categorías/Subcategorías...", self)
        action_auditoria.triggered.connect(self._open_auditoria_categorias)
        herramientas_menu.addAction(action_auditoria)

        herramientas_menu.addSeparator()

        action_import_trans = QAction("Importar Transacciones...", self)
        if IMPROVED_THEME_AVAILABLE:
            action_import_trans.setIcon(IconManager.get_icon("import_export"))
        action_import_trans.triggered.connect(self._open_importar_transacciones)
        herramientas_menu.addAction(action_import_trans)

    def _create_toolbar(self):
        """Create the main toolbar"""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)
        
        # ✅ NUEVO: Save toolbar reference for undo/redo buttons
        self.toolbar = toolbar

        # Project selector combo
        toolbar.addWidget(QLabel("Proyecto:  "))
        self.project_combo = QComboBox()
        self.project_combo.setMinimumWidth(200)
        self.project_combo.currentIndexChanged.connect(self._on_project_selected)
        toolbar.addWidget(self.project_combo)

        toolbar.addSeparator()

        # Account filter combo
        toolbar.addWidget(QLabel("Cuenta: "))
        self.account_combo = QComboBox()
        self.account_combo.setMinimumWidth(200)
        self.account_combo.currentIndexChanged.connect(self._on_account_combo_changed)
        toolbar.addWidget(self.account_combo)

        toolbar.addSeparator()

        # Refresh button
        self.action_refresh = QAction("🔄 Actualizar", self)
        self.action_refresh.triggered.connect(self._refresh_transactions)
        toolbar.addAction(self.action_refresh)

        # Add transaction button
        self.action_add = QAction("➕ Nueva Transacción", self)
        self.action_add.triggered.connect(self._add_transaction)
        toolbar.addAction(self.action_add)
        
        # Transfer button
        self.action_transfer = QAction("🔄 Transferencia", self)
        self.action_transfer.triggered.connect(self._add_transfer)
        toolbar.addAction(self.action_transfer)
        
        toolbar.addSeparator()
        
        # ✅ NUEVO: Undo/Redo buttons (will be configured in _setup_undo_redo)
        self.undo_button = QAction("⏪ Deshacer", self)
        self.undo_button.triggered.connect(self._perform_undo)
        self.undo_button.setEnabled(False)
        toolbar.addAction(self.undo_button)
        
        self.redo_button = QAction("⏩ Rehacer", self)
        self.redo_button.triggered.connect(self._perform_redo)
        self.redo_button.setEnabled(False)
        toolbar.addAction(self.redo_button)

    def _create_accounts_sidebar(self) -> QWidget:
        """Create the modern sidebar with navigation and accounts"""
        self.sidebar = SidebarWidget()
        
        # Set project name
        self.sidebar.set_project_name(self.proyecto_nombre)
        
        # Connect signals
        self.sidebar.navigation_changed.connect(self._on_navigation_changed)
        self.sidebar.account_selected.connect(self._on_account_selected)
        self.sidebar.import_requested.connect(self._open_importar_transacciones)
        self.sidebar.auditoria_requested.connect(self._open_auditoria_categorias)
        
        return self.sidebar

    # ------------------------------------------------------------------ DATA LOAD

    def _load_projects(self):
        """Load available projects into the project selector combo"""
        if not hasattr(self. firebase_client, 'is_initialized') or not self.firebase_client.is_initialized():
            logger.warning("Firebase not initialized, cannot load projects")
            return
        
        try:
            logger.info("Loading projects for combo selector")
            proyectos_raw = self.firebase_client.get_proyectos()
            
            # Normalize results
            proyectos = []
            for p in proyectos_raw: 
                if hasattr(p, 'to_dict'):
                    data = p.to_dict() or {}
                    proj_id = p.id
                    proj_nombre = data.get('nombre', f'Proyecto {proj_id}')
                else:
                    proj_id = p.get('id', '')
                    proj_nombre = p. get('nombre', f'Proyecto {proj_id}')
                
                proyectos.append({'id': str(proj_id), 'nombre': proj_nombre})
            
            # ✅ CRÍTICO: Desconectar señal ANTES de poblar para evitar cambios no deseados
            self.project_combo.currentIndexChanged.disconnect(self._on_project_selected)
            
            # Populate combo
            self.project_combo.clear()
            for proyecto in proyectos:
                self.project_combo.addItem(proyecto['nombre'], proyecto['id'])
            
            # ✅ Select current project (usar current_proyecto_id, no proyecto_id)
            proyecto_id_actual = getattr(self, 'current_proyecto_id', self.proyecto_id)
            
            for i in range(self.project_combo. count()):
                if str(self.project_combo.itemData(i)) == str(proyecto_id_actual):
                    self.project_combo.setCurrentIndex(i)
                    break
            
            # ✅ RECONECTAR señal DESPUÉS de seleccionar
            self.project_combo.currentIndexChanged.connect(self._on_project_selected)
            
            logger.info(f"Loaded {len(proyectos)} projects into selector")
        
        except Exception as e:
            logger.error(f"Error loading projects: {e}")

    def _on_project_selected(self, index: int):
        """Handle project selection from combo"""
        if index < 0:
            return
        
        project_id = self. project_combo.itemData(index)
        project_name = self.project_combo.itemText(index)
        
        if not project_id or project_id == self.proyecto_id:
            return
        
        logger.info(f"Project changed to: {project_name} ({project_id})")
        
        # ✅ NUEVO: Clear undo/redo history on project change
        self._on_project_change_clear_history()
        
        # Update current project
        self.proyecto_id = project_id
        self.proyecto_nombre = project_name
        self.proyecto_nombre_actual = project_name
        
        # ✅ NUEVO: Actualizar variables para acceso externo
        self.current_proyecto_id = project_id
        self.current_proyecto_nombre = project_name
        
        # ✅ NUEVO: Emitir señal para que main_ynab guarde el proyecto
        self.project_changed.emit(str(project_id), str(project_name))
        
        # Update window title
        self.setWindowTitle(f"PROGRAIN 5.0 - {project_name}")
        
        # Update sidebar project name
        self.sidebar. set_project_name(project_name)
        
        # Reload all project data
        self._load_initial_data()

    def _load_initial_data(self):
        """Load initial data from Firebase"""
        logger.info(f"Loading data for project: {self.proyecto_id}")

        # Load accounts
        self.cuentas = self.firebase_client.get_cuentas_by_proyecto(self.proyecto_id)
        logger.info(f"Loaded {len(self.cuentas)} accounts")

        # Load categories
        self.categorias = self.firebase_client.get_categorias_by_proyecto(self. proyecto_id)
        logger.info(f"Loaded {len(self.categorias)} categories")

        # Load subcategories
        self.subcategorias = self.firebase_client. get_subcategorias_by_proyecto(self.proyecto_id)
        logger.info(f"Loaded {len(self.subcategorias)} subcategories")

        # Update UI
        self._populate_accounts()
        self. transactions_widget.set_cuentas_map(self.cuentas)
        self.transactions_widget.set_categorias_map(self. categorias)
        self.transactions_widget.set_subcategorias_map(self.subcategorias)

        # Load transactions
        self._refresh_transactions()

    def _populate_accounts(self):
        """Populate accounts in sidebar and combo"""
        # Update sidebar with accounts
        self.sidebar.set_accounts(self.cuentas)
        
        # Clear and populate combo
        self.account_combo.clear()
        
        # Add "All accounts" option
        self.account_combo.addItem("Todas las cuentas", None)
        
        # Add individual accounts
        for cuenta in self.cuentas:
            cuenta_id = cuenta. get("id")
            cuenta_nombre = cuenta.get("nombre", "Sin nombre")
            self.account_combo.addItem(cuenta_nombre, cuenta_id)
        
        logger.info(f"Populated {len(self.cuentas)} accounts in UI")

    # ------------------------------------------------------------------ ACCOUNT SELECTION

    def _on_account_selected(self, cuenta_id: Optional[str]):
        """Handle account selection from sidebar"""
        logger.info(f"Account selected from sidebar: {cuenta_id}")
        
        self.current_cuenta_id = cuenta_id
        self._refresh_transactions()
        
        # Sincronizar el combobox
        if cuenta_id:
            for i in range(self.account_combo.count()):
                if self.account_combo.itemData(i) == cuenta_id:
                    self.account_combo.setCurrentIndex(i)
                    break
        else:
            self.account_combo.setCurrentIndex(0)

    def _on_account_combo_changed(self, index: int):
        """Handle account selection in combo"""
        cuenta_id = self.account_combo.itemData(index)
        self. current_cuenta_id = cuenta_id
        
        # Sync with sidebar
        self.sidebar.select_account(cuenta_id)
        
        self._refresh_transactions()

    # ------------------------------------------------------------------ TRANSACTIONS

    def _refresh_transactions(self):
        """Refresh transactions from Firebase"""
        try:
            logger.info(f"Refreshing transactions (cuenta_id={self.current_cuenta_id})")

            transactions = self.firebase_client.get_transacciones_by_proyecto(
                self.proyecto_id,
                cuenta_id=self.current_cuenta_id,
            )

            self.transactions_widget.load_transactions(transactions)

            # Update status
            count = len(transactions)
            if self.current_cuenta_id:
                cuenta_nombre = next(
                    (c["nombre"] for c in self.cuentas if c["id"] == self.current_cuenta_id),
                    "Cuenta",
                )
                self.statusBar().showMessage(
                    f"Mostrando {count} transacciones de {cuenta_nombre}"
                )
            else:
                self.statusBar().showMessage(f"Mostrando {count} transacciones")

        except Exception as e:
            logger.error(f"Error refreshing transactions:  {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Error al cargar transacciones:\n{str(e)}",
            )

    def _add_transaction(self):
        """Handle add transaction action"""
        dialog = TransactionDialog(
            firebase_client=self.firebase_client,
            proyecto_id=self.proyecto_id,
            cuentas=self.cuentas,
            categorias=self. categorias,
            subcategorias=self.subcategorias,
            parent=self,
        )

        if dialog.exec():
            self._refresh_transactions()

    def _add_transfer(self):
        """Handle add transfer action"""
        if not self.proyecto_id: 
            QMessageBox.warning(
                self,
                "Transferencias",
                "Debe seleccionar un proyecto primero.",
            )
            return
        
        if len(self.cuentas) < 2:
            QMessageBox.warning(
                self,
                "Transferencias",
                "Necesita al menos 2 cuentas en el proyecto para crear transferencias.",
            )
            return
        
        dialog = TransferDialog(
            firebase_client=self.firebase_client,
            proyecto_id=self.proyecto_id,
            cuentas=self.cuentas,
            parent=self,
        )

        if dialog.exec():
            self._refresh_transactions()

    def _edit_transaction(self, trans_id: str):
        """Handle edit transaction action."""
        if not trans_id:
            return

        dialog = TransactionDialog(
            firebase_client=self.firebase_client,
            proyecto_id=self.proyecto_id,
            cuentas=self.cuentas,
            categorias=self.categorias,
            subcategorias=self.subcategorias,
            parent=self,
            transaction_id=trans_id,
        )

        if dialog.exec():
            self._refresh_transactions()

    def _on_delete_transaction(self, trans_id: str):
        """Handle transaction deletion request."""
        try:
            logger.info(f"Attempting to delete transaction {trans_id}")
            
            if not self.proyecto_id:
                QMessageBox.warning(
                    self, "Error", "No hay un proyecto seleccionado."
                )
                return
            
            success = self.firebase_client.delete_transaccion(
                self.proyecto_id,
                trans_id,
                soft_delete=True
            )
            
            if success:
                logger.info(f"Transaction {trans_id} deleted successfully")
                QMessageBox.information(
                    self,
                    "Transacción Anulada",
                    "La transacción ha sido anulada exitosamente."
                )
                self._refresh_transactions()
            else:
                logger.error(f"Failed to delete transaction {trans_id}")
                QMessageBox.critical(
                    self,
                    "Error",
                    "No se pudo anular la transacción.\nPor favor, intente nuevamente."
                )
                
        except Exception as e: 
            logger.error(f"Error deleting transaction {trans_id}: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Error al anular la transacción:\n{str(e)}"
            )

    # ------------------------------------------------------------------ PROJECTS

    def _change_project(self):
        """Handle changing to a different project."""
        try:
            proyectos = self.firebase_client.get_proyectos()
            if not proyectos:
                QMessageBox.warning(
                    self,
                    "Cambiar proyecto",
                    "No se encontraron proyectos en Firebase.",
                )
                return

            dialog = ProjectDialog(proyectos=proyectos, parent=self)
            if dialog.exec() != ProjectDialog.DialogCode.Accepted:
                return

            result = dialog.get_selected_project()
            if not result:
                return

            # Crear nuevo proyecto si es necesario
            if result[0] is None and len(result) == 3:
                _, nombre, descripcion = result
                proyecto_id = self.firebase_client.create_proyecto(nombre, descripcion)
                if not proyecto_id:
                    QMessageBox.critical(
                        self,
                        "Error",
                        "No se pudo crear el proyecto.  Verifique la conexión a Firebase.",
                    )
                    return
            else:
                proyecto_id, nombre = result[0], result[1]

            # ✅ NUEVO: Clear undo/redo history on project change
            self._on_project_change_clear_history()

            # Actualizar estado
            self.proyecto_id = proyecto_id
            self.proyecto_nombre = nombre
            self. proyecto_nombre_actual = nombre
            self.setWindowTitle(f"PROGRAIN 5.0 - {nombre}")

            self._load_initial_data()

        except Exception as e:
            logger.error("Error changing project: %s", e)
            QMessageBox.critical(
                self,
                "Error",
                f"Error al cambiar de proyecto:\n{str(e)}",
            )

    # ------------------------------------------------------------------ FIREBASE CONFIG

    def _open_firebase_config(self):
        """Abrir diálogo de configuración de Firebase."""
        from progain4.ui.dialogs.firebase_config_dialog import show_firebase_config_dialog
        
        config = ConfigManager()
        
        result = show_firebase_config_dialog(parent=self, config_manager=config)
        
        if result: 
            cred_path, bucket = result
            
            reply = QMessageBox.question(
                self,
                "Configuración actualizada",
                "La configuración de Firebase se actualizó correctamente.\n\n"
                "¿Desea reiniciar la aplicación ahora para aplicar los cambios?",
                QMessageBox.StandardButton.Yes | QMessageBox. StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                logger.info("Restarting application after Firebase config change")
                
                # Cerrar ventana actual
                self.close()
                
                # Reiniciar el proceso
                if getattr(sys, 'frozen', False):
                    # Si es ejecutable
                    os.execl(sys.executable, sys.executable)
                else:
                    # Si es script
                    python = sys.executable
                    os.execl(python, python, *sys.argv)

    # ------------------------------------------------------------------ REPORTS

    def _open_account_summary_report(self):
        """Open account summary report"""
        dialog = ResumenPorCuentaReport(
            firebase_client=self.firebase_client,
            proyecto_id=self.proyecto_id,
            proyecto_nombre=self.proyecto_nombre_actual,
            moneda="RD$",
            parent=self,
        )
        dialog.exec()

    def _open_detailed_date_report(self):
        """Open detailed date report"""
        dialog = DetailedDateReport(
            firebase_client=self.firebase_client,
            proyecto_id=self. proyecto_id,
            parent=self,
        )
        dialog.exec()

    def _abrir_reporte_gastos_categoria(self):
        """Open Gastos por Categoría report"""
        if not getattr(self, "proyecto_id", None):
            QMessageBox.warning(
                self,
                "Proyecto requerido",
                "Debe seleccionar un proyecto primero.",
            )
            return

        proyecto_nombre = getattr(self, "proyecto_nombre_actual", self.proyecto_nombre)

        ventana = GastosPorCategoriaWindowFirebase(
            self.firebase_client,
            self.proyecto_id,
            proyecto_nombre,
            moneda="RD$",
            parent=self,
        )
        ventana.show()

    # ------------------------------------------------------------------ GESTION DIALOGS

    def _open_gestion_cuentas_maestras(self):
        """Abrir gestión de cuentas maestras."""
        if not self.firebase_client.is_initialized():
            QMessageBox.warning(self, "Firebase", "Firebase no está inicializado.")
            return

        dialog = GestionCuentasMaestrasDialog(
            firebase_client=self.firebase_client,
            parent=self,
        )
        dialog.exec()
        self._load_initial_data()

    def _open_gestion_cuentas_proyecto(self):
        """Abrir gestión de cuentas del proyecto."""
        if not getattr(self, "proyecto_id", None):
            QMessageBox.warning(self, "Proyecto requerido", "Debe seleccionar un proyecto primero.")
            return

        if not self.firebase_client.is_initialized():
            QMessageBox.warning(self, "Firebase", "Firebase no está inicializado.")
            return

        dialog = GestionCuentasProyectoDialog(
            firebase_client=self.firebase_client,
            proyecto_id=self.proyecto_id,
            proyecto_nombre=self.proyecto_nombre_actual,
            parent=self,
        )
        if dialog.exec():
            self._load_initial_data()

    def _open_gestion_categorias_maestras(self):
        """Abrir gestión de categorías maestras."""
        if not self. firebase_client.is_initialized():
            QMessageBox.warning(self, "Firebase", "Firebase no está inicializado.")
            return

        dialog = GestionCategoriasMaestrasDialog(
            firebase_client=self.firebase_client,
            parent=self,
        )
        dialog.data_changed.connect(self._recargar_categorias_maestras)  # ✅ Conectar señal
        dialog.exec()
        self. categorias = self.firebase_client.get_categorias_by_proyecto(self.proyecto_id)
        self. subcategorias = self.firebase_client.get_subcategorias_by_proyecto(self.proyecto_id)
        self.transactions_widget.set_categorias_map(self.categorias)
        self.transactions_widget.set_subcategorias_map(self.subcategorias)


    def _recargar_categorias_maestras(self):
        """
        Recarga categorías y subcategorías maestras después de modificarlas. 
        Se ejecuta automáticamente al cerrar el diálogo de gestión con cambios.
        """
        try:
            logger.info("Recargando categorías y subcategorías maestras...")
            
            # Recargar desde Firebase
            self.categorias = self. firebase_client.get_categorias_maestras() or []
            self.subcategorias = self. firebase_client.get_subcategorias_maestras() or []
            
            logger.info(
                f"Loaded {len(self.categorias)} categories and "
                f"{len(self. subcategorias)} subcategories"
            )
            
            QMessageBox.information(
                self,
                "Actualización Completa",
                f"✅ Categorías maestras actualizadas correctamente\n\n"
                f"• Categorías: {len(self. categorias)}\n"
                f"• Subcategorías:  {len(self.subcategorias)}\n\n"
                f"Los cambios ya están disponibles.",
            )
            
        except Exception as e:
            logger. error(f"Error reloading master categories: {e}")
            QMessageBox.warning(
                self,
                "Error",
                f"No se pudieron recargar las categorías:\n{e}",
            )


    def _open_gestion_categorias_proyecto(self):
        """Abrir gestión de categorías del proyecto."""
        if not getattr(self, "proyecto_id", None):
            QMessageBox.warning(self, "Proyecto requerido", "Debe seleccionar un proyecto primero.")
            return

        dialog = GestionCategoriasProyectoDialog(
            firebase_client=self. firebase_client,
            proyecto_id=self.proyecto_id,
            proyecto_nombre=self. proyecto_nombre_actual,
            parent=self,
        )
        if dialog.exec():
            self. categorias = self.firebase_client.get_categorias_by_proyecto(self.proyecto_id)
            self.subcategorias = self.firebase_client.get_subcategorias_by_proyecto(self.proyecto_id)
            self.transactions_widget.set_categorias_map(self.categorias)
            self.transactions_widget.set_subcategorias_map(self.subcategorias)

    def _open_gestion_subcategorias_proyecto(self):
        """Abrir gestión de subcategorías del proyecto."""
        if not getattr(self, "proyecto_id", None):
            QMessageBox.warning(self, "Proyecto requerido", "Debe seleccionar un proyecto primero.")
            return

        if not self.firebase_client.is_initialized():
            QMessageBox.warning(self, "Firebase", "Firebase no está inicializado.")
            return

        dialog = GestionSubcategoriasProyectoDialog(
            firebase_client=self. firebase_client,
            proyecto_id=self.proyecto_id,
            proyecto_nombre=self. proyecto_nombre_actual,
            parent=self,
        )
        if dialog.exec():
            self.subcategorias = self. firebase_client.get_subcategorias_by_proyecto(self. proyecto_id)
            self.transactions_widget.set_subcategorias_map(self.subcategorias)

    def _open_gestion_presupuestos(self):
        """Abrir gestión de presupuestos."""
        if not getattr(self, "proyecto_id", None):
            QMessageBox.warning(self, "Proyecto requerido", "Debe seleccionar un proyecto primero.")
            return

        if not self.firebase_client.is_initialized():
            QMessageBox.warning(self, "Firebase", "Firebase no está inicializado.")
            return

        dialog = GestionPresupuestosDialog(
            firebase_client=self.firebase_client,
            proyecto_id=self.proyecto_id,
            proyecto_nombre=self.proyecto_nombre_actual,
            parent=self,
        )
        dialog.exec()

    def _open_gestion_presupuestos_subcategorias(self):
        """Abrir gestión de presupuestos por subcategoría."""
        if not getattr(self, "proyecto_id", None):
            QMessageBox.warning(self, "Proyecto requerido", "Debe seleccionar un proyecto primero.")
            return

        if not self.firebase_client.is_initialized():
            QMessageBox.warning(self, "Firebase", "Firebase no está inicializado.")
            return

        dialog = GestionPresupuestosSubcategoriasDialog(
            firebase_client=self.firebase_client,
            proyecto_id=self. proyecto_id,
            proyecto_nombre=self.proyecto_nombre_actual,
            parent=self,
        )
        dialog.exec()

    # ------------------------------------------------------------------ DASHBOARDS

    def _open_dashboard_gastos_avanzado(self):
        """Abrir dashboard de gastos."""
        if not getattr(self, "proyecto_id", None):
            QMessageBox.warning(self, "Proyecto requerido", "Debe seleccionar un proyecto primero.")
            return

        if not self.firebase_client.is_initialized():
            QMessageBox.warning(self, "Firebase", "Firebase no está inicializado.")
            return

        win = DashboardGastosAvanzadoWindowFirebase(
            firebase_client=self.firebase_client,
            proyecto_id=self.proyecto_id,
            proyecto_nombre=self.proyecto_nombre_actual,
            moneda="RD$",
            parent=self,
        )
        win.show()

    def _open_dashboard_ingresos_vs_gastos(self):
        """Abrir dashboard de ingresos vs gastos."""
        if not getattr(self, "proyecto_id", None):
            QMessageBox.warning(self, "Proyecto requerido", "Debe seleccionar un proyecto primero.")
            return

        if not self.firebase_client.is_initialized():
            QMessageBox. warning(self, "Firebase", "Firebase no está inicializado.")
            return

        win = DashboardIngresosVsGastosWindowFirebase(
            firebase_client=self.firebase_client,
            proyecto_id=self.proyecto_id,
            proyecto_nombre=self.proyecto_nombre_actual,
            moneda="RD$",
            parent=self,
        )
        win.show()

    def _open_dashboard_global_cuentas(self):
        """Abrir dashboard global de cuentas."""
        if not self.firebase_client.is_initialized():
            QMessageBox.warning(self, "Firebase", "Firebase no está inicializado.")
            return

        win = DashboardGlobalCuentasWindowFirebase(
            firebase_client=self.firebase_client,
            moneda="RD$",
            parent=self,
        )
        win.show()

    # ------------------------------------------------------------------ HERRAMIENTAS

    def _open_auditoria_categorias(self):
        """Abrir auditoría de categorías."""
        if not getattr(self, "proyecto_id", None):
            QMessageBox.warning(self, "Error", "No hay un proyecto activo.")
            return

        if not self.firebase_client.is_initialized():
            QMessageBox.warning(self, "Firebase", "Firebase no está inicializado.")
            return

        dlg = AuditoriaCategoriasFirebaseDialog(
            self.firebase_client,
            self.proyecto_id,
            self.proyecto_nombre_actual,
            "RD$",
            self,
        )
        dlg.exec()

    def _open_importar_transacciones(self):
        """Abrir importador de transacciones."""
        if not getattr(self, "proyecto_id", None):
            QMessageBox.warning(self, "Error", "No hay un proyecto activo.")
            return
        if not self.firebase_client.is_initialized():
            QMessageBox.warning(self, "Firebase", "Firebase no está inicializado.")
            return

        dlg = ImporterWindowFirebaseQt(
            parent=self,
            firebase_client=self.firebase_client,
            proyecto_id=self.proyecto_id,
            proyecto_nombre=self.proyecto_nombre_actual,
            moneda="RD$",
        )
        dlg.exec()
        self._refresh_transactions()

    # ------------------------------------------------------------------ NAVIGATION

    def _on_navigation_changed(self, item_key:  str):
        """Handle navigation item selection."""
        logger.info(f"Navigation changed to: {item_key}")
        
        if item_key == "dashboard":
            self._navigate_to_dashboard()
        elif item_key == "transactions":
            self._navigate_to_transactions()
        elif item_key == "cash_flow":
            self._navigate_to_cash_flow()
        elif item_key == "budget":
            self._navigate_to_budget()

    def _navigate_to_dashboard(self):
        """Navigate to Dashboard."""
        logger.info("Opening Dashboard")
        self._open_dashboard_gastos_avanzado()

    def _navigate_to_transactions(self):
        """Navigate to Transactions view."""
        logger.info("Navigating to Transactions")
        self. transactions_widget.setFocus()
        self._refresh_transactions()
        self.statusBar().showMessage("Vista de transacciones")

    def _navigate_to_cash_flow(self):
        """Navigate to Cash Flow."""
        logger.info("Opening Cash Flow")
        
        if not self.proyecto_id:
            QMessageBox.warning(self, "Flujo de Caja", "Debe seleccionar un proyecto primero.")
            return
        
        if self.cashflow_window is None:
            self.cashflow_window = CashflowWindow(
                firebase_client=self.firebase_client,
                parent=self,
            )
        
        self.cashflow_window.set_project(self.proyecto_id, self.proyecto_nombre_actual)
        
        from datetime import date
        today = date.today()
        self.cashflow_window.set_period(date(today.year, 1, 1), today)
        
        self.cashflow_window.refresh()
        self.cashflow_window.show()
        self.cashflow_window.raise_()
        self.cashflow_window.activateWindow()

    def _navigate_to_budget(self):
        """Navigate to Budget."""
        logger.info("Opening Budget management")
        self._open_gestion_presupuestos()

    # ------------------------------------------------------------------ THEME

    def _change_theme(self, theme_name: str):
        """Change application theme."""
        try:
            logger.info(f"Changing theme to: {theme_name}")
            
            app = QApplication.instance()
            if app:
                theme_manager. apply_theme(app, theme_name)
                
                config = ConfigManager()
                if config.set_theme(theme_name):
                    logger.info(f"Theme '{theme_name}' saved")
                else:
                    logger.warning(f"Failed to save theme '{theme_name}'")
                
                if IMPROVED_THEME_AVAILABLE:
                    self._update_toolbar_icons(theme_name)
                
                self.statusBar().showMessage(f"Tema cambiado a: {theme_name. capitalize()}")
                logger.info(f"Theme changed to: {theme_name}")
            else:
                logger. error("Could not get QApplication instance")
                QMessageBox.warning(self, "Error", "No se pudo cambiar el tema.")
        except Exception as e:
            logger.error(f"Error changing theme: {e}")
            QMessageBox.critical(self, "Error", f"Error al cambiar el tema:\n{str(e)}")
            
    def _update_toolbar_icons(self, theme_name):
        """Update toolbar icons based on theme."""
        if not IMPROVED_THEME_AVAILABLE: 
            return
            
        try:
            palette = THEMES. get(theme_name, THEMES['light'])
            icon_color = palette.get('sidebar_text', '#000000')
            
            if self.action_refresh: 
                self.action_refresh. setIcon(IconManager.get_icon("refresh", icon_color))
            if self.action_add: 
                self.action_add. setIcon(IconManager.get_icon("add", icon_color))
            if self.action_transfer:
                self.action_transfer.setIcon(IconManager.get_icon("transactions", icon_color))
                
        except Exception as e:
            logger.warning(f"Could not update toolbar icons: {e}")

    def _open_global_accounts_window(self):
        """Abrir explorador global de cuentas."""
        if not self.firebase_client.is_initialized():
            QMessageBox.warning(self, "Error", "Firebase no está conectado.")
            return

        from progain4.ui.widgets.accounts_window import AccountsWindow
        
        global_win = AccountsWindow(self.firebase_client, parent=self)
        if hasattr(global_win, 'set_global_mode'):
            global_win.set_global_mode()
        
        global_win.setAttribute(Qt. WidgetAttribute.WA_DeleteOnClose)
        global_win.show()

    def _open_import_categorias(self):
        """Open dialog to import categories from another project."""
        if not self.proyecto_id:
            QMessageBox.warning(self, "Sin Proyecto", "Debe seleccionar un proyecto primero.")
            return
        
        try:
            dlg = ImportCategoriesDialog(
                firebase_client=self.firebase_client,
                proyecto_actual_id=self.proyecto_id,
                parent=self
            )
            
            if dlg.exec() == QDialog.DialogCode.Accepted:
                # Recargar categorías en la UI
                logger.info("Categories imported successfully, refreshing UI")
                # Recargar categorías y subcategorías
                self.categorias = self.firebase_client. get_categorias_by_proyecto(self.proyecto_id)
                self.subcategorias = self.firebase_client.get_subcategorias_by_proyecto(self.proyecto_id)
                
                # Refrescar transacciones para que vean las nuevas categorías
                self._refresh_transactions()
        
        except Exception as e:
            logger.error(f"Error opening import dialog: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Error al abrir diálogo:\n{str(e)}")

    # ==================== UNDO/REDO METHODS ====================
    
    def _setup_undo_redo(self):
        """Setup undo/redo shortcuts and initial state."""
        from PyQt6.QtGui import QShortcut, QKeySequence
        
        # Additional keyboard shortcuts (beyond menu items)
        undo_shortcut = QShortcut(QKeySequence.StandardKey.Undo, self)
        undo_shortcut.activated.connect(self._perform_undo)
        
        redo_shortcut1 = QShortcut(QKeySequence.StandardKey.Redo, self)
        redo_shortcut1.activated.connect(self._perform_redo)
        
        redo_shortcut2 = QShortcut(QKeySequence("Ctrl+Shift+Z"), self)
        redo_shortcut2.activated.connect(self._perform_redo)
        
        # Update initial state
        self._update_undo_redo_state()
    
    def _perform_undo(self):
        """Perform undo operation."""
        if self.undo_manager.undo(parent_widget=self):
            self._refresh_current_view()
            self._update_undo_redo_state()
            # Get the description of what was redone (it's now in redo stack)
            desc = self.undo_manager.get_redo_description()
            self.statusBar().showMessage(f"✅ Deshecho: {desc}", 3000)
        else:
            if not self.undo_manager.can_undo():
                self.statusBar().showMessage("No hay acciones para deshacer", 2000)
    
    def _perform_redo(self):
        """Perform redo operation."""
        if self.undo_manager.redo(parent_widget=self):
            self._refresh_current_view()
            self._update_undo_redo_state()
            # Get the description of what was undone (it's now in undo stack)
            desc = self.undo_manager.get_undo_description()
            self.statusBar().showMessage(f"✅ Rehecho: {desc}", 3000)
        else:
            if not self.undo_manager.can_redo():
                self.statusBar().showMessage("No hay acciones para rehacer", 2000)
    
    def _update_undo_redo_state(self):
        """Update the enabled/disabled state and text of undo/redo actions."""
        can_undo = self.undo_manager.can_undo()
        can_redo = self.undo_manager.can_redo()
        
        # Update menu actions
        if self.undo_action:
            self.undo_action.setEnabled(can_undo)
            if can_undo:
                desc = self.undo_manager.get_undo_description()
                # Truncate description if too long
                if len(desc) > 50:
                    desc = desc[:50] + "..."
                self.undo_action.setText(f"Deshacer: {desc}")
            else:
                self.undo_action.setText("Deshacer")
        
        if self.redo_action:
            self.redo_action.setEnabled(can_redo)
            if can_redo:
                desc = self.undo_manager.get_redo_description()
                # Truncate description if too long
                if len(desc) > 50:
                    desc = desc[:50] + "..."
                self.redo_action.setText(f"Rehacer: {desc}")
            else:
                self.redo_action.setText("Rehacer")
        
        # Update toolbar buttons
        if self.undo_button:
            self.undo_button.setEnabled(can_undo)
            if can_undo:
                desc = self.undo_manager.get_undo_description()
                self.undo_button.setToolTip(f"Deshacer: {desc}")
            else:
                self.undo_button.setToolTip("Deshacer (Ctrl+Z)")
        
        if self.redo_button:
            self.redo_button.setEnabled(can_redo)
            if can_redo:
                desc = self.undo_manager.get_redo_description()
                self.redo_button.setToolTip(f"Rehacer: {desc}")
            else:
                self.redo_button.setToolTip("Rehacer (Ctrl+Y)")
    
    def _show_undo_history(self):
        """Show the undo history dialog."""
        from progain4.ui.dialogs.undo_history_dialog import UndoHistoryDialog
        dialog = UndoHistoryDialog(self.undo_manager, self)
        dialog.exec()
    
    def _refresh_current_view(self):
        """Refresh the current view after undo/redo."""
        # Refresh transactions display
        self._refresh_transactions()
        
        # Refresh sidebar if needed
        if hasattr(self, 'sidebar'):
            self.sidebar.refresh()
    
    def _on_project_change_clear_history(self):
        """Clear undo/redo history when changing projects."""
        if hasattr(self, 'undo_manager'):
            self.undo_manager.clear()
            self._update_undo_redo_state()
            logger.info("Cleared undo/redo history on project change")