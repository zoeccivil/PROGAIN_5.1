"""
Transfer Dialog for PROGRAIN 4.0/5.0

Dialog for creating transfers between accounts within the same project.
Creates two atomic transactions: one withdrawal and one deposit.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLabel, QComboBox, QLineEdit, QTextEdit, QDateEdit, QPushButton,
    QMessageBox, QDoubleSpinBox
)
from PyQt6.QtCore import QDate, Qt

import logging

logger = logging.getLogger(__name__)


class TransferDialog(QDialog):
    """
    Dialog for creating a transfer between two accounts.
    
    Creates two transactions:
    - Withdrawal from origin account (negative amount)
    - Deposit to destination account (positive amount)
    """
    
    def __init__(
        self,
        firebase_client,
        proyecto_id: str,
        cuentas: List[Dict[str, Any]],
        parent=None
    ):
        """
        Initialize transfer dialog.
        
        Args:
            firebase_client: FirebaseClient instance
            proyecto_id: Current project ID
            cuentas: List of accounts in the project
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.firebase_client = firebase_client
        self.proyecto_id = proyecto_id
        self.cuentas = cuentas
        
        # Window setup
        self.setWindowTitle("Nueva Transferencia")
        self.setModal(True)
        self.setMinimumWidth(500)
        
        # Initialize UI
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("<h2>Nueva Transferencia</h2>")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Info message
        info_label = QLabel(
            "ℹ️ Las transferencias crean un Gasto en la cuenta origen "
            "y un Ingreso en la cuenta destino, vinculados automáticamente."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("padding: 10px; background-color: #FFF3CD; border-radius: 4px;")
        layout.addWidget(info_label)
        
        # Main details group
        main_group = QGroupBox("Detalles de la Transferencia")
        main_layout = QFormLayout()
        
        # Origin account
        self.cuenta_origen_combo = QComboBox()
        for cuenta in self.cuentas:
            self.cuenta_origen_combo.addItem(cuenta.get('nombre', 'Sin nombre'), cuenta.get('id'))
        main_layout.addRow("Cuenta Origen:", self.cuenta_origen_combo)
        
        # Destination account
        self.cuenta_destino_combo = QComboBox()
        for cuenta in self.cuentas:
            self.cuenta_destino_combo.addItem(cuenta.get('nombre', 'Sin nombre'), cuenta.get('id'))
        # Select second account by default if available
        if len(self.cuentas) > 1:
            self.cuenta_destino_combo.setCurrentIndex(1)
        main_layout.addRow("Cuenta Destino:", self.cuenta_destino_combo)
        
        # Date
        self.fecha_edit = QDateEdit()
        self.fecha_edit.setCalendarPopup(True)
        self.fecha_edit.setDate(QDate.currentDate())
        self.fecha_edit.setDisplayFormat("yyyy-MM-dd")
        main_layout.addRow("Fecha:", self.fecha_edit)
        
        # Amount
        self.monto_spin = QDoubleSpinBox()
        self.monto_spin.setRange(0.01, 999999999.99)
        self.monto_spin.setDecimals(2)
        self.monto_spin.setPrefix("RD$ ")
        self.monto_spin.setValue(0.00)
        main_layout.addRow("Monto:", self.monto_spin)
        
        # Note/Description
        main_layout.addRow(QLabel("Nota:"))
        self.nota_edit = QTextEdit()
        self.nota_edit.setPlaceholderText("Descripción de la transferencia (opcional)")
        self.nota_edit.setMaximumHeight(80)
        main_layout.addRow(self.nota_edit)
        
        main_group.setLayout(main_layout)
        layout.addWidget(main_group)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("Crear Transferencia")
        save_btn.clicked.connect(self._on_save)
        save_btn.setDefault(True)
        buttons_layout.addWidget(save_btn)
        
        layout.addLayout(buttons_layout)
        
        self.setLayout(layout)
    
    def _on_save(self):
        """Handle save button click - validate and create transfer"""
        # Validation
        cuenta_origen_id = self.cuenta_origen_combo.currentData()
        cuenta_destino_id = self.cuenta_destino_combo.currentData()
        monto = self.monto_spin.value()
        nota = self.nota_edit.toPlainText().strip()
        
        # Validate accounts are different
        if cuenta_origen_id == cuenta_destino_id:
            QMessageBox.warning(
                self,
                "Error de Validación",
                "La cuenta origen y destino deben ser diferentes.",
            )
            return
        
        # Validate amount
        if monto <= 0:
            QMessageBox.warning(
                self,
                "Error de Validación",
                "El monto debe ser mayor a cero.",
            )
            return
        
        # Validate project
        if not self.proyecto_id:
            QMessageBox.critical(
                self,
                "Error",
                "No hay un proyecto activo.",
            )
            return
        
        # Get date
        qdate = self.fecha_edit.date()
        fecha = datetime(qdate.year(), qdate.month(), qdate.day())
        
        # Get account names for descriptions
        cuenta_origen_nombre = self.cuenta_origen_combo.currentText()
        cuenta_destino_nombre = self.cuenta_destino_combo.currentText()
        
        # Confirm with user
        confirm_msg = (
            f"¿Crear transferencia?\n\n"
            f"De: {cuenta_origen_nombre}\n"
            f"A: {cuenta_destino_nombre}\n"
            f"Monto: RD$ {monto:,.2f}\n"
            f"Fecha: {fecha.strftime('%Y-%m-%d')}\n\n"
            f"Esto creará dos transacciones en el proyecto."
        )
        
        reply = QMessageBox.question(
            self,
            "Confirmar Transferencia",
            confirm_msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Create transfer
        try:
            success = self.firebase_client.create_transfer(
                proyecto_id=self.proyecto_id,
                fecha=fecha,
                cuenta_origen_id=cuenta_origen_id,
                cuenta_destino_id=cuenta_destino_id,
                monto=monto,
                nota=nota
            )
            
            if success:
                QMessageBox.information(
                    self,
                    "Transferencia Creada",
                    f"Transferencia creada exitosamente:\n\n"
                    f"RD$ {monto:,.2f} de {cuenta_origen_nombre} a {cuenta_destino_nombre}",
                )
                self.accept()
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    "No se pudo crear la transferencia. Verifique los logs para más detalles.",
                )
        
        except Exception as e:
            logger.error(f"Error creating transfer: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Error al crear la transferencia:\n{str(e)}",
            )
