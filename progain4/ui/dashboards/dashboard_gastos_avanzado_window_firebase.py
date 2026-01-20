from typing import List, Dict, Any, Optional
from datetime import date
import logging

from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QComboBox,
    QDateEdit,
    QFileDialog,
    QMessageBox,
    QTreeWidget,
    QTreeWidgetItem,
    QSplitter,
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QGuiApplication
from PyQt6.QtWebEngineWidgets import QWebEngineView

import pandas as pd
import plotly.express as px

# Reemplazamos pdfkit/tempfile/base64 con nuestro ReportGenerator
try:
    from progain4.services.report_generator import ReportGenerator
    REPORT_GENERATOR_AVAILABLE = True
except ImportError:
    REPORT_GENERATOR_AVAILABLE = False

logger = logging.getLogger(__name__)

class DashboardGastosAvanzadoWindowFirebase(QMainWindow):
    """
    Dashboard avanzado de gastos (Firebase).

    - Filtro por:
        * Cuenta
        * Periodo (fecha desde/hasta)
        * Categoría / Subcategoría
    - Panel lateral con árbol de categorías/subcategorías y checkbox para incluir/excluir.
    - Gráficos Plotly (donut, pastel, barras).
    - Exportación a imagen y PDF con tabla de detalle.

    Requiere en FirebaseClient:
      - get_cuentas_por_proyecto(proyecto_id)
      - get_rango_fechas_transacciones_gasto(proyecto_id) -> (date_min, date_max) o (None, None)
      - get_gastos_agrupados_por_categoria(
            proyecto_id,
            fecha_inicio: date,
            fecha_fin: date,
            cuenta_id: Optional[str],
        ) -> List[Dict[nombre, total_gastado]]

      - get_gastos_agrupados_por_categoria_y_subcategoria(
            proyecto_id,
            fecha_inicio: date,
            fecha_fin: date,
            cuenta_id: Optional[str],
        ) -> List[Dict[categoria, subcategoria, cuenta, total_gastado]]

      - get_transacciones_gasto_detalle(
            proyecto_id,
            fecha_inicio: date,
            fecha_fin: date,
            cuenta_id: Optional[str],
        ) -> List[Dict[categoria, subcategoria, monto, fecha]]
    """

    def __init__(self, firebase_client, proyecto_id: str, proyecto_nombre: str, moneda: str, parent=None):
        super().__init__(parent)
        self.firebase_client = firebase_client
        self.proyecto_id = proyecto_id
        self.proyecto_nombre = proyecto_nombre
        self.moneda = moneda or "RD$"

        self.setWindowTitle(f"Gastos Avanzados (Firebase) - {proyecto_nombre}")
        self.resize(1400, 800)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(splitter)

        # ----------------- PANEL LATERAL -----------------
        lateral_widget = QWidget()
        lateral_layout = QVBoxLayout(lateral_widget)

        # Filtro de cuenta
        lateral_layout.addWidget(QLabel("Cuenta:"))
        self.combo_cuentas = QComboBox()
        lateral_layout.addWidget(self.combo_cuentas)

        # Filtro: Categoría/Subcategoría
        lateral_layout.addWidget(QLabel("Filtrar por:"))
        self.combo_filtro_lateral = QComboBox()
        self.combo_filtro_lateral.addItems(["Categoría", "Subcategoría"])
        lateral_layout.addWidget(self.combo_filtro_lateral)

        lateral_layout.addWidget(QLabel("Categorías/Subcategorías:"))
        self.tree_categorias = QTreeWidget()
        self.tree_categorias.setHeaderLabels(["Nombre", "Total"])
        lateral_layout.addWidget(self.tree_categorias, stretch=1)

        self.btn_select_all = QPushButton("Seleccionar todo")
        self.btn_clear = QPushButton("Limpiar selección")
        lateral_layout.addWidget(self.btn_select_all)
        lateral_layout.addWidget(self.btn_clear)

        splitter.addWidget(lateral_widget)

        # ----------------- PANEL CENTRAL -----------------
        central_widget = QWidget()
        central_layout = QVBoxLayout(central_widget)

        # Filtros superiores (fechas + tipo de gráfico)
        filtro_layout = QHBoxLayout()
        filtro_layout.addWidget(QLabel("Desde:"))
        self.date_desde = QDateEdit()
        self.date_desde.setCalendarPopup(True)
        filtro_layout.addWidget(self.date_desde)

        filtro_layout.addWidget(QLabel("Hasta:"))
        self.date_hasta = QDateEdit()
        self.date_hasta.setCalendarPopup(True)
        filtro_layout.addWidget(self.date_hasta)

        filtro_layout.addWidget(QLabel("Tipo de gráfico:"))
        self.combo_tipo_grafico = QComboBox()
        self.combo_tipo_grafico.addItems(["Donut", "Pastel", "Barra"])
        filtro_layout.addWidget(self.combo_tipo_grafico)

        central_layout.addLayout(filtro_layout)

        # Resumen total
        self.label_resumen = QLabel(f"Total gastado: {self.moneda} 0.00")
        self.label_resumen.setStyleSheet("font-size:18px;font-weight:bold;")
        central_layout.addWidget(self.label_resumen)

        # Vista HTML para Plotly
        self.web_view = QWebEngineView()
        central_layout.addWidget(self.web_view, stretch=1)

        # Botones de exportación
        export_layout = QHBoxLayout()
        self.btn_export_img = QPushButton("Exportar imagen")
        self.btn_export_pdf = QPushButton("Exportar PDF")
        export_layout.addWidget(self.btn_export_img)
        export_layout.addWidget(self.btn_export_pdf)
        export_layout.addStretch()
        central_layout.addLayout(export_layout)

        splitter.addWidget(central_widget)
        splitter.setStretchFactor(1, 3)

        # Estado
        self.datos_full: Optional[pd.DataFrame] = None
        self.figura_actual = None

        # Inicialización de combos/datos
        self._init_cuentas()
        self._init_rango_fechas()

        # Conexiones
        self.combo_cuentas.currentIndexChanged.connect(self.cargar_datos_categorias)
        self.combo_filtro_lateral.currentIndexChanged.connect(self.cargar_datos_categorias)
        self.tree_categorias.itemChanged.connect(self.actualizar_dashboard)
        self.date_desde.dateChanged.connect(self.actualizar_dashboard)
        self.date_hasta.dateChanged.connect(self.actualizar_dashboard)
        self.combo_tipo_grafico.currentIndexChanged.connect(self.actualizar_dashboard)
        self.btn_select_all.clicked.connect(self.seleccionar_todo)
        self.btn_clear.clicked.connect(self.limpiar_seleccion)
        self.btn_export_img.clicked.connect(self.exportar_grafico_imagen)
        self.btn_export_pdf.clicked.connect(self.exportar_reporte_pdf)

        # Carga inicial
        self.cargar_datos_categorias()

        # Centrar ventana
        self.center_window()

    # ----------------------------------------------------- Helpers UI

    def center_window(self):
        frame_geom = self.frameGeometry()
        screen = QGuiApplication.primaryScreen()
        if screen:
            screen_center = screen.availableGeometry().center()
            frame_geom.moveCenter(screen_center)
            self.move(frame_geom.topLeft())

    def _init_cuentas(self):
        self.combo_cuentas.clear()
        self.combo_cuentas.addItem("Todas", None)
        try:
            cuentas = self.firebase_client.get_cuentas_por_proyecto(self.proyecto_id) or []
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudieron cargar las cuentas del proyecto:\n{e}",
            )
            cuentas = []

        for c in cuentas:
            # c["id"] es int
            self.combo_cuentas.addItem(c.get("nombre", str(c["id"])), c["id"])


    def _init_rango_fechas(self):
        try:
            fecha_ini, fecha_fin = self.firebase_client.get_rango_fechas_transacciones_gasto(
                self.proyecto_id
            )
        except Exception:
            fecha_ini = fecha_fin = None

        if fecha_ini:
            q_ini = QDate(fecha_ini.year, fecha_ini.month, fecha_ini.day)
        else:
            q_ini = QDate.currentDate().addMonths(-1)

        if fecha_fin:
            q_fin = QDate(fecha_fin.year, fecha_fin.month, fecha_fin.day)
        else:
            q_fin = QDate.currentDate()

        self.date_desde.setDate(q_ini)
        self.date_hasta.setDate(q_fin)

    def _get_periodo(self) -> tuple[date, date]:
        qd_ini: QDate = self.date_desde.date()
        qd_fin: QDate = self.date_hasta.date()
        return (
            date(qd_ini.year(), qd_ini.month(), qd_ini.day()),
            date(qd_fin.year(), qd_fin.month(), qd_fin.day()),
        )

    # ----------------------------------------------------- Datos categorías / subcategorías

    def cargar_datos_categorias(self):
        """Llena el árbol lateral y el DataFrame `datos_full` desde Firebase."""
        self.tree_categorias.blockSignals(True)
        self.tree_categorias.clear()
        self.tree_categorias.blockSignals(False)

        filtro_tipo = self.combo_filtro_lateral.currentText()
        cuenta_id = self.combo_cuentas.currentData()
        fecha_ini, fecha_fin = self._get_periodo()

        font_bold = QFont()
        font_bold.setBold(True)

        # ================== POR CATEGORÍA ==================
        if filtro_tipo == "Categoría":
            try:
                raw = (
                    self.firebase_client.get_gastos_agrupados_por_categoria(
                        self.proyecto_id, fecha_ini, fecha_fin, cuenta_id
                    )
                    or []
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"No se pudieron cargar los gastos por categoría:\n{e}",
                )
                raw = []

            self.datos_full = pd.DataFrame(raw)
            if self.datos_full.empty:
                self.actualizar_dashboard()
                return

            # Esperamos columnas: nombre (categoría), total_gastado
            for _, row in self.datos_full.iterrows():
                nombre = row.get("nombre") or row.get("categoria") or "Sin nombre"
                total_cat = float(row.get("total_gastado", 0.0))
                cat_item = QTreeWidgetItem(
                    [str(nombre), f"{self.moneda}{total_cat:,.2f}"]
                )
                cat_item.setFont(0, font_bold)
                cat_item.setFlags(
                    cat_item.flags() | Qt.ItemFlag.ItemIsUserCheckable
                )
                cat_item.setCheckState(0, Qt.CheckState.Checked)
                self.tree_categorias.addTopLevelItem(cat_item)

        # ================== POR SUBCATEGORÍA ==================
        else:
            try:
                raw = (
                    self.firebase_client.get_gastos_agrupados_por_categoria_y_subcategoria(
                        self.proyecto_id, fecha_ini, fecha_fin, cuenta_id
                    )
                    or []
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"No se pudieron cargar los gastos por subcategoría:\n{e}",
                )
                raw = []

            self.datos_full = pd.DataFrame(raw)
            if self.datos_full.empty:
                self.actualizar_dashboard()
                return

            # Esperamos columnas: categoria, subcategoria (o nombre), cuenta?, total_gastado
            categorias = self.datos_full.groupby(["categoria"])
            for cat, cat_group in categorias:
                nombre_cat = (
                    cat if isinstance(cat, str) else cat[0] if isinstance(cat, tuple) else str(cat)
                )
                total_cat = float(cat_group["total_gastado"].sum())
                cat_item = QTreeWidgetItem(
                    [str(nombre_cat), f"{self.moneda}{total_cat:,.2f}"]
                )
                cat_item.setFont(0, font_bold)
                cat_item.setFlags(
                    cat_item.flags() | Qt.ItemFlag.ItemIsUserCheckable
                )
                cat_item.setCheckState(0, Qt.CheckState.Checked)

                subcats = cat_group[cat_group["subcategoria"].notnull()]
                for _, sub_row in subcats.iterrows():
                    subcat = sub_row["subcategoria"]
                    total_sub = float(sub_row["total_gastado"])
                    sub_item = QTreeWidgetItem(
                        [str(subcat), f"{self.moneda}{total_sub:,.2f}"]
                    )
                    sub_item.setFlags(
                        sub_item.flags() | Qt.ItemFlag.ItemIsUserCheckable
                    )
                    sub_item.setCheckState(0, Qt.CheckState.Checked)
                    cat_item.addChild(sub_item)

                self.tree_categorias.addTopLevelItem(cat_item)
                cat_item.setExpanded(True)

        self.actualizar_dashboard()

    # ----------------------------------------------------- Actualizar gráfico

    def actualizar_dashboard(self):
        filtro_tipo = self.combo_filtro_lateral.currentText()
        cuenta_id = self.combo_cuentas.currentData()
        fecha_ini_q = self.date_desde.date().toString("yyyy-MM-dd")
        fecha_fin_q = self.date_hasta.date().toString("yyyy-MM-dd")
        tipo_grafico = self.combo_tipo_grafico.currentText()
        df = self.datos_full if self.datos_full is not None else pd.DataFrame()

        if df.empty:
            self.web_view.setHtml("<h2>No hay datos para mostrar</h2>")
            self.label_resumen.setText(f"Total gastado: {self.moneda} 0.00")
            self.figura_actual = None
            return

        # --- Filtrar por selección en árbol ---
        seleccionadas = []

        if filtro_tipo == "Categoría":
            columna_nombre = "nombre" if "nombre" in df.columns else "categoria"
            if columna_nombre not in df.columns:
                self.web_view.setHtml("<h2>No hay datos para mostrar</h2>")
                self.label_resumen.setText(f"Total gastado: {self.moneda} 0.00")
                self.figura_actual = None
                return

            for i in range(self.tree_categorias.topLevelItemCount()):
                cat_item = self.tree_categorias.topLevelItem(i)
                if cat_item.checkState(0) == Qt.CheckState.Checked:
                    seleccionadas.append(cat_item.text(0))

            df_filtrado = df[df[columna_nombre].isin(seleccionadas)]
            nombres_col = columna_nombre

        else:  # Subcategoría
            nombres_col = "subcategoria"
            if nombres_col not in df.columns:
                self.web_view.setHtml("<h2>No hay datos para mostrar</h2>")
                self.label_resumen.setText(f"Total gastado: {self.moneda} 0.00")
                self.figura_actual = None
                return

            seleccionadas_sub = []
            for i in range(self.tree_categorias.topLevelItemCount()):
                cat_item = self.tree_categorias.topLevelItem(i)
                if cat_item.checkState(0) == Qt.CheckState.Checked:
                    seleccionadas_sub.append(cat_item.text(0))
                for j in range(cat_item.childCount()):
                    sub_item = cat_item.child(j)
                    if sub_item.checkState(0) == Qt.CheckState.Checked:
                        seleccionadas_sub.append(sub_item.text(0))

            df_filtrado = df[df[nombres_col].isin(seleccionadas_sub)]

        # Filtro adicional por cuenta, si columna 'cuenta' existe
        if cuenta_id and "cuenta" in df_filtrado.columns:
            cuenta_nombre = self.combo_cuentas.currentText()
            df_filtrado = df_filtrado[df_filtrado["cuenta"] == cuenta_nombre]

        if df_filtrado.empty:
            self.web_view.setHtml("<h2>No hay datos para mostrar</h2>")
            self.label_resumen.setText(f"Total gastado: {self.moneda} 0.00")
            self.figura_actual = None
            return

        total = float(df_filtrado["total_gastado"].sum())
        self.label_resumen.setText(f"Total gastado: {self.moneda} {total:,.2f}")

        # --- Construcción del gráfico ---
        titulo_base = "Gastos por Categoría" if filtro_tipo == "Categoría" else "Gastos por Subcategoría"
        subtitulo = f"{fecha_ini_q} a {fecha_fin_q}"

        if tipo_grafico == "Donut":
            fig = px.pie(
                df_filtrado,
                names=nombres_col,
                values="total_gastado",
                hole=0.55,
                color_discrete_sequence=px.colors.qualitative.Pastel,
                title=f"{titulo_base}<br><sup>{subtitulo}</sup>",
            )
        elif tipo_grafico == "Pastel":
            fig = px.pie(
                df_filtrado,
                names=nombres_col,
                values="total_gastado",
                color_discrete_sequence=px.colors.qualitative.Pastel,
                title=f"{titulo_base}<br><sup>{subtitulo}</sup>",
            )
        else:  # Barra
            fig = px.bar(
                df_filtrado,
                x="total_gastado",
                y=nombres_col,
                orientation="h",
                color=nombres_col,
                color_discrete_sequence=px.colors.qualitative.Pastel,
                title=f"{titulo_base}<br><sup>{subtitulo}</sup>",
            )

        fig.update_layout(margin=dict(l=30, r=30, t=60, b=30), font=dict(size=15))
        fig.update_traces(textposition="inside", texttemplate=f"%{{label}}<br>{self.moneda}%{{value:,.2f}}")

        html = fig.to_html(include_plotlyjs="cdn", full_html=False)
        self.web_view.setHtml(html)
        self.figura_actual = fig

    # ----------------------------------------------------- Selección árbol

    def seleccionar_todo(self):
        for i in range(self.tree_categorias.topLevelItemCount()):
            cat_item = self.tree_categorias.topLevelItem(i)
            cat_item.setCheckState(0, Qt.CheckState.Checked)
            for j in range(cat_item.childCount()):
                sub_item = cat_item.child(j)
                sub_item.setCheckState(0, Qt.CheckState.Checked)

    def limpiar_seleccion(self):
        for i in range(self.tree_categorias.topLevelItemCount()):
            cat_item = self.tree_categorias.topLevelItem(i)
            cat_item.setCheckState(0, Qt.CheckState.Unchecked)
            for j in range(cat_item.childCount()):
                sub_item = cat_item.child(j)
                sub_item.setCheckState(0, Qt.CheckState.Unchecked)

    # ----------------------------------------------------- Exportación imagen

    def exportar_grafico_imagen(self):
        if not self.figura_actual:
            return

        from datetime import datetime

        fecha_str = datetime.now().strftime("%Y-%m-%d")
        nombre_archivo = f"{self.proyecto_nombre}_Dashboard_Gastos_Avanzado_{fecha_str}.png"
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar gráfico como imagen...",
            nombre_archivo,
            "Imagen PNG (*.png)",
        )
        if filepath:
            try:
                self.figura_actual.write_image(filepath, width=1200, height=700)
                QMessageBox.information(self, "Éxito", "Gráfico guardado correctamente.", parent=self)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"No se pudo guardar la imagen:\n{e}")

    # ----------------------------------------------------- Datos detalle para PDF

    def obtener_tabla_reporte(self) -> pd.DataFrame:
        cuenta_id = self.combo_cuentas.currentData()
        fecha_ini, fecha_fin = self._get_periodo()

        try:
            raw = self.firebase_client.get_transacciones_gasto_detalle(
                self.proyecto_id, fecha_ini, fecha_fin, cuenta_id
            ) or []
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudieron obtener los datos de detalle para el reporte:\n{e}",
            )
            return pd.DataFrame()

        return pd.DataFrame(raw)

    # ----------------------------------------------------- Exportación PDF

    def exportar_reporte_pdf(self):
            """
            Genera un PDF profesional con el resumen del dashboard (Gráfico + Tabla Resumen).
            Usa los mismos datos agregados (self.datos_full) que se ven en pantalla.
            """
            if not self.figura_actual or self.datos_full is None or self.datos_full.empty:
                QMessageBox.warning(self, "Sin datos", "No hay información para exportar.")
                return

            filename, _ = QFileDialog.getSaveFileName(self, "Guardar PDF", "Reporte_Gastos_Avanzado.pdf", "PDF (*.pdf)")
            if not filename: return

            try:
                from progain4.services.report_generator import ReportGenerator
                
                # 1. Preparar datos DIRECTAMENTE del Dashboard (self.datos_full)
                # Así aseguramos que el reporte coincida con lo que ves en pantalla.
                df = self.datos_full.copy()
                
                datos_exportar = []
                
                # Detectar columnas dinámicas (puede ser 'nombre' o 'categoria' según la consulta)
                col_cat = "nombre" if "nombre" in df.columns else "categoria"
                col_sub = "subcategoria" if "subcategoria" in df.columns else None
                col_monto = "total_gastado"
                
                # Procesar filas
                if col_sub:
                    # Caso: Vista por Subcategoría (agrupamos visualmente)
                    # Ordenamos por Categoría y luego por Monto descendente
                    df = df.sort_values(by=[col_cat, col_monto], ascending=[True, False])
                    
                    for _, row in df.iterrows():
                        monto = float(row.get(col_monto, 0))
                        if monto > 0:
                            datos_exportar.append({
                                "Categoría": str(row.get(col_cat, "Sin Categoría")),
                                "Subcategoría": str(row.get(col_sub, "") or ""),
                                "Monto": monto, # El ReportGenerator aplicará formato de moneda
                                "Tipo": "Gasto" # Para que salga en rojo
                            })
                else:
                    # Caso: Vista por Categoría (más simple)
                    df = df.sort_values(by=[col_monto], ascending=False)
                    for _, row in df.iterrows():
                        monto = float(row.get(col_monto, 0))
                        if monto > 0:
                            datos_exportar.append({
                                "Categoría": str(row.get(col_cat, "Sin Categoría")),
                                "Monto": monto,
                                "Tipo": "Gasto"
                            })

                # 2. Configurar generador
                rango = f"{self.date_desde.text()} - {self.date_hasta.text()}"
                
                # Mapa de columnas para el PDF (Título columna -> Título reporte)
                cols_map = {"Categoría": "Categoría", "Monto": "Total Gastado"}
                if col_sub:
                    cols_map["Subcategoría"] = "Subcategoría"

                rg = ReportGenerator(
                    data=datos_exportar,
                    title="Reporte de Gastos Avanzado",
                    project_name=self.proyecto_nombre,
                    date_range=rango,
                    currency_symbol=self.moneda,
                    column_map=cols_map
                )
                
                # 3. Exportar (Gráfico + Tabla de datos)
                figures = {'grafico_principal': self.figura_actual}
                
                ok, msg = rg.dashboard_to_pdf(filename, figures)
                
                if ok:
                    QMessageBox.information(self, "Éxito", "PDF exportado correctamente.")
                else:
                    QMessageBox.warning(self, "Error", f"Error al exportar: {msg}")

            except Exception as e:
                logger.error(f"Error export PDF: {e}")
                QMessageBox.critical(self, "Error", str(e))