"""
Accounts Window for PROGRAIN 4.0/5.0

Super window for managing and viewing account transactions.
Supports both Project Mode (specific project) and Global Mode (all projects).
Features:
- Auto-date adjustment based on transaction history.
- PDF Export using specialized ReportGenerator.
- Global Category/Subcategory mapping fixed.
"""

from datetime import datetime, date
from typing import List, Dict, Any, Optional
import csv
import logging

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QPushButton, QLabel, QDateEdit, QMessageBox,
    QFileDialog, QAbstractItemView, QComboBox, QLineEdit, QSplitter, QMenu
)
from PyQt6.QtCore import Qt, QDate, QTimer
from PyQt6.QtGui import QAction

from progain4.services.firebase_client import FirebaseClient
# Importamos tu generador de reportes
try:
    from progain4.services.report_generator import ReportGenerator
    REPORT_GENERATOR_AVAILABLE = True
except ImportError:
    REPORT_GENERATOR_AVAILABLE = False
    logging.warning("ReportGenerator no encontrado en progain4.services.report_generator")

logger = logging.getLogger(__name__)


class AccountsWindow(QMainWindow):
    """
    Super window for viewing and managing account transactions.
    """
    
    def __init__(self, firebase_client: FirebaseClient, parent=None):
        super().__init__(parent)
        
        self.firebase_client = firebase_client
        self.proyecto_id: Optional[str] = None
        self.proyecto_nombre: str = ""
        self.cuenta_id: Optional[str] = None
        
        self.is_global = False
        
        # Data
        self.cuentas: List[Dict[str, Any]] = []
        self.transacciones: List[Dict[str, Any]] = []
        self.filtered_transactions: List[Dict[str, Any]] = []
        
        # Maps (ID -> Nombre)
        self.categorias_map: Dict[str, str] = {}
        self.subcategorias_map: Dict[str, str] = {}
        self.cuentas_map: Dict[str, str] = {}
        
        # Filter state
        self.filter_text: str = ""
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._apply_filters)
        
        # Window setup
        self.setWindowTitle("Gestión de Cuentas")
        self.setGeometry(100, 100, 1200, 700)
        
        self._init_ui()

    def set_global_mode(self):
        """Activa el modo global."""
        self.is_global = True
        self.proyecto_id = None
        self.setWindowTitle("Explorador Global de Cuentas (Todos los Proyectos)")
        self.title_label.setText("<h2>Movimientos Globales - Todas las Cuentas</h2>")
        
        # 1. Cargar Cuentas
        self._load_all_accounts_global()
        
        # 2. Cargar Categorías y Subcategorías GLOBALES (Corrección Importante)
        self._load_categorias_globales()
        
        self.refresh()

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        
        # Title
        self.title_label = QLabel("<h2>Gestión de Cuentas</h2>")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.title_label)
        
        # Controls
        controls_group = self._create_controls()
        main_layout.addWidget(controls_group)
        
        # Table
        table_group = self._create_transactions_table()
        main_layout.addWidget(table_group)
        
        # Export Buttons
        export_layout = QHBoxLayout()
        export_layout.addStretch()
        
        csv_button = QPushButton("📄 Exportar CSV")
        csv_button.clicked.connect(self._export_csv)
        export_layout.addWidget(csv_button)
        
        pdf_button = QPushButton("📑 Exportar PDF")
        pdf_button.clicked.connect(self._export_pdf)
        if not REPORT_GENERATOR_AVAILABLE:
            pdf_button.setEnabled(False)
            pdf_button.setToolTip("ReportGenerator no disponible")
        export_layout.addWidget(pdf_button)
        
        main_layout.addLayout(export_layout)
        central_widget.setLayout(main_layout)
        
    def _create_controls(self) -> QWidget:
        group = QGroupBox("Controles")
        layout = QVBoxLayout()
        
        # Account
        account_layout = QHBoxLayout()
        account_layout.addWidget(QLabel("Cuenta:"))
        self.account_combo = QComboBox()
        self.account_combo.setMinimumWidth(250)
        self.account_combo.currentIndexChanged.connect(self._on_account_changed)
        account_layout.addWidget(self.account_combo)
        account_layout.addStretch()
        layout.addLayout(account_layout)
        
        # Filters
        filter_layout = QHBoxLayout()
        
        filter_layout.addWidget(QLabel("Desde:"))
        self.fecha_desde_edit = QDateEdit()
        self.fecha_desde_edit.setCalendarPopup(True)
        self.fecha_desde_edit.setDisplayFormat("yyyy-MM-dd")
        self.fecha_desde_edit.setDate(QDate(QDate.currentDate().year(), 1, 1))
        self.fecha_desde_edit.dateChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.fecha_desde_edit)
        
        filter_layout.addWidget(QLabel("Hasta:"))
        self.fecha_hasta_edit = QDateEdit()
        self.fecha_hasta_edit.setCalendarPopup(True)
        self.fecha_hasta_edit.setDisplayFormat("yyyy-MM-dd")
        self.fecha_hasta_edit.setDate(QDate.currentDate())
        self.fecha_hasta_edit.dateChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.fecha_hasta_edit)
        
        filter_layout.addSpacing(20)
        
        filter_layout.addWidget(QLabel("Buscar:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Descripción, comentario...")
        self.search_edit.setMinimumWidth(200)
        self.search_edit.textChanged.connect(self._on_search_text_changed)
        self.search_edit.setClearButtonEnabled(True)
        filter_layout.addWidget(self.search_edit)
        
        filter_layout.addStretch()
        
        refresh_btn = QPushButton("🔄 Actualizar")
        refresh_btn.clicked.connect(self.refresh)
        filter_layout.addWidget(refresh_btn)
        
        layout.addLayout(filter_layout)
        group.setLayout(layout)
        return group
    
    def _create_transactions_table(self) -> QWidget:
        group = QGroupBox("Transacciones")
        layout = QVBoxLayout()
        
        self.summary_label = QLabel()
        self.summary_label.setStyleSheet("font-weight: bold; padding: 5px;")
        layout.addWidget(self.summary_label)
        
        self.trans_table = QTableWidget()
        self.trans_table.setColumnCount(7)
        self.trans_table.setHorizontalHeaderLabels([
            "Fecha", "Tipo", "Descripción", "Categoría", "Subcategoría", "Transferencia", "Monto"
        ])
        
        self.trans_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.trans_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.trans_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.trans_table.setAlternatingRowColors(True)
        
        self.trans_table.itemDoubleClicked.connect(self._on_transaction_double_clicked)
        self.trans_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.trans_table.customContextMenuRequested.connect(self._show_context_menu)
        
        header = self.trans_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        
        layout.addWidget(self.trans_table)
        group.setLayout(layout)
        return group
    
    def set_project(self, project_id: str, project_name: str):
        self.is_global = False
        self.proyecto_id = project_id
        self.proyecto_nombre = project_name
        self.title_label.setText(f"<h2>Gestión de Cuentas - {project_name}</h2>")
        self._load_accounts()
        self._load_categorias()
        
    def select_account(self, cuenta_id: Any):
        self.cuenta_id = str(cuenta_id) if cuenta_id else None
        for i in range(self.account_combo.count()):
            if str(self.account_combo.itemData(i)) == str(self.cuenta_id):
                self.account_combo.setCurrentIndex(i)
                break
        self.refresh()
    
    def refresh(self):
        if not self.is_global and not self.proyecto_id:
            return
        
        logger.info(f"Refrescando... (Global: {self.is_global}, Cuenta: {self.cuenta_id})")
        
        self._load_transactions()
        
        # Ajuste automático de fecha
        if self.transacciones:
            fechas_validas = []
            for t in self.transacciones:
                d = self._parse_date(t.get('fecha'))
                if d: fechas_validas.append(d)
            
            if fechas_validas:
                primera_fecha = min(fechas_validas)
                self.fecha_desde_edit.blockSignals(True)
                self.fecha_desde_edit.setDate(primera_fecha)
                self.fecha_desde_edit.blockSignals(False)

        self._apply_filters()
        
    def _load_accounts(self):
        if not self.proyecto_id: return
        try:
            self.cuentas = self.firebase_client.get_cuentas_by_proyecto(self.proyecto_id)
            self.cuentas_map = {str(c['id']): c['nombre'] for c in self.cuentas}
            self.account_combo.blockSignals(True)
            self.account_combo.clear()
            self.account_combo.addItem("Todas las cuentas", None)
            for cuenta in self.cuentas:
                self.account_combo.addItem(cuenta['nombre'], str(cuenta['id']))
            self.account_combo.blockSignals(False)
        except Exception as e:
            logger.error(f"Error loading accounts: {e}")

    def _load_all_accounts_global(self):
        try:
            if hasattr(self.firebase_client, 'get_cuentas_maestras'):
                self.cuentas = self.firebase_client.get_cuentas_maestras()
            else:
                self.cuentas = []
            
            # 🔍 Crear DOBLE MAPEO: doc.id → nombre Y cuenta_id → nombre
            self.cuentas_map = {}  # Mapeo mixto
            self. doc_id_to_cuenta_id = {}  # doc.id → cuenta_id numérico
            self.cuenta_id_to_doc_id = {}  # cuenta_id numérico → doc.id
            
            for c in self.cuentas:
                doc_id = str(c.get('id', ''))  # ID del documento (alfanumérico)
                nombre = c.get('nombre', 'Sin nombre')
                
                # Agregar por doc.id
                self.cuentas_map[doc_id] = nombre
                
                # Si tiene un campo cuenta_id numérico interno, agregarlo también
                # (Algunas cuentas antiguas pueden tener este campo)
                if 'cuenta_id' in c:
                    cuenta_id_num = str(c['cuenta_id'])
                    self.cuentas_map[cuenta_id_num] = nombre
                    self.doc_id_to_cuenta_id[doc_id] = cuenta_id_num
                    self.cuenta_id_to_doc_id[cuenta_id_num] = doc_id
                else:
                    # Si no tiene cuenta_id, usar el doc_id como fallback
                    self.cuentas_map[doc_id] = nombre
            
            logger.info(f"Cuentas globales:  {len(self.cuentas)} cuentas, {len(self.cuentas_map)} IDs mapeados")
            
            # Popular el combo
            self.account_combo.blockSignals(True)
            self.account_combo.clear()
            self.account_combo.addItem("Todas las cuentas (Global)", None)
            for c in self.cuentas:
                # Usar el doc. id como valor del combo
                self.account_combo.addItem(c.get('nombre', 'Sin nombre'), str(c.get('id')))
            self.account_combo.blockSignals(False)
            
        except Exception as e: 
            logger.error(f"Error loading global accounts: {e}")

    def _load_categorias(self):
        if not self.proyecto_id: return
        try:
            categorias = self.firebase_client.get_categorias_by_proyecto(self.proyecto_id)
            self.categorias_map = {str(c['id']): c['nombre'] for c in categorias}
            subcategorias = self.firebase_client.get_subcategorias_by_proyecto(self.proyecto_id)
            self.subcategorias_map = {str(s['id']): s['nombre'] for s in subcategorias}
        except Exception:
            pass

    # --- NUEVO MÉTODO PARA CARGAR CATEGORÍAS GLOBALES ---
    def _load_categorias_globales(self):
        """Carga todas las categorías y subcategorías del sistema para mapeo global."""
        try:
            # Categorías
            if hasattr(self.firebase_client, 'get_categorias'):
                cats = self.firebase_client.get_categorias()
                self.categorias_map = {str(c['id']): c.get('nombre', '') for c in cats}
            
            # Subcategorías
            if hasattr(self.firebase_client, 'get_subcategorias'):
                subcats = self.firebase_client.get_subcategorias()
                self.subcategorias_map = {str(s['id']): s.get('nombre', '') for s in subcats}
                
            logger.info(f"Mapas globales cargados: {len(self.categorias_map)} cats, {len(self.subcategorias_map)} subcats")
        except Exception as e:
            logger.error(f"Error loading global categories maps: {e}")

    def _load_transactions(self):
        try:
            if self.is_global:
                if hasattr(self.firebase_client, 'get_transacciones_globales'):
                    todas = self.firebase_client.get_transacciones_globales(limit=10000)
                else:
                    todas = []
                
                if self.cuenta_id:
                    # El combo devuelve doc.id (alfanumérico)
                    # Pero las transacciones tienen cuenta_id numérico
                    # Necesitamos buscar ambos
                    
                    logger.info(f"🔍 Filtrando por cuenta doc.id: {self. cuenta_id}")
                    
                    # Obtener el cuenta_id numérico si existe
                    cuenta_id_num = self.doc_id_to_cuenta_id.get(str(self.cuenta_id))
                    
                    logger.info(f"🔍 Cuenta ID numérico correspondiente: {cuenta_id_num}")
                    logger.info(f"🔍 Total transacciones globales: {len(todas)}")
                    
                    self. transacciones = []
                    for t in todas:
                        t_cuenta_id = str(t.get('cuenta_id', ''))
                        
                        # Comparar con ambos IDs
                        if t_cuenta_id == str(self.cuenta_id):  # Por doc.id
                            self. transacciones.append(t)
                        elif cuenta_id_num and t_cuenta_id == str(cuenta_id_num):  # Por cuenta_id numérico
                            self.transacciones.append(t)
                        # También verificar transferencias
                        elif t.get('es_transferencia'):
                            rel_id = str(t.get('transferencia_cuenta_relacionada', ''))
                            if rel_id == str(self.cuenta_id) or (cuenta_id_num and rel_id == str(cuenta_id_num)):
                                self.transacciones. append(t)
                    
                    logger.info(f"✅ Transacciones filtradas: {len(self.transacciones)}")
                    
                    # 🔍 DEBUG: Mostrar primeras 3 transacciones
                    if self.transacciones:
                        logger.info("📊 Primeras transacciones encontradas:")
                        for i, t in enumerate(self.transacciones[:3], 1):
                            logger. info(f"  {i}. Fecha: {t.get('fecha')} | Tipo: {t.get('tipo')} | Monto: {t. get('monto')} | CuentaID: {t.get('cuenta_id')}")
                    else:
                        logger.warning("⚠️ No se encontraron transacciones para esta cuenta")
                        # Debug: mostrar IDs de las primeras 5 transacciones
                        if todas:
                            logger.info("📋 IDs de cuenta en primeras 5 transacciones:")
                            for i, t in enumerate(todas[:5], 1):
                                logger.info(f"  {i}. cuenta_id: {t.get('cuenta_id')} | tipo: {t.get('tipo')}")
                else:
                    self.transacciones = todas
                    logger.info(f"✅ Modo global sin filtro: {len(self.transacciones)} transacciones")
            else:
                if not self.proyecto_id: 
                    return
                self.transacciones = self.firebase_client.get_transacciones_by_proyecto(
                    self.proyecto_id, cuenta_id=self.cuenta_id
                )
                logger.info(f"✅ Modo proyecto: {len(self.transacciones)} transacciones")
                
        except Exception as e: 
            logger.error(f"Error loading transactions: {e}", exc_info=True)
            self.transacciones = []

    def _on_account_changed(self, index: int):
        if index < 0: return
        self.cuenta_id = self.account_combo.itemData(index)
        self.refresh()
    
    def _on_search_text_changed(self, text: str):
        self.filter_text = text.lower().strip()
        self.search_timer.stop()
        self.search_timer.start(300)

    def _parse_date(self, date_val: Any) -> Optional[date]:
        if not date_val: return None
        if isinstance(date_val, datetime): return date_val.date()
        if isinstance(date_val, date): return date_val
        if isinstance(date_val, str):
            try: return datetime.strptime(date_val[:10], "%Y-%m-%d").date()
            except ValueError: return None
        return None

    def _apply_filters(self):
        if not self.transacciones:
            self.filtered_transactions = []
            self._update_table()
            return
        
        filtered = self.transacciones.copy()
        fecha_desde = self.fecha_desde_edit.date().toPyDate()
        fecha_hasta = self.fecha_hasta_edit.date().toPyDate()
        
        filtered_temp = []
        for t in filtered:
            t_date = self._parse_date(t.get('fecha'))
            if t_date and fecha_desde <= t_date <= fecha_hasta:
                filtered_temp.append(t)
        filtered = filtered_temp
        
        if self.filter_text:
            filtered = [
                t for t in filtered
                if (self.filter_text in t.get('descripcion', '').lower() or
                    self.filter_text in t.get('comentario', '').lower() or
                    self.filter_text in t.get('nota', '').lower())
            ]
        
        self.filtered_transactions = filtered
        self._update_table()
    
    def _update_table(self):
        self.trans_table.setRowCount(0)
        display_data = self.filtered_transactions
        
        if not display_data:
            self. summary_label.setText("No hay transacciones para mostrar")
            return
        
        # Calcular totales (excluyendo transferencias para evitar duplicación)
        total_ingresos = 0.0
        total_gastos = 0.0
        
        for t in display_data: 
            tipo = t.get('tipo', '').lower()
            monto = float(t.get('monto', 0))
            
            # Solo contar ingresos/gastos reales (no transferencias internas)
            if 'ingreso' in tipo: 
                total_ingresos += monto
            elif 'gasto' in tipo:
                total_gastos += monto
        
        balance = total_ingresos - total_gastos
        
        cuenta_nombre = self.cuentas_map.get(str(self.cuenta_id), "Seleccionada") if self.cuenta_id else "Todas"
        self.summary_label.setText(
            f"Vista: {cuenta_nombre} | "
            f"Items: {len(display_data)} | "
            f"Ingresos:  RD$ {total_ingresos:,.2f} | "
            f"Gastos:  RD$ {total_gastos:,.2f} | "
            f"Balance: RD$ {balance:,.2f}"
        )
        
        self. trans_table.setRowCount(len(display_data))
        
        for row, trans in enumerate(display_data):
            # Fecha
            fecha_str = str(trans.get('fecha', ''))
            self.trans_table.setItem(row, 0, QTableWidgetItem(fecha_str))
            
            # Tipo
            tipo_val = trans.get('tipo', '').capitalize().replace('_', ' ')
            item_tipo = QTableWidgetItem(tipo_val)
            if 'ingreso' in tipo_val.lower(): 
                item_tipo.setForeground(Qt.GlobalColor. darkGreen)
            elif 'gasto' in tipo_val.lower(): 
                item_tipo.setForeground(Qt.GlobalColor.darkRed)
            self.trans_table. setItem(row, 1, item_tipo)
            
            # Descripción
            desc = trans.get('descripcion', '')
            self.trans_table. setItem(row, 2, QTableWidgetItem(desc))
            
            # Categoría (ya usa el mapa global si estamos en modo global)
            cid = str(trans.get('categoria_id', ''))
            cat_nombre = self.categorias_map.get(cid, cid if cid != '0' else '')
            self.trans_table.setItem(row, 3, QTableWidgetItem(cat_nombre))
            
            # Subcategoría
            sid = str(trans. get('subcategoria_id', ''))
            sub_nombre = self.subcategorias_map. get(sid, '')
            self.trans_table.setItem(row, 4, QTableWidgetItem(sub_nombre))
            
            # Transferencia (soporta nuevo y viejo formato)
            tr_info = ""
            if trans.get('es_transferencia'):
                # Nuevo formato
                cuenta_rel = str(trans.get('transferencia_cuenta_relacionada', ''))
                tipo_transf = trans.get('transferencia_tipo', '')
                
                if cuenta_rel: 
                    nombre_rel = self.cuentas_map.get(cuenta_rel, f"Cuenta {cuenta_rel}")
                    if tipo_transf == 'salida':
                        tr_info = f"→ {nombre_rel}"
                    elif tipo_transf == 'entrada':
                        tr_info = f"← {nombre_rel}"
                    else:
                        tr_info = nombre_rel
            elif trans.get('transferencia'):
                # Formato antiguo (compatibilidad)
                if 'transferencia_origen' in trans: 
                    oid = str(trans['transferencia_origen'])
                    nombre_origen = self.cuentas_map.get(oid, oid)
                    tr_info = f"← {nombre_origen}"
                elif 'transferencia_destino' in trans:
                    did = str(trans['transferencia_destino'])
                    nombre_destino = self.cuentas_map.get(did, did)
                    tr_info = f"→ {nombre_destino}"
            
            self.trans_table.setItem(row, 5, QTableWidgetItem(tr_info))
            
            # Monto
            try: 
                m = float(trans. get('monto', 0))
            except: 
                m = 0.0
            
            item_m = QTableWidgetItem(f"RD$ {m:,.2f}")
            item_m.setTextAlignment(Qt.AlignmentFlag. AlignRight | Qt.AlignmentFlag.AlignVCenter)
            
            # Color según tipo
            if 'ingreso' in tipo_val.lower(): 
                item_m.setForeground(Qt.GlobalColor.darkGreen)
            elif 'gasto' in tipo_val.lower(): 
                item_m.setForeground(Qt.GlobalColor.darkRed)
            
            self.trans_table.setItem(row, 6, item_m)

    def _export_csv(self):
        if not self.filtered_transactions: return
        filename, _ = QFileDialog.getSaveFileName(self, "Guardar CSV", "reporte.csv", "CSV (*.csv)")
        if filename:
            try:
                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(["Fecha", "Tipo", "Descripción", "Monto"])
                    for t in self.filtered_transactions:
                        writer.writerow([t.get('fecha'), t.get('tipo'), t.get('descripcion'), t.get('monto')])
                QMessageBox.information(self, "Éxito", "CSV exportado.")
            except Exception as e:
                logger.error(str(e))

    def _export_pdf(self):
        if not self.filtered_transactions:
            QMessageBox.warning(self, "Exportar", "No hay datos para exportar.")
            return

        if not REPORT_GENERATOR_AVAILABLE:
            QMessageBox.critical(self, "Error", "Falta el módulo ReportGenerator.")
            return

        filename, _ = QFileDialog.getSaveFileName(
            self, "Guardar PDF", f"Reporte_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf", "PDF Files (*.pdf)"
        )
        
        if not filename:
            return

        try:
            # Preparar datos con nombres legibles
            data_export = []
            for t in self.filtered_transactions:
                row = t.copy()
                
                # Resolvemos nombres
                cid = str(t.get('categoria_id', ''))
                sid = str(t.get('subcategoria_id', ''))
                
                # Ahora self.categorias_map tendrá datos incluso en modo global
                row['Categoría'] = self.categorias_map.get(cid, cid if cid!='0' else '')
                row['Subcategoría'] = self.subcategorias_map.get(sid, '')
                
                tr_info = ""
                if t.get('transferencia'):
                    if 'transferencia_origen' in t:
                        oid = str(t['transferencia_origen'])
                        tr_info = f"De: {self.cuentas_map.get(oid, oid)}"
                    elif 'transferencia_destino' in t:
                        did = str(t['transferencia_destino'])
                        tr_info = f"A: {self.cuentas_map.get(did, did)}"
                row['Transferencia'] = tr_info
                
                clean_row = {
                    "Fecha": str(t.get('fecha', '')),
                    "Tipo": str(t.get('tipo', '')).capitalize(),
                    "Descripción": t.get('descripcion', ''),
                    "Categoría": row['Categoría'],
                    "Subcategoría": row['Subcategoría'],
                    "Transferencia": tr_info,
                    "Monto": t.get('monto', 0.0)
                }
                data_export.append(clean_row)

            cuenta_txt = self.account_combo.currentText()
            rango = f"{self.fecha_desde_edit.date().toString('dd/MM/yyyy')} - {self.fecha_hasta_edit.date().toString('dd/MM/yyyy')}"
            
            report = ReportGenerator(
                data=data_export,
                title=f"Reporte de Transacciones - {cuenta_txt}",
                project_name=self.proyecto_nombre or "Global",
                date_range=rango,
                currency_symbol="RD$"
            )
            
            success, msg = report.to_pdf(filename)
            
            if success:
                QMessageBox.information(self, "Éxito", f"PDF exportado correctamente:\n{filename}")
            else:
                QMessageBox.critical(self, "Error", f"No se pudo generar el PDF:\n{msg}")
                
        except Exception as e:
            logger.error(f"Error exportando PDF: {e}")
            QMessageBox.critical(self, "Error", f"Error inesperado:\n{str(e)}")

    def _on_transaction_double_clicked(self, item):
        row = item.row()
        display_data = self.filtered_transactions
        if row < 0 or row >= len(display_data): return
        
        trans = display_data[row]
        trans_id = trans.get('id', '')
        
        from progain4.ui.dialogs.transaction_dialog import TransactionDialog
        dialog = TransactionDialog(
            firebase_client=self.firebase_client,
            proyecto_id=self.proyecto_id,
            cuentas=self.cuentas,
            parent=self,
            transaction_id=trans_id,
        )
        if dialog.exec():
            self.refresh()

    def _show_context_menu(self, position):
        selected_items = self.trans_table.selectedItems()
        if not selected_items: return
        
        menu = QMenu(self)
        edit_action = QAction("✏️ Editar transacción", self)
        edit_action.triggered.connect(lambda: self._on_transaction_double_clicked(selected_items[0]))
        menu.addAction(edit_action)
        menu.exec(self.trans_table.viewport().mapToGlobal(position))