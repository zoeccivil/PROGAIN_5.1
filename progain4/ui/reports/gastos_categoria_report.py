from collections import defaultdict
from datetime import datetime, date
from typing import Dict, Any, List, Optional
import logging

from PyQt6.QtCore import Qt, QDate
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QTreeWidget,
    QTreeWidgetItem,
    QDateEdit,
    QComboBox,
    QFileDialog,
    QMessageBox,
)
from PyQt6.QtGui import QFont

# Importamos el generador de reportes desde su ubicación correcta
try:
    from progain4.services.report_generator import ReportGenerator
    REPORT_GENERATOR_AVAILABLE = True
except ImportError:
    REPORT_GENERATOR_AVAILABLE = False
    logging.warning("ReportGenerator no encontrado en progain4.services.report_generator")

logger = logging.getLogger(__name__)


class GastosPorCategoriaWindowFirebase(QMainWindow):
    """
    Versión Firebase del reporte 'Gastos por Categoría' de PROGRAIN 3.0.

    - Usa FirebaseClient para leer transacciones, categorías y subcategorías.
    - Agrega gastos por categoría/subcategoría.
    - Muestra un árbol (categorías como padre, subcategorías como hijos).
    - Exporta a PDF/Excel usando report_generator.ReportGenerator.
    """

    def __init__(
        self,
        firebase_client,
        proyecto_id: str,
        proyecto_nombre: str,
        moneda: str = "RD$",
        parent=None,
    ):
        super().__init__(parent)

        self.firebase_client = firebase_client
        self.proyecto_id = proyecto_id
        self.proyecto_nombre = proyecto_nombre
        self.moneda = moneda

        self.setWindowTitle("Gastos por Categoría (Firebase)")
        self.resize(950, 650)
        
        # --- MEJORA UI: Permitir maximizar explícitamente ---
        self.setWindowFlags(Qt.WindowType.Window)

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # --- Filtros de fecha y categoría ---
        filtro_layout = QHBoxLayout()
        filtro_layout.addWidget(QLabel("Desde:"))
        self.date_desde = QDateEdit()
        self.date_desde.setCalendarPopup(True)
        self.date_desde.setDisplayFormat("yyyy-MM-dd")
        # Inicialmente un mes atrás, luego se ajusta con datos reales
        self.date_desde.setDate(QDate.currentDate().addMonths(-1))
        filtro_layout.addWidget(self.date_desde)

        filtro_layout.addWidget(QLabel("Hasta:"))
        self.date_hasta = QDateEdit()
        self.date_hasta.setCalendarPopup(True)
        self.date_hasta.setDisplayFormat("yyyy-MM-dd")
        self.date_hasta.setDate(QDate.currentDate())
        filtro_layout.addWidget(self.date_hasta)

        filtro_layout.addWidget(QLabel("Categoría:"))
        self.combo_categoria = QComboBox()
        filtro_layout.addWidget(self.combo_categoria)

        self.btn_filtrar = QPushButton("Filtrar")
        filtro_layout.addWidget(self.btn_filtrar)

        filtro_layout.addStretch()
        layout.addLayout(filtro_layout)

        # Proyecto
        layout.addWidget(QLabel(f"Proyecto: {self.proyecto_nombre}"))

        # Árbol categorías / subcategorías
        self.tree = QTreeWidget()
        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels(
            ["Categoría / Subcategoría", f"Monto ({self.moneda})"]
        )
        self.tree.setAlternatingRowColors(True)
        # Ajustar ancho columna 0
        self.tree.setColumnWidth(0, 400)
        layout.addWidget(self.tree, stretch=1)

        # Botones exportación
        export_layout = QHBoxLayout()
        self.btn_exportar_excel = QPushButton("Exportar Excel")
        self.btn_exportar_pdf = QPushButton("Exportar PDF")
        
        if not REPORT_GENERATOR_AVAILABLE:
            self.btn_exportar_excel.setEnabled(False)
            self.btn_exportar_pdf.setEnabled(False)
            self.btn_exportar_pdf.setToolTip("ReportGenerator no disponible")

        export_layout.addWidget(self.btn_exportar_excel)
        export_layout.addWidget(self.btn_exportar_pdf)
        export_layout.addStretch()
        layout.addLayout(export_layout)

        # Estado interno para exportar sin depender del árbol
        self._export_rows: List[Dict[str, Any]] = []

        # Cache de transacciones
        self._all_transacciones: Optional[List[Dict[str, Any]]] = None

        # Conexiones
        self.btn_filtrar.clicked.connect(self.actualizar_tree)
        self.btn_exportar_excel.clicked.connect(self.exportar_excel)
        self.btn_exportar_pdf.clicked.connect(self.exportar_pdf)
        self.date_desde.dateChanged.connect(self.actualizar_tree)
        self.date_hasta.dateChanged.connect(self.actualizar_tree)

        # Auto-ajustar columna al expandir un nodo
        self.tree.itemExpanded.connect(self._ajustar_columna_categorias)

        self._cargar_categorias()
        self._init_date_range_from_data()
        self.actualizar_tree()

    # ------------------------------------------------------------------ Fonts

    def _font_bold(self) -> QFont:
        f = QFont()
        f.setBold(True)
        return f

    def _font_normal(self) -> QFont:
        return QFont()

    # ------------------------------------------------------------------ Helper Fechas

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

    # ------------------------------------------------------------------ Rango inicial

    def _init_date_range_from_data(self):
        """
        Inicializa el rango de fechas:
        - Desde: fecha mínima de transacción de tipo 'gasto' del proyecto.
        - Hasta: hoy.
        """
        try:
            if self._all_transacciones is None:
                self._all_transacciones = self.firebase_client.get_transacciones_by_proyecto(
                    self.proyecto_id
                )
            transacciones = self._all_transacciones or []

            fechas_validas = []
            for t in transacciones:
                if str(t.get("tipo", "")).lower() != "gasto":
                    continue
                
                # --- CORRECCIÓN: Uso de helper para parsear fecha ---
                d = self._parse_date(t.get("fecha"))
                if d:
                    fechas_validas.append(d)

            if fechas_validas:
                min_date = min(fechas_validas)
                # Bloquear señales para evitar recarga prematura
                self.date_desde.blockSignals(True)
                self.date_desde.setDate(min_date)
                self.date_desde.blockSignals(False)
            else:
                # Sin gastos: usar último mes
                self.date_desde.setDate(QDate.currentDate().addMonths(-1))

            self.date_hasta.setDate(QDate.currentDate())

        except Exception as e:
            QMessageBox.warning(
                self,
                "Advertencia",
                f"No se pudo inicializar el rango de fechas automáticamente:\n{e}",
            )

    # ------------------------------------------------------------------ Data helpers

    def _cargar_categorias(self):
        """Llena el combo con categorías del proyecto, más 'Todas'."""
        self.combo_categoria.clear()
        self.combo_categoria.addItem("Todas")

        categorias = self.firebase_client.get_categorias_by_proyecto(self.proyecto_id)
        for c in categorias:
            nombre = c.get("nombre", "")
            if nombre:
                self.combo_categoria.addItem(nombre)

    def _obtener_agrupacion_gastos(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Devuelve estructura:
        {
           'CategoriaNombre': [
               {'subcategoria': 'SubcatNombre', 'total_gasto': float},
               ...
           ],
           ...
        }
        """
        # Rango de fechas (QDate -> python date)
        qdesde = self.date_desde.date()
        qhasta = self.date_hasta.date()
        desde_date = qdesde.toPyDate()
        hasta_date = qhasta.toPyDate()

        # Catálogos
        categorias = self.firebase_client.get_categorias_by_proyecto(self.proyecto_id)
        subcategorias = self.firebase_client.get_subcategorias_by_proyecto(
            self.proyecto_id
        )

        cat_by_id = {str(c["id"]): c for c in categorias}
        subcat_by_id = {str(s["id"]): s for s in subcategorias}

        cat_name_by_id = {cid: c.get("nombre", "") for cid, c in cat_by_id.items()}
        subcat_info_by_id = {
            sid: (s.get("nombre", ""), str(s.get("categoria_id", "")))
            for sid, s in subcat_by_id.items()
        }

        # Transacciones
        if self._all_transacciones is None:
            self._all_transacciones = self.firebase_client.get_transacciones_by_proyecto(
                self.proyecto_id
            )
        transacciones = self._all_transacciones or []

        cat_map: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))

        for t in transacciones:
            tipo = str(t.get("tipo", "")).lower()
            if tipo != "gasto":
                continue

            # --- CORRECCIÓN: Uso de helper para parsear fecha ---
            fecha_date = self._parse_date(t.get("fecha"))
            
            if not fecha_date:
                continue

            if not (desde_date <= fecha_date <= hasta_date):
                continue

            categoria_id = str(t.get("categoria_id", ""))
            subcategoria_id = (
                str(t.get("subcategoria_id", ""))
                if t.get("subcategoria_id") is not None
                else None
            )
            
            try:
                monto = float(t.get("monto", 0.0))
            except (ValueError, TypeError):
                monto = 0.0

            cat_nombre = cat_name_by_id.get(categoria_id, "Sin categoría")
            sub_nombre: Optional[str] = None
            if subcategoria_id and subcategoria_id in subcat_info_by_id:
                sub_nombre = subcat_info_by_id[subcategoria_id][0]

            cat_map[cat_nombre][sub_nombre] += monto

        result: Dict[str, List[Dict[str, Any]]] = {}
        for cat_nombre, sub_dict in cat_map.items():
            lista_subs: List[Dict[str, Any]] = []
            for sub_nombre, total_val in sub_dict.items():
                lista_subs.append(
                    {
                        "subcategoria": sub_nombre or "",
                        "total_gasto": total_val,
                    }
                )
            result[cat_nombre] = lista_subs

        return result

    # ------------------------------------------------------------------ UI update

    def actualizar_tree(self):
        """Actualiza el árbol y la estructura para exportación."""
        try:
            categoria_filtro = self.combo_categoria.currentText()
            datos = self._obtener_agrupacion_gastos()

            self.tree.clear()
            self._export_rows = []

            if not datos:
                return

            total_general = 0.0

            for cat in sorted(datos.keys()):
                if categoria_filtro != "Todas" and cat != categoria_filtro:
                    continue

                sub_list = datos[cat]
                total_cat = sum(s["total_gasto"] for s in sub_list)
                total_general += total_cat

                cat_item = QTreeWidgetItem(
                    [cat, f"{self.moneda} {total_cat:,.2f}"]
                )
                cat_item.setFont(0, self._font_bold())
                cat_item.setFont(1, self._font_bold())

                # Fila categoría para exportación
                self._export_rows.append(
                    {
                        "Categoría": cat,
                        "Subcategoría": None,
                        "Monto": total_cat,
                    }
                )

                # Subcategorías
                for s in sorted(
                    sub_list,
                    key=lambda x: (x["subcategoria"] == "", x["subcategoria"] or ""),
                ):
                    sub_nombre = s["subcategoria"] or ""
                    total_sub = s["total_gasto"]
                    sub_item = QTreeWidgetItem(
                        [f"   {sub_nombre}", f"{self.moneda} {total_sub:,.2f}"]
                    )
                    sub_item.setFont(0, self._font_normal())
                    cat_item.addChild(sub_item)

                    if sub_nombre:
                        self._export_rows.append(
                            {
                                "Categoría": cat,
                                "Subcategoría": sub_nombre,
                                "Monto": total_sub,
                            }
                        )

                self.tree.addTopLevelItem(cat_item)
                # Expandir por defecto para ver detalles
                cat_item.setExpanded(True)

            # Total general
            total_item = QTreeWidgetItem(
                ["TOTAL GENERAL", f"{self.moneda} {total_general:,.2f}"]
            )
            total_item.setFont(0, self._font_bold())
            total_item.setFont(1, self._font_bold())
            self.tree.addTopLevelItem(total_item)

            # Fila total general para exportación
            self._export_rows.append(
                {
                    "Categoría": "TOTAL GENERAL",
                    "Subcategoría": None,
                    "Monto": total_general,
                }
            )

            # Ajuste inicial de la columna de texto
            self._ajustar_columna_categorias()

        except Exception as e:
            logger.error(f"Error updating tree: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Error al actualizar el reporte de gastos por categoría:\n{e}",
            )

    def _ajustar_columna_categorias(self):
        """
        Ensancha la columna de 'Categoría / Subcategoría' a un ancho
        considerable cuando se actualiza o se expande un nodo.
        """
        # Ancho base generoso; puedes ajustarlo a tu gusto (en píxeles)
        ancho_base = 400
        self.tree.setColumnWidth(0, ancho_base)

    # ------------------------------------------------------------------ Export

    def exportar_excel(self):
        """Exporta usando ReportGenerator.to_excel_categoria."""
        if not self._export_rows:
            QMessageBox.warning(self, "Sin datos", "No hay datos para exportar.")
            return

        ruta_archivo, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar Excel",
            f"{self.proyecto_nombre}_gastos_categoria.xlsx",
            "Archivos Excel (*.xlsx)",
        )
        if not ruta_archivo:
            return

        try:
            # Aseguramos importación del servicio corregido
            from progain4.services.report_generator import ReportGenerator

            date_range = (
                f"{self.date_desde.date().toString('dd/MM/yyyy')} - "
                f"{self.date_hasta.date().toString('dd/MM/yyyy')}"
            )

            rg = ReportGenerator(
                data=self._export_rows,
                title="Gastos por Categoría",
                project_name=self.proyecto_nombre,
                date_range=date_range,
                currency_symbol=self.moneda,
                column_map={
                    "Categoría": "Categoría",
                    "Subcategoría": "Subcategoría",
                    "Monto": "Monto",
                },
            )
            ok, msg = rg.to_excel_categoria(ruta_archivo)
            if ok:
                QMessageBox.information(
                    self, "Exportación", "Datos exportados a Excel correctamente."
                )
            else:
                QMessageBox.warning(
                    self, "Error Excel", f"No se pudo exportar Excel: {msg}"
                )
        except Exception as e:
            QMessageBox.warning(
                self, "Error Excel", f"No se pudo exportar Excel: {e}"
            )

    def exportar_pdf(self):
        """Exporta usando ReportGenerator.to_pdf_gastos_por_categoria."""
        if not self._export_rows:
            QMessageBox.warning(self, "Sin datos", "No hay datos para exportar.")
            return

        ruta_archivo, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar PDF",
            f"{self.proyecto_nombre}_gastos_categoria.pdf",
            "Archivos PDF (*.pdf)",
        )
        if not ruta_archivo:
            return

        try:
            # Aseguramos importación del servicio corregido
            from progain4.services.report_generator import ReportGenerator

            date_range = (
                f"{self.date_desde.date().toString('dd/MM/yyyy')} - "
                f"{self.date_hasta.date().toString('dd/MM/yyyy')}"
            )

            rg = ReportGenerator(
                data=self._export_rows,
                title="Gastos por Categoría",
                project_name=self.proyecto_nombre,
                date_range=date_range,
                currency_symbol=self.moneda,
                column_map={
                    "Categoría": "Categoría",
                    "Subcategoría": "Subcategoría",
                    "Monto": "Monto",
                },
            )
            
            # Mantenemos la llamada específica al método de reporte por categoría
            # que ya tiene el formato de colores y agrupación ideal
            ok, msg = rg.to_pdf_gastos_por_categoria(ruta_archivo)
            
            if ok:
                QMessageBox.information(
                    self, "Exportación", "Datos exportados a PDF correctamente."
                )
            else:
                QMessageBox.warning(
                    self, "Error PDF", f"No se pudo exportar PDF: {msg}"
                )
        except Exception as e:
            QMessageBox.warning(
                self, "Error PDF", f"No se pudo exportar PDF: {e}"
            )