from typing import List, Dict, Any, Optional

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QLabel,
    QPushButton,
    QComboBox,
    QGroupBox,
    QMessageBox,
    QHeaderView,
)
from PyQt6.QtCore import Qt


class AuditoriaCategoriasFirebaseDialog(QDialog):
    """
    Auditoría: Reasignar Transacciones Huérfanas (Firebase).

    - Muestra:
        * Transacciones con categoría huérfana.
        * Transacciones con subcategoría huérfana.

    - Permite:
        * Reasignar seleccionadas (categoría o subcategoría).
        * Reasignar TODAS las de una categoría/subcategoría origen.
    """

    def __init__(
        self,
        firebase_client,
        proyecto_id: str,
        proyecto_nombre: str,
        moneda: str,
        parent=None,
    ):
        super().__init__(parent)
        self.firebase_client = firebase_client
        self.proyecto_id = proyecto_id
        self.proyecto_nombre = proyecto_nombre
        self.moneda = moneda or "RD$"

        self.setWindowTitle(
            f"Auditoría: Reasignar Transacciones Huérfanas en '{proyecto_nombre}'"
        )
        # Permite redimensionar / maximizar
        self.resize(1100, 750)

        layout = QVBoxLayout(self)

        # --- Cargar datos huérfanos ---
        self.trans_no_categoria = (
            self.firebase_client.get_transacciones_sin_categoria_activa(proyecto_id)
            or []
        )
        self.trans_no_subcategoria = (
            self.firebase_client.get_transacciones_sin_subcategoria_activa(proyecto_id)
            or []
        )

        info_text = (
            f"Se encontraron {len(self.trans_no_categoria)} transacciones con categoría "
            f"huérfana y {len(self.trans_no_subcategoria)} con subcategoría huérfana."
        )
        layout.addWidget(QLabel(info_text))

        # --- Panel de Categoría Huérfana ---
        cat_group = QGroupBox("Transacciones con Categoría Huérfana")
        cat_layout = QVBoxLayout(cat_group)
        self.table_cat = QTableWidget(len(self.trans_no_categoria), 6)
        self.table_cat.setHorizontalHeaderLabels(
            ["Fecha", "Descripción", "Categoría", "Subcategoría", "Cuenta", "Monto"]
        )
        # Columnas ocupan todo el ancho de la tabla
        self.table_cat.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        for i, t in enumerate(self.trans_no_categoria):
            self.table_cat.setItem(i, 0, QTableWidgetItem(str(t.get("fecha", ""))))
            self.table_cat.setItem(
                i, 1, QTableWidgetItem(str(t.get("descripcion", "")))
            )
            self.table_cat.setItem(
                i, 2, QTableWidgetItem(str(t.get("categoriaNombre", "")))
            )
            self.table_cat.setItem(
                i, 3, QTableWidgetItem(str(t.get("subcategoriaNombre", "")))
            )
            self.table_cat.setItem(
                i, 4, QTableWidgetItem(str(t.get("cuentaNombre", "")))
            )
            self.table_cat.setItem(
                i,
                5,
                QTableWidgetItem(
                    f"{self.moneda} {float(t.get('monto', 0.0)):,.2f}"
                ),
            )
        self.table_cat.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        cat_layout.addWidget(self.table_cat)
        layout.addWidget(cat_group)

        # --- Panel de Subcategoría Huérfana ---
        sub_group = QGroupBox("Transacciones con Subcategoría Huérfana")
        sub_layout = QVBoxLayout(sub_group)
        self.table_sub = QTableWidget(len(self.trans_no_subcategoria), 6)
        self.table_sub.setHorizontalHeaderLabels(
            ["Fecha", "Descripción", "Categoría", "Subcategoría", "Cuenta", "Monto"]
        )
        self.table_sub.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        for i, t in enumerate(self.trans_no_subcategoria):
            self.table_sub.setItem(i, 0, QTableWidgetItem(str(t.get("fecha", ""))))
            self.table_sub.setItem(
                i, 1, QTableWidgetItem(str(t.get("descripcion", "")))
            )
            self.table_sub.setItem(
                i, 2, QTableWidgetItem(str(t.get("categoriaNombre", "")))
            )
            self.table_sub.setItem(
                i, 3, QTableWidgetItem(str(t.get("subcategoriaNombre", "")))
            )
            self.table_sub.setItem(
                i, 4, QTableWidgetItem(str(t.get("cuentaNombre", "")))
            )
            self.table_sub.setItem(
                i,
                5,
                QTableWidgetItem(
                    f"{self.moneda} {float(t.get('monto', 0.0)):,.2f}"
                ),
            )
        self.table_sub.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        sub_layout.addWidget(self.table_sub)
        layout.addWidget(sub_group)

        # --- Panel de destino de reasignación ---
        reasig_group = QGroupBox("Destino de Reasignación")
        reasig_layout = QHBoxLayout(reasig_group)
        reasig_layout.addWidget(QLabel("Nueva Categoría:"))
        self.combo_cat_destino = QComboBox()
        reasig_layout.addWidget(self.combo_cat_destino)

        reasig_layout.addWidget(QLabel("Nueva Subcategoría:"))
        self.combo_sub_destino = QComboBox()
        reasig_layout.addWidget(self.combo_sub_destino)
        layout.addWidget(reasig_group)

        # Cargar categorías destino desde catálogo maestro
        categorias_destino_data = self.firebase_client.get_categorias_maestras() or []
        self.cat_destino_map = {
            c.get("nombre", f"Cat {c.get('id')}"): str(c["id"])
            for c in categorias_destino_data
            if "id" in c
        }
        self.combo_cat_destino.addItems(
            sorted(self.cat_destino_map.keys(), key=lambda x: x.upper())
        )

        def update_subcats():
            cat_nombre = self.combo_cat_destino.currentText()
            cat_id = self.cat_destino_map.get(cat_nombre)
            self.combo_sub_destino.clear()
            if not cat_id:
                return
            subcategorias_data = [
                s
                for s in self.firebase_client.get_subcategorias_maestras() or []
                if str(s.get("categoria_id")) == str(cat_id)
            ]
            nombres = [
                s.get("nombre", f"Sub {s.get('id')}") for s in subcategorias_data
            ]
            self.combo_sub_destino.addItems(
                sorted(nombres, key=lambda x: x.upper())
            )

        self.combo_cat_destino.currentIndexChanged.connect(update_subcats)
        update_subcats()

        # --- Botones de reasignación selección ---
        btn_layout = QHBoxLayout()
        btn_cat = QPushButton("Reasignar Seleccionados de Categoría")
        btn_sub = QPushButton("Reasignar Seleccionados de Subcategoría")
        btn_layout.addWidget(btn_cat)
        btn_layout.addWidget(btn_sub)
        layout.addLayout(btn_layout)

        # --- Botones de reasignación masiva ---
        btn_masivo_cat = QPushButton(
            "Reasignar TODAS las transacciones de Categoría Huérfana"
        )
        btn_masivo_sub = QPushButton(
            "Reasignar TODAS las transacciones de Subcategoría Huérfana"
        )
        layout.addWidget(btn_masivo_cat)
        layout.addWidget(btn_masivo_sub)

        # --- Funciones internas de reasignación ---

        def _obtener_ids_destino() -> Optional[tuple[int, int, str, str]]:
            cat_destino_nombre = self.combo_cat_destino.currentText()
            sub_destino_nombre = self.combo_sub_destino.currentText()
            if not cat_destino_nombre or not sub_destino_nombre:
                QMessageBox.warning(
                    self,
                    "Destino Requerido",
                    "Debes seleccionar una nueva categoría y subcategoría de destino.",
                )
                return None
            cat_destino_id = self.cat_destino_map.get(cat_destino_nombre)
            if not cat_destino_id:
                QMessageBox.warning(
                    self,
                    "Destino Requerido",
                    "Categoría de destino inválida.",
                )
                return None
            try:
                sub_destino_id = self.firebase_client.obtener_o_crear_subcategoria(
                    sub_destino_nombre, cat_destino_id
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"No se pudo obtener/crear la subcategoría destino:\n{e}",
                )
                return None
            return (
                cat_destino_id,
                sub_destino_id,
                cat_destino_nombre,
                sub_destino_nombre,
            )

        def reasignar_seleccion(table, tipo: str):
            selected_rows = table.selectionModel().selectedRows()
            if not selected_rows:
                QMessageBox.warning(
                    self,
                    "Sin Selección",
                    "Por favor, selecciona al menos una transacción.",
                )
                return

            ids_dest = _obtener_ids_destino()
            if not ids_dest:
                return
            (
                cat_destino_id,
                sub_destino_id,
                cat_dest_nombre,
                sub_dest_nombre,
            ) = ids_dest

            seleccionados: List[str] = []
            for idx in selected_rows:
                row = idx.row()
                if tipo == "cat":
                    t = self.trans_no_categoria[row]
                else:
                    t = self.trans_no_subcategoria[row]
                tid = t.get("id")
                if tid:
                    seleccionados.append(str(tid))

            if not seleccionados:
                QMessageBox.warning(
                    self,
                    "Sin Selección",
                    "No se encontraron IDs de transacciones seleccionadas.",
                )
                return

            ok = self.firebase_client.reasignar_multiples_transacciones(
                self.proyecto_id,
                seleccionados,
                cat_destino_id,
                sub_destino_id,
                categoria_destino_nombre=cat_dest_nombre,
                subcategoria_destino_nombre=sub_dest_nombre,
            )
            if ok:
                QMessageBox.information(
                    self,
                    "Éxito",
                    f"{len(seleccionados)} transacciones han sido reasignadas.",
                )
                # Eliminar filas de la tabla visualmente
                for idx in sorted(
                    selected_rows, key=lambda x: x.row(), reverse=True
                ):
                    table.removeRow(idx.row())
            else:
                QMessageBox.critical(
                    self, "Error", "Ocurrió un error al reasignar las transacciones."
                )

        btn_cat.clicked.connect(lambda: reasignar_seleccion(self.table_cat, "cat"))
        btn_sub.clicked.connect(lambda: reasignar_seleccion(self.table_sub, "sub"))

        def reasignar_todas_categoria():
            if not self.trans_no_categoria:
                QMessageBox.information(
                    self,
                    "Sin datos",
                    "No hay transacciones con categoría huérfana.",
                )
                return

            ids_dest = _obtener_ids_destino()
            if not ids_dest:
                return
            (
                cat_destino_id,
                sub_destino_id,
                cat_dest_nombre,
                sub_dest_nombre,
            ) = ids_dest

            # Tomamos todos los categoria_id origen presentes en la lista
            origen_ids = set()
            for t in self.trans_no_categoria:
                origen_ids.add(t.get("categoria_id"))

            ok_total = True
            for origen in origen_ids:
                if origen is None:
                    # No podemos filtrar por None con Firestore; estas ya las cubre la reasignación por IDs,
                    # pero para simplificar, las reasignamos usando reasignar_multiples_transacciones
                    # con lista de ids de self.trans_no_categoria
                    trans_ids = [
                        str(t.get("id"))
                        for t in self.trans_no_categoria
                        if t.get("categoria_id") is None
                    ]
                    if trans_ids:
                        ok = self.firebase_client.reasignar_multiples_transacciones(
                            self.proyecto_id,
                            trans_ids,
                            cat_destino_id,
                            sub_destino_id,
                            categoria_destino_nombre=cat_dest_nombre,
                            subcategoria_destino_nombre=sub_dest_nombre,
                        )
                        ok_total = ok_total and ok
                else:
                    ok = (
                        self.firebase_client.reasignar_transacciones_por_categoria_origen(
                            self.proyecto_id,
                            origen,
                            cat_destino_id,
                            sub_destino_id,
                            categoria_destino_nombre=cat_dest_nombre,
                            subcategoria_destino_nombre=sub_dest_nombre,
                        )
                    )
                    ok_total = ok_total and ok

            if ok_total:
                QMessageBox.information(
                    self,
                    "Éxito",
                    "Todas las transacciones con categoría huérfana han sido reasignadas.",
                )
                self.table_cat.setRowCount(0)
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    "Ocurrió un error al reasignar las transacciones.",
                )

        def reasignar_todas_subcategoria():
            if not self.trans_no_subcategoria:
                QMessageBox.information(
                    self,
                    "Sin datos",
                    "No hay transacciones con subcategoría huérfana.",
                )
                return

            ids_dest = _obtener_ids_destino()
            if not ids_dest:
                return
            (
                cat_destino_id,
                sub_destino_id,
                cat_dest_nombre,
                sub_dest_nombre,
            ) = ids_dest

            origen_ids = set()
            for t in self.trans_no_subcategoria:
                origen_ids.add(t.get("subcategoria_id"))

            ok_total = True
            for origen in origen_ids:
                if origen is None:
                    trans_ids = [
                        str(t.get("id"))
                        for t in self.trans_no_subcategoria
                        if t.get("subcategoria_id") is None
                    ]
                    if trans_ids:
                        ok = self.firebase_client.reasignar_multiples_transacciones(
                            self.proyecto_id,
                            trans_ids,
                            cat_destino_id,
                            sub_destino_id,
                            categoria_destino_nombre=cat_dest_nombre,
                            subcategoria_destino_nombre=sub_dest_nombre,
                        )
                        ok_total = ok_total and ok
                else:
                    ok = (
                        self.firebase_client.reasignar_transacciones_por_subcategoria_origen(
                            self.proyecto_id,
                            origen,
                            cat_destino_id,
                            sub_destino_id,
                            categoria_destino_nombre=cat_dest_nombre,
                            subcategoria_destino_nombre=sub_dest_nombre,
                        )
                    )
                    ok_total = ok_total and ok

            if ok_total:
                QMessageBox.information(
                    self,
                    "Éxito",
                    "Todas las transacciones con subcategoría huérfana han sido reasignadas.",
                )
                self.table_sub.setRowCount(0)
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    "Ocurrió un error al reasignar las transacciones.",
                )

        btn_masivo_cat.clicked.connect(reasignar_todas_categoria)
        btn_masivo_sub.clicked.connect(reasignar_todas_subcategoria)

        # --- Botón Cerrar ---
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.clicked.connect(self.close)
        layout.addWidget(btn_cerrar)