"""
Cash Flow Window for PROGRAIN 4.0/5.0

Displays cash flow summary per project with:
- Summary by account (total income, expenses, balance)
- Summary by month (income, expenses, balance)
- Date range filters
- CSV/PDF export capabilities
"""

from datetime import datetime, date
from typing import List, Dict, Any, Optional
from collections import defaultdict
import csv
import logging

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QPushButton, QLabel, QDateEdit, QMessageBox,
    QFileDialog, QAbstractItemView
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor

from progain4.services.firebase_client import FirebaseClient

# Importar el generador de reportes
try:
    from progain4.services.report_generator import ReportGenerator
    REPORT_GENERATOR_AVAILABLE = True
except ImportError: 
    REPORT_GENERATOR_AVAILABLE = False

logger = logging. getLogger(__name__)


class CashflowWindow(QMainWindow):
    """
    Cash flow window for displaying income/expense summaries by account and month.
    Similar to YNAB/market apps. 
    """
    
    def __init__(self, firebase_client: FirebaseClient, parent=None):
        super().__init__(parent)
        
        self.firebase_client = firebase_client
        self.proyecto_id:  Optional[str] = None
        self.proyecto_nombre: str = ""
        self.fecha_inicio: Optional[date] = None
        self.fecha_fin: Optional[date] = None
        
        # Data storage
        self.transacciones: List[Dict[str, Any]] = []
        self.cuentas_map: Dict[str, str] = {}
        
        # Window setup
        self.setWindowTitle("Flujo de Caja")
        self.resize(1000, 700)
        
        self._init_ui()
        
    def _init_ui(self):
        """Initialize the user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        
        # Title
        self.title_label = QLabel("<h2>Flujo de Caja</h2>")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self. title_label)
        
        # Date range controls
        date_group = self._create_date_controls()
        main_layout.addWidget(date_group)
        
        # Summary by account
        account_group = self._create_account_summary_table()
        main_layout.addWidget(account_group)
        
        # Summary by month
        month_group = self._create_month_summary_table()
        main_layout.addWidget(month_group)
        
        # Export buttons
        export_layout = QHBoxLayout()
        export_layout.addStretch()
        
        csv_button = QPushButton("ðŸ“„ Exportar CSV")
        csv_button.clicked.connect(self._export_csv)
        export_layout.addWidget(csv_button)
        
        pdf_button = QPushButton("ðŸ“‘ Exportar PDF")
        pdf_button.clicked.connect(self._export_pdf)
        if not REPORT_GENERATOR_AVAILABLE:
            pdf_button.setEnabled(False)
            pdf_button.setToolTip("ReportGenerator no disponible")
        export_layout. addWidget(pdf_button)
        
        main_layout.addLayout(export_layout)
        
        central_widget.setLayout(main_layout)
        
    def _create_date_controls(self) -> QWidget:
        """Create date range filter controls"""
        group = QGroupBox("Rango de Fechas")
        layout = QHBoxLayout()
        
        # Start date
        layout.addWidget(QLabel("Desde:"))
        self.fecha_inicio_edit = QDateEdit()
        self.fecha_inicio_edit.setCalendarPopup(True)
        self.fecha_inicio_edit. setDisplayFormat("yyyy-MM-dd")
        # Default:  first day of current year
        today = QDate.currentDate()
        self.fecha_inicio_edit.setDate(QDate(today.year(), 1, 1))
        layout.addWidget(self.fecha_inicio_edit)
        
        layout.addSpacing(20)
        
        # End date
        layout.addWidget(QLabel("Hasta:"))
        self.fecha_fin_edit = QDateEdit()
        self.fecha_fin_edit.setCalendarPopup(True)
        self.fecha_fin_edit. setDisplayFormat("yyyy-MM-dd")
        self.fecha_fin_edit.setDate(today)
        layout.addWidget(self.fecha_fin_edit)
        
        layout.addSpacing(20)
        
        # Refresh button
        refresh_btn = QPushButton("ðŸ”„ Actualizar")
        refresh_btn.clicked.connect(self._on_refresh_clicked)
        layout.addWidget(refresh_btn)
        
        layout.addStretch()
        
        group.setLayout(layout)
        return group
    
    def _create_account_summary_table(self) -> QWidget:
        """Create account summary table"""
        group = QGroupBox("Resumen por Cuenta")
        layout = QVBoxLayout()
        
        self.account_table = QTableWidget()
        self.account_table.setColumnCount(4)
        self.account_table.setHorizontalHeaderLabels([
            "Cuenta", "Total Ingresos", "Total Gastos", "Balance"
        ])
        
        # Table settings
        self.account_table. setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.account_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.account_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.account_table. setAlternatingRowColors(True)
        
        # Header settings
        header = self.account_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode. Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        
        layout.addWidget(self.account_table)
        group.setLayout(layout)
        return group
    
    def _create_month_summary_table(self) -> QWidget:
        """Create monthly summary table"""
        group = QGroupBox("Resumen por Mes")
        layout = QVBoxLayout()
        
        self.month_table = QTableWidget()
        self.month_table.setColumnCount(4)
        self.month_table. setHorizontalHeaderLabels([
            "Mes/AÃ±o", "Ingresos", "Gastos", "Balance"
        ])
        
        # Table settings
        self.month_table.setSelectionBehavior(QAbstractItemView. SelectionBehavior.SelectRows)
        self.month_table.setSelectionMode(QAbstractItemView.SelectionMode. SingleSelection)
        self.month_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.month_table.setAlternatingRowColors(True)
        
        # Header settings
        header = self. month_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView. ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        
        layout.addWidget(self. month_table)
        group.setLayout(layout)
        return group
    
    def set_project(self, project_id: str, project_name: str):
        """Set the current project."""
        self.proyecto_id = project_id
        self.proyecto_nombre = project_name
        self.title_label.setText(f"<h2>Flujo de Caja - {project_name}</h2>")
        
        # Load accounts for this project
        self._load_accounts()
        self. refresh()

    def set_period(self, start:  date, end: date):
        """
        Establece el rango de fechas y actualiza la UI.
        MÃ©todo requerido por MainWindow4.
        """
        self. fecha_inicio = start
        self.fecha_fin = end
        
        # Actualizar controles UI (bloqueando seÃ±ales para evitar doble carga)
        self.fecha_inicio_edit.blockSignals(True)
        self.fecha_fin_edit.blockSignals(True)
        
        self.fecha_inicio_edit.setDate(QDate(start.year, start.month, start.day))
        self.fecha_fin_edit.setDate(QDate(end.year, end.month, end.day))
        
        self.fecha_inicio_edit.blockSignals(False)
        self.fecha_fin_edit.blockSignals(False)
        
        # Refrescar datos con nuevas fechas
        self. refresh()

    def _parse_date(self, date_val: Any) -> Optional[date]:
        """Helper para parsear fechas de Firebase."""
        if not date_val:  
            return None
        try:
            if isinstance(date_val, datetime): 
                return date_val.date()
            if isinstance(date_val, date): 
                return date_val
            if isinstance(date_val, str):
                return datetime.strptime(date_val[: 10], "%Y-%m-%d").date()
        except ValueError:  
            return None
        return None

    def refresh(self):
        """Refresh data and update tables."""
        if not self.proyecto_id:
            logger.warning("No project set, cannot refresh")
            return
        
        # Leer fechas de la UI
        q_inicio = self.fecha_inicio_edit.date()
        q_fin = self.fecha_fin_edit.date()
        
        self.fecha_inicio = date(q_inicio.year(), q_inicio.month(), q_inicio.day())
        self.fecha_fin = date(q_fin.year(), q_fin.month(), q_fin.day())
        
        logger.info(f"Refreshing cashflow for project {self.proyecto_id}")
        
        # Cargar transacciones
        self._load_transactions()
        
        # Actualizar tablas
        self._update_account_summary()
        self._update_month_summary()
        
    def _load_accounts(self):
        """Load accounts for the current project"""
        if not self.proyecto_id:  
            return
        try:
            cuentas = self.firebase_client.get_cuentas_by_proyecto(self.proyecto_id)
            self.cuentas_map = {str(c['id']): c['nombre'] for c in cuentas}
        except Exception as e: 
            logger.error(f"Error loading accounts: {e}")
            self.cuentas_map = {}
    
    def _load_transactions(self):
        """Load transactions for the current project and period (Filter in Memory)"""
        if not self. proyecto_id:  
            return
        
        try:
            logger.info(f"Loading transactions for project {self.proyecto_id}, period: {self.fecha_inicio} to {self.fecha_fin}")
            
            # Get ALL transactions for the project
            all_trans = self. firebase_client.get_transacciones_by_proyecto(
                self.proyecto_id, 
                cuenta_id=None,
                include_deleted=False
            )
            
            logger.info(f"Retrieved {len(all_trans)} total transactions from project")
            
            # Filter by date range in Python
            self.transacciones = []
            for trans in all_trans: 
                trans_date = self._parse_date(trans.get('fecha'))
                if trans_date and self.fecha_inicio <= trans_date <= self.fecha_fin:
                    self.transacciones. append(trans)
            
            logger.info(f"Filtered to {len(self.transacciones)} transactions in period {self.fecha_inicio} to {self.fecha_fin}")
            
        except Exception as e:  
            logger.error(f"Error loading transactions: {e}", exc_info=True)
            self.transacciones = []
    
    def _update_account_summary(self):
        """Update account summary table (includes transfers per account, excludes from total)"""
        account_summary = defaultdict(lambda:  {'ingresos': 0.0, 'gastos': 0.0})
        
        # Para el total general (sin transferencias)
        total_real = {'ingresos': 0.0, 'gastos': 0.0}
        
        for trans in self.transacciones:
            cuenta_id = str(trans.get('cuenta_id', ''))
            try:  
                monto = float(trans.get('monto', 0.0))
            except:  
                monto = 0.0
            tipo = str(trans.get('tipo', '')).lower()
            es_transferencia = trans.get('es_transferencia') == True
            
            # âœ… Contar en la cuenta individual (incluye transferencias)
            if 'ingreso' in tipo:  
                account_summary[cuenta_id]['ingresos'] += monto
                # Solo contar en total si NO es transferencia
                if not es_transferencia:
                    total_real['ingresos'] += monto
            elif 'gasto' in tipo:
                account_summary[cuenta_id]['gastos'] += monto
                # Solo contar en total si NO es transferencia
                if not es_transferencia:
                    total_real['gastos'] += monto
        
        # NÃºmero de filas:  cuentas + separador + total
        num_cuentas = len(account_summary)
        self.account_table.setRowCount(num_cuentas + 2)  # +1 separador, +1 total
        
        row = 0
        font_bold = QFont()
        font_bold.setBold(True)
        
        # Filas de cuentas individuales
        for cuenta_id, data in sorted(account_summary.items(), key=lambda x: self.cuentas_map.get(x[0], x[0])):
            cuenta_nombre = self.cuentas_map.get(cuenta_id, f'ID:{cuenta_id}')
            ing = data['ingresos']
            gas = data['gastos']
            bal = ing - gas
            
            self.account_table.setItem(row, 0, QTableWidgetItem(cuenta_nombre))
            
            item_ing = QTableWidgetItem(f"RD$ {ing:,.2f}")
            item_ing.setForeground(Qt.GlobalColor.darkGreen)
            item_ing.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.account_table.setItem(row, 1, item_ing)
            
            item_gas = QTableWidgetItem(f"RD$ {gas:,.2f}")
            item_gas. setForeground(Qt.GlobalColor.darkRed)
            item_gas. setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.account_table.setItem(row, 2, item_gas)
            
            item_bal = QTableWidgetItem(f"RD$ {bal:,.2f}")
            color = Qt.GlobalColor.darkGreen if bal >= 0 else Qt.GlobalColor.darkRed
            item_bal.setForeground(color)
            item_bal.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt. AlignmentFlag.AlignVCenter)
            item_bal.setFont(font_bold)
            self.account_table.setItem(row, 3, item_bal)
            row += 1
        
        # Fila separadora (visual)
        for col in range(4):
            sep_item = QTableWidgetItem("")
            sep_item.setBackground(QColor(240, 240, 240))
            self.account_table.setItem(row, col, sep_item)
        row += 1
        
        # Fila TOTAL GENERAL (sin transferencias)
        total_label = QTableWidgetItem("TOTAL GENERAL (sin transferencias internas)")
        total_label. setFont(font_bold)
        total_label.setForeground(Qt.GlobalColor. darkBlue)
        self.account_table.setItem(row, 0, total_label)
        
        t_ing = QTableWidgetItem(f"RD$ {total_real['ingresos']:,.2f}")
        t_ing.setForeground(Qt. GlobalColor.darkGreen)
        t_ing.setFont(font_bold)
        t_ing.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.account_table.setItem(row, 1, t_ing)
        
        t_gas = QTableWidgetItem(f"RD$ {total_real['gastos']:,.2f}")
        t_gas.setForeground(Qt.GlobalColor.darkRed)
        t_gas.setFont(font_bold)
        t_gas.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.account_table.setItem(row, 2, t_gas)
        
        tot_bal = total_real['ingresos'] - total_real['gastos']
        t_bal = QTableWidgetItem(f"RD$ {tot_bal:,.2f}")
        t_bal.setForeground(Qt.GlobalColor.darkGreen if tot_bal >= 0 else Qt.GlobalColor.darkRed)
        t_bal.setFont(font_bold)
        t_bal.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.account_table.setItem(row, 3, t_bal)
        
        logger.info(f"Account summary:  {num_cuentas} accounts, Total: RD$ {tot_bal:,.2f}")
    
    def _update_month_summary(self):
        """Update monthly summary table (excludes internal transfers)"""
        month_summary = defaultdict(lambda: {'ingresos':  0.0, 'gastos': 0.0})
        
        for trans in self. transacciones:
            # âœ… EXCLUIR TRANSFERENCIAS del resumen mensual (son movimientos internos)
            if trans.get('es_transferencia') == True:
                continue
            
            d = self._parse_date(trans. get('fecha'))
            if not d: 
                continue
            month_key = f"{d.year}-{d.month:02d}"
            
            try: 
                monto = float(trans. get('monto', 0.0))
            except:
                monto = 0.0
            tipo = str(trans.get('tipo', '')).lower()
            
            if 'ingreso' in tipo:
                month_summary[month_key]['ingresos'] += monto
            elif 'gasto' in tipo: 
                month_summary[month_key]['gastos'] += monto
        
        num_months = len(month_summary)
        self.month_table.setRowCount(num_months + 2)  # +1 separador, +1 total
        
        row = 0
        font_bold = QFont()
        font_bold.setBold(True)
        
        total_ing_acum = 0.0
        total_gas_acum = 0.0
        
        # Meses ordenados (mÃ¡s reciente primero)
        for month_key in sorted(month_summary.keys(), reverse=True):
            data = month_summary[month_key]
            ing = data['ingresos']
            gas = data['gastos']
            bal = ing - gas
            
            total_ing_acum += ing
            total_gas_acum += gas
            
            # Format label
            y, m = month_key.split('-')
            m_names = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
            lbl = f"{m_names[int(m)-1]} {y}"
            
            self.month_table.setItem(row, 0, QTableWidgetItem(lbl))
            
            item_ing = QTableWidgetItem(f"RD$ {ing:,.2f}")
            item_ing.setForeground(Qt.GlobalColor. darkGreen)
            item_ing.setTextAlignment(Qt. AlignmentFlag.AlignRight | Qt.AlignmentFlag. AlignVCenter)
            self.month_table.setItem(row, 1, item_ing)
            
            item_gas = QTableWidgetItem(f"RD$ {gas:,.2f}")
            item_gas.setForeground(Qt. GlobalColor.darkRed)
            item_gas.setTextAlignment(Qt.AlignmentFlag. AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.month_table. setItem(row, 2, item_gas)
            
            item_bal = QTableWidgetItem(f"RD$ {bal:,.2f}")
            item_bal.setForeground(Qt. GlobalColor.darkGreen if bal >= 0 else Qt.GlobalColor.darkRed)
            item_bal.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item_bal.setFont(font_bold)
            self.month_table.setItem(row, 3, item_bal)
            
            row += 1
        
        # Fila separadora
        for col in range(4):
            sep_item = QTableWidgetItem("")
            sep_item.setBackground(QColor(240, 240, 240))
            self.month_table.setItem(row, col, sep_item)
        row += 1
        
        # Fila TOTAL
        total_label = QTableWidgetItem("TOTAL ACUMULADO")
        total_label.setFont(font_bold)
        total_label.setForeground(Qt.GlobalColor.darkBlue)
        self.month_table.setItem(row, 0, total_label)
        
        t_ing = QTableWidgetItem(f"RD$ {total_ing_acum:,.2f}")
        t_ing.setForeground(Qt.GlobalColor.darkGreen)
        t_ing.setFont(font_bold)
        t_ing.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.month_table.setItem(row, 1, t_ing)
        
        t_gas = QTableWidgetItem(f"RD$ {total_gas_acum:,.2f}")
        t_gas.setForeground(Qt.GlobalColor.darkRed)
        t_gas.setFont(font_bold)
        t_gas.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.month_table.setItem(row, 2, t_gas)
        
        tot_bal = total_ing_acum - total_gas_acum
        t_bal = QTableWidgetItem(f"RD$ {tot_bal:,.2f}")
        t_bal.setForeground(Qt.GlobalColor.darkGreen if tot_bal >= 0 else Qt.GlobalColor.darkRed)
        t_bal.setFont(font_bold)
        t_bal.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.month_table.setItem(row, 3, t_bal)
        
        logger.info(f"Month summary: {num_months} months, Total balance: RD$ {tot_bal:,.2f}")

    def _on_refresh_clicked(self):
        self.refresh()
    
    def _export_csv(self):
        if not self.proyecto_id:
            QMessageBox.warning(self, "Exportar", "No hay datos para exportar")
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "Guardar CSV", f"flujo_caja_{self.proyecto_nombre}.csv", "CSV Files (*.csv)"
        )
        if not filename:  
            return
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([f"Flujo de Caja - {self.proyecto_nombre}"])
                writer. writerow([f"PerÃ­odo: {self.fecha_inicio} - {self.fecha_fin}"])
                writer.writerow([])
                
                writer.writerow(["RESUMEN POR CUENTA"])
                writer.writerow(["Cuenta", "Total Ingresos", "Total Gastos", "Balance"])
                for r in range(self.account_table.rowCount()):
                    cols = [self.account_table.item(r, c).text() if self.account_table.item(r, c) else "" for c in range(4)]
                    writer.writerow(cols)
                
                writer.writerow([])
                writer.writerow(["RESUMEN MENSUAL"])
                writer.writerow(["Mes/AÃ±o", "Ingresos", "Gastos", "Balance"])
                for r in range(self.month_table.rowCount()):
                    cols = [self.month_table.item(r, c).text() if self.month_table.item(r, c) else "" for c in range(4)]
                    writer.writerow(cols)
            
            QMessageBox.information(self, "Exportar", "CSV exportado exitosamente.")
        except Exception as e:
            logger.error(f"Error exporting CSV: {e}")
            QMessageBox.critical(self, "Error", f"Error al exportar CSV:\n{str(e)}")
    
    def _export_pdf(self):
        """Export summary to PDF using ReportGenerator"""
        if not REPORT_GENERATOR_AVAILABLE:
            QMessageBox.warning(self, "Error", "El mÃ³dulo ReportGenerator no estÃ¡ disponible.")
            return
            
        if not self.proyecto_id:
            QMessageBox.warning(self, "Exportar", "No hay datos para exportar")
            return
            
        filename, _ = QFileDialog.getSaveFileName(
            self, "Guardar PDF", f"flujo_caja_{self.proyecto_nombre}.pdf", "PDF Files (*.pdf)"
        )
        if not filename: 
            return
            
        try:
            # Preparar datos para el reporte (Usamos la tabla mensual plana para el PDF)
            data_export = []
            
            # Recolectar datos de la tabla visual para mantener formato
            for r in range(self.month_table.rowCount()):
                item = self.month_table.item(r, 0)
                if not item:
                    continue
                mes_lbl = item.text()
                
                def parse_monto(txt):
                    try:  
                        return float(txt. replace("RD$", "").replace(",", "").strip())
                    except:  
                        return 0.0
                
                ing_item = self.month_table.item(r, 1)
                gas_item = self.month_table.item(r, 2)
                bal_item = self.month_table.item(r, 3)
                
                ing = parse_monto(ing_item.text() if ing_item else "0")
                gas = parse_monto(gas_item.text() if gas_item else "0")
                bal = parse_monto(bal_item.text() if bal_item else "0")
                
                data_export.append({
                    "Mes": mes_lbl,
                    "Ingresos": ing,
                    "Gastos": gas,
                    "Balance": bal,
                    "Tipo": "Ingreso" if bal >= 0 else "Gasto"  # Para color
                })
                
            date_range_str = f"{self.fecha_inicio} - {self.fecha_fin}"
            
            rg = ReportGenerator(
                data=data_export,
                title="Reporte de Flujo de Caja",
                project_name=self.proyecto_nombre,
                date_range=date_range_str,
                currency_symbol="RD$",
                column_map={"Mes": "Mes", "Ingresos": "Total Ingresos", "Gastos": "Total Gastos", "Balance": "Balance"}
            )
            
            # Usamos to_pdf (tabular) en vez de dashboard_to_pdf
            ok, msg = rg.to_pdf(filename)
            
            if ok:
                QMessageBox.information(self, "Exportar", "PDF exportado exitosamente.")
            else:
                QMessageBox.critical(self, "Error", f"Error al exportar PDF:  {msg}")
                
        except Exception as e:
            logger. error(f"Error exporting PDF: {e}")
            QMessageBox.critical(self, "Error", f"Error al exportar PDF:\n{str(e)}")
