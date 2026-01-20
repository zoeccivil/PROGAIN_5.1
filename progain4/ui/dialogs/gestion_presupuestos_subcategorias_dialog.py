from typing import List, Dict, Any, Optional
from datetime import date

from PyQt6.QtCore import Qt, QDate
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QMessageBox,
    QHBoxLayout,
    QHeaderView,
    QComboBox,
    QFileDialog,
    QDateEdit,
)

from report_generator import ReportGenerator  # ajusta el import si tu ruta es distinta


class GestionPresupuestosSubcategoriasDialog(QDialog):
    """
    Gestión avanzada de Presupuestos por Subcategoría para un proyecto (Firebase).

    Características:
      - Periodo: mes actual / personalizado (fecha inicio y fin).
      - Filtro por categoría y subcategoría.
      - Presupuesto por subcategoría:
          * Monto planificado
          * Gasto real (en el periodo)
          * Diferencia y % usado (colores)
      - Totales globales.
      - Exportación a Excel / PDF.

    Requiere métodos en FirebaseClient:
      - get_categorias_por_proyecto(proyecto_id)
      - get_subcategorias_por_proyecto(proyecto_id)
        -> con al menos: id, nombre, categoria_id, nombre_categoria (opcional)
      - get_presupuestos_subcategorias_por_proyecto(proyecto_id, fecha_inicio, fecha_fin)
        -> [
             {
               "subcategoria_id": str,
               "monto": float,
               "observaciones": str,
             }
           ]
      - get_gasto_por_subcategoria_en_periodo(proyecto_id, subcategoria_id, fecha_inicio, fecha_fin)
        -> float
      - save_presupuestos_subcategorias_proyecto(proyecto_id, fecha_inicio, fecha_fin, lista_presupuestos)
        lista_presupuestos: [
          {
            "subcategoria_id": str,
            "subcategoria_nombre": str,
            "categoria_id": str,
            "categoria_nombre": str,
            "monto": float,
          }
        ]
    """

    COL_CATEGORIA = 0
    COL_SUBCATEGORIA = 1
    COL_PRESUPUESTO = 2
    COL_GASTADO = 3
    COL_DIFERENCIA = 4
    COL_PORCENTAJE = 5

    def __init__(self, firebase_client, proyecto_id: str, proyecto_nombre: str, parent=None):
        super().__init__(parent)
        self.firebase_client = firebase_client
        self.proyecto_id = proyecto_id
        self.proyecto_nombre = proyecto_nombre

        self.setWindowTitle(f"Presupuestos por Subcategoría - {proyecto_nombre}")
        self.setFixedSize(950, 700)

        layout = QVBoxLayout(self)

        # --- Periodo ---
        periodo_layout = QHBoxLayout()
        periodo_layout.addWidget(QLabel("Periodo del presupuesto:"))

        self.combo_periodo = QComboBox()
        self.combo_periodo.addItems(["Mes actual", "Personalizado"])
        periodo_layout.addWidget(self.combo_periodo)

        self.date_inicio = QDateEdit()
        self.date_fin = QDateEdit()
        for de in (self.date_inicio, self.date_fin):
            de.setDisplayFormat("dd/MM/yyyy")
            de.setCalendarPopup(True)

        periodo_layout.addWidget(QLabel("Desde:"))
        periodo_layout.addWidget(self.date_inicio)
        periodo_layout.addWidget(QLabel("Hasta:"))
        periodo_layout.addWidget(self.date_fin)
        periodo_layout.addStretch()

        layout.addLayout(periodo_layout)

        descripcion = QLabel(
            "Filtra por categoría y subcategoría, asigna presupuestos y compara con los gastos reales en el periodo."
        )
        descripcion.setWordWrap(True)
        layout.addWidget(descripcion)

        # --- Filtros categoría / subcategoría ---
        filtro_layout = QHBoxLayout()
        filtro_layout.addWidget(QLabel("Categoría:"))
        self.combo_categoria = QComboBox()
        filtro_layout.addWidget(self.combo_categoria)

        filtro_layout.addWidget(QLabel("Subcategoría:"))
        self.combo_subcategoria = QComboBox()
        filtro_layout.addWidget(self.combo_subcategoria)

        filtro_layout.addStretch()
        layout.addLayout(filtro_layout)

        # --- Tabla ---
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["Categoría", "Subcategoría", "Presupuesto", "Gastado", "Diferencia", "% usado"]
        )
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(self.COL_CATEGORIA, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(self.COL_SUBCATEGORIA, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(self.COL_PRESUPUESTO, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.COL_GASTADO, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.COL_DIFERENCIA, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.COL_PORCENTAJE, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.table)

        # --- Totales ---
        self.label_totales = QLabel("")
        self.label_totales.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.label_totales)

        # --- Botones ---
        btn_layout = QHBoxLayout()
        self.btn_recalcular = QPushButton("Recalcular")
        self.btn_guardar = QPushButton("Guardar Cambios")
        self.btn_exportar_excel = QPushButton("Exportar a Excel")
        self.btn_exportar_pdf = QPushButton("Exportar a PDF")
        self.btn_cancelar = QPushButton("Cancelar")

        btn_layout.addWidget(self.btn_recalcular)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_exportar_excel)
        btn_layout.addWidget(self.btn_exportar_pdf)
        btn_layout.addWidget(self.btn_guardar)
        btn_layout.addWidget(self.btn_cancelar)
        layout.addLayout(btn_layout)

        # --- Estado ---
        self.categorias: List[Dict[str, Any]] = []
        self.subcategorias: List[Dict[str, Any]] = []
        # Mapa subcategoria_id -> monto presupuesto
        self.presupuestos_actuales: Dict[str, float] = {}

        # Conexiones
        self.combo_periodo.currentIndexChanged.connect(self._on_periodo_changed)
        self.combo_categoria.currentIndexChanged.connect(self._refrescar_tabla_filtrada)
        self.combo_subcategoria.currentIndexChanged.connect(self._refrescar_tabla_filtrada)

        self.btn_recalcular.clicked.connect(self._recalcular)
        self.btn_guardar.clicked.connect(self._guardar)
        self.btn_cancelar.clicked.connect(self.reject)
        self.btn_exportar_excel.clicked.connect(self._exportar_excel)
        self.btn_exportar_pdf.clicked.connect(self._exportar_pdf)

        # Inicialización
        self._init_fechas_por_defecto()
        self._cargar_cat_subcat()
        self._recalcular()

    # ------------------------------------------------------------------ Periodo

    def _init_fechas_por_defecto(self):
        today = QDate.currentDate()
        inicio_mes = QDate(today.year(), today.month(), 1)
        fin_mes = QDate(today.year(), today.month(), today.daysInMonth())
        self.date_inicio.setDate(inicio_mes)
        self.date_fin.setDate(fin_mes)
        self.combo_periodo.setCurrentIndex(0)
        self._update_date_edit_enabled()

    def _update_date_edit_enabled(self):
        personalizado = self.combo_periodo.currentIndex() == 1
        self.date_inicio.setEnabled(personalizado)
        self.date_fin.setEnabled(personalizado)

    def _on_periodo_changed(self, idx: int):
        if idx == 0:  # Mes actual
            self._init_fechas_por_defecto()
        self._update_date_edit_enabled()

    def _get_periodo(self) -> tuple[date, date]:
        qd_ini: QDate = self.date_inicio.date()
        qd_fin: QDate = self.date_fin.date()
        return (
            date(qd_ini.year(), qd_ini.month(), qd_ini.day()),
            date(qd_fin.year(), qd_fin.month(), qd_fin.day()),
        )

    # ------------------------------------------------------------------ Carga de cat/subcat

    def _cargar_cat_subcat(self):
        if not self.firebase_client.is_initialized():
            QMessageBox.warning(self, "Firebase", "Firebase no está inicializado.")
            return

        try:
            self.categorias = (
                self.firebase_client.get_categorias_por_proyecto(self.proyecto_id) or []
            )
            self.subcategorias = (
                self.firebase_client.get_subcategorias_by_proyecto(self.proyecto_id) or []
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudieron cargar categorías/subcategorías del proyecto:\n{e}",
            )
            self.categorias = []
            self.subcategorias = []
            return

        # Mapa categoria_id -> nombre
        cat_map = {str(c["id"]): c.get("nombre", f"Categoría {c['id']}") for c in self.categorias}
        # Enriquecer subcategorías con nombre de categoría
        for s in self.subcategorias:
            cid = str(s.get("categoria_id", ""))
            s["categoria_nombre"] = cat_map.get(cid, f"Categoría {cid}")

        # Llenar combos
        self.combo_categoria.blockSignals(True)
        self.combo_categoria.clear()
        self.combo_categoria.addItem("Todas las categorías", None)
        for c in sorted(self.categorias, key=lambda x: x.get("nombre", "").upper()):
            self.combo_categoria.addItem(c["nombre"], str(c["id"]))
        self.combo_categoria.blockSignals(False)

        self._llenar_combo_subcategorias()

    def _llenar_combo_subcategorias(self):
        cat_id = self.combo_categoria.currentData()
        self.combo_subcategoria.blockSignals(True)
        self.combo_subcategoria.clear()
        self.combo_subcategoria.addItem("Todas las subcategorías", None)

        if cat_id is None:
            sub_filtradas = self.subcategorias
        else:
            sub_filtradas = [s for s in self.subcategorias if str(s.get("categoria_id")) == str(cat_id)]

        for s in sorted(sub_filtradas, key=lambda x: x.get("nombre", "").upper()):
            self.combo_subcategoria.addItem(s["nombre"], str(s["id"]))

        self.combo_subcategoria.blockSignals(False)

    # ------------------------------------------------------------------ Recalcular tabla

    def _recalcular(self):
        """Carga presupuestos actuales y recalcula importes de la tabla."""
        if not self.subcategorias:
            self.table.setRowCount(0)
            self.label_totales.setText("No hay subcategorías definidas para este proyecto.")
            return

        fecha_inicio, fecha_fin = self._get_periodo()

        # Presupuestos ya guardados por subcategoría
        try:
            presup = (
                self.firebase_client.get_presupuestos_subcategorias_por_proyecto(
                    self.proyecto_id, fecha_inicio, fecha_fin
                )
                or []
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudieron cargar los presupuestos por subcategoría:\n{e}",
            )
            presup = []

        self.presupuestos_actuales = {
            str(p["subcategoria_id"]): float(p.get("monto", 0.0)) for p in presup
        }

        self._refrescar_tabla_filtrada()

    def _refrescar_tabla_filtrada(self):
        """Filtra por categoría/subcategoría y rellena la tabla."""
        self._llenar_combo_subcategorias()

        cat_id_filtro = self.combo_categoria.currentData()
        sub_id_filtro = self.combo_subcategoria.currentData()

        # Filtrar subcategorías según combos
        sub_list = self.subcategorias
        if cat_id_filtro is not None:
            sub_list = [s for s in sub_list if str(s.get("categoria_id")) == str(cat_id_filtro)]

        if sub_id_filtro is not None:
            sub_list = [s for s in sub_list if str(s.get("id")) == str(sub_id_filtro)]

        self._cargar_tabla(sub_list)

    def _cargar_tabla(self, sub_list: List[Dict[str, Any]]):
        fecha_inicio, fecha_fin = self._get_periodo()

        self.table.setRowCount(len(sub_list))
        total_presupuesto = 0.0
        total_gasto = 0.0

        for row, sub in enumerate(sub_list):
            sub_id = str(sub["id"])
            sub_nombre = sub.get("nombre", f"Subcategoría {sub_id}")
            cat_id = str(sub.get("categoria_id", ""))
            cat_nombre = sub.get("categoria_nombre", f"Categoría {cat_id}")

            presupuesto = float(self.presupuestos_actuales.get(sub_id, 0.0))

            # Gasto real
            try:
                gastado = float(
                    self.firebase_client.get_gasto_por_subcategoria_en_periodo(
                        self.proyecto_id, sub_id, fecha_inicio, fecha_fin
                    )
                )
            except AttributeError:
                gastado = 0.0
            except Exception:
                gastado = 0.0

            diferencia = presupuesto - gastado
            total_presupuesto += presupuesto
            total_gasto += gastado

            # Categoría
            item_cat = QTableWidgetItem(cat_nombre)
            item_cat.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            item_cat.setData(Qt.ItemDataRole.UserRole, cat_id)
            self.table.setItem(row, self.COL_CATEGORIA, item_cat)

            # Subcategoría
            item_sub = QTableWidgetItem(sub_nombre)
            item_sub.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            item_sub.setData(Qt.ItemDataRole.UserRole, sub_id)
            self.table.setItem(row, self.COL_SUBCATEGORIA, item_sub)

            # Presupuesto (editable)
            item_pres = QTableWidgetItem(f"{presupuesto:.2f}")
            item_pres.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item_pres.setFlags(
                Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsEditable
            )
            self.table.setItem(row, self.COL_PRESUPUESTO, item_pres)

            # Gastado
            item_gast = QTableWidgetItem(f"{gastado:.2f}")
            item_gast.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item_gast.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(row, self.COL_GASTADO, item_gast)

            # Diferencia
            item_dif = QTableWidgetItem(f"{diferencia:.2f}")
            item_dif.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if diferencia < 0:
                item_dif.setForeground(Qt.GlobalColor.red)
            self.table.setItem(row, self.COL_DIFERENCIA, item_dif)

            # % usado
            if presupuesto > 0:
                pct = (gastado / presupuesto) * 100.0
            else:
                pct = 0.0
            item_pct = QTableWidgetItem(f"{pct:.1f}%")
            item_pct.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if pct > 100:
                item_pct.setForeground(Qt.GlobalColor.red)
            elif pct >= 80:
                item_pct.setForeground(Qt.GlobalColor.darkYellow)
            else:
                item_pct.setForeground(Qt.GlobalColor.darkGreen)
            self.table.setItem(row, self.COL_PORCENTAJE, item_pct)

        saldo = total_presupuesto - total_gasto
        self.label_totales.setText(
            f"Total presupuesto: {total_presupuesto:.2f} | "
            f"Total gastado: {total_gasto:.2f} | "
            f"Saldo: {saldo:.2f}"
        )

    # ------------------------------------------------------------------ Guardar

    def _guardar(self):
        filas_invalidas: List[int] = []
        nuevos_presupuestos: List[Dict[str, Any]] = []

        for row in range(self.table.rowCount()):
            item_cat = self.table.item(row, self.COL_CATEGORIA)
            item_sub = self.table.item(row, self.COL_SUBCATEGORIA)
            item_pres = self.table.item(row, self.COL_PRESUPUESTO)

            if not item_cat or not item_sub or not item_pres:
                continue

            cat_id = str(item_cat.data(Qt.ItemDataRole.UserRole))
            cat_nombre = item_cat.text().strip()
            sub_id = str(item_sub.data(Qt.ItemDataRole.UserRole))
            sub_nombre = item_sub.text().strip()

            pres_str = item_pres.text().replace(",", "").strip()
            if pres_str == "":
                monto = 0.0
            else:
                try:
                    monto = float(pres_str)
                except Exception:
                    filas_invalidas.append(row + 1)
                    continue

            nuevos_presupuestos.append(
                {
                    "categoria_id": cat_id,
                    "categoria_nombre": cat_nombre,
                    "subcategoria_id": sub_id,
                    "subcategoria_nombre": sub_nombre,
                    "monto": monto,
                }
            )

        if filas_invalidas:
            QMessageBox.warning(
                self,
                "Error",
                f"Presupuesto inválido en las filas: {', '.join(map(str, filas_invalidas))}",
            )
            return

        fecha_inicio, fecha_fin = self._get_periodo()

        try:
            exito = self.firebase_client.save_presupuestos_subcategorias_proyecto(
                self.proyecto_id,
                fecha_inicio,
                fecha_fin,
                nuevos_presupuestos,
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudieron guardar los presupuestos por subcategoría:\n{e}",
            )
            return

        if exito:
            QMessageBox.information(
                self,
                "Presupuestos",
                "Presupuestos por subcategoría actualizados correctamente.",
            )
            self.accept()
        else:
            QMessageBox.warning(
                self,
                "Error",
                "No se pudieron guardar los presupuestos por subcategoría.",
            )

    # ------------------------------------------------------------------ Exportar

    def _recolectar_datos_tabla(self) -> List[Dict[str, Any]]:
        datos: List[Dict[str, Any]] = []
        for row in range(self.table.rowCount()):
            item_cat = self.table.item(row, self.COL_CATEGORIA)
            item_sub = self.table.item(row, self.COL_SUBCATEGORIA)
            item_pres = self.table.item(row, self.COL_PRESUPUESTO)
            item_gast = self.table.item(row, self.COL_GASTADO)
            item_dif = self.table.item(row, self.COL_DIFERENCIA)
            item_pct = self.table.item(row, self.COL_PORCENTAJE)
            if not item_cat or not item_sub:
                continue
            datos.append(
                {
                    "Categoría": item_cat.text(),
                    "Subcategoría": item_sub.text(),
                    "Presupuesto": float(item_pres.text().replace(",", "")) if item_pres else 0.0,
                    "Gastado": float(item_gast.text().replace(",", "")) if item_gast else 0.0,
                    "Diferencia": float(item_dif.text().replace(",", "")) if item_dif else 0.0,
                    "% usado": item_pct.text() if item_pct else "",
                }
            )
        return datos

    def _exportar_excel(self):
        datos = self._recolectar_datos_tabla()
        if not datos:
            QMessageBox.warning(self, "Exportación", "No hay datos para exportar.")
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar reporte Excel",
            "presupuestos_subcategorias.xlsx",
            "Archivos Excel (*.xlsx)",
        )
        if not filepath:
            return

        column_map = {
            "Categoría": "Categoría",
            "Subcategoría": "Subcategoría",
            "Presupuesto": "Presupuesto",
            "Gastado": "Gastado",
            "Diferencia": "Diferencia",
            "% usado": "% usado",
        }

        rg = ReportGenerator(
            data=datos,
            title="Presupuestos por Subcategoría",
            project_name=self.proyecto_nombre,
            date_range="",
            currency_symbol="RD$",
            column_map=column_map,
        )
        ok, msg = rg.to_excel(filepath)
        if ok:
            QMessageBox.information(self, "Exportación", "Reporte exportado correctamente.")
        else:
            QMessageBox.warning(self, "Error", f"No se pudo exportar: {msg}")

    def _exportar_pdf(self):
        datos = self._recolectar_datos_tabla()
        if not datos:
            QMessageBox.warning(self, "Exportación", "No hay datos para exportar.")
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar reporte PDF",
            "presupuestos_subcategorias.pdf",
            "Archivos PDF (*.pdf)",
        )
        if not filepath:
            return

        column_map = {
            "Categoría": "Categoría",
            "Subcategoría": "Subcategoría",
            "Presupuesto": "Presupuesto",
            "Gastado": "Gastado",
            "Diferencia": "Diferencia",
            "% usado": "% usado",
        }

        rg = ReportGenerator(
            data=datos,
            title="Presupuestos por Subcategoría",
            project_name=self.proyecto_nombre,
            date_range="",
            currency_symbol="RD$",
            column_map=column_map,
        )
        ok, msg = rg.to_pdf(filepath)
        if ok:
            QMessageBox.information(self, "Exportación", "Reporte PDF exportado correctamente.")
        else:
            QMessageBox.warning(self, "Error", f"No se pudo exportar PDF: {msg}")