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
    QLineEdit,
    QDateEdit,
    QComboBox,
)


class GestionPresupuestosDialog(QDialog):
    """
    Gestión avanzada de Presupuestos por Categoría para un proyecto (Firebase).

    Características:
      - Presupuesto por categoría con:
          * monto planificado
          * gasto real (acumulado en el periodo)
          * diferencia y % utilizado
          * observaciones
      - Periodo de presupuesto:
          * Mensual (mes actual)
          * Personalizado (fecha inicio / fin)
      - Totales globales de presupuesto y gasto.
      - Destaca en color rojo las categorías sobre-presupuestadas.

    Requiere métodos en FirebaseClient:
      - get_categorias_por_proyecto(proyecto_id)
      - get_presupuestos_por_proyecto(proyecto_id, fecha_inicio, fecha_fin)
          -> lista de dicts:
             {
               "categoria_id": str,
               "monto": float,
               "observaciones": str,
             }
      - get_gasto_por_categoria_en_periodo(proyecto_id, categoria_id, fecha_inicio, fecha_fin)
          -> float
      - save_presupuestos_proyecto(proyecto_id, fecha_inicio, fecha_fin, lista_presupuestos)
          lista_presupuestos: List[Dict[id, monto, observaciones]]
    """

    COL_CATEGORIA = 0
    COL_PRESUPUESTO = 1
    COL_GASTADO = 2
    COL_DIFERENCIA = 3
    COL_PORCENTAJE = 4
    COL_OBSERVACIONES = 5

    def __init__(self, firebase_client, proyecto_id: str, proyecto_nombre: str, parent=None):
        super().__init__(parent)

        self.firebase_client = firebase_client
        self.proyecto_id = proyecto_id
        self.proyecto_nombre = proyecto_nombre

        self.setWindowTitle(f"Gestionar Presupuestos del Proyecto: {proyecto_nombre}")
        self.setFixedSize(900, 650)

        main_layout = QVBoxLayout(self)

        # --- Cabecera: periodo ---
        header_layout = QHBoxLayout()
        header_label = QLabel("Periodo del presupuesto:")
        header_layout.addWidget(header_label)

        self.combo_periodo = QComboBox()
        self.combo_periodo.addItems(["Mes actual", "Personalizado"])
        header_layout.addWidget(self.combo_periodo)

        self.date_inicio = QDateEdit()
        self.date_fin = QDateEdit()
        for de in (self.date_inicio, self.date_fin):
            de.setDisplayFormat("dd/MM/yyyy")
            de.setCalendarPopup(True)

        header_layout.addWidget(QLabel("Desde:"))
        header_layout.addWidget(self.date_inicio)
        header_layout.addWidget(QLabel("Hasta:"))
        header_layout.addWidget(self.date_fin)

        header_layout.addStretch()
        main_layout.addLayout(header_layout)

        main_layout.addWidget(
            QLabel(
                "Asigna el presupuesto por categoría y compara con los gastos reales en el periodo seleccionado:"
            )
        )

        # --- Tabla principal ---
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            [
                "Categoría",
                "Presupuesto",
                "Gastado",
                "Diferencia",
                "% usado",
                "Observaciones",
            ]
        )
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(self.COL_CATEGORIA, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(self.COL_PRESUPUESTO, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.COL_GASTADO, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.COL_DIFERENCIA, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.COL_PORCENTAJE, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.COL_OBSERVACIONES, QHeaderView.ResizeMode.Stretch)
        main_layout.addWidget(self.table)

        # --- Totales ---
        self.label_totales = QLabel("")
        self.label_totales.setAlignment(Qt.AlignmentFlag.AlignRight)
        main_layout.addWidget(self.label_totales)

        # --- Botones ---
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_recalcular = QPushButton("Recalcular")
        self.btn_guardar = QPushButton("Guardar Cambios")
        self.btn_cancelar = QPushButton("Cancelar")
        btn_layout.addWidget(self.btn_recalcular)
        btn_layout.addWidget(self.btn_guardar)
        btn_layout.addWidget(self.btn_cancelar)
        main_layout.addLayout(btn_layout)

        # Estado interno
        self.categorias: List[Dict[str, Any]] = []
        # Mapa categoria_id -> {"monto": float, "observaciones": str}
        self.presupuestos_actuales: Dict[str, Dict[str, Any]] = {}

        # Conexiones
        self.combo_periodo.currentIndexChanged.connect(self._on_periodo_changed)
        self.btn_recalcular.clicked.connect(self._recalcular)
        self.btn_guardar.clicked.connect(self._guardar)
        self.btn_cancelar.clicked.connect(self.reject)

        # Inicialización de fechas y datos
        self._init_fechas_por_defecto()
        self._cargar_datos_iniciales()

    # ------------------------------------------------------------------ Fechas / periodo

    def _init_fechas_por_defecto(self):
        """Inicializa el periodo a 'mes actual'."""
        today = QDate.currentDate()
        inicio_mes = QDate(today.year(), today.month(), 1)
        fin_mes = QDate(today.year(), today.month(), today.daysInMonth())
        self.date_inicio.setDate(inicio_mes)
        self.date_fin.setDate(fin_mes)
        # Por defecto: Mes actual
        self.combo_periodo.setCurrentIndex(0)
        self._update_date_edit_enabled()

    def _update_date_edit_enabled(self):
        """Activa/desactiva los QDateEdit según el tipo de periodo."""
        personalizado = self.combo_periodo.currentIndex() == 1
        self.date_inicio.setEnabled(personalizado)
        self.date_fin.setEnabled(personalizado)

    def _on_periodo_changed(self, idx: int):
        """Cuando cambia el tipo de periodo, actualizamos fechas si es mes actual."""
        if idx == 0:  # Mes actual
            self._init_fechas_por_defecto()
        self._update_date_edit_enabled()

    def _get_periodo(self) -> tuple[date, date]:
        """Devuelve (fecha_inicio, fecha_fin) como objetos date de Python."""
        qd_ini: QDate = self.date_inicio.date()
        qd_fin: QDate = self.date_fin.date()
        return (
            date(qd_ini.year(), qd_ini.month(), qd_ini.day()),
            date(qd_fin.year(), qd_fin.month(), qd_fin.day()),
        )

    # ------------------------------------------------------------------ Carga de datos

    def _cargar_datos_iniciales(self):
        """Carga categorías del proyecto y presupuestos/gastos para el periodo."""
        if not self.firebase_client.is_initialized():
            QMessageBox.warning(
                self,
                "Firebase",
                "Firebase no está inicializado.",
            )
            return

        try:
            self.categorias = (
                self.firebase_client.get_categorias_por_proyecto(self.proyecto_id) or []
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudieron cargar las categorías del proyecto:\n{e}",
            )
            self.categorias = []
            return

        self._recalcular()

    def _recalcular(self):
        """Recalcula la tabla de presupuestos y gastos para el periodo actual."""
        if not self.categorias:
            self.table.setRowCount(0)
            self.label_totales.setText("No hay categorías activas en este proyecto.")
            return

        fecha_inicio, fecha_fin = self._get_periodo()

        # Cargar presupuestos actuales desde Firebase
        try:
            presupuestos = (
                self.firebase_client.get_presupuestos_por_proyecto(
                    self.proyecto_id, fecha_inicio, fecha_fin
                )
                or []
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudieron cargar los presupuestos actuales:\n{e}",
            )
            presupuestos = []

        self.presupuestos_actuales = {
            str(p["categoria_id"]): {
                "monto": float(p.get("monto", 0.0)),
                "observaciones": p.get("observaciones", ""),
            }
            for p in presupuestos
        }

        # Construir tabla
        self.table.setRowCount(len(self.categorias))

        total_presupuesto = 0.0
        total_gasto = 0.0

        for row, cat in enumerate(self.categorias):
            cat_id = str(cat["id"])
            nombre = cat.get("nombre", f"Categoría {cat_id}")

            data_pres = self.presupuestos_actuales.get(
                cat_id, {"monto": 0.0, "observaciones": ""}
            )
            presupuesto = float(data_pres.get("monto", 0.0))
            observ = data_pres.get("observaciones", "")

            # Gasto real en el periodo y diferencia
            try:
                gasto = float(
                    self.firebase_client.get_gasto_por_categoria_en_periodo(
                        self.proyecto_id, cat_id, fecha_inicio, fecha_fin
                    )
                )
            except AttributeError:
                # Si aún no existe este método, asumimos 0 temporalmente
                gasto = 0.0
            except Exception:
                gasto = 0.0

            diferencia = presupuesto - gasto
            total_presupuesto += presupuesto
            total_gasto += gasto

            # Columna: Categoría (no editable)
            item_cat = QTableWidgetItem(nombre)
            item_cat.setFlags(
                Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
            )
            item_cat.setData(Qt.ItemDataRole.UserRole, cat_id)
            self.table.setItem(row, self.COL_CATEGORIA, item_cat)

            # Columna: Presupuesto (editable)
            item_pres = QTableWidgetItem(f"{presupuesto:.2f}")
            item_pres.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item_pres.setFlags(
                Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsEditable
            )
            self.table.setItem(row, self.COL_PRESUPUESTO, item_pres)

            # Columna: Gastado (no editable)
            item_gasto = QTableWidgetItem(f"{gasto:.2f}")
            item_gasto.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item_gasto.setFlags(
                Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
            )
            self.table.setItem(row, self.COL_GASTADO, item_gasto)

            # Columna: Diferencia
            item_dif = QTableWidgetItem(f"{diferencia:.2f}")
            item_dif.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if diferencia < 0:
                item_dif.setForeground(Qt.GlobalColor.red)
            self.table.setItem(row, self.COL_DIFERENCIA, item_dif)

            # Columna: % usado
            if presupuesto > 0:
                porcentaje = (gasto / presupuesto) * 100.0
            else:
                porcentaje = 0.0
            item_pct = QTableWidgetItem(f"{porcentaje:.1f}%")
            item_pct.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            # Colorear según nivel de uso (verde < 80%, naranja 80-100, rojo > 100)
            if porcentaje > 100:
                item_pct.setForeground(Qt.GlobalColor.red)
            elif porcentaje >= 80:
                item_pct.setForeground(Qt.GlobalColor.darkYellow)
            else:
                item_pct.setForeground(Qt.GlobalColor.darkGreen)
            self.table.setItem(row, self.COL_PORCENTAJE, item_pct)

            # Columna: Observaciones (editable)
            item_obs = QTableWidgetItem(observ)
            item_obs.setFlags(
                Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsEditable
            )
            self.table.setItem(row, self.COL_OBSERVACIONES, item_obs)

        saldo = total_presupuesto - total_gasto
        self.label_totales.setText(
            f"Total presupuesto: {total_presupuesto:.2f} | "
            f"Total gastado: {total_gasto:.2f} | "
            f"Saldo: {saldo:.2f}"
        )

    # ------------------------------------------------------------------ Guardar

    def _guardar(self):
        """Valida y guarda los presupuestos modificados en Firebase."""
        filas_invalidas: List[int] = []
        nuevos_presupuestos: List[Dict[str, Any]] = []

        for row in range(self.table.rowCount()):
            item_cat = self.table.item(row, self.COL_CATEGORIA)
            item_pres = self.table.item(row, self.COL_PRESUPUESTO)
            item_obs = self.table.item(row, self.COL_OBSERVACIONES)

            if not item_cat or not item_pres:
                continue

            categoria_id = str(item_cat.data(Qt.ItemDataRole.UserRole))
            categoria_nombre = item_cat.text().strip()
            presupuesto_str = item_pres.text().replace(",", "").strip()
            observaciones = item_obs.text().strip() if item_obs else ""

            if presupuesto_str == "":
                monto = 0.0
            else:
                try:
                    monto = float(presupuesto_str)
                except Exception:
                    filas_invalidas.append(row + 1)
                    continue

            nuevos_presupuestos.append(
                {
                    "categoria_id": categoria_id,
                    "categoria_nombre": categoria_nombre,
                    "monto": monto,
                    "observaciones": observaciones,
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
            exito = self.firebase_client.save_presupuestos_proyecto(
                self.proyecto_id,
                fecha_inicio,
                fecha_fin,
                nuevos_presupuestos,
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudieron guardar los presupuestos:\n{e}",
            )
            return

        if exito:
            QMessageBox.information(
                self,
                "Presupuestos",
                "Presupuestos actualizados correctamente.",
            )
            self.accept()
        else:
            QMessageBox.warning(
                self,
                "Error",
                "No se pudieron guardar los presupuestos.",
            )