"""
Transactions Widget for PROGRAIN 4.0/5.0

Central widget displaying transactions table with filtering capabilities.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QLabel, QComboBox, QLineEdit, QToolBar, QMenu,
    QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QAction, QCursor
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

# Importamos el visor de adjuntos que creamos antes
try:
    from progain4.ui.dialogs.attachments_viewer_dialog import AttachmentsViewerDialog
    ATTACHMENTS_AVAILABLE = True
except ImportError:
    ATTACHMENTS_AVAILABLE = False

logger = logging.getLogger(__name__)


class TransactionsWidget(QWidget):
    """
    Widget for displaying and managing transactions.
    
    Displays transactions in a table with columns: 
    - Fecha (Date)
    - Tipo (Type:  Ingreso/Gasto)
    - Descripción (Description)
    - Categoría (Category)
    - Subcategoría (Subcategory)
    - Cuenta (Account)
    - Monto (Amount)
    - Adjuntos (Attachments)
    """
    
    # Signals
    transaction_selected = pyqtSignal(str)  # Emits transaction ID
    transaction_double_clicked = pyqtSignal(str)  # Emits transaction ID
    transaction_deleted = pyqtSignal(str)  # Emits transaction ID to delete
    
    def __init__(self, parent=None):
        super().__init__(parent)

        self.transactions_data:  List[Dict[str, Any]] = []  # All transactions (raw from Firebase)
        self.filtered_transactions: List[Dict[str, Any]] = []  # Filtered subset
        self.cuentas_map: Dict[str, str] = {}        # cuenta_id -> nombre
        self.categorias_map: Dict[str, str] = {}     # categoria_id -> nombre
        self. subcategorias_map: Dict[str, str] = {}  # subcategoria_id -> nombre

        # ✅ NUEVO: Filtro de cuenta (viene desde main_window cuando selecciona en sidebar/combo)
        self.filter_cuenta_id:  Optional[str] = None  # None = "Todas las cuentas"

        # Filter state
        self.filter_month: Optional[int] = None  # 1-12 or None for "Todos"
        self.filter_year: Optional[int] = None   # Year or None for "Todos"
        self.filter_text: str = ""               # Search text

        # Debounce timer for search input
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._apply_filters)

        self._init_ui()

    def set_subcategorias_map(self, subcategorias:  List[Dict[str, Any]]):
        """
        Set the subcategories mapping for display. 

        Args:
            subcategorias: List of subcategory dicts with 'id' and 'nombre'
        """
        self.subcategorias_map = {
            str(sub["id"]): sub.get("nombre", str(sub["id"])) for sub in subcategorias
        }

    def _init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create filter toolbar
        filter_toolbar = self._create_filter_toolbar()
        layout.addWidget(filter_toolbar)
        
        # Create table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        
        # Headers aligned with data
        self.table.setHorizontalHeaderLabels([
            "Fecha", "Tipo", "Descripción", "Categoría",
            "Subcategoría", "Cuenta", "Monto", "Adjuntos"
        ])
        
        # Table settings
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        
        # Header settings
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Fecha
        header.setSectionResizeMode(1, QHeaderView. ResizeMode.ResizeToContents)  # Tipo
        header.setSectionResizeMode(2, QHeaderView.ResizeMode. Stretch)           # Descripción
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Categoría
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Subcategoría
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Cuenta
        header.setSectionResizeMode(6, QHeaderView. ResizeMode.ResizeToContents)  # Monto
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)  # Adjuntos
        
        # ✅ Habilitar sorting clickeable en columnas
        self.table.setSortingEnabled(True)
        
        # Connect signals
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        
        layout.addWidget(self.table)
        self.setLayout(layout)

    def _create_filter_toolbar(self) -> QWidget:
        """Create the filter toolbar with month/year/search controls"""
        toolbar = QToolBar()
        toolbar.setMovable(False)
        
        # Month filter
        toolbar.addWidget(QLabel("Mes:"))
        self.month_combo = QComboBox()
        self.month_combo. setMinimumWidth(120)
        self.month_combo.addItem("Todos", None)
        months = [
            "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
        ]
        for i, month_name in enumerate(months, start=1):
            self.month_combo.addItem(month_name, i)
        self.month_combo.currentIndexChanged.connect(self._on_month_changed)
        toolbar.addWidget(self.month_combo)
        
        toolbar.addSeparator()
        
        # Year filter
        toolbar.addWidget(QLabel("Año:"))
        self.year_combo = QComboBox()
        self.year_combo.setMinimumWidth(100)
        self.year_combo.addItem("Todos", None)
        # We'll populate years dynamically when transactions are loaded
        self.year_combo.currentIndexChanged.connect(self._on_year_changed)
        toolbar.addWidget(self.year_combo)
        
        toolbar.addSeparator()
        
        # Search field
        toolbar.addWidget(QLabel("Buscar:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Descripción, comentario...")
        self.search_edit. setMinimumWidth(200)
        self.search_edit.textChanged.connect(self._on_search_text_changed)
        self.search_edit.setClearButtonEnabled(True)
        toolbar.addWidget(self.search_edit)
        
        return toolbar

    def _on_month_changed(self, index: int):
        """Handle month filter change"""
        self. filter_month = self.month_combo.itemData(index)
        logger.debug(f"Month filter changed to: {self.filter_month}")
        self._apply_filters()

    def _on_year_changed(self, index: int):
        """Handle year filter change"""
        self.filter_year = self.year_combo.itemData(index)
        logger.debug(f"Year filter changed to: {self.filter_year}")
        self._apply_filters()

    def _on_search_text_changed(self, text: str):
        """Handle search text change with debounce"""
        self.filter_text = text. lower().strip()
        # Debounce:  wait 300ms after last keystroke before filtering
        self.search_timer. stop()
        self.search_timer.start(300)

    def _parse_date(self, date_val: Any) -> Optional[datetime]:
        """Helper to parse date from either String (Firebase) or Datetime (SIEMPRE retorna offset-naive)"""
        if not date_val:
            return None
        
        # Si ya es datetime, eliminar timezone si lo tiene
        if isinstance(date_val, datetime):
            # Convertir a naive (sin timezone)
            if date_val.tzinfo is not None:
                return date_val.replace(tzinfo=None)
            return date_val
        
        # Si es string, parsear
        if isinstance(date_val, str):
            try:
                # Intenta parsear string YYYY-MM-DD
                # Tomar solo los primeros 10 chars para evitar problemas con horas
                dt = datetime.strptime(date_val[:10], "%Y-%m-%d")
                # Asegurar que es naive
                return dt.replace(tzinfo=None)
            except (ValueError, IndexError):
                return None
        
        return None

    def _apply_filters(self):
        """
        Apply all active filters to transactions. 
        
        ✅ CORREGIDO: Ya NO filtra por cuenta aquí (Firebase ya filtró).
        Solo aplica filtros de mes/año/búsqueda sobre los datos recibidos.
        """
        if not self.transactions_data:
            self.filtered_transactions = []
            self._populate_table()
            return
        
        filtered = self.transactions_data.copy()
        
        # ❌ ELIMINADO: Filtro de cuenta (Firebase ya trae filtrado)
        # Las transacciones en self.transactions_data YA vienen filtradas por cuenta
        
        # Apply month filter
        if self.filter_month is not None:
            filtered_temp = []
            for t in filtered:
                dt = self._parse_date(t.get('fecha'))
                if dt and dt.month == self.filter_month:
                    filtered_temp. append(t)
            filtered = filtered_temp
        
        # Apply year filter
        if self. filter_year is not None: 
            filtered_temp = []
            for t in filtered:
                dt = self._parse_date(t.get('fecha'))
                if dt and dt.year == self. filter_year:
                    filtered_temp.append(t)
            filtered = filtered_temp
        
        # Apply text search filter (search in descripcion and comentario)
        if self.filter_text:
            filtered = [
                t for t in filtered
                if (self.filter_text in t.get('descripcion', '').lower() or
                    self.filter_text in t.get('comentario', '').lower() or
                    self.filter_text in t.get('nota', '').lower())
            ]
        
        self.filtered_transactions = filtered
        logger.info(f"Filters applied: {len(self.filtered_transactions)}/{len(self.transactions_data)} transactions")
        self._populate_table()

    def set_cuentas_map(self, cuentas: List[Dict[str, Any]]):
        """Set the accounts mapping for display."""
        self.cuentas_map = {str(cuenta['id']): cuenta['nombre'] for cuenta in cuentas}
        
    def set_categorias_map(self, categorias: List[Dict[str, Any]]):
        """Set the categories mapping for display."""
        self.categorias_map = {str(cat['id']): cat['nombre'] for cat in categorias}
        
    def load_transactions(self, transactions: List[Dict[str, Any]]):
        """
        Load transactions into the table.
        
        ✅ IMPORTANTE: Las transacciones YA vienen filtradas por cuenta desde Firebase.
        Este método solo las recibe y aplica filtros adicionales (mes/año/búsqueda).
        """
        self.transactions_data = transactions
        self. filtered_transactions = transactions. copy()
        
        # Update year combo with years present in transactions
        self._update_year_combo()
        
        # Apply current filters (mes/año/búsqueda)
        self._apply_filters()

    def _update_year_combo(self):
        """Update year combo with years from loaded transactions"""
        # Extract unique years from transactions
        years = set()
        for trans in self.transactions_data:
            dt = self._parse_date(trans.get('fecha'))
            if dt:
                years.add(dt.year)
        
        # Sort years descending
        sorted_years = sorted(years, reverse=True)
        
        # Remember current selection
        current_year = self.year_combo.currentData()
        
        # Rebuild combo
        self.year_combo.blockSignals(True)
        self.year_combo.clear()
        self.year_combo.addItem("Todos", None)
        for year in sorted_years:
            self.year_combo.addItem(str(year), year)
        
        # Restore selection if possible
        if current_year is not None:
            for i in range(self.year_combo.count()):
                if self.year_combo.itemData(i) == current_year:
                    self.year_combo.setCurrentIndex(i)
                    break
        
        self. year_combo.blockSignals(False)
        
    def _populate_table(self):
        """Populate the table with filtered transaction data"""
        # ✅ Desactivar sorting temporalmente
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        
        display_data = self.filtered_transactions if hasattr(self, 'filtered_transactions') else self.transactions_data
        
        # Ordenar por fecha descendente
        if display_data:
            def safe_date_key(trans):
                dt = self._parse_date(trans.get('fecha'))
                return dt if dt else datetime(1900, 1, 1)
            
            display_data = sorted(display_data, key=safe_date_key, reverse=True)
        
        if not display_data:
            self.table.setSortingEnabled(True)
            return
        
        self.table.setRowCount(len(display_data))
        
        for row, trans in enumerate(display_data):
            # ✅ GUARDAR EL ID DE TRANSACCIÓN EN LA PRIMERA COLUMNA (oculto)
            trans_id = trans.get('id', '')
            
            # Fecha (Col 0)
            fecha_val = trans.get('fecha')
            if isinstance(fecha_val, str) and len(fecha_val) >= 10:
                fecha_str = fecha_val[:10]
            elif isinstance(fecha_val, datetime):
                fecha_str = fecha_val.strftime('%Y-%m-%d')
            else:
                fecha_str = "Sin fecha"
            
            fecha_item = QTableWidgetItem(fecha_str)
            fecha_item.setData(Qt.ItemDataRole.UserRole, trans_id)  # ✅ GUARDAR ID AQUÍ
            self.table.setItem(row, 0, fecha_item)
            
            # Tipo (Col 1)
            tipo = trans.get('tipo', '').capitalize()
            tipo_item = QTableWidgetItem(tipo)
            if 'ingreso' in tipo.lower():
                tipo_item.setForeground(Qt.GlobalColor.darkGreen)
            elif 'gasto' in tipo.lower():
                tipo_item.setForeground(Qt.GlobalColor. darkRed)
            self.table.setItem(row, 1, tipo_item)
            
            # Descripción (Col 2)
            descripcion = trans.get('descripcion', '')
            self.table.setItem(row, 2, QTableWidgetItem(descripcion))
            
            # Categoría (Col 3)
            categoria_id = str(trans.get('categoria_id', ''))
            categoria_nombre = self.categorias_map.get(
                categoria_id,
                categoria_id if categoria_id and categoria_id != 'None' else 'Sin categoría'
            )
            self.table.setItem(row, 3, QTableWidgetItem(categoria_nombre))

            # Subcategoría (Col 4)
            subcategoria_id = str(trans. get('subcategoria_id', ''))
            sub_nombre = self.subcategorias_map.get(subcategoria_id, '')
            self.table.setItem(row, 4, QTableWidgetItem(sub_nombre))

            # Cuenta (Col 5)
            cuenta_id = str(trans.get('cuenta_id', ''))
            cuenta_nombre = self.cuentas_map.get(cuenta_id, cuenta_id)
            self.table.setItem(row, 5, QTableWidgetItem(cuenta_nombre))
            
            # Monto (Col 6)
            try:
                monto = float(trans.get('monto', 0))
            except: 
                monto = 0.0
            
            monto_item = QTableWidgetItem(f"${monto: ,.2f}")
            monto_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 6, monto_item)
            
            # Adjuntos (Col 7)
            adjuntos = trans.get('adjuntos_paths', []) or trans.get('adjuntos', [])
            adjuntos_item = QTableWidgetItem()
            if adjuntos:
                count = len(adjuntos) if isinstance(adjuntos, list) else 1
                adjuntos_item.setText(f"📎 {count}")
                adjuntos_item.setToolTip(f"{count} archivo(s) adjunto(s)")
            else:
                adjuntos_item.setText("")
            adjuntos_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 7, adjuntos_item)
        
        # ✅ Reactivar sorting
        self.table. setSortingEnabled(True)

    def _on_selection_changed(self):
        """Handle selection change in table"""
        selected_rows = self.table.selectedItems()
        if selected_rows:
            row = selected_rows[0].row()
            
            # ✅ OBTENER ID DESDE EL ITEM
            fecha_item = self.table.item(row, 0)
            if fecha_item:
                trans_id = fecha_item.data(Qt.ItemDataRole.UserRole)
                if trans_id: 
                    self.transaction_selected.emit(trans_id)
                
    def _on_item_double_clicked(self, item):
        """Handle double-click on table item"""
        row = item.row()
        
        # ✅ OBTENER ID DESDE EL ITEM
        fecha_item = self. table.item(row, 0)
        if fecha_item: 
            trans_id = fecha_item.data(Qt.ItemDataRole.UserRole)
            if trans_id:
                self. transaction_double_clicked.emit(trans_id)

    def get_selected_transaction(self) -> Optional[Dict[str, Any]]:
        """Get the currently selected transaction."""
        selected_rows = self. table.selectedItems()
        if selected_rows:
            row = selected_rows[0].row()
            display_data = self.filtered_transactions if hasattr(self, 'filtered_transactions') else self.transactions_data
            if 0 <= row < len(display_data):
                return display_data[row]
        return None
        
    def refresh(self):
        """Refresh the table display"""
        self._populate_table()

    def _show_context_menu(self, position):
        """Show context menu on right-click"""
        selected_items = self.table.selectedItems()
        if not selected_items: 
            return
        
        row = selected_items[0].row()
        
        # ✅ OBTENER EL ID DE TRANSACCIÓN DESDE EL ITEM (columna 0)
        fecha_item = self.table.item(row, 0)
        if not fecha_item:
            return
        
        trans_id = fecha_item.data(Qt.ItemDataRole.UserRole)
        if not trans_id:
            logger.warning(f"No transaction ID found in row {row}")
            return
        
        # ✅ BUSCAR LA TRANSACCIÓN POR ID (no por índice)
        trans = next((t for t in self.transactions_data if t.get('id') == trans_id), None)
        if not trans:
            logger.warning(f"Transaction {trans_id} not found in data")
            return
        
        menu = QMenu(self)
        
        # EDITAR
        edit_action = QAction("✏️ Editar transacción", self)
        edit_action.triggered.connect(lambda: self. transaction_double_clicked. emit(trans_id))
        menu.addAction(edit_action)
        
        # ADJUNTOS
        has_attachments = bool(trans.get('adjuntos_paths') or trans.get('adjuntos'))
        view_attachments_action = QAction("📎 Ver adjuntos", self)
        view_attachments_action.setEnabled(has_attachments)
        view_attachments_action. triggered.connect(lambda: self._view_attachments(trans_id))
        menu.addAction(view_attachments_action)
        
        menu.addSeparator()
        
        # ELIMINAR
        delete_action = QAction("🗑️ Anular transacción", self)
        delete_action.triggered.connect(lambda: self._request_delete_transaction(trans_id))
        menu.addAction(delete_action)
        
        menu.exec(self.table.viewport().mapToGlobal(position))

    def _request_delete_transaction(self, trans_id: str):
        """
        Muestra confirmación y emite señal de borrado si el usuario acepta.
        La lógica real de borrado debe implementarse en MainWindow o donde se maneje la señal.
        """
        # Obtener información de la transacción para mostrar en el mensaje
        trans = next((t for t in self.transactions_data if t.get('id') == trans_id), None)
        
        if not trans:
            return
        
        # Preparar mensaje con detalles
        descripcion = trans.get('descripcion', 'Sin descripción')
        monto = trans.get('monto', 0)
        fecha = trans.get('fecha', '')
        if isinstance(fecha, str) and len(fecha) >= 10:
            fecha = fecha[:10]
        
        mensaje = f"""¿Está seguro de que desea anular esta transacción?

Fecha: {fecha}
Descripción: {descripcion}
Monto: ${monto:,.2f}

Esta acción no se puede deshacer."""
        
        reply = QMessageBox.question(
            self,
            "Confirmar Anulación",
            mensaje,
            QMessageBox.StandardButton. Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            logger.info(f"User confirmed deletion of transaction {trans_id}")
            # Emitir la señal para que MainWindow o el controlador maneje el borrado
            self. transaction_deleted.emit(trans_id)

    def _view_attachments(self, trans_id: str):
        """View attachments for a transaction (usando URLs públicas permanentes)"""
        logger.info(f"View attachments requested for transaction {trans_id}")
        
        try:
            # Obtener firebase_client y proyecto_id desde el padre (main_window)
            main_window = self.window()
            
            if not hasattr(main_window, 'firebase_client'):
                QMessageBox.critical(
                    self,
                    "Error",
                    "No se pudo acceder a Firebase. Reinicia la aplicación."
                )
                return
            
            if not hasattr(main_window, 'proyecto_id'):
                QMessageBox.critical(
                    self,
                    "Error",
                    "No hay proyecto seleccionado."
                )
                return
            
            firebase_client = main_window.firebase_client
            proyecto_id = str(main_window.proyecto_id)
            
            # ✅ Usar get_attachment_urls() que construye URLs públicas
            attachments = firebase_client.get_attachment_urls(
                proyecto_id=proyecto_id,
                transaccion_id=trans_id
            )
            
            if not attachments:
                QMessageBox. warning(
                    self,
                    "Sin adjuntos",
                    "Esta transacción no tiene archivos adjuntos."
                )
                return
            
            # Extraer solo las URLs para el diálogo
            adjuntos_urls = [att["url"] for att in attachments]
            
            # Abrir diálogo con URLs públicas (nunca expiran ✅)
            dlg = AttachmentsViewerDialog(adjuntos_urls, parent=self)
            dlg.exec()
            
            logger.info(f"Opened {len(adjuntos_urls)} attachments successfully")
            
        except Exception as e:
            logger.error(f"Error viewing attachments: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Error",
                f"Error al abrir adjuntos:\n{str(e)}"
            )

    def actualizar_combos_categorias(self, categorias: List[Dict], subcategorias: List[Dict]):
        """
        Actualiza los combos de categorías/subcategorías después de modificar las maestras.
        
        Args:
            categorias:  Lista de categorías maestras
            subcategorias: Lista de subcategorías maestras
        """
        # Guardar valores actuales seleccionados (si existen)
        cat_actual = self.combo_categoria.currentData() if hasattr(self, 'combo_categoria') else None
        sub_actual = self.combo_subcategoria.currentData() if hasattr(self, 'combo_subcategoria') else None
        
        # ✅ ACTUALIZAR COMBO DE CATEGORÍAS
        if hasattr(self, 'combo_categoria'):
            self.combo_categoria.blockSignals(True)  # Evitar eventos mientras actualizamos
            self.combo_categoria.clear()
            
            for cat in sorted(categorias, key=lambda x: x.get('nombre', '')):
                self.combo_categoria.addItem(cat['nombre'], cat['id'])
            
            # Intentar restaurar la selección anterior
            if cat_actual: 
                idx = self.combo_categoria.findData(cat_actual)
                if idx >= 0:
                    self.combo_categoria.setCurrentIndex(idx)
            
            self.combo_categoria.blockSignals(False)
        
        # ✅ ACTUALIZAR COMBO DE SUBCATEGORÍAS
        if hasattr(self, 'combo_subcategoria'):
            self.combo_subcategoria.blockSignals(True)
            self.combo_subcategoria.clear()
            
            # Filtrar subcategorías según la categoría actual
            if cat_actual:
                subs_filtradas = [s for s in subcategorias if s.get('categoria_id') == cat_actual]
            else:
                subs_filtradas = subcategorias
            
            for sub in sorted(subs_filtradas, key=lambda x: x.get('nombre', '')):
                self.combo_subcategoria.addItem(sub['nombre'], sub['id'])
            
            # Intentar restaurar la selección anterior
            if sub_actual:
                idx = self.combo_subcategoria.findData(sub_actual)
                if idx >= 0:
                    self.combo_subcategoria.setCurrentIndex(idx)
            
            self.combo_subcategoria.blockSignals(False)
        
        logger.info(f"✅ Combos actualizados:  {len(categorias)} categorías, {len(subcategorias)} subcategorías")