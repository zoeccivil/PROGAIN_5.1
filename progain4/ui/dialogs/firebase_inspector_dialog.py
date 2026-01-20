"""
Firebase Inspector Dialog for PROGRAIN 4.0/5.0

Debug tool to inspect Firebase data for the current project.
"""

from typing import List, Dict, Any
from datetime import datetime

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QTabWidget, QTableWidget, QTableWidgetItem,
    QLabel, QHeaderView, QPushButton, QHBoxLayout, QMessageBox
)
from PyQt6.QtCore import Qt


class FirebaseInspectorDialog(QDialog):
    """
    Dialog for inspecting Firebase data.
    
    Shows accounts, categories, and transaction summaries from Firestore.
    This is a debug/diagnostic tool.
    """
    
    def __init__(self, firebase_client, proyecto_id: str, parent=None):
        """
        Initialize Firebase inspector.
        
        Args:
            firebase_client: FirebaseClient instance
            proyecto_id: Current project ID
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.firebase_client = firebase_client
        self.proyecto_id = proyecto_id
        
        # Window setup
        self.setWindowTitle(f"Inspector de Firebase - Proyecto: {proyecto_id}")
        self.setModal(True)
        self.setMinimumSize(800, 600)
        
        self._init_ui()
        self._load_data()
    
    def _init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()
        
        # Title
        title = QLabel(f"<h2>Inspector de Datos de Firebase</h2>")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Project info
        info_label = QLabel(f"<b>Proyecto ID:</b> {self.proyecto_id}")
        layout.addWidget(info_label)
        
        # Tab widget
        self.tabs = QTabWidget()
        
        # Accounts tab
        self.accounts_table = self._create_table(["ID", "Nombre", "Tipo", "Principal", "Saldo Inicial", "Moneda"])
        self.tabs.addTab(self.accounts_table, "Cuentas")
        
        # Categories tab
        self.categories_table = self._create_table(["ID", "Nombre", "Tipo"])
        self.tabs.addTab(self.categories_table, "Categorías")
        
        # Transactions summary tab
        summary_widget = QVBoxLayout()
        self.summary_label = QLabel("<p>Cargando resumen...</p>")
        self.summary_label.setWordWrap(True)
        summary_widget.addWidget(self.summary_label)
        
        self.transactions_by_account_table = self._create_table(
            ["Cuenta", "# Transacciones", "Total Ingresos", "Total Gastos"]
        )
        summary_widget.addWidget(QLabel("<b>Transacciones por Cuenta:</b>"))
        summary_widget.addWidget(self.transactions_by_account_table)
        
        summary_tab = QDialog()
        summary_tab.setLayout(summary_widget)
        self.tabs.addTab(summary_tab, "Resumen de Transacciones")
        
        layout.addWidget(self.tabs)
        
        # Close button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        close_btn = QPushButton("Cerrar")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def _create_table(self, headers: List[str]) -> QTableWidget:
        """Create a table widget with headers"""
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        return table
    
    def _load_data(self):
        """Load data from Firebase"""
        try:
            # Load accounts
            self._load_accounts()
            
            # Load categories
            self._load_categories()
            
            # Load transaction summary
            self._load_transaction_summary()
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Error al cargar datos de Firebase:\n{str(e)}"
            )
    
    def _load_accounts(self):
        """Load and display accounts"""
        try:
            cuentas = self.firebase_client.get_cuentas_by_proyecto(self.proyecto_id)
            
            self.accounts_table.setRowCount(len(cuentas))
            
            for row, cuenta in enumerate(cuentas):
                # ID
                self.accounts_table.setItem(row, 0, QTableWidgetItem(cuenta.get('id', '')))
                
                # Nombre
                self.accounts_table.setItem(row, 1, QTableWidgetItem(cuenta.get('nombre', '')))
                
                # Tipo
                self.accounts_table.setItem(row, 2, QTableWidgetItem(cuenta.get('tipo', '')))
                
                # Principal
                is_principal = cuenta.get('is_principal', False)
                self.accounts_table.setItem(row, 3, QTableWidgetItem("Sí" if is_principal else "No"))
                
                # Saldo inicial
                saldo = cuenta.get('saldo_inicial', 0.0)
                self.accounts_table.setItem(row, 4, QTableWidgetItem(f"{saldo:,.2f}"))
                
                # Moneda
                self.accounts_table.setItem(row, 5, QTableWidgetItem(cuenta.get('moneda', '')))
        
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error al cargar cuentas:\n{str(e)}")
    
    def _load_categories(self):
        """Load and display categories"""
        try:
            categorias = self.firebase_client.get_categorias_by_proyecto(self.proyecto_id)
            
            self.categories_table.setRowCount(len(categorias))
            
            for row, categoria in enumerate(categorias):
                # ID
                self.categories_table.setItem(row, 0, QTableWidgetItem(categoria.get('id', '')))
                
                # Nombre
                self.categories_table.setItem(row, 1, QTableWidgetItem(categoria.get('nombre', '')))
                
                # Tipo
                self.categories_table.setItem(row, 2, QTableWidgetItem(categoria.get('tipo', '')))
        
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error al cargar categorías:\n{str(e)}")
    
    def _load_transaction_summary(self):
        """Load and display transaction summary"""
        try:
            # Get all transactions
            transacciones = self.firebase_client.get_transacciones_by_proyecto(self.proyecto_id)
            
            # Get all accounts for mapping
            cuentas = self.firebase_client.get_cuentas_by_proyecto(self.proyecto_id)
            cuentas_map = {c['id']: c['nombre'] for c in cuentas}
            
            # Calculate summary
            total_transactions = len(transacciones)
            
            # Find date range
            if transacciones:
                fechas = [t.get('fecha') for t in transacciones if t.get('fecha')]
                if fechas:
                    fechas = [f for f in fechas if isinstance(f, datetime)]
                    if fechas:
                        primera_fecha = min(fechas).strftime('%Y-%m-%d')
                        ultima_fecha = max(fechas).strftime('%Y-%m-%d')
                    else:
                        primera_fecha = "N/A"
                        ultima_fecha = "N/A"
                else:
                    primera_fecha = "N/A"
                    ultima_fecha = "N/A"
            else:
                primera_fecha = "N/A"
                ultima_fecha = "N/A"
            
            # Summary by account
            account_summary = {}
            for trans in transacciones:
                cuenta_id = trans.get('cuenta_id', 'unknown')
                tipo = trans.get('tipo', '').lower()
                monto = float(trans.get('monto', 0))
                
                if cuenta_id not in account_summary:
                    account_summary[cuenta_id] = {
                        'count': 0,
                        'ingresos': 0.0,
                        'gastos': 0.0
                    }
                
                account_summary[cuenta_id]['count'] += 1
                
                if tipo == 'ingreso':
                    account_summary[cuenta_id]['ingresos'] += monto
                elif tipo == 'gasto':
                    account_summary[cuenta_id]['gastos'] += monto
            
            # Update summary label
            summary_text = f"""
            <p><b>Total de transacciones:</b> {total_transactions}</p>
            <p><b>Primera transacción:</b> {primera_fecha}</p>
            <p><b>Última transacción:</b> {ultima_fecha}</p>
            <p><b>Número de cuentas:</b> {len(cuentas)}</p>
            """
            self.summary_label.setText(summary_text)
            
            # Update table
            self.transactions_by_account_table.setRowCount(len(account_summary))
            
            for row, (cuenta_id, summary) in enumerate(account_summary.items()):
                # Cuenta nombre
                cuenta_nombre = cuentas_map.get(cuenta_id, f"ID: {cuenta_id}")
                self.transactions_by_account_table.setItem(row, 0, QTableWidgetItem(cuenta_nombre))
                
                # Count
                self.transactions_by_account_table.setItem(
                    row, 1, QTableWidgetItem(str(summary['count']))
                )
                
                # Ingresos
                self.transactions_by_account_table.setItem(
                    row, 2, QTableWidgetItem(f"RD$ {summary['ingresos']:,.2f}")
                )
                
                # Gastos
                self.transactions_by_account_table.setItem(
                    row, 3, QTableWidgetItem(f"RD$ {summary['gastos']:,.2f}")
                )
        
        except Exception as e:
            self.summary_label.setText(f"<p style='color: red;'>Error: {str(e)}</p>")
