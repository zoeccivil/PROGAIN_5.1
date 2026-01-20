from typing import List, Dict, Any, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QMessageBox,
)


class GestionCuentasProyectoDialog(QDialog):
    """
    Gestión de Cuentas del Proyecto (versión Firebase).

    Versión corregida y alineada con el modelo actual:

    - Las transacciones usan:
        cuenta_id: número
        cuentaNombre: string

    - El catálogo global 'cuentas' tiene:
        id: numérico o string convertible a int
        nombre: string

    - La relación proyecto-cuenta se guarda en:
        proyectos/{proyecto_id}/cuentas_proyecto/{doc} con:
            cuenta_id: número
            cuenta_nombre: string
            principal: bool

    Requiere que FirebaseClient exponga:

      - get_cuentas_maestras() -> List[Dict[str, Any]]
            [
              { "id": 7, "nombre": "FEDASA BR 7225", ... },
              ...
            ]

      - get_cuentas_proyecto(proyecto_id: str) -> List[Dict[str, Any]]
            [
              { "cuenta_id": 7, "nombre": "FEDASA BR 7225", "principal": True },
              ...
            ]

      - save_cuentas_proyecto(
            proyecto_id: str,
            cuentas: List[Dict[str, Any]],
        ) -> bool
            cuentas: [
              { "cuenta_id": 7, "nombre": "FEDASA BR 7225", "principal": True },
              ...
            ]
    """

    def __init__(self, firebase_client, proyecto_id: str, proyecto_nombre: str, parent=None):
        super().__init__(parent)
        self.firebase_client = firebase_client
        self.proyecto_id = proyecto_id
        self.proyecto_nombre = proyecto_nombre

        self.setWindowTitle(f"Gestionar Cuentas del Proyecto: {proyecto_nombre}")
        self.setFixedSize(700, 400)

        # --- Layout principal ---
        main_layout = QVBoxLayout(self)

        # --- Layout de listas ---
        listas_layout = QHBoxLayout()

        # Cuentas disponibles (maestras)
        disponibles_layout = QVBoxLayout()
        disponibles_layout.addWidget(QLabel("Cuentas Disponibles"))
        self.list_disponibles = QListWidget()
        disponibles_layout.addWidget(self.list_disponibles)
        listas_layout.addLayout(disponibles_layout)

        # Botones mover
        mover_layout = QVBoxLayout()
        self.btn_agregar = QPushButton(">>")
        self.btn_quitar = QPushButton("<<")
        mover_layout.addStretch()
        mover_layout.addWidget(self.btn_agregar)
        mover_layout.addWidget(self.btn_quitar)
        mover_layout.addStretch()
        listas_layout.addLayout(mover_layout)

        # Cuentas del proyecto
        proyecto_layout = QVBoxLayout()
        proyecto_layout.addWidget(QLabel("Cuentas del Proyecto"))
        self.list_proyecto = QListWidget()
        proyecto_layout.addWidget(self.list_proyecto)
        self.btn_principal = QPushButton("Establecer como Principal")
        proyecto_layout.addWidget(self.btn_principal)
        listas_layout.addLayout(proyecto_layout)

        main_layout.addLayout(listas_layout)

        # --- Botones inferiores ---
        btn_layout = QHBoxLayout()
        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_guardar = QPushButton("Guardar Cambios")
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancelar)
        btn_layout.addWidget(self.btn_guardar)
        main_layout.addLayout(btn_layout)

        # --- Estado interno ---
        # cuentas_disponibles: List[Dict[id(int), nombre(str)]]
        self.cuentas_disponibles: List[Dict[str, Any]] = []
        # cuentas_proyecto: List[Dict[id(int), nombre(str), principal(bool)]]
        self.cuentas_proyecto: List[Dict[str, Any]] = []
        self.id_cuenta_principal: Optional[int] = None

        # --- Cargar datos iniciales ---
        self._cargar_cuentas()

        # --- Conexiones ---
        self.btn_agregar.clicked.connect(self._mover_a_proyecto)
        self.btn_quitar.clicked.connect(self._quitar_de_proyecto)
        self.btn_principal.clicked.connect(self._establecer_principal)
        self.btn_guardar.clicked.connect(self._guardar_cambios)
        self.btn_cancelar.clicked.connect(self.reject)

    # ------------------------------------------------------------------ CARGA INICIAL

    def _cargar_cuentas(self):
        """
        Carga: 
        - Todas las cuentas maestras (disponibles).
        - Todas las cuentas asociadas al proyecto. 
        Determina la cuenta principal si existe. 

        Normaliza todo a: 
          - id numérico (int) o string según lo que venga de Firebase
          - nombre str
        """
        try:
            # Todas las cuentas maestras (globales)
            maestras = self.firebase_client.get_cuentas_maestras() or []

            # Normalizamos:  aceptar IDs numéricos o strings
            cuentas_globales:  List[Dict[str, Any]] = []
            for c in maestras:
                raw_id = c.get("id")
                
                # Aceptar tanto IDs numéricos como strings
                if raw_id is None: 
                    continue
                
                # Intentar convertir a int si es posible, sino usar como string
                try:
                    cid = int(raw_id)
                except (ValueError, TypeError):
                    cid = str(raw_id)
                
                cuentas_globales.append(
                    {
                        "id": cid,
                        "nombre": c.get("nombre", f"Cuenta {cid}"),
                        "raw": c,
                    }
                )

            # Cuentas asociadas al proyecto
            cuentas_proy = self. firebase_client.get_cuentas_proyecto(self.proyecto_id) or []
            # Esperamos estructura: {"cuenta_id": int/str, "nombre": str, "principal": bool}

            self.cuentas_proyecto = []
            ids_proy = set()

            self.id_cuenta_principal = None

            for c in cuentas_proy:
                cuenta_id_raw = c.get("cuenta_id")
                if cuenta_id_raw is None: 
                    continue
                
                # Aceptar tanto int como string
                try:
                    cid = int(cuenta_id_raw)
                except (ValueError, TypeError):
                    cid = str(cuenta_id_raw)

                nombre = c.get("nombre", f"Cuenta {cid}")
                principal = bool(c.get("principal", False))

                self.cuentas_proyecto.append(
                    {
                        "id": cid,
                        "nombre": nombre,
                        "principal": principal,
                    }
                )
                ids_proy.add(cid)
                if principal and self.id_cuenta_principal is None:
                    self.id_cuenta_principal = cid

            # Si no hay principal marcada pero hay cuentas, ponemos la primera como principal
            if self.cuentas_proyecto and self.id_cuenta_principal is None:
                self.id_cuenta_principal = self.cuentas_proyecto[0]["id"]
                self.cuentas_proyecto[0]["principal"] = True

            # Cuentas disponibles = globales que no están ya en el proyecto
            self.cuentas_disponibles = [
                {"id": c["id"], "nombre": c["nombre"]}
                for c in cuentas_globales
                if c["id"] not in ids_proy
            ]

            # Ordenamos por nombre para que se vea prolijo
            self.cuentas_disponibles.sort(key=lambda x: (x["nombre"] or "").upper())
            self.cuentas_proyecto. sort(key=lambda x: (x["nombre"] or "").upper())

            self._actualizar_listas()

        except Exception as e: 
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudieron cargar las cuentas del proyecto:\n{e}",
            )


    def _actualizar_listas(self):
        """Refresca las listas de disponibles y proyecto en la UI."""
        self.list_disponibles.clear()
        for c in self.cuentas_disponibles:
            item = QListWidgetItem(c["nombre"])
            # Guardamos el id numérico en UserRole
            item.setData(Qt.ItemDataRole.UserRole, c["id"])
            self.list_disponibles.addItem(item)

        self.list_proyecto.clear()
        for c in self.cuentas_proyecto:
            txt = c["nombre"]
            if self.id_cuenta_principal is not None and self.id_cuenta_principal == c["id"]:
                txt += " (Principal)"
            item = QListWidgetItem(txt)
            item.setData(Qt.ItemDataRole.UserRole, c["id"])
            self.list_proyecto.addItem(item)

    # ------------------------------------------------------------------ ACCIONES

    def _mover_a_proyecto(self):
        items = self.list_disponibles.selectedItems()
        if not items:
            return

        item = items[0]
        cuenta_id = item.data(Qt.ItemDataRole.UserRole)  # int
        nombre = item.text()

        cuenta = next((c for c in self.cuentas_disponibles if c["id"] == cuenta_id), None)
        if cuenta:
            self.cuentas_disponibles.remove(cuenta)
            self.cuentas_proyecto.append(
                {
                    "id": cuenta["id"],
                    "nombre": cuenta["nombre"],
                    "principal": False,
                }
            )
            # Si no hay principal todavía, esta puede serlo
            if self.id_cuenta_principal is None:
                self.id_cuenta_principal = cuenta["id"]
                for c in self.cuentas_proyecto:
                    c["principal"] = (c["id"] == self.id_cuenta_principal)

            self._actualizar_listas()

    def _quitar_de_proyecto(self):
        items = self.list_proyecto.selectedItems()
        if not items:
            return

        item = items[0]
        cuenta_id = item.data(Qt.ItemDataRole.UserRole)  # int
        nombre_sin_flag = item.text().replace(" (Principal)", "")

        cuenta = next((c for c in self.cuentas_proyecto if c["id"] == cuenta_id), None)
        if cuenta:
            # Si era la principal, la quitamos
            if self.id_cuenta_principal == cuenta["id"]:
                self.id_cuenta_principal = None

            self.cuentas_proyecto.remove(cuenta)
            # De vuelta a disponibles
            self.cuentas_disponibles.append(
                {"id": cuenta["id"], "nombre": nombre_sin_flag}
            )

            # Si no queda principal pero hay cuentas, marcamos la primera
            if self.cuentas_proyecto and self.id_cuenta_principal is None:
                self.id_cuenta_principal = self.cuentas_proyecto[0]["id"]
                self.cuentas_proyecto[0]["principal"] = True

            self._actualizar_listas()

    def _establecer_principal(self):
        items = self.list_proyecto.selectedItems()
        if not items:
            QMessageBox.warning(
                self,
                "Sin selección",
                "Selecciona una cuenta del proyecto para establecer como principal.",
            )
            return

        item = items[0]
        cuenta_id = item.data(Qt.ItemDataRole.UserRole)  # int

        cuenta = next((c for c in self.cuentas_proyecto if c["id"] == cuenta_id), None)
        if cuenta:
            self.id_cuenta_principal = cuenta["id"]
            # Actualizar flags internos
            for c in self.cuentas_proyecto:
                c["principal"] = (c["id"] == self.id_cuenta_principal)
            self._actualizar_listas()

    def _guardar_cambios(self):
        if not self.cuentas_proyecto:
            QMessageBox.warning(
                self,
                "Error",
                "Debes asignar al menos una cuenta al proyecto.",
            )
            return

        if self.id_cuenta_principal is None:
            QMessageBox.warning(
                self,
                "Error",
                "Debes establecer una cuenta principal.",
            )
            return

        # Construimos la lista para FirebaseClient.save_cuentas_proyecto
        cuentas_payload:  List[Dict[str, Any]] = []
        for c in self.cuentas_proyecto:
            # Asegurarse de que cuenta_id sea del tipo correcto (int o str según Firebase)
            cuenta_id = c["id"]
            
            cuentas_payload.append(
                {
                    "cuenta_id": cuenta_id,  # Puede ser int o str
                    "nombre": c["nombre"],
                    "principal": bool(c. get("principal", False)),
                }
            )

        try:
            exito = self.firebase_client.save_cuentas_proyecto(
                self.proyecto_id,
                cuentas_payload,
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudieron guardar las cuentas del proyecto:\n{e}",
            )
            return

        if exito: 
            QMessageBox.information(
                self,
                "Guardado",
                "Cuentas del proyecto actualizadas correctamente.",
            )
            self.accept()
        else:
            QMessageBox.warning(
                self,
                "Error",
                "No se pudieron guardar las cuentas del proyecto.",
            )