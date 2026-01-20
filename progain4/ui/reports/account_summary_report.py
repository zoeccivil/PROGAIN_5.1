"""
Account Summary Report for PROGRAIN 4.0/5.0

Shows summary of transactions grouped by account.
Firebase-based implementation (migrated from resumen_por_cuenta_window.py)
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView, QMessageBox
)
from PyQt6.QtCore import Qt


class AccountSummaryReport(QDialog):
    """
    Report showing transaction summary by account.
    
    Equivalent to resumen_por_cuenta_window.py from PROGRAIN 3.0
    """
    
    def __init__(self, firebase_client, proyecto_id: str, parent=None):
        """
        Initialize account summary report.
        
        Args:
            firebase_client: FirebaseClient instance
            proyecto_id: Current project ID
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.firebase_client = firebase_client
        self.proyecto_id = proyecto_id
        
        # Window setup
        self.setWindowTitle("Resumen por Cuenta (Firebase)")
        self.setModal(True)
        self.setMinimumSize(700, 500)
        
        self._init_ui()
        self._load_data()
    
    def _init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("<h2>Resumen por Cuenta</h2>")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Info
        info = QLabel("Resumen de transacciones agrupadas por cuenta (datos de Firebase)")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Cuenta", "# Transacciones", "Ingresos", "Gastos", "Balance"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)
        
        # Totals label
        self.totals_label = QLabel()
        self.totals_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.totals_label)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        refresh_btn = QPushButton("🔄 Actualizar")
        refresh_btn.clicked.connect(self._load_data)
        buttons_layout.addWidget(refresh_btn)
        
        close_btn = QPushButton("Cerrar")
        close_btn.clicked.connect(self.accept)
        buttons_layout.addWidget(close_btn)
        
        layout.addLayout(buttons_layout)
        
        self.setLayout(layout)
    
    def _load_data(self):
        """Load and display account summary data"""
        try:
            # Get all accounts
            cuentas = self.firebase_client.get_cuentas_by_proyecto(self.proyecto_id)
            
            if not cuentas:
                QMessageBox.information(
                    self,
                    "Sin datos",
                    "No hay cuentas en este proyecto."
                )
                return
            
            # Prepare data
            account_data = []
            total_general_ingresos = 0.0
            total_general_gastos = 0.0
            
            for cuenta in cuentas:
                cuenta_id = cuenta['id']
                cuenta_nombre = cuenta.get('nombre', 'Sin nombre')
                
                # Get transactions for this account
                transacciones = self.firebase_client.get_transacciones_by_proyecto(
                    self.proyecto_id,
                    cuenta_id=cuenta_id
                )
                
                # Calculate totals
                num_trans = len(transacciones)
                total_ingresos = sum(
                    t['monto'] for t in transacciones if t.get('tipo') == 'ingreso'
                )
                total_gastos = sum(
                    t['monto'] for t in transacciones if t.get('tipo') == 'gasto'
                )
                balance = total_ingresos - total_gastos
                
                account_data.append({
                    'nombre': cuenta_nombre,
                    'num_trans': num_trans,
                    'ingresos': total_ingresos,
                    'gastos': total_gastos,
                    'balance': balance
                })
                
                total_general_ingresos += total_ingresos
                total_general_gastos += total_gastos
            
            # Update table
            self.table.setRowCount(len(account_data))
            
            for row, data in enumerate(account_data):
                # Cuenta
                self.table.setItem(row, 0, QTableWidgetItem(data['nombre']))
                
                # # Transacciones
                self.table.setItem(row, 1, QTableWidgetItem(str(data['num_trans'])))
                
                # Ingresos
                ingresos_item = QTableWidgetItem(f"RD$ {data['ingresos']:,.2f}")
                ingresos_item.setForeground(Qt.GlobalColor.darkGreen)
                self.table.setItem(row, 2, ingresos_item)
                
                # Gastos
                gastos_item = QTableWidgetItem(f"RD$ {data['gastos']:,.2f}")
                gastos_item.setForeground(Qt.GlobalColor.darkRed)
                self.table.setItem(row, 3, gastos_item)
                
                # Balance
                balance_item = QTableWidgetItem(f"RD$ {data['balance']:,.2f}")
                if data['balance'] >= 0:
                    balance_item.setForeground(Qt.GlobalColor.darkGreen)
                else:
                    balance_item.setForeground(Qt.GlobalColor.darkRed)
                self.table.setItem(row, 4, balance_item)
            
            # Update totals
            balance_general = total_general_ingresos - total_general_gastos
            self.totals_label.setText(
                f"<b>TOTALES:</b> "
                f"Ingresos: <span style='color: green;'>RD$ {total_general_ingresos:,.2f}</span> | "
                f"Gastos: <span style='color: red;'>RD$ {total_general_gastos:,.2f}</span> | "
                f"Balance: <span style='color: {'green' if balance_general >= 0 else 'red'};'>RD$ {balance_general:,.2f}</span>"
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Error al cargar el resumen:\n{str(e)}"
            )
