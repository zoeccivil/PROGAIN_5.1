from typing import List, Dict, Any, Optional

from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QComboBox,
    QLabel,
    QPushButton,
    QSplitter,
    QFileDialog,
    QMessageBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWebEngineWidgets import QWebEngineView

import pandas as pd
import plotly.express as px
import pdfkit
import base64
import tempfile
import os


class DashboardGlobalCuentasWindowFirebase(QMainWindow):
    """
    Dashboard Global de Cuentas (Firebase).

    - Panel izquierdo:
        * Tabla con: Cuenta, Ingresos, Gastos, Balance.

    - Panel derecho:
        * Filtros:
            - Tipo de gráfico:
                · Balance neto por cuenta
                · Ingresos vs Gastos por cuenta
                · Gastos por proyecto (cuenta seleccionada)
            - Cuenta (Todas / una)
            - Paleta de colores
        * Gráfico Plotly
        * Exportar PDF
    """

    def __init__(self, firebase_client, moneda: str = "RD$", parent=None):
        super().__init__(parent)
        self.firebase_client = firebase_client
        self.moneda = moneda or "RD$"

        self.setWindowTitle("Dashboard Global de Cuentas (Firebase)")
        self.resize(1600, 900)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(splitter)

        # ---------------- Panel izquierdo: tabla ----------------
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        left_layout.addWidget(QLabel("Resumen de cuentas:"))
        self.table_cuentas = QTableWidget()
        left_layout.addWidget(self.table_cuentas)

        splitter.addWidget(left_widget)

        # ---------------- Panel derecho: filtros + gráfico ----------------
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        filtro_layout = QHBoxLayout()
        filtro_layout.addWidget(QLabel("Tipo de gráfico:"))

        self.combo_tipo_grafico = QComboBox()
        self.combo_tipo_grafico.addItems(
            [
                "Balance neto por cuenta",
                "Ingresos vs Gastos por cuenta",
                "Gastos por proyecto (cuenta seleccionada)",
            ]
        )
        filtro_layout.addWidget(self.combo_tipo_grafico)

        filtro_layout.addWidget(QLabel("Cuenta:"))
        self.combo_cuentas = QComboBox()
        filtro_layout.addWidget(self.combo_cuentas)

        filtro_layout.addWidget(QLabel("Paleta:"))
        self.combo_paleta = QComboBox()
        self.combo_paleta.addItems(
            ["Pastel", "Set3", "Dark2", "Viridis", "Plasma", "Blues", "Greens"]
        )
        filtro_layout.addWidget(self.combo_paleta)

        right_layout.addLayout(filtro_layout)

        # Gráfico
        self.web_view = QWebEngineView()
        right_layout.addWidget(self.web_view, stretch=1)

        # Botón exportar PDF
        export_layout = QHBoxLayout()
        self.btn_export_pdf = QPushButton("Exportar PDF")
        export_layout.addStretch()
        export_layout.addWidget(self.btn_export_pdf)
        right_layout.addLayout(export_layout)

        splitter.addWidget(right_widget)
        splitter.setStretchFactor(1, 3)

        # Estado interno
        self.df_cuentas: pd.DataFrame = pd.DataFrame()
        self.df_transacciones: pd.DataFrame = pd.DataFrame()
        self.figura_actual = None

        # Cargar datos iniciales desde Firebase
        self._cargar_datos_globales()
        self._cargar_tabla_principal()
        self._cargar_filtros()
        self._actualizar_grafico()

        # Conexiones
        self.combo_tipo_grafico.currentIndexChanged.connect(self._actualizar_grafico)
        self.combo_cuentas.currentIndexChanged.connect(self._actualizar_grafico)
        self.combo_paleta.currentIndexChanged.connect(self._actualizar_grafico)
        self.btn_export_pdf.clicked.connect(self._exportar_reporte_pdf)

        self._center_window()

    # --------------------------------------------------------- Helpers UI

    def _center_window(self):
        frame_geom = self.frameGeometry()
        screen = QGuiApplication.primaryScreen()
        if screen:
            screen_center = screen.availableGeometry().center()
            frame_geom.moveCenter(screen_center)
            self.move(frame_geom.topLeft())

    # --------------------------------------------------------- Carga de datos

    def _cargar_datos_globales(self):
        """
        Obtiene:
          - df_cuentas: resumen global de todas las cuentas
          - df_transacciones: todas las transacciones (para desglose por proyecto)
        usando FirebaseClient.
        """
        try:
            resumen = (
                self.firebase_client.get_balances_globales_todas_cuentas() or []
            )
        except AttributeError:
            # Si no existe aún, la implementamos aparte en FirebaseClient
            resumen = []
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudo obtener el resumen global de cuentas desde Firebase:\n{e}",
            )
            resumen = []

        self.df_cuentas = pd.DataFrame(resumen)
        if not self.df_cuentas.empty:
            # Normalizamos nombres de columnas esperadas:
            # se espera: "cuenta_id", "cuenta_nombre", "total_ingresos", "total_gastos"
            if "cuenta_nombre" in self.df_cuentas.columns:
                self.df_cuentas.rename(columns={"cuenta_nombre": "cuenta"}, inplace=True)
            if "cuenta" not in self.df_cuentas.columns and "nombre" in self.df_cuentas.columns:
                self.df_cuentas.rename(columns={"nombre": "cuenta"}, inplace=True)

        # Transacciones globales (para gastos por proyecto)
        try:
            trans = self.firebase_client.get_todas_las_transacciones_globales() or []
        except AttributeError:
            trans = []
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudieron obtener las transacciones globales:\n{e}",
            )
            trans = []

        self.df_transacciones = pd.DataFrame(trans)
        if not self.df_transacciones.empty:
            # aseguramos columnas utilizadas: tipo, cuenta_id, cuenta_nombre, proyecto_id, proyecto_nombre, monto
            pass  # suponemos que el helper las devuelve ya normalizadas

    # --------------------------------------------------------- Tabla principal

    def _cargar_tabla_principal(self):
        df = self.df_cuentas.copy()
        if df.empty:
            self.table_cuentas.setRowCount(0)
            self.table_cuentas.setColumnCount(0)
            return

        if "total_ingresos" not in df.columns:
            df["total_ingresos"] = 0.0
        if "total_gastos" not in df.columns:
            df["total_gastos"] = 0.0
        if "balance" not in df.columns:
            df["balance"] = df["total_ingresos"] - df["total_gastos"]

        self.table_cuentas.setRowCount(len(df))
        self.table_cuentas.setColumnCount(4)
        self.table_cuentas.setHorizontalHeaderLabels(
            ["Cuenta", "Ingresos", "Gastos", "Balance"]
        )

        for i, row in df.iterrows():
            self.table_cuentas.setItem(i, 0, QTableWidgetItem(str(row.get("cuenta", ""))))
            self.table_cuentas.setItem(
                i,
                1,
                QTableWidgetItem(f"{float(row['total_ingresos']):,.2f}"),
            )
            self.table_cuentas.setItem(
                i,
                2,
                QTableWidgetItem(f"{float(row['total_gastos']):,.2f}"),
            )
            self.table_cuentas.setItem(
                i,
                3,
                QTableWidgetItem(f"{float(row['balance']):,.2f}"),
            )

        self.df_cuentas = df  # guardamos normalizado

    # --------------------------------------------------------- Filtros

    def _cargar_filtros(self):
        df = self.df_cuentas
        self.combo_cuentas.clear()
        self.combo_cuentas.addItem("Todas", None)
        if df.empty:
            return

        cuentas = df["cuenta"].dropna().unique().tolist()
        for nombre in sorted(cuentas, key=lambda x: str(x).upper()):
            self.combo_cuentas.addItem(nombre, nombre)

    # --------------------------------------------------------- Gráfico

    def _actualizar_grafico(self):
        tipo = self.combo_tipo_grafico.currentText()
        cuenta_sel_nombre = self.combo_cuentas.currentData()
        paleta = self.combo_paleta.currentText()
        df = self.df_cuentas.copy()

        if df.empty:
            fig = px.bar(x=["Sin datos"], y=[0])
            self.figura_actual = fig
            self.web_view.setHtml(
                fig.to_html(include_plotlyjs="cdn", full_html=False)
            )
            return

        if "total_ingresos" not in df.columns:
            df["total_ingresos"] = 0.0
        if "total_gastos" not in df.columns:
            df["total_gastos"] = 0.0
        if "balance" not in df.columns:
            df["balance"] = df["total_ingresos"] - df["total_gastos"]

        palettes = {
            "Pastel": px.colors.qualitative.Pastel,
            "Set3": px.colors.qualitative.Set3,
            "Dark2": px.colors.qualitative.Dark2,
            "Viridis": px.colors.sequential.Viridis,
            "Plasma": px.colors.sequential.Plasma,
            "Blues": px.colors.sequential.Blues,
            "Greens": px.colors.sequential.Greens,
        }
        palette_colors = palettes.get(paleta, px.colors.qualitative.Pastel)

        if tipo == "Balance neto por cuenta":
            fig = px.bar(
                df,
                x="balance",
                y="cuenta",
                orientation="h",
                labels={"cuenta": "Cuenta", "balance": "Balance"},
                color_discrete_sequence=palette_colors,
            )
            fig.update_layout(title="Balance neto por cuenta")
        elif tipo == "Ingresos vs Gastos por cuenta":
            df_melt = df.melt(
                id_vars="cuenta",
                value_vars=["total_ingresos", "total_gastos"],
                var_name="Tipo",
                value_name="Monto",
            )
            df_melt["Tipo"] = df_melt["Tipo"].map(
                {
                    "total_ingresos": "Ingresos",
                    "total_gastos": "Gastos",
                }
            )
            fig = px.bar(
                df_melt,
                x="Monto",
                y="cuenta",
                color="Tipo",
                orientation="h",
                labels={"cuenta": "Cuenta", "Monto": "Monto"},
                barmode="group",
                color_discrete_sequence=palette_colors,
            )
            fig.update_layout(
                bargap=0.15,
                bargroupgap=0.05,
                title="Ingresos vs Gastos por Cuenta (Global)",
                font_family="Arial",
                font_color="#333",
                legend_title="Tipo",
                plot_bgcolor="#f8f9fa",
            )
            fig.update_xaxes(tickformat=",")
        elif tipo == "Gastos por proyecto (cuenta seleccionada)":
            fig = self._grafico_gastos_por_proyecto(cuenta_sel_nombre, palette_colors)
        else:
            fig = px.bar(x=["Sin datos"], y=[0])

        self.figura_actual = fig
        self.web_view.setHtml(
            fig.to_html(include_plotlyjs="cdn", full_html=False)
        )

    def _grafico_gastos_por_proyecto(self, cuenta_sel_nombre: Optional[str], palette_colors):
        df_trx = self.df_transacciones.copy()
        if df_trx.empty:
            return px.bar(x=["Sin datos"], y=[0])

        # Filtramos solo gastos
        df_trx = df_trx[df_trx["tipo"] == "Gasto"]

        # Filtrar por cuenta si se seleccionó una
        if cuenta_sel_nombre:
            # suponemos que el helper devuelve 'cuenta_nombre'
            if "cuenta_nombre" in df_trx.columns:
                df_trx = df_trx[df_trx["cuenta_nombre"] == cuenta_sel_nombre]
            elif "cuenta" in df_trx.columns:
                df_trx = df_trx[df_trx["cuenta"] == cuenta_sel_nombre]

        if df_trx.empty:
            return px.bar(x=["Sin datos"], y=[0])

        # Agrupar por proyecto
        nombre_col = "proyecto_nombre" if "proyecto_nombre" in df_trx.columns else "proyecto_id"
        gastos_proj = (
            df_trx.groupby(nombre_col)["monto"].sum().reset_index(name="monto")
        )

        if gastos_proj.empty:
            return px.bar(x=["Sin datos"], y=[0])

        fig = px.pie(
            gastos_proj,
            names=nombre_col,
            values="monto",
            title="Gastos por Proyecto",
            color_discrete_sequence=palette_colors,
        )
        return fig

    # --------------------------------------------------------- Exportar PDF

    def _exportar_reporte_pdf(self):
        if self.figura_actual is None:
            QMessageBox.warning(self, "Sin gráfico", "No hay gráfico para exportar.")
            return

        wkhtml_path = r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
        if not os.path.exists(wkhtml_path):
            wkhtml_path = r"C:\Program Files\wkhtmltopdf\wkhtmltopdf.exe"
            if not os.path.exists(wkhtml_path):
                QMessageBox.warning(
                    self,
                    "Error",
                    f"No se encontró wkhtmltopdf.exe en las rutas conocidas.",
                )
                return
        config = pdfkit.configuration(wkhtmltopdf=wkhtml_path)

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar reporte PDF",
            "dashboard_global_cuentas.pdf",
            "Archivo PDF (*.pdf)",
        )
        if not filename:
            return

        # Exporta el gráfico actual como imagen PNG
        temp_img = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        try:
            self.figura_actual.write_image(temp_img.name, width=1600, height=900)
        except Exception:
            # fallback: capturar directamente el QWebEngineView
            self.web_view.grab().save(temp_img.name)
        temp_img.close()

        with open(temp_img.name, "rb") as f:
            img_data = f.read()
        img_base64 = base64.b64encode(img_data).decode("utf-8")
        img_src = f"data:image/png;base64,{img_base64}"

        # Tabla principal en HTML
        if self.df_cuentas.empty:
            tabla_html = "<p>No hay datos de cuentas.</p>"
        else:
            df_print = self.df_cuentas.copy()
            tabla_html = df_print.to_html(
                index=False,
                float_format=lambda x: f"{x:,.2f}",
                border=1,
                justify="left",
            )

        html = f"""
        <html>
        <head>
        <meta charset="utf-8"/>
        <style>
        body {{ font-family: 'Arial Narrow', Arial, sans-serif; }}
        h1 {{ font-size:24px; }}
        table {{ border: 1px solid #ccc; border-collapse: collapse; width: 100%; margin-top: 24px; font-family: 'Arial Narrow', Arial, sans-serif; font-size:13px; }}
        th, td {{ border: 1px solid #ccc; padding: 6px; text-align: left; }}
        th {{ background: #e3eefd; }}
        </style>
        </head>
        <body>
        <h1>Dashboard Global de Cuentas</h1>
        <img src="{img_src}" style="width:100%;max-width:1400px;"/>
        {tabla_html}
        </body>
        </html>
        """

        options = {
            "page-size": "Legal",
            "orientation": "Landscape",
            "encoding": "UTF-8",
            "margin-top": "0.5in",
            "margin-bottom": "0.5in",
            "margin-left": "0.5in",
            "margin-right": "0.5in",
        }

        try:
            pdfkit.from_string(html, filename, configuration=config, options=options)
            QMessageBox.information(self, "Éxito", "PDF exportado correctamente.")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo exportar PDF: {e}")
        finally:
            try:
                os.remove(temp_img.name)
            except Exception:
                pass