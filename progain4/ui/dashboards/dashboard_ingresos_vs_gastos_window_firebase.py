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
    QTreeWidget,
    QTreeWidgetItem,
    QSplitter,
    QFileDialog,
    QMessageBox,
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QGuiApplication, QFont
from PyQt6.QtWebEngineWidgets import QWebEngineView

import pandas as pd
import plotly.express as px

# Reemplazamos pdfkit/tempfile/base64 con ReportGenerator
try:
    from progain4.services.report_generator import ReportGenerator
    REPORT_GENERATOR_AVAILABLE = True
except ImportError:
    REPORT_GENERATOR_AVAILABLE = False

logger = logging.getLogger(__name__)

class DashboardIngresosVsGastosWindowFirebase(QMainWindow):
    """
    Dashboard Ingresos vs Gastos (Firebase).

    Mantiene el mismo “orden gráfico” que el dashboard de gastos:

      - Panel lateral:
          * Cuenta
          * Filtro por Categoría / Subcategoría
          * Árbol de categorías/subcategorías con totales

      - Panel central:
          * Filtros de fecha
          * Tipo de gráfico (Barra, Línea, Pastel)
          * Gráfico Plotly (ingreso vs gasto por mes)
          * Tabla dinámica (Income / Expenses / Net Income por mes)

    Requiere en FirebaseClient:

      - get_cuentas_por_proyecto(proyecto_id)

      - get_rango_fechas_transacciones_gasto(proyecto_id)
        (lo usamos como rango inicial; puedes hacer otro para ingresos si quieres)

      - get_agrupado_ingresos_por_mes(
            proyecto_id: str,
            fecha_inicio: date,
            fecha_fin: date,
            cuenta_id: Optional[int],
        ) -> List[Dict[mes, categoria, subcategoria, monto]]

      - get_agrupado_gastos_por_mes(
            proyecto_id: str,
            fecha_inicio: date,
            fecha_fin: date,
            cuenta_id: Optional[int],
        ) -> List[Dict[mes, categoria, subcategoria, monto]]
    """

    def __init__(self, firebase_client, proyecto_id: str, proyecto_nombre: str, moneda: str, parent=None):
        super().__init__(parent)
        self.firebase_client = firebase_client
        self.proyecto_id = proyecto_id
        self.proyecto_nombre = proyecto_nombre
        self.moneda = moneda or "RD$"

        self.setWindowTitle(f"Ingresos vs Gastos (Firebase) - {proyecto_nombre}")
        self.resize(1400, 800)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(splitter)

        # ----------------------------------------------------- Panel lateral
        lateral_widget = QWidget()
        lateral_layout = QVBoxLayout(lateral_widget)

        lateral_layout.addWidget(QLabel("Cuenta:"))
        self.combo_cuentas = QComboBox()
        lateral_layout.addWidget(self.combo_cuentas)

        lateral_layout.addWidget(QLabel("Filtrar por:"))
        self.combo_filtro_lateral = QComboBox()
        self.combo_filtro_lateral.addItems(["Categoría", "Subcategoría"])
        lateral_layout.addWidget(self.combo_filtro_lateral)

        lateral_layout.addWidget(QLabel("Categorías/Subcategorías:"))
        self.tree_categorias = QTreeWidget()
        self.tree_categorias.setHeaderLabels(["Nombre", "Total"])
        lateral_layout.addWidget(self.tree_categorias, stretch=1)

        splitter.addWidget(lateral_widget)

        # ----------------------------------------------------- Panel central
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
        self.combo_tipo_grafico.addItems(["Barra", "Línea", "Pastel"])
        filtro_layout.addWidget(self.combo_tipo_grafico)

        central_layout.addLayout(filtro_layout)

        # Gráfico principal
        self.web_view = QWebEngineView()
        central_layout.addWidget(self.web_view, stretch=2)

        # Tabla dinámica
        self.web_tabla = QWebEngineView()
        central_layout.addWidget(self.web_tabla, stretch=2)

        # Botones exportación
        export_layout = QHBoxLayout()
        self.btn_export_pdf = QPushButton("Exportar PDF")
        export_layout.addStretch()
        export_layout.addWidget(self.btn_export_pdf)
        central_layout.addLayout(export_layout)

        splitter.addWidget(central_widget)
        splitter.setStretchFactor(1, 3)

        # Estado
        self.figura_actual = None
        self.df_ingresos: pd.DataFrame = pd.DataFrame()
        self.df_gastos: pd.DataFrame = pd.DataFrame()

        # Inicialización
        self._init_cuentas()
        self._init_rango_fechas()

        # Conexiones
        self.combo_cuentas.currentIndexChanged.connect(self.actualizar_dashboard)
        self.combo_filtro_lateral.currentIndexChanged.connect(self.actualizar_dashboard)
        self.date_desde.dateChanged.connect(self.actualizar_dashboard)
        self.date_hasta.dateChanged.connect(self.actualizar_dashboard)
        self.combo_tipo_grafico.currentIndexChanged.connect(self.actualizar_dashboard)
        self.btn_export_pdf.clicked.connect(self.exportar_reporte_pdf)

        # Carga inicial
        self.actualizar_dashboard()

        self._center_window()

    # ----------------------------------------------------- Helpers UI

    def _center_window(self):
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
            # get_cuentas_por_proyecto normaliza id como int
            self.combo_cuentas.addItem(c.get("nombre", str(c["id"])), c["id"])

    def _init_rango_fechas(self):
        # Podemos usar el rango de gastos como aproximación del rango total
        try:
            fecha_ini, fecha_fin = self.firebase_client.get_rango_fechas_transacciones_gasto(
                self.proyecto_id
            )
        except Exception:
            fecha_ini = fecha_fin = None

        if fecha_ini:
            q_ini = QDate(fecha_ini.year, fecha_ini.month, fecha_ini.day)
        else:
            q_ini = QDate.currentDate().addMonths(-6)

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

    # ----------------------------------------------------- Datos desde Firebase

# ----------------------------------------------------- Datos desde Firebase

    def _obtener_ingresos_agrupados(self) -> pd.DataFrame:
        cuenta_id = self.combo_cuentas.currentData()
        fecha_ini, fecha_fin = self._get_periodo()
        try:
            raw = self.firebase_client.get_agrupado_ingresos_por_mes(
                self.proyecto_id,
                fecha_ini,
                fecha_fin,
                cuenta_id,
            ) or []
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudieron cargar los ingresos agrupados:\n{e}",
            )
            raw = []

        if not raw:
            return pd.DataFrame(columns=["mes", "categoria", "subcategoria", "monto"])

        df = pd.DataFrame(raw)
        
        # ✅ EXCLUIR TRANSFERENCIAS Y CATEGORÍA 0
        if 'es_transferencia' in df.columns: 
            df = df[df['es_transferencia'] != True]
        if 'categoria' in df.columns:
            df = df[df['categoria'] != '0']
            df = df[df['categoria'] != 0]
            df = df[df['categoria']. notna()]
        
        # normalizamos columnas esperadas
        for col in ["mes", "categoria", "subcategoria", "monto"]: 
            if col not in df.columns:
                df[col] = None
        return df[["mes", "categoria", "subcategoria", "monto"]]

    def _obtener_gastos_agrupados(self) -> pd.DataFrame:
        cuenta_id = self.combo_cuentas.currentData()
        fecha_ini, fecha_fin = self._get_periodo()
        try:
            raw = self.firebase_client.get_agrupado_gastos_por_mes(
                self.proyecto_id,
                fecha_ini,
                fecha_fin,
                cuenta_id,
            ) or []
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudieron cargar los gastos agrupados:\n{e}",
            )
            raw = []

        if not raw:
            return pd.DataFrame(columns=["mes", "categoria", "subcategoria", "monto"])

        df = pd.DataFrame(raw)
        
        # ✅ EXCLUIR TRANSFERENCIAS Y CATEGORÍA 0
        if 'es_transferencia' in df.columns:
            df = df[df['es_transferencia'] != True]
        if 'categoria' in df.columns:
            df = df[df['categoria'] != '0']
            df = df[df['categoria'] != 0]
            df = df[df['categoria'].notna()]
        
        for col in ["mes", "categoria", "subcategoria", "monto"]:
            if col not in df.columns:
                df[col] = None
        return df[["mes", "categoria", "subcategoria", "monto"]]

    def _obtener_gastos_agrupados(self) -> pd.DataFrame:
        cuenta_id = self.combo_cuentas.currentData()
        fecha_ini, fecha_fin = self._get_periodo()
        try:
            raw = self.firebase_client.get_agrupado_gastos_por_mes(
                self.proyecto_id,
                fecha_ini,
                fecha_fin,
                cuenta_id,
            ) or []
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudieron cargar los gastos agrupados:\n{e}",
            )
            raw = []

        if not raw:
            return pd.DataFrame(columns=["mes", "categoria", "subcategoria", "monto"])

        df = pd.DataFrame(raw)
        for col in ["mes", "categoria", "subcategoria", "monto"]:
            if col not in df.columns:
                df[col] = None
        return df[["mes", "categoria", "subcategoria", "monto"]]

    # ----------------------------------------------------- Actualizar dashboard

    def actualizar_dashboard(self):
        self.df_ingresos = self._obtener_ingresos_agrupados()
        self.df_gastos = self._obtener_gastos_agrupados()

        df_ing = self.df_ingresos
        df_gas = self.df_gastos

        # Meses únicos (YYYY-MM)
        meses = sorted(
            set(df_ing["mes"].dropna().tolist() + df_gas["mes"].dropna().tolist())
        )

        if not meses:
            fig = px.bar(x=["Sin datos"], y=[0])
            self.figura_actual = fig
            self.web_view.setHtml(fig.to_html(include_plotlyjs="cdn", full_html=False))
            self.web_tabla.setHtml("<h3>No hay datos en el rango seleccionado.</h3>")
            self.tree_categorias.clear()
            return

        # Series ingresos/gastos por mes
        ingresos_por_mes = (
            df_ing.groupby("mes")["monto"].sum().reindex(meses, fill_value=0).astype(float)
        )
        gastos_por_mes = (
            df_gas.groupby("mes")["monto"].sum().reindex(meses, fill_value=0).astype(float)
        )

        chart_df = pd.DataFrame(
            {
                "Mes": meses,
                "Ingresos": ingresos_por_mes.values,
                "Gastos": gastos_por_mes.values,
            }
        )

        chart_type = self.combo_tipo_grafico.currentText()
        if chart_type == "Barra":
            fig = px.bar(
                chart_df,
                x="Mes",
                y=["Ingresos", "Gastos"],
                labels={"value": f"{self.moneda}", "Mes": "Mes"},
                barmode="group",
            )
            fig.update_traces(marker_line_width=0)
            fig.update_layout(showlegend=True)
        elif chart_type == "Línea":
            fig = px.line(
                chart_df,
                x="Mes",
                y=["Ingresos", "Gastos"],
                markers=True,
            )
        elif chart_type == "Pastel":
            total_ingresos = float(ingresos_por_mes.sum())
            total_gastos = float(gastos_por_mes.sum())
            fig = px.pie(
                names=["Ingresos", "Gastos"],
                values=[total_ingresos, total_gastos],
                hole=0.3,
                title="Ingresos vs Gastos (totales)",
            )
        else:
            fig = px.bar(x=["Sin datos"], y=[0])

        fig.update_layout(margin=dict(l=30, r=30, t=60, b=30), font=dict(size=14))
        self.figura_actual = fig
        self.web_view.setHtml(fig.to_html(include_plotlyjs="cdn", full_html=False))

        # Tabla dinámica
        tabla_html = self._generar_tabla_dinamica(
            df_ing, df_gas, meses, ingresos_por_mes, gastos_por_mes
        )
        self.web_tabla.setHtml(tabla_html)

        # Árbol lateral de categorías/subcategorías
        self._actualizar_arbol_lateral(df_ing, df_gas)

    # ----------------------------------------------------- Árbol lateral

    def _actualizar_arbol_lateral(self, df_ing: pd.DataFrame, df_gas: pd.DataFrame):
        self.tree_categorias.clear()
        font_bold = QFont()
        font_bold.setBold(True)

        filtro_tipo = self.combo_filtro_lateral.currentText()

        # Total por categoría / subcategoría combinando ingresos y gastos
        categorias = set(
            df_ing["categoria"].dropna().tolist() + df_gas["categoria"].dropna().tolist()
        )

        for cat in sorted(categorias, key=lambda x: str(x).upper()):
            total_cat = 0.0
            if not df_ing.empty:
                total_cat += float(
                    df_ing[df_ing["categoria"] == cat]["monto"].sum()
                )
            if not df_gas.empty:
                total_cat += float(
                    df_gas[df_gas["categoria"] == cat]["monto"].sum()
                )

            item_cat = QTreeWidgetItem(
                [str(cat), f"{self.moneda}{total_cat:,.2f}"]
            )
            item_cat.setFont(0, font_bold)
            self.tree_categorias.addTopLevelItem(item_cat)

            # Subcategorías
            if filtro_tipo == "Subcategoría":
                sub_ing = df_ing[df_ing["categoria"] == cat]["subcategoria"].dropna().tolist()
                sub_gas = df_gas[df_gas["categoria"] == cat]["subcategoria"].dropna().tolist()
                subcats = set(sub_ing + sub_gas)
                for sub in sorted(subcats, key=lambda x: str(x).upper()):
                    total_sub = 0.0
                    if not df_ing.empty:
                        total_sub += float(
                            df_ing[
                                (df_ing["categoria"] == cat)
                                & (df_ing["subcategoria"] == sub)
                            ]["monto"].sum()
                        )
                    if not df_gas.empty:
                        total_sub += float(
                            df_gas[
                                (df_gas["categoria"] == cat)
                                & (df_gas["subcategoria"] == sub)
                            ]["monto"].sum()
                        )
                    item_sub = QTreeWidgetItem(
                        [str(sub), f"{self.moneda}{total_sub:,.2f}"]
                    )
                    item_cat.addChild(item_sub)

    # ----------------------------------------------------- Tabla dinámica

    def _generar_tabla_dinamica(self, df_ing, df_gas, meses, s_ing, s_gas):
            """
            Genera HTML detallado para visualización en pantalla con formato correcto.
            Incluye desglose por categorías y subcategorías.
            """
            # CSS para que se vea profesional en el widget web
            html = """
            <style>
                table { 
                    width: 100%; 
                    border-collapse: collapse; 
                    font-family: 'Segoe UI', Arial, sans-serif; 
                    font-size: 11px; 
                    color: #333;
                }
                th { 
                    background-color: #f0f4f8; 
                    border: 1px solid #d1d5db; 
                    padding: 8px; 
                    text-align: right; 
                    font-weight: bold;
                    color: #1f2937;
                }
                td { 
                    border: 1px solid #e5e7eb; 
                    padding: 6px 8px; 
                    text-align: right; 
                }
                td.label { 
                    text-align: left; 
                    font-weight: 600; 
                    background-color: #f9fafb;
                }
                td.sublabel {
                    text-align: left;
                    padding-left: 24px;
                    color: #4b5563;
                }
                .row-total { background-color: #f3f4f6; font-weight: bold; }
                .row-net { background-color: #eef2ff; font-weight: bold; border-top: 2px solid #c7d2fe; }
                .pos { color: #059669; } /* Verde */
                .neg { color: #dc2626; } /* Rojo */
            </style>
            """
            
            html += "<table><thead><tr><th style='text-align:left'>Concepto</th>"
            for m in meses:
                html += f"<th>{m}</th>"
            html += "<th>Total</th></tr></thead><tbody>"

            # --- SECCIÓN INGRESOS ---
            # Fila Resumen Ingresos
            tot_ing_global = 0.0
            cols_ing = ""
            for m in meses:
                val = float(s_ing.get(m, 0))
                tot_ing_global += val
                cols_ing += f"<td class='pos'>{self.moneda} {val:,.2f}</td>"
            
            html += f"<tr class='row-total'><td class='label'>Total Ingresos</td>{cols_ing}<td class='pos'>{self.moneda} {tot_ing_global:,.2f}</td></tr>"

            # (Opcional: Si quisieras detallar ingresos por categoría, agregarías el loop aquí similar a gastos)

            # --- SECCIÓN GASTOS (Detallado) ---
            # Obtener todas las categorías de gastos ordenadas
            cats = sorted(set(df_gas["categoria"].dropna().tolist()), key=lambda x: str(x).upper())
            
            for cat in cats:
                # Fila Categoría
                html += f"<tr><td class='label'>{cat}</td>"
                
                cat_tot_row = 0.0
                cat_cells = ""
                
                # Totales por mes para esta categoría
                for m in meses:
                    val = float(df_gas[(df_gas["mes"] == m) & (df_gas["categoria"] == cat)]["monto"].sum())
                    cat_tot_row += val
                    style = "class='neg'" if val > 0 else "style='color:#ccc'" # Gris si es 0
                    val_fmt = f"-{self.moneda} {val:,.2f}" if val > 0 else f"{self.moneda} 0.00"
                    cat_cells += f"<td {style}>{val_fmt}</td>"
                
                html += f"{cat_cells}<td class='neg'>-{self.moneda} {cat_tot_row:,.2f}</td></tr>"

                # Subcategorías de esta categoría
                subcats = sorted(
                    df_gas[df_gas["categoria"] == cat]["subcategoria"].dropna().unique(),
                    key=lambda x: str(x).upper()
                )
                
                for sub in subcats:
                    html += f"<tr><td class='sublabel'>↳ {sub}</td>"
                    sub_tot_row = 0.0
                    
                    for m in meses:
                        val = float(df_gas[(df_gas["mes"] == m) & (df_gas["categoria"] == cat) & (df_gas["subcategoria"] == sub)]["monto"].sum())
                        sub_tot_row += val
                        # Si el valor es 0, lo mostramos tenue o vacío
                        txt = f"-{self.moneda} {val:,.2f}" if val > 0 else "-"
                        color = "color:#dc2626" if val > 0 else "color:#e5e7eb"
                        html += f"<td style='{color}'>{txt}</td>"
                    
                    # Total Subcategoría
                    txt_tot = f"-{self.moneda} {sub_tot_row:,.2f}" if sub_tot_row > 0 else "-"
                    html += f"<td style='color:#dc2626'>{txt_tot}</td></tr>"

            # --- TOTAL GASTOS ---
            tot_gas_global = 0.0
            cols_gas = ""
            for m in meses:
                val = float(s_gas.get(m, 0))
                tot_gas_global += val
                cols_gas += f"<td class='neg'>-{self.moneda} {val:,.2f}</td>"
            
            html += f"<tr class='row-total' style='border-top: 2px solid #ccc'><td class='label'>Total Gastos</td>{cols_gas}<td class='neg'>-{self.moneda} {tot_gas_global:,.2f}</td></tr>"

            # --- BALANCE NETO ---
            html += "<tr class='row-net'><td class='label'>Resultado Neto (Ingresos - Gastos)</td>"
            tot_net_global = 0.0
            
            for m in meses:
                net = float(s_ing.get(m, 0)) - float(s_gas.get(m, 0))
                tot_net_global += net
                color_class = "pos" if net >= 0 else "neg"
                html += f"<td class='{color_class}'>{self.moneda} {net:,.2f}</td>"
                
            color_tot = "pos" if tot_net_global >= 0 else "neg"
            html += f"<td class='{color_tot}'>{self.moneda} {tot_net_global:,.2f}</td></tr>"

            html += "</tbody></table>"
            return html

    # ----------------------------------------------------- Exportar PDF

    def exportar_reporte_pdf(self):
            """Genera PDF profesional usando ReportGenerator."""
            if not self.figura_actual:
                QMessageBox.warning(self, "Sin gráfico", "No hay datos para exportar.")
                return

            filename, _ = QFileDialog.getSaveFileName(self, "Guardar PDF", "Reporte_Ingresos_vs_Gastos.pdf", "PDF (*.pdf)")
            if not filename: return

            try:
                # 1. Preparar datos tabulares para ReportGenerator
                # Transformamos la estructura matricial (meses en columnas) a lista de registros
                # para que ReportGenerator pueda imprimir una tabla bonita.
                # O mejor aún: le pasamos los datos ya resumidos por mes.
                
                datos_exportar = []
                
                # Meses
                meses = sorted(set(self.df_ingresos["mes"].dropna().tolist() + self.df_gastos["mes"].dropna().tolist()))
                
                for m in meses:
                    ing = self.df_ingresos[self.df_ingresos["mes"]==m]["monto"].sum()
                    gas = self.df_gastos[self.df_gastos["mes"]==m]["monto"].sum()
                    
                    datos_exportar.append({
                        "Mes": m,
                        "Ingresos": ing,
                        "Gastos": gas,
                        "Balance": ing - gas,
                        "_raw_tipo": "ingreso" if (ing-gas)>=0 else "gasto" # Truco para colorear balance
                    })

                # 2. Configurar
                rango = f"{self.date_desde.text()} - {self.date_hasta.text()}"
                rg = ReportGenerator(
                    data=datos_exportar,
                    title="Ingresos vs Gastos",
                    project_name=self.proyecto_nombre,
                    date_range=rango,
                    currency_symbol=self.moneda,
                    column_map={"Mes": "Mes", "Ingresos": "Total Ingresos", "Gastos": "Total Gastos", "Balance": "Balance Neto"}
                )
                
                # 3. Exportar (Gráfico + Tabla)
                figures = {'grafico': self.figura_actual}
                ok, msg = rg.dashboard_to_pdf(filename, figures)
                
                if ok:
                    QMessageBox.information(self, "Éxito", "PDF exportado correctamente.")
                else:
                    QMessageBox.warning(self, "Error", f"Error al exportar: {msg}")

            except Exception as e:
                logger.error(f"Error PDF: {e}")
                QMessageBox.critical(self, "Error", str(e))