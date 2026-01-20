"""
Detailed Date Report for PROGRAIN 4.0/5.0

Shows all transactions in a detailed table with date range filters
and export to PDF / Excel using report_generator.ReportGenerator.

Firebase-based implementation (migrated from reporte_detallado_fecha.py)
"""

from datetime import datetime, date
from typing import List, Dict, Any, Optional
import logging

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QLabel,
    QHeaderView,
    QMessageBox,
    QDateEdit,
    QFileDialog,
)
from PyQt6.QtCore import Qt, QDate

# Importamos el generador de reportes desde su nueva ubicación
try:
    from progain4.services.report_generator import ReportGenerator
    REPORT_GENERATOR_AVAILABLE = True
except ImportError:
    REPORT_GENERATOR_AVAILABLE = False
    logging.warning("ReportGenerator no encontrado en progain4.services.report_generator")

logger = logging.getLogger(__name__)


class DetailedDateReport(QDialog):
    """
    Report showing detailed list of transactions with date range filters.

    Funcionalmente equivalente a reporte_detallado_fecha.py de PROGRAIN 3.0,
    pero leyendo datos desde Firebase via FirebaseClient.
    """

    def __init__(self, firebase_client, proyecto_id: str, parent=None):
        super().__init__(parent)

        self.firebase_client = firebase_client
        self.proyecto_id = proyecto_id

        # Filas que se muestran actualmente en la tabla (listas de dicts)
        self.transacciones_filtradas: List[Dict[str, Any]] = []

        # Cache de todas las transacciones del proyecto
        self._all_transacciones: Optional[List[Dict[str, Any]]] = None

        # Config ventana
        self.setWindowTitle("Reporte Detallado por Fecha (Firebase)")
        
        # --- MEJORA UI: Permitir maximizar y redimensionar ---
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMinMaxButtonsHint)
        self.setModal(True)
        self.resize(1000, 700)  # Tamaño inicial un poco más grande

        self._init_ui()
        self._init_date_range_from_data()
        self._load_data()  # primer llenado

    # ------------------------------------------------------------------ UI

    def _init_ui(self):
        layout = QVBoxLayout()

        title = QLabel("<h2>Reporte Detallado de Transacciones</h2>")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        info = QLabel("Listado de transacciones del proyecto (datos de Firebase)")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info)

        # Filtros de fecha
        filtros_layout = QHBoxLayout()
        filtros_layout.addWidget(QLabel("Desde: "))

        self.date_desde = QDateEdit()
        self.date_desde.setCalendarPopup(True)
        self.date_desde.setDisplayFormat("yyyy-MM-dd")
        self.date_desde.setDate(QDate.currentDate().addMonths(-1))  # provisional
        filtros_layout. addWidget(self.date_desde)

        filtros_layout. addWidget(QLabel("Hasta:"))
        self.date_hasta = QDateEdit()
        self.date_hasta.setCalendarPopup(True)
        self.date_hasta.setDisplayFormat("yyyy-MM-dd")
        self.date_hasta. setDate(QDate.currentDate())
        filtros_layout. addWidget(self.date_hasta)

        filtros_layout. addStretch()
        layout.addLayout(filtros_layout)

        # ✅ MODIFICADO: Tabla visual con columna "Adjuntos"
        self.table = QTableWidget()
        self.table. setColumnCount(7)  # ✅ CAMBIO: 6 → 7 columnas
        self.table.setHorizontalHeaderLabels(
            ["Fecha", "Tipo", "Cuenta", "Categoría", "Descripción", "Monto", "Adjuntos"]  # ✅ NUEVO
        )

        header = self.table.horizontalHeader()
        # --- MEJORA UI: Columnas ajustables por el usuario ---
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)  # Fecha
        header.setSectionResizeMode(1, QHeaderView. ResizeMode.Interactive)  # Tipo
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)  # Cuenta
        header. setSectionResizeMode(3, QHeaderView.ResizeMode. Interactive)  # Categoría
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)      # Descripción (elástica)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode. Interactive)  # Monto
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Interactive)  # ✅ NUEVO:  Adjuntos
        
        # Anchos iniciales sugeridos
        self.table.setColumnWidth(0, 100)
        self.table.setColumnWidth(1, 80)
        self.table.setColumnWidth(2, 150)
        self.table.setColumnWidth(3, 150)
        self.table.setColumnWidth(5, 120)
        self.table.setColumnWidth(6, 80)  # ✅ NUEVO:  Adjuntos

        self. table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget. SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

        # Totales
        self.totals_label = QLabel()
        self.totals_label.setAlignment(Qt.AlignmentFlag. AlignRight)
        layout.addWidget(self.totals_label)

        # Botones
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        btn_pdf = QPushButton("Exportar a PDF")
        btn_pdf.clicked.connect(self._exportar_pdf)
        if not REPORT_GENERATOR_AVAILABLE:
            btn_pdf.setEnabled(False)
            btn_pdf.setToolTip("ReportGenerator no disponible")
        buttons_layout.addWidget(btn_pdf)

        btn_excel = QPushButton("Exportar a Excel")
        btn_excel.clicked.connect(self._exportar_excel)
        if not REPORT_GENERATOR_AVAILABLE:
            btn_excel.setEnabled(False)
        buttons_layout.addWidget(btn_excel)

        refresh_btn = QPushButton("🔄 Actualizar (recargar desde Firebase)")
        refresh_btn.clicked.connect(self._reload_from_firebase)
        buttons_layout.addWidget(refresh_btn)

        close_btn = QPushButton("Cerrar")
        close_btn.clicked. connect(self.accept)
        buttons_layout.addWidget(close_btn)

        layout.addLayout(buttons_layout)

        self.setLayout(layout)

        # Cambios de fecha refrescan inmediatamente
        self.date_desde.dateChanged. connect(self._load_data)
        self.date_hasta. dateChanged.connect(self._load_data)
    # ------------------------------------------------------------------ HELPER FECHAS

    def _parse_date(self, date_val: Any) -> Optional[date]:
        """
        Convierte cualquier formato de fecha (String, Datetime con zona, etc.)
        a un objeto date nativo SIN zona horaria para comparar sin errores.
        """
        if not date_val:
            return None
        
        try:
            # Caso 1: Ya es datetime.date (pero no datetime)
            if type(date_val) is date:
                return date_val
                
            # Caso 2: Es datetime (puede tener tzinfo)
            if isinstance(date_val, datetime):
                # .date() elimina la hora y la zona horaria automáticamente
                return date_val.date()
            
            # Caso 3: Es string (YYYY-MM-DD...)
            if isinstance(date_val, str):
                # Tomamos solo los primeros 10 chars por si viene con hora
                return datetime.strptime(date_val[:10], "%Y-%m-%d").date()
                
        except Exception:
            return None
        return None

    # ------------------------------------------------------------------ INIT RANGE

    def _reload_from_firebase(self):
        """Forzar recarga completa de Firebase y re-aplicar filtros."""
        self._all_transacciones = None
        self._init_date_range_from_data()
        self._load_data()

    def _init_date_range_from_data(self):
        """
        Inicializa el rango de fechas:
        - Desde: fecha mínima de las transacciones del proyecto.
        - Hasta: hoy.
        """
        try:
            if self._all_transacciones is None:
                self._all_transacciones = self.firebase_client.get_transacciones_by_proyecto(
                    self.proyecto_id
                )

            transacciones = self._all_transacciones or []
            if not transacciones:
                self.date_desde.setDate(QDate.currentDate().addMonths(-1))
                self.date_hasta.setDate(QDate.currentDate())
                self.table.setRowCount(0)
                self.transacciones_filtradas = []
                self.totals_label.setText("No hay transacciones en este proyecto.")
                return

            fechas_validas = []
            for t in transacciones:
                d = self._parse_date(t.get("fecha"))
                if d:
                    fechas_validas.append(d)

            if fechas_validas:
                min_date = min(fechas_validas)
                # Bloqueamos señales para evitar recarga prematura
                self.date_desde.blockSignals(True)
                self.date_desde.setDate(min_date)
                self.date_desde.blockSignals(False)
            else:
                self.date_desde.setDate(QDate.currentDate().addMonths(-1))

            self.date_hasta.setDate(QDate.currentDate())

        except Exception as e:
            logger.error(f"Error init date range: {e}")
            # No mostramos popup para no interrumpir, solo logueamos y usamos default
            self.date_desde.setDate(QDate.currentDate().addMonths(-1))

    # ------------------------------------------------------------------ DATA

    def _load_data(self):
        """
        Carga transacciones desde cache/Firebase, aplica rango de fechas
        y llena tanto la tabla como self.transacciones_filtradas en el
        formato esperado por ReportGenerator (CON SOPORTE DE ADJUNTOS).
        """
        try:
            qdesde = self.date_desde.date()
            qhasta = self.date_hasta. date()
            
            # Conversión segura a date de Python
            desde_date = qdesde.toPyDate()
            hasta_date = qhasta.toPyDate()

            if hasta_date < desde_date:
                self.totals_label.setText("<font color='red'>Fecha 'Hasta' menor que 'Desde'</font>")
                self.table.setRowCount(0)
                return

            # Obtener todas las transacciones (cacheadas si es posible)
            if self._all_transacciones is None:
                self._all_transacciones = self.firebase_client.get_transacciones_by_proyecto(
                    self.proyecto_id
                )
            transacciones = self._all_transacciones or []

            # Mapas de cuentas y categorías
            cuentas_list = self.firebase_client.get_cuentas_by_proyecto(self.proyecto_id)
            categorias_list = self.firebase_client.get_categorias_by_proyecto(self.proyecto_id)
            
            cuentas_map = {str(c["id"]): c.get("nombre", "Sin nombre") for c in cuentas_list}
            categorias_map = {str(c["id"]): c.get("nombre", "Sin nombre") for c in categorias_list}

            filtradas: List[Dict[str, Any]] = []
            total_ingresos = 0.0
            total_gastos = 0.0

            for t in transacciones:
                # --- CORRECCIÓN CLAVE: Uso de _parse_date para evitar error offset-naive ---
                fecha_date = self._parse_date(t.get("fecha"))
                
                if not fecha_date:
                    continue

                if not (desde_date <= fecha_date <= hasta_date):
                    continue
                
                # Preparar datos
                fecha_str = fecha_date.strftime("%Y-%m-%d")
                tipo = str(t.get("tipo", "")).lower()
                cuenta_nombre = cuentas_map.get(str(t. get("cuenta_id", "")), str(t.get("cuenta_id", "Sin cuenta")))
                categoria_nombre = categorias_map.get(str(t. get("categoria_id", "")), str(t.get("categoria_id", "Sin categoría")))
                descripcion = t.get("descripcion", "")
                
                # ✅ CORREGIDO: Validación robusta de monto
                try:
                    monto_val = t.get("monto", 0.0)
                    if monto_val is None or monto_val == '':
                        monto = 0.0
                    else:
                        monto = float(monto_val)
                except (ValueError, TypeError):
                    monto = 0.0

                if "ingreso" in tipo:
                    total_ingresos += monto
                elif "gasto" in tipo:
                    total_gastos += monto

                # ✅ NUEVO: Detectar adjuntos
                adjuntos_paths = t.get("adjuntos_paths", [])
                adjuntos_count = len(adjuntos_paths) if adjuntos_paths else 0
                adjuntos_display = f"📎 {adjuntos_count}" if adjuntos_count > 0 else ""
                
                # 🔍 DEBUG TEMPORAL
                if adjuntos_count > 0:
                    logger.info(f"✅ Transacción {t. get('id')} tiene {adjuntos_count} adjuntos:  {adjuntos_paths}")

                # Estructura EXACTA que espera ReportGenerator
                # Guardamos tipo original en '_raw_tipo' para coloreado interno
                filtradas.append(
                    {
                        "Fecha": fecha_str,
                        "Cuenta": cuenta_nombre,
                        "Categoría": categoria_nombre,
                        "Descripción": descripcion,
                        "Monto": monto,
                        "Tipo": t.get("tipo", "").capitalize(),  # Visible en Excel/PDF
                        "Adjuntos": adjuntos_display,  # ✅ NUEVO: Columna de adjuntos
                        "_raw_tipo":  tipo,  # Uso interno para colores
                        "_transaction_id": t.get("id", ""),  # ✅ NUEVO: ID para sección de adjuntos
                        "_adjuntos_paths": adjuntos_paths  # ✅ NUEVO:  Paths de archivos
                    }
                )

            self.transacciones_filtradas = filtradas

            # --- Poblar tabla visual (agregar columna de adjuntos)
            self.table.setRowCount(len(filtradas))
            for row, t in enumerate(filtradas):
                # Fecha
                self. table.setItem(row, 0, QTableWidgetItem(t["Fecha"]))

                # Tipo
                tipo_item = QTableWidgetItem(t["Tipo"])
                raw_tipo = t["_raw_tipo"]
                if "ingreso" in raw_tipo: 
                    tipo_item.setForeground(Qt.GlobalColor. darkGreen)
                elif "gasto" in raw_tipo: 
                    tipo_item.setForeground(Qt.GlobalColor.darkRed)
                self.table.setItem(row, 1, tipo_item)

                # Cuenta
                self. table.setItem(row, 2, QTableWidgetItem(t["Cuenta"]))
                # Categoría
                self. table.setItem(row, 3, QTableWidgetItem(t["Categoría"]))
                # Descripción
                self.table.setItem(row, 4, QTableWidgetItem(t["Descripción"]))

                # ✅ CORREGIDO: Monto con validación
                try:
                    # ✅ CORREGIDO: Monto - Asegurar conversión a float
                    monto_valor = t.get('Monto', 0.0)
                    if not isinstance(monto_valor, (int, float)):
                        try:
                            monto_valor = float(monto_valor)
                        except Exception:
                            monto_valor = 0.0
                    
                    monto_display = f"RD$ {monto_valor:,.2f}"
                    monto_item = QTableWidgetItem(monto_display)
                except Exception:
                    monto_display = "RD$ 0.00"
                    monto_item = QTableWidgetItem(monto_display)

                monto_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if "ingreso" in raw_tipo: 
                    monto_item.setForeground(Qt.GlobalColor.darkGreen)
                elif "gasto" in raw_tipo:
                    monto_item.setForeground(Qt.GlobalColor.darkRed)
                self.table.setItem(row, 5, monto_item)
                
                # ✅ NUEVO: Columna Adjuntos
                adjuntos_item = QTableWidgetItem(t["Adjuntos"])
                adjuntos_item.setTextAlignment(Qt. AlignmentFlag.AlignCenter | Qt.AlignmentFlag. AlignVCenter)
                if t["Adjuntos"]: 
                    adjuntos_item.setForeground(Qt. GlobalColor.darkBlue)
                self.table.setItem(row, 6, adjuntos_item)

            # Totales
            total_trans = len(filtradas)
            if total_trans == 0:
                self.totals_label.setText("No hay transacciones en el rango seleccionado.")
            else:
                balance = total_ingresos - total_gastos
                self.totals_label.setText(
                    f"<b>Items:</b> {total_trans} | "
                    f"<b>Ingresos:</b> <font color='green'>RD$ {total_ingresos:,.2f}</font> | "
                    f"<b>Gastos:</b> <font color='red'>RD$ {total_gastos:,.2f}</font> | "
                    f"<b>Balance: </b> <font color='#004080'>RD$ {balance: ,.2f}</font>"
                )

        except Exception as e: 
            logger.error(f"Error loading report data: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Error al cargar el reporte:\n{str(e)}")
            
# ------------------------------------------------------------------ EXPORT

    def _exportar_pdf(self):
        """Exportar datos filtrados a PDF usando ReportGenerator con adjuntos incrustados."""
        if not self.transacciones_filtradas:
            QMessageBox.information(self, "Sin datos", "No hay datos para exportar.")
            return

        # Diálogo de guardado
        fecha_ini = self.date_desde. date().toString("yyyy-MM-dd")
        fecha_fin = self.date_hasta.date().toString("yyyy-MM-dd")
        nombre_defecto = f"Reporte_Detallado_{fecha_ini}_{fecha_fin}.pdf"

        filepath, _ = QFileDialog.getSaveFileName(self, "Guardar PDF", nombre_defecto, "PDF Files (*.pdf)")
        if not filepath:
            return

        try:
            # Preparar datos para el generador (mantener campos internos para adjuntos)
            data_export = []
            for t in self.transacciones_filtradas:
                row = t.copy()
                # NO eliminar _transaction_id y _adjuntos_paths (los necesita el generador)
                # Solo eliminar _raw_tipo si existe
                if "_raw_tipo" in row:
                    del row["_raw_tipo"]
                data_export.append(row)

            # Configurar generador
            rango = f"{self.date_desde.text()} - {self.date_hasta. text()}"
            
            # ✅ MODIFICADO: Mapa de columnas incluyendo Adjuntos
            # ✅ MODIFICADO:  Mapa de columnas incluyendo Adjuntos Y columnas internas
            col_map = {
                "Fecha":  "Fecha",
                "Tipo": "Tipo",
                "Cuenta": "Cuenta",
                "Categoría": "Categoría",
                "Descripción": "Descripción",
                "Monto": "Monto",
                "Adjuntos": "Adjuntos",
                "_transaction_id": "_transaction_id",  # ✅ NUEVO:  Mantener columna interna
                "_adjuntos_paths": "_adjuntos_paths"   # ✅ NUEVO:  Mantener columna interna
            }

            # ✅ MODIFICADO:  Pasar firebase_client y proyecto_id para adjuntos
            rg = ReportGenerator(
                data=data_export,
                title="Reporte Detallado de Transacciones",
                project_name=str(self.proyecto_id),
                date_range=rango,
                currency_symbol="RD$",
                column_map=col_map,
                firebase_client=self. firebase_client,  # ✅ NUEVO
                proyecto_id=self.proyecto_id  # ✅ NUEVO
            )
            
            success, msg = rg. to_pdf(filepath)
            
            if success:
                QMessageBox.information(self, "Éxito", f"PDF exportado correctamente:\n{filepath}")
            else:
                QMessageBox.warning(self, "Error PDF", f"No se pudo generar el PDF:\n{msg}")

        except Exception as e:
            logger.error(f"Error exporting PDF: {e}")
            QMessageBox.critical(self, "Error", f"Error inesperado al exportar:\n{e}")


    def _exportar_excel(self):
        """Exportar datos filtrados a Excel usando ReportGenerator."""
        if not self.transacciones_filtradas:
            QMessageBox.information(self, "Sin datos", "No hay datos para exportar.")
            return

        fecha_ini = self.date_desde.date().toString("yyyy-MM-dd")
        fecha_fin = self.date_hasta.date().toString("yyyy-MM-dd")
        nombre_defecto = f"Reporte_Detallado_{fecha_ini}_{fecha_fin}.xlsx"

        filepath, _ = QFileDialog.getSaveFileName(self, "Guardar Excel", nombre_defecto, "Excel Files (*.xlsx)")
        if not filepath:
            return

        try:
            # Preparar datos
            data_export = []
            for t in self.transacciones_filtradas:
                row = t.copy()
                if "_raw_tipo" in row:
                    del row["_raw_tipo"]
                data_export.append(row)

            rango = f"{self.date_desde.text()} - {self.date_hasta.text()}"
            
            rg = ReportGenerator(
                data=data_export,
                title="Reporte Detallado de Transacciones",
                project_name=str(self.proyecto_id),
                date_range=rango,
                currency_symbol="RD$"
            )
            
            success, msg = rg.to_excel(filepath)
            
            if success:
                QMessageBox.information(self, "Éxito", "Excel exportado correctamente.")
            else:
                QMessageBox.warning(self, "Error Excel", f"No se pudo generar el Excel:\n{msg}")

        except Exception as e:
            logger.error(f"Error exporting Excel: {e}")
            QMessageBox.critical(self, "Error", f"Error inesperado al exportar:\n{e}")