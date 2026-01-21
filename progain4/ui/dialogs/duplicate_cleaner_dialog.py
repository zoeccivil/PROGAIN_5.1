"""
Diálogo para limpiar transacciones duplicadas en Firebase. 

Criterio de duplicado:
- Misma fecha
- Misma descripción
- Mismo monto
- Mismo proyecto

Mantiene la primera transacción encontrada y elimina el resto.
"""

import logging
from typing import Dict
import hashlib
from collections import defaultdict

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QMessageBox,
    QTextEdit, QProgressBar, QGroupBox
)
from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)


class CleanupWorker(QThread):
    """Worker thread para limpiar duplicados sin bloquear UI"""

    progress = pyqtSignal(int, int)  # (current, total)
    log = pyqtSignal(str)
    finished = pyqtSignal(int, int)  # (total_duplicates, total_deleted)
    error = pyqtSignal(str)

    def __init__(self, firebase_client, proyecto_id:  str, dry_run: bool = True):
        super().__init__()
        self.firebase_client = firebase_client
        self. proyecto_id = str(proyecto_id)
        self.dry_run = dry_run
        self._is_running = True

    def stop(self):
        self._is_running = False

    def _generate_hash(self, trans:  Dict) -> str:
        """Genera hash único basado en fecha, descripción y monto"""
        try:
            fecha = str(trans.get('fecha', ''))
            desc = str(trans.get('descripcion', '')).strip().lower()
            monto = f"{float(trans.get('monto', 0)):.2f}"

            raw = f"{fecha}|{desc}|{monto}"
            return hashlib.md5(raw.encode('utf-8')).hexdigest()
        except Exception as e: 
            logger.error(f"Error generando hash: {e}")
            return f"error_{id(trans)}"

    def run(self):
        try:
            self.log.emit("📂 Obteniendo transacciones del proyecto...")

            # Obtener todas las transacciones del proyecto
            trans_ref = (
                self.firebase_client. db. collection('proyectos')
                .document(self.proyecto_id)
                .collection('transacciones')
            )

            docs = list(trans_ref.stream())
            total = len(docs)

            self.log.emit(f"📊 Total de transacciones: {total}")
            self.log.emit("")

            if total == 0:
                self. log.emit("⚠️ No hay transacciones en este proyecto")
                self.finished.emit(0, 0)
                return

            # Agrupar por hash
            hash_groups = defaultdict(list)

            self.log.emit("🔍 Analizando duplicados...")

            for i, doc in enumerate(docs):
                if not self._is_running:
                    self.log.emit("⚠️ Proceso cancelado por el usuario")
                    return

                data = doc.to_dict()
                data['_doc_id'] = doc.id

                h = self._generate_hash(data)
                hash_groups[h].append(data)

                self.progress.emit(i + 1, total)

            # Encontrar duplicados
            duplicates_found = 0
            docs_to_delete = []

            self.log.emit("")
            self.log.emit("=" * 70)
            self.log.emit("DUPLICADOS ENCONTRADOS:")
            self.log.emit("=" * 70)

            for h, group in hash_groups. items():
                if len(group) > 1:
                    duplicates_found += 1

                    # Mantener el primero, marcar el resto para eliminar
                    keep = group[0]
                    delete = group[1:]

                    self.log.emit(f"\n🔁 Duplicado #{duplicates_found}:")
                    self.log.emit(f"   📅 Fecha: {keep. get('fecha')}")
                    self.log. emit(f"   💰 Monto: {keep.get('monto')}")
                    self.log.emit(f"   📝 Descripción: {keep. get('descripcion', '')[:60]}...")
                    self.log.emit(f"   🔢 Apariciones: {len(group)}")
                    self.log.emit(f"   ✅ Mantener: {keep['_doc_id']}")

                    for dup in delete:
                        self.log.emit(f"   ❌ Eliminar:  {dup['_doc_id']}")
                        docs_to_delete.append((dup['_doc_id'], dup))  # ✅ Guardar snapshot

            self.log.emit("")
            self.log.emit("=" * 70)
            self.log.emit(f"📊 RESUMEN:")
            self.log. emit(f"   Total transacciones: {total}")
            self.log.emit(f"   Grupos duplicados: {duplicates_found}")
            self.log.emit(f"   Documentos a eliminar: {len(docs_to_delete)}")
            self.log.emit("=" * 70)
            self.log.emit("")

            # Eliminar duplicados (si no es dry run)
            deleted_count = 0

            if not self.dry_run and docs_to_delete:
                self.log.emit("🗑️ Eliminando duplicados...")

                for i, (doc_id, snapshot) in enumerate(docs_to_delete):
                    if not self._is_running:
                        self.log.emit("⚠️ Eliminación cancelada")
                        break

                    try:
                        trans_ref. document(doc_id).delete()
                        deleted_count += 1
                        self.log.emit(f"   ✅ Eliminado:  {doc_id}")
                    except Exception as e:
                        self.log.emit(f"   ❌ Error eliminando {doc_id}: {e}")

                    self.progress.emit(i + 1, len(docs_to_delete))

                self.log.emit("")
                self.log.emit(f"✅ Eliminados {deleted_count} documentos duplicados")

            elif self.dry_run and docs_to_delete:
                self.log.emit("ℹ️ MODO SIMULACIÓN - No se eliminó nada")
                self.log.emit("ℹ️ Ejecuta en modo REAL para eliminar duplicados")

            self.finished.emit(duplicates_found, deleted_count)

        except Exception as e: 
            logger.exception(f"Error en CleanupWorker: {e}")
            self.error.emit(str(e))


class DuplicateCleanerDialog(QDialog):
    """
    Diálogo para limpiar duplicados en Firebase.
    
    ✅ MODIFICADO: Usa FirebaseClient existente, no requiere credenciales nuevas. 
    """

    def __init__(self, firebase_client, proyecto_id: str, proyecto_nombre: str, parent=None):
        super().__init__(parent)
        self.firebase_client = firebase_client
        self.proyecto_id = str(proyecto_id)
        self.proyecto_nombre = proyecto_nombre
        self.worker = None

        self.setWindowTitle(f"Limpiador de Duplicados - {proyecto_nombre}")
        self.resize(900, 700)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # === Título ===
        title = QLabel(f"🔍 Limpiador de Duplicados\n\nProyecto: {self.proyecto_nombre}")
        title.setStyleSheet("font-weight: bold; font-size: 14pt;")
        layout.addWidget(title)

        # === Información ===
        info_group = QGroupBox("ℹ️ Criterio de Duplicado")
        info_layout = QVBoxLayout(info_group)
        info_layout.addWidget(QLabel("Se consideran duplicadas las transacciones con: "))
        info_layout.addWidget(QLabel("  • Misma fecha"))
        info_layout.addWidget(QLabel("  • Misma descripción"))
        info_layout.addWidget(QLabel("  • Mismo monto"))
        info_layout.addWidget(QLabel("\nSe mantendrá la primera transacción y se eliminarán las demás."))
        layout.addWidget(info_group)

        # === Acciones ===
        action_group = QGroupBox("🔧 Acciones")
        action_layout = QHBoxLayout(action_group)

        self.btn_analyze = QPushButton("🔍 Analizar Duplicados (Simulación)")
        self.btn_analyze.clicked.connect(lambda: self.start_cleanup(dry_run=True))
        action_layout.addWidget(self. btn_analyze)

        self.btn_clean = QPushButton("🗑️ Eliminar Duplicados (REAL)")
        self.btn_clean.clicked.connect(lambda: self.start_cleanup(dry_run=False))
        self.btn_clean.setStyleSheet("background-color: #ff6b6b; color: white; font-weight: bold;")
        action_layout.addWidget(self.btn_clean)

        self.btn_cancel = QPushButton("⏹️ Cancelar")
        self.btn_cancel. setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancel_cleanup)
        action_layout.addWidget(self. btn_cancel)

        layout.addWidget(action_group)

        # === Progreso ===
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # === Log ===
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("font-family: 'Courier New'; font-size: 10pt;")
        layout.addWidget(self.log_text)

        # === Botón cerrar ===
        btn_close = QPushButton("Cerrar")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

    def log(self, msg:  str):
        self.log_text.append(msg)

    def start_cleanup(self, dry_run: bool = True):
        """Inicia proceso de limpieza"""

        # Confirmación para modo REAL
        if not dry_run:
            reply = QMessageBox.question(
                self,
                "⚠️ CONFIRMAR ELIMINACIÓN",
                "¿Estás seguro de que quieres ELIMINAR los duplicados?\n\n"
                "Esta acción NO se puede deshacer.\n\n"
                "Recomendación: Ejecuta primero en modo Simulación.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if reply == QMessageBox. StandardButton.No:
                return

        # Limpiar log
        self.log_text.clear()

        mode = "SIMULACIÓN" if dry_run else "ELIMINACIÓN REAL"
        self.log(f"🚀 Iniciando en modo: {mode}")
        self.log(f"📁 Proyecto: {self.proyecto_nombre} (ID: {self.proyecto_id})")
        self.log("")

        # Configurar UI
        self.btn_analyze. setEnabled(False)
        self.btn_clean.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        # Iniciar worker
        self.worker = CleanupWorker(self.firebase_client, self.proyecto_id, dry_run)
        self.worker. progress. connect(self.on_progress)
        self.worker.log. connect(self.log)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def cancel_cleanup(self):
        """Cancela el proceso en curso"""
        if self.worker and self. worker. isRunning():
            self.log("⏹️ Cancelando proceso...")
            self.worker.stop()
            self.worker.wait()

    def on_progress(self, current:  int, total: int):
        """Actualiza barra de progreso"""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)

    def on_finished(self, duplicates_found: int, deleted_count: int):
        """Proceso terminado"""
        self.progress_bar.setVisible(False)

        self.log("")
        self.log("=" * 70)
        self.log("✅ PROCESO COMPLETADO")
        self.log(f"   Grupos duplicados encontrados: {duplicates_found}")
        self.log(f"   Documentos eliminados: {deleted_count}")
        self.log("=" * 70)

        # Restaurar UI
        self.btn_analyze. setEnabled(True)
        self.btn_clean.setEnabled(True)
        self.btn_cancel.setEnabled(False)

        if deleted_count > 0:
            QMessageBox.information(
                self,
                "✅ Completado",
                f"Se eliminaron {deleted_count} transacciones duplicadas.\n\n"
                f"Se encontraron {duplicates_found} grupos de duplicados."
            )
            
            # ✅ Notificar al padre para que refresque
            if self.parent():
                self. parent().statusBar().showMessage(
                    f"✅ Limpieza completada:  {deleted_count} duplicados eliminados",
                    5000
                )

    def on_error(self, error_msg: str):
        """Error durante el proceso"""
        self.log(f"❌ ERROR: {error_msg}")

        self.progress_bar.setVisible(False)
        self.btn_analyze.setEnabled(True)
        self.btn_clean. setEnabled(True)
        self.btn_cancel.setEnabled(False)

        QMessageBox. critical(self, "Error", f"Error durante el proceso:\n{error_msg}")