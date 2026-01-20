from datetime import datetime, date
from typing import List, Dict, Any, Optional
import logging

from PyQt6.QtCore import Qt, QDate
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QFileDialog,
    QMessageBox,
    QDateEdit,
    QComboBox,
    QHeaderView
)

# Importamos el generador de reportes desde su nueva ubicación
try:
    from progain4.services.report_generator import ReportGenerator
    REPORT_GENERATOR_AVAILABLE = True
except ImportError:
    REPORT_GENERATOR_AVAILABLE = False
    logging.warning("ReportGenerator no encontrado en progain4.services.report_generator")

logger = logging.getLogger(__name__)


class ResumenPorCuentaReport(QDialog):
    """
    Resumen por Cuenta (Firebase).

    Equivalente funcional del ResumenPorCuentaWindow original, pero:
    - Lee transacciones desde FirebaseClient.
    - Agrega por cuenta: Ingresos, Gastos, Balance.
    - Permite filtrar por rango de fechas y tipo de cuenta.
    - Exporta PDF/Excel vía ReportGenerator.to_pdf_resumen_por_cuenta /
      to_excel_resumen_por_cuenta.
    """

    def __init__(self, firebase_client, proyecto_id: str, proyecto_nombre: str, moneda: str = "RD$", parent=None):
        super().__init__(parent)

        self.firebase_client = firebase_client
        self.proyecto_id = proyecto_id
        self.proyecto_nombre = proyecto_nombre
        self.moneda = moneda

        # Datos preparados para exportar (lista de dicts)
        # Cada fila: {"Cuenta": str, "Ingresos": float, "Gastos": float, "Balance": float}
        self._rows_export: List[Dict[str, Any]] = []

        # Cache transacciones para inicializar rango
        self._all_transacciones: Optional[List[Dict[str, Any]]] = None

        self.setWindowTitle("Resumen por Cuenta (Firebase)")
        
        # --- MEJORA UI: Permitir maximizar ---
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMinMaxButtonsHint)
        self.setModal(True)
        self.resize(950, 650)

        self._init_ui()
        self._init_date_range_from_data()
        self._load_and_fill()

    # ------------------------------------------------------------------ UI

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Título
        title = QLabel("<h2>Resumen por Cuenta</h2>")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Proyecto / filtros
        layout.addWidget(QLabel(f"Proyecto: {self.proyecto_nombre}"))

        filtros_layout = QHBoxLayout()
        filtros_layout.addWidget(QLabel("Desde:"))
        self.date_desde = QDateEdit()
        self.date_desde.setCalendarPopup(True)
        self.date_desde.setDisplayFormat("yyyy-MM-dd")
        self.date_desde.setDate(QDate.currentDate().addMonths(-1))  # provisional
        filtros_layout.addWidget(self.date_desde)

        filtros_layout.addWidget(QLabel("Hasta:"))
        self.date_hasta = QDateEdit()
        self.date_hasta.setCalendarPopup(True)
        self.date_hasta.setDisplayFormat("yyyy-MM-dd")
        self.date_hasta.setDate(QDate.currentDate())
        filtros_layout.addWidget(self.date_hasta)

        filtros_layout.addWidget(QLabel("Tipo de cuenta:"))
        self.combo_tipo_cuenta = QComboBox()
        self.combo_tipo_cuenta.addItem("Todas", None)
        self.combo_tipo_cuenta.addItem("Efectivo", "efectivo")
        self.combo_tipo_cuenta.addItem("Banco", "banco")
        self.combo_tipo_cuenta.addItem("Tarjeta", "tarjeta")
        self.combo_tipo_cuenta.addItem("Inversión", "inversion")
        self.combo_tipo_cuenta.addItem("Ahorro", "ahorro")
        filtros_layout.addWidget(self.combo_tipo_cuenta)

        btn_filtrar = QPushButton("Filtrar")
        btn_filtrar.clicked.connect(self._load_and_fill)
        filtros_layout.addWidget(btn_filtrar)

        filtros_layout.addStretch()
        layout.addLayout(filtros_layout)

        # Tabla
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Cuenta", "Ingresos", "Gastos", "Balance"])
        self.table.setAlternatingRowColors(True)
        
        # --- MEJORA UI: Columnas redimensionables ---
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)      # Cuenta (elástica)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)  # Ingresos
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)  # Gastos
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)  # Balance
        
        layout.addWidget(self.table, stretch=1)

        # Totales
        self.label_totales = QLabel()
        self.label_totales.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.label_totales)

        # Botones exportar / cerrar
        botones_layout = QHBoxLayout()
        botones_layout.addStretch()
        
        btn_pdf = QPushButton("Exportar PDF")
        btn_pdf.clicked.connect(self._exportar_pdf)
        if not REPORT_GENERATOR_AVAILABLE:
            btn_pdf.setEnabled(False)
            btn_pdf.setToolTip("ReportGenerator no disponible")
        botones_layout.addWidget(btn_pdf)

        btn_excel = QPushButton("Exportar Excel")
        btn_excel.clicked.connect(self._exportar_excel)
        if not REPORT_GENERATOR_AVAILABLE:
            btn_excel.setEnabled(False)
        botones_layout.addWidget(btn_excel)

        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.clicked.connect(self.accept)
        botones_layout.addWidget(btn_cerrar)

        layout.addLayout(botones_layout)

        # Recarga automática al cambiar fechas o tipo
        self.date_desde.dateChanged.connect(self._load_and_fill)
        self.date_hasta.dateChanged.connect(self._load_and_fill)
        self.combo_tipo_cuenta.currentIndexChanged.connect(self._load_and_fill)

    # ------------------------------------------------------------------ HELPERS

    def _parse_date(self, date_val: Any) -> Optional[date]:
        """Convierte fecha a date nativo sin zona horaria."""
        if not date_val:
            return None
        try:
            if type(date_val) is date: return date_val
            if isinstance(date_val, datetime): return date_val.date()
            if isinstance(date_val, str):
                return datetime.strptime(date_val[:10], "%Y-%m-%d").date()
        except Exception:
            return None
        return None

    # ------------------------------------------------------------------ RANGO INICIAL

    def _init_date_range_from_data(self):
        """
        Desde = fecha mínima de transacción del proyecto.
        Hasta = hoy.
        """
        try:
            if self._all_transacciones is None:
                self._all_transacciones = self.firebase_client.get_transacciones_by_proyecto(
                    self.proyecto_id
                )
            trans = self._all_transacciones or []
            if not trans:
                self.date_desde.setDate(QDate.currentDate().addMonths(-1))
                self.date_hasta.setDate(QDate.currentDate())
                return

            fechas_validas = []
            for t in trans:
                d = self._parse_date(t.get("fecha"))
                if d: fechas_validas.append(d)

            if fechas_validas:
                min_date = min(fechas_validas)
                self.date_desde.blockSignals(True)
                self.date_desde.setDate(min_date)
                self.date_desde.blockSignals(False)
            else:
                self.date_desde.setDate(QDate.currentDate().addMonths(-1))

            self.date_hasta.setDate(QDate.currentDate())

        except Exception as e:
            QMessageBox.warning(
                self,
                "Advertencia",
                f"No se pudo inicializar el rango de fechas automáticamente:\n{e}",
            )

    # ------------------------------------------------------------------ CÁLCULO Y CARGA

    def _load_and_fill(self):
        """Carga transacciones, calcula resumen por cuenta y llena tabla/export."""
        try:
            qdesde = self.date_desde.date()
            qhasta = self.date_hasta.date()
            
            desde_date = qdesde.toPyDate()
            hasta_date = qhasta.toPyDate()

            if hasta_date < desde_date:
                self.label_totales.setText("<font color='red'>Fecha 'Hasta' menor que 'Desde'</font>")
                self.table.setRowCount(0)
                return

            tipo_cuenta_filter = self.combo_tipo_cuenta.currentData()
            
            # Cuentas del proyecto
            cuentas = self.firebase_client.get_cuentas_by_proyecto(self.proyecto_id)
            cuentas_by_id = {str(c["id"]): c for c in cuentas}

            # Transacciones (cache)
            if self._all_transacciones is None:
                self._all_transacciones = self.firebase_client.get_transacciones_by_proyecto(
                    self.proyecto_id
                )
            transacciones = self._all_transacciones or []

            # Agregación
            resumen: Dict[str, Dict[str, float]] = {}
            total_ingresos = 0.0
            total_gastos = 0.0

            for t in transacciones:
                # --- CORRECCIÓN: Parseo seguro ---
                fecha_date = self._parse_date(t.get("fecha"))
                if not fecha_date: continue

                if not (desde_date <= fecha_date <= hasta_date):
                    continue

                cuenta_id = str(t.get("cuenta_id", ""))
                cuenta_data = cuentas_by_id.get(cuenta_id)
                if not cuenta_data:
                    continue

                # Filtrar por tipo de cuenta
                tipo_cuenta = str(cuenta_data.get("tipo", "")).lower()
                if tipo_cuenta_filter and tipo_cuenta != tipo_cuenta_filter:
                    continue

                cuenta_nombre = cuenta_data.get("nombre", f"Cuenta {cuenta_id}")

                tipo = str(t.get("tipo", "")).lower()
                try:
                    monto = float(t.get("monto", 0.0))
                except: monto = 0.0

                if cuenta_nombre not in resumen:
                    resumen[cuenta_nombre] = {"Ingresos": 0.0, "Gastos": 0.0}

                if "ingreso" in tipo:
                    resumen[cuenta_nombre]["Ingresos"] += monto
                    total_ingresos += monto
                elif "gasto" in tipo:
                    resumen[cuenta_nombre]["Gastos"] += monto
                    total_gastos += monto

            # Construir filas para tabla y export
            rows: List[Dict[str, Any]] = []
            for cuenta_nombre in sorted(resumen.keys()):
                ing = resumen[cuenta_nombre]["Ingresos"]
                gas = resumen[cuenta_nombre]["Gastos"]
                bal = ing - gas
                rows.append(
                    {
                        "Cuenta": cuenta_nombre,
                        "Ingresos": ing,
                        "Gastos": gas,
                        "Balance": bal,
                    }
                )

            self._rows_export = rows

            # Llenar tabla
            self.table.setRowCount(len(rows))
            for i, row in enumerate(rows):
                # Cuenta
                item_cuenta = QTableWidgetItem(str(row["Cuenta"]))
                item_cuenta.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(i, 0, item_cuenta)

                # Ingresos
                item_ing = QTableWidgetItem(f"{self.moneda} {row['Ingresos']:,.2f}")
                item_ing.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                item_ing.setForeground(Qt.GlobalColor.darkGreen)
                self.table.setItem(i, 1, item_ing)

                # Gastos
                item_gas = QTableWidgetItem(f"{self.moneda} {row['Gastos']:,.2f}")
                item_gas.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                item_gas.setForeground(Qt.GlobalColor.darkRed)
                self.table.setItem(i, 2, item_gas)

                # Balance
                bal = row['Balance']
                item_bal = QTableWidgetItem(f"{self.moneda} {bal:,.2f}")
                item_bal.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if bal < 0: item_bal.setForeground(Qt.GlobalColor.darkRed)
                else: item_bal.setForeground(Qt.GlobalColor.darkBlue)
                self.table.setItem(i, 3, item_bal)

            # Totales globales
            balance_total = total_ingresos - total_gastos
            self.label_totales.setText(
                f"<b>Totales:</b> "
                f"Ingresos: <span style='color:green;'>{self.moneda} {total_ingresos:,.2f}</span> | "
                f"Gastos: <span style='color:red;'>{self.moneda} {total_gastos:,.2f}</span> | "
                f"Balance: <span style='color:#004080;'>{self.moneda} {balance_total:,.2f}</span>"
            )

        except Exception as e:
            logger.error(f"Error loading summary: {e}")
            QMessageBox.critical(self, "Error", f"Error al generar el resumen:\n{e}")

    # ------------------------------------------------------------------ EXPORT

    def _exportar_pdf(self):
        """Exportar resumen por cuenta a PDF usando ReportGenerator."""
        if not self._rows_export:
            QMessageBox.warning(self, "Sin datos", "No hay datos para exportar.")
            return

        fecha_ini = self.date_desde.date().toString("yyyy-MM-dd")
        fecha_fin = self.date_hasta.date().toString("yyyy-MM-dd")
        nombre_archivo = f"{self.proyecto_nombre}_Resumen_Cuenta_{fecha_ini}_{fecha_fin}.pdf"

        ruta_archivo, _ = QFileDialog.getSaveFileName(
            self, "Guardar PDF", nombre_archivo, "Archivos PDF (*.pdf)"
        )
        if not ruta_archivo:
            return

        try:
            # Aseguramos importación
            from progain4.services.report_generator import ReportGenerator

            rg = ReportGenerator(
                data=self._rows_export,
                title="Resumen por Cuenta",
                project_name=self.proyecto_nombre,
                date_range=f"{fecha_ini} - {fecha_fin}",
                currency_symbol=self.moneda,
                column_map={
                    "Cuenta": "Cuenta",
                    "Ingresos": "Ingresos",
                    "Gastos": "Gastos",
                    "Balance": "Balance",
                },
            )

            ok, msg = rg.to_pdf_resumen_por_cuenta(ruta_archivo)
            if ok:
                QMessageBox.information(self, "Exportación", "Resumen exportado a PDF correctamente.")
            else:
                QMessageBox.warning(self, "Error PDF", f"No se pudo exportar PDF: {msg}")
                
        except Exception as e:
            logger.error(f"Error PDF export: {e}")
            QMessageBox.critical(self, "Error", f"Error inesperado: {e}")

    def _exportar_excel(self):
        """Exportar resumen por cuenta a Excel usando ReportGenerator."""
        if not self._rows_export:
            QMessageBox.warning(self, "Sin datos", "No hay datos para exportar.")
            return

        fecha_ini = self.date_desde.date().toString("yyyy-MM-dd")
        fecha_fin = self.date_hasta.date().toString("yyyy-MM-dd")
        nombre_archivo = f"{self.proyecto_nombre}_Resumen_Cuenta_{fecha_ini}_{fecha_fin}.xlsx"

        ruta_archivo, _ = QFileDialog.getSaveFileName(
            self, "Guardar Excel", nombre_archivo, "Archivos Excel (*.xlsx)"
        )
        if not ruta_archivo:
            return

        try:
            from progain4.services.report_generator import ReportGenerator

            rg = ReportGenerator(
                data=self._rows_export,
                title="Resumen por Cuenta",
                project_name=self.proyecto_nombre,
                date_range=f"{fecha_ini} - {fecha_fin}",
                currency_symbol=self.moneda,
                column_map={
                    "Cuenta": "Cuenta",
                    "Ingresos": "Ingresos",
                    "Gastos": "Gastos",
                    "Balance": "Balance",
                },
            )

            ok, msg = rg.to_excel_resumen_por_cuenta(ruta_archivo)
            if ok:
                QMessageBox.information(self, "Exportación", "Resumen exportado a Excel correctamente.")
            else:
                QMessageBox.warning(self, "Error Excel", f"No se pudo exportar Excel: {msg}")
                
        except Exception as e:
            logger.error(f"Error Excel export: {e}")
            QMessageBox.critical(self, "Error", f"Error inesperado: {e}")