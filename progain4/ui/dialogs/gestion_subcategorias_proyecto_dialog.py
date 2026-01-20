from typing import List, Dict, Any, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QMessageBox,
    QHBoxLayout,
    QComboBox,
    QInputDialog,
)

CHECK_MARK = "✔"
CHECK_SPACE = " " * len(CHECK_MARK)


class GestionSubcategoriasProyectoDialog(QDialog):
    """
    Gestionar cuáles subcategorías maestras estarán activas en un proyecto.

    - Primero eliges una categoría del proyecto (ya filtrada por proyecto).
    - Muestra las subcategorías maestras de esa categoría, con marca '✔' para indicar selección.
    - Puedes agregar/renombrar/borrar subcategorías maestras (afecta catálogo global).
    - Guarda la selección en proyectos/{proyecto_id}/subcategorias_proyecto.
    """

    def __init__(self, firebase_client, proyecto_id: str, proyecto_nombre: str, parent=None):
        super().__init__(parent)
        self.firebase_client = firebase_client
        self.proyecto_id = proyecto_id
        self.proyecto_nombre = proyecto_nombre

        self.setWindowTitle(f"Gestionar Subcategorías del Proyecto: {proyecto_nombre}")
        self.setFixedSize(520, 580)

        layout = QVBoxLayout(self)
        label_intro = QLabel(
            "Selecciona la categoría y marca las subcategorías que estarán activas en este proyecto:"
        )
        label_intro.setWordWrap(True)
        layout.addWidget(label_intro)

        # Selector de categoría (categorías del proyecto)
        self.combo_categoria = QComboBox()
        layout.addWidget(self.combo_categoria)

        # Lista de subcategorías con marca ✔ en el texto
        self.lista_subcategorias = QListWidget()
        self.lista_subcategorias.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        layout.addWidget(self.lista_subcategorias)

        # Resumen de cuántas subcategorías seleccionadas (para la categoría actual y global)
        self.label_resumen = QLabel("0 subcategorías seleccionadas")
        self.label_resumen.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.label_resumen)

        # Botones de gestión de subcategoría maestra
        btn_sub_layout = QHBoxLayout()
        self.btn_agregar_sub = QPushButton("Agregar")
        self.btn_editar_sub = QPushButton("Renombrar")
        self.btn_borrar_sub = QPushButton("Borrar")
        btn_sub_layout.addWidget(self.btn_agregar_sub)
        btn_sub_layout.addWidget(self.btn_editar_sub)
        btn_sub_layout.addWidget(self.btn_borrar_sub)
        layout.addLayout(btn_sub_layout)

        # Botones de guardar/cancelar
        btn_layout = QHBoxLayout()
        self.btn_guardar = QPushButton("Guardar Cambios")
        self.btn_cancelar = QPushButton("Cancelar")
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_guardar)
        btn_layout.addWidget(self.btn_cancelar)
        layout.addLayout(btn_layout)

        # Estado
        self.categorias: List[Dict[str, Any]] = []  # categorías del proyecto
        # Mapa: categoria_id -> set(subcategoria_id seleccionada)
        self.seleccion_por_categoria: Dict[str, set[str]] = {}
        self.cat_id_actual: Optional[str] = None

        # Conexiones
        self.combo_categoria.currentIndexChanged.connect(self._cambiar_categoria)
        self.btn_guardar.clicked.connect(self._guardar)
        self.btn_cancelar.clicked.connect(self.reject)
        self.btn_agregar_sub.clicked.connect(self._agregar_subcategoria)
        self.btn_editar_sub.clicked.connect(self._renombrar_subcategoria)
        self.btn_borrar_sub.clicked.connect(self._borrar_subcategoria)

        self.lista_subcategorias.itemClicked.connect(self._toggle_item)

        # Carga inicial
        self._cargar_categorias()

    # ------------------------------------------------------------------ Carga

    def _cargar_categorias(self):
        """Carga categorías activas del proyecto en el combo con sus nombres."""
        try:
            # 1️⃣ Obtener IDs de categorías activas en el proyecto
            categorias_proyecto = self.firebase_client.get_categorias_por_proyecto(self.proyecto_id) or []
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudieron cargar las categorías del proyecto:\n{e}",
            )
            return

        # 2️⃣ Obtener categorías maestras para tener los nombres
        try:
            categorias_maestras = self.firebase_client.get_categorias_maestras() or []
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudieron cargar las categorías maestras:\n{e}",
            )
            return

        # 3️⃣ Crear mapa:   id -> nombre
        categorias_map = {
            str(cat. get("id")): cat.get("nombre", f"Categoría {cat.get('id')}")
            for cat in categorias_maestras
        }

        # 4️⃣ Construir lista de categorías del proyecto con nombres
        self.categorias = []
        for cat_proyecto in categorias_proyecto:
            cat_id = str(cat_proyecto.get("id", ""))
            if not cat_id:
                continue
            
            # Obtener el nombre desde el mapa de maestras
            cat_nombre = categorias_map. get(cat_id, f"Categoría {cat_id}")
            
            self.categorias.append({
                "id": cat_id,
                "nombre": cat_nombre
            })

        # 5️⃣ Poblar combo con nombres correctos
        self.combo_categoria.clear()
        
        # Ordenar alfabéticamente por nombre
        self. categorias.sort(key=lambda c: c["nombre"]. upper())
        
        for cat in self.categorias:
            self.combo_categoria.addItem(cat["nombre"], cat["id"])

        if self.categorias:
            # Cargar selección previa
            self._cargar_seleccion_global()
            self._cambiar_categoria()
        else:
            self.cat_id_actual = None
            self.lista_subcategorias.clear()
            self._actualizar_resumen()

    def _cargar_seleccion_global(self):
        """
        Carga desde Firebase las subcategorías ya asociadas al proyecto
        y las distribuye en self.seleccion_por_categoria.
        """
        try:
            subcats_proyecto = self.firebase_client.get_subcategorias_por_proyecto(
                self.proyecto_id
            ) or []
        except Exception as e:
            QMessageBox.warning(
                self,
                "Advertencia",
                f"No se pudo cargar la configuración de subcategorías del proyecto:\n{e}",
            )
            subcats_proyecto = []

        # Esperamos una estructura mínima: {id, nombre, categoria_id}
        self.seleccion_por_categoria.clear()
        for sub in subcats_proyecto:
            cat_id = str(sub.get("categoria_id", ""))
            sub_id = str(sub.get("id", ""))
            if not cat_id or not sub_id:
                continue
            if cat_id not in self.seleccion_por_categoria:
                self.seleccion_por_categoria[cat_id] = set()
            self.seleccion_por_categoria[cat_id].add(sub_id)

    # ------------------------------------------------------------------ Cambio de categoría

    def _guardar_seleccion_actual(self):
        """Guarda la selección actual de subcategorías para la categoría activa."""
        if self.cat_id_actual is None:
            return

        seleccion = set()
        for i in range(self.lista_subcategorias.count()):
            item = self.lista_subcategorias.item(i)
            sub_id = str(item.data(Qt.ItemDataRole.UserRole))
            # Basado en nuestro propio set, pero aquí podemos leer del texto
            # o mantenerlo en un set intermedio
            if self._item_es_seleccionado(item):
                seleccion.add(sub_id)

        self.seleccion_por_categoria[self.cat_id_actual] = seleccion

    def _cambiar_categoria(self):
        """Cambia de categoría en el combo y actualiza la lista de subcategorías."""
        # Antes de cambiar, guardamos el estado actual
        self._guardar_seleccion_actual()

        idx = self.combo_categoria.currentIndex()
        if idx < 0 or not self.categorias:
            self.lista_subcategorias.clear()
            self. cat_id_actual = None
            self._actualizar_resumen()
            return

        cat_id = str(self.combo_categoria.currentData())
        self.cat_id_actual = cat_id

        # Cargar subcategorías maestras de esa categoría
        try: 
            subcats = self.firebase_client.get_subcategorias_maestras_by_categoria(cat_id) or []
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudieron cargar las subcategorías maestras:\n{e}",
            )
            self.lista_subcategorias.clear()
            self._actualizar_resumen()
            return

        self.lista_subcategorias.clear()

        # IDs previamente seleccionados para esta categoría
        seleccionadas_ids = self.seleccion_por_categoria.get(cat_id, set())

        for sub in subcats:
            sub_id = str(sub. get("id", ""))
            if not sub_id:
                continue
            
            # ✅ CORRECCIÓN: Validar que el nombre existe y no esté vacío
            nombre_raw = sub.get("nombre", "")
            if not nombre_raw or nombre_raw.strip() == "":
                # Si no tiene nombre, intentar obtenerlo del ID o generar uno
                nombre_puro = f"Subcategoría {sub_id}"
            else:
                nombre_puro = nombre_raw. strip()
            
            # ✅ VALIDACIÓN ADICIONAL: Si el nombre parece ser solo un ID, mejorarlo
            if nombre_puro. startswith("Categoría ") or nombre_puro.isdigit():
                nombre_puro = f"Subcategoría {sub_id}"
            
            seleccionada = sub_id in seleccionadas_ids
            texto = f"{CHECK_MARK if seleccionada else CHECK_SPACE}  {nombre_puro}"

            item = QListWidgetItem(texto)
            item.setData(Qt.ItemDataRole.UserRole, sub_id)
            item.setData(Qt.ItemDataRole.UserRole + 1, nombre_puro)
            item.setFlags(
                Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsEnabled
            )
            self.lista_subcategorias.addItem(item)

        if self.lista_subcategorias. count() > 0:
            self.lista_subcategorias.setCurrentRow(0)

        self._actualizar_resumen()

    # ------------------------------------------------------------------ Helpers selección

    def _item_es_seleccionado(self, item: QListWidgetItem) -> bool:
        """Determina si un item está seleccionado basado en el texto (✔ o espacio)."""
        texto = item.text()
        return texto.startswith(CHECK_MARK)

    def _actualizar_item_texto(self, item: QListWidgetItem, seleccionado: bool):
        """Pone o quita la marca ✔ en el texto del item."""
        nombre_puro = item.data(Qt.ItemDataRole.UserRole + 1) or ""
        item.setText(f"{CHECK_MARK if seleccionado else CHECK_SPACE}  {nombre_puro}")

    def _toggle_item(self, item: QListWidgetItem):
        """Al hacer clic en una subcategoría, alternamos su selección."""
        sub_id = str(item.data(Qt.ItemDataRole.UserRole))
        if self.cat_id_actual is None:
            return

        # Aseguramos que haya un set para esta categoría
        if self.cat_id_actual not in self.seleccion_por_categoria:
            self.seleccion_por_categoria[self.cat_id_actual] = set()

        if sub_id in self.seleccion_por_categoria[self.cat_id_actual]:
            self.seleccion_por_categoria[self.cat_id_actual].remove(sub_id)
            self._actualizar_item_texto(item, False)
        else:
            self.seleccion_por_categoria[self.cat_id_actual].add(sub_id)
            self._actualizar_item_texto(item, True)

        self._actualizar_resumen()

    def _contar_todas_seleccionadas(self) -> int:
        """Cuenta el total de subcategorías seleccionadas (todas las categorías)."""
        total = 0
        for ids in self.seleccion_por_categoria.values():
            total += len(ids)
        return total

    def _actualizar_resumen(self):
        """Actualiza 'X subcategorías seleccionadas' y los textos de la lista actual."""
        # Sincroniza texto de los items de la categoría actual
        if self.cat_id_actual is not None:
            seleccion_actual = self.seleccion_por_categoria.get(self.cat_id_actual, set())
            for i in range(self.lista_subcategorias.count()):
                item = self.lista_subcategorias.item(i)
                sub_id = str(item.data(Qt.ItemDataRole.UserRole))
                self._actualizar_item_texto(item, sub_id in seleccion_actual)

        n = self._contar_todas_seleccionadas()
        if n == 1:
            texto = "1 subcategoría seleccionada"
        else:
            texto = f"{n} subcategorías seleccionadas"
        self.label_resumen.setText(texto)

    # ------------------------------------------------------------------ CRUD subcategorías maestras

    def _agregar_subcategoria(self):
        if self.cat_id_actual is None:
            QMessageBox.warning(
                self,
                "Sin categoría",
                "Selecciona una categoría primero.",
            )
            return

        nombre, ok = QInputDialog.getText(
            self,
            "Nueva Subcategoría",
            "Nombre de la subcategoría:",
        )
        if not (ok and nombre.strip()):
            return

        try:
            self.firebase_client.create_subcategoria_maestra(
                nombre.strip(), self.cat_id_actual
            )
            # Recargar solo lista actual
            self._cambiar_categoria()
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudo agregar la subcategoría:\n{e}",
            )

    def _renombrar_subcategoria(self):
        if self.cat_id_actual is None:
            QMessageBox.warning(
                self,
                "Sin categoría",
                "Selecciona una categoría primero.",
            )
            return

        fila = self.lista_subcategorias.currentRow()
        if fila < 0:
            QMessageBox.warning(
                self,
                "Sin selección",
                "Selecciona una subcategoría para renombrar.",
            )
            return

        # Obtener subcategorías maestras actuales
        subcats = self.firebase_client.get_subcategorias_maestras_by_categoria(
            self.cat_id_actual
        ) or []
        if fila >= len(subcats):
            return

        sub = subcats[fila]
        nuevo_nombre, ok = QInputDialog.getText(
            self,
            "Renombrar Subcategoría",
            "Nuevo nombre:",
            text=sub["nombre"],
        )
        if not (ok and nuevo_nombre.strip()):
            return

        try:
            self.firebase_client.update_subcategoria_maestra(
                sub["id"], nuevo_nombre.strip()
            )
            self._cambiar_categoria()
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudo renombrar la subcategoría:\n{e}",
            )

    def _borrar_subcategoria(self):
        if self.cat_id_actual is None:
            QMessageBox.warning(
                self,
                "Sin categoría",
                "Selecciona una categoría primero.",
            )
            return

        fila = self.lista_subcategorias.currentRow()
        if fila < 0:
            QMessageBox.warning(
                self,
                "Sin selección",
                "Selecciona una subcategoría para borrar.",
            )
            return

        subcats = self.firebase_client.get_subcategorias_maestras_by_categoria(
            self.cat_id_actual
        ) or []
        if fila >= len(subcats):
            return

        sub = subcats[fila]
        if (
            QMessageBox.question(
                self,
                "Confirmar",
                f"¿Borrar la subcategoría '{sub['nombre']}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            != QMessageBox.StandardButton.Yes
        ):
            return

        try:
            self.firebase_client.delete_subcategoria_maestra(sub["id"])
            # Eliminarla también de la selección si estaba
            if (
                self.cat_id_actual in self.seleccion_por_categoria
                and sub["id"] in self.seleccion_por_categoria[self.cat_id_actual]
            ):
                self.seleccion_por_categoria[self.cat_id_actual].remove(sub["id"])
            self._cambiar_categoria()
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudo borrar la subcategoría:\n{e}",
            )

    # ------------------------------------------------------------------ Guardar

    def _guardar(self):
        # Antes de guardar, aseguramos que estado actual esté en el diccionario
        self._guardar_seleccion_actual()

        # Unimos todas las subcategorías seleccionadas de todas las categorías
        todas_seleccionadas_ids: set[str] = set()
        for sub_ids in self.seleccion_por_categoria.values():
            todas_seleccionadas_ids.update(sub_ids)

        if not todas_seleccionadas_ids:
            QMessageBox.warning(
                self,
                "Error",
                "Debes seleccionar al menos una subcategoría.",
            )
            return

        try:
            exito = self.firebase_client.asignar_subcategorias_a_proyecto(
                self.proyecto_id, list(todas_seleccionadas_ids)
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudieron guardar las subcategorías del proyecto:\n{e}",
            )
            return

        if exito:
            QMessageBox.information(
                self,
                "Guardado",
                "Subcategorías del proyecto actualizadas correctamente.",
            )
            self.accept()
        else:
            QMessageBox.warning(
                self,
                "Error",
                "No se pudieron guardar los cambios.",
            )