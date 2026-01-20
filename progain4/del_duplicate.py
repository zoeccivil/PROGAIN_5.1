"""
Script para eliminar transacciones duplicadas en Firebase. 

Criterio de duplicado:  
- Misma fecha
- Misma descripción  
- Mismo monto
- Mismo proyecto

Mantiene la primera transacción encontrada y elimina el resto.
"""

import sys
from pathlib import Path
from typing import Dict, List, Tuple
import hashlib
from collections import defaultdict

from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QFileDialog, QMessageBox,
    QTextEdit, QProgressBar, QComboBox, QGroupBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

import firebase_admin
from firebase_admin import credentials, firestore


class CleanupWorker(QThread):
    """Worker thread para limpiar duplicados sin bloquear UI"""
    
    progress = pyqtSignal(int, int)  # (current, total)
    log = pyqtSignal(str)
    finished = pyqtSignal(int, int)  # (total_duplicates, total_deleted)
    error = pyqtSignal(str)
    
    def __init__(self, db, proyecto_id:  str, dry_run: bool = True):
        super().__init__()
        self.db = db
        self.proyecto_id = proyecto_id
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
            return f"error_{id(trans)}"
    
    def run(self):
        try:
            self.log.emit("📂 Obteniendo transacciones del proyecto...")
            
            # Obtener todas las transacciones del proyecto
            trans_ref = (
                self.db.collection('proyectos')
                .document(str(self.proyecto_id))
                .collection('transacciones')
            )
            
            docs = list(trans_ref.stream())
            total = len(docs)
            
            self.log.emit(f"📊 Total de transacciones:   {total}")
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
            
            for h, group in hash_groups.items():
                if len(group) > 1:
                    duplicates_found += 1
                    
                    # Mantener el primero, marcar el resto para eliminar
                    keep = group[0]
                    delete = group[1:]
                    
                    self.log.emit(f"\n🔁 Duplicado #{duplicates_found}:")
                    self.log.emit(f"   📅 Fecha: {keep. get('fecha')}")
                    self.log. emit(f"   💰 Monto: {keep.get('monto')}")
                    self.log.emit(f"   📝 Descripción:  {keep.get('descripcion', '')[:60]}...")
                    self.log.emit(f"   🔢 Apariciones: {len(group)}")
                    self.log.emit(f"   ✅ Mantener: {keep['_doc_id']}")
                    
                    for dup in delete:
                        self.log.emit(f"   ❌ Eliminar:  {dup['_doc_id']}")
                        docs_to_delete.append(dup['_doc_id'])
            
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
                
                for i, doc_id in enumerate(docs_to_delete):
                    if not self._is_running:
                        self.log.emit("⚠️ Eliminación cancelada")
                        break
                    
                    try:
                        trans_ref.document(doc_id).delete()
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
            self. error.emit(str(e))


class DuplicateCleanerDialog(QDialog):
    """Diálogo para limpiar duplicados en Firebase"""
    
    def __init__(self):
        super().__init__()
        self.db = None
        self.worker = None
        self.proyectos = []
        
        self.setWindowTitle("Limpiador de Duplicados - Firebase")
        self.resize(900, 700)
        
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # === Grupo 1: Credenciales ===
        cred_group = QGroupBox("Paso 1: Cargar Credenciales de Firebase")
        cred_layout = QHBoxLayout(cred_group)
        
        self.btn_load_creds = QPushButton("📁 Seleccionar archivo JSON de credenciales")
        self.btn_load_creds.clicked.connect(self.load_credentials)
        cred_layout.addWidget(self.btn_load_creds)
        
        self.lbl_creds_status = QLabel("⚠️ Sin credenciales")
        cred_layout.addWidget(self.lbl_creds_status)
        
        layout.addWidget(cred_group)
        
        # === Grupo 2: Proyecto ===
        proj_group = QGroupBox("Paso 2: Seleccionar Proyecto")
        proj_layout = QHBoxLayout(proj_group)
        
        proj_layout.addWidget(QLabel("Proyecto: "))
        self.combo_proyecto = QComboBox()
        self.combo_proyecto.setEnabled(False)
        proj_layout.addWidget(self.combo_proyecto)
        
        layout.addWidget(proj_group)
        
        # === Grupo 3: Acciones ===
        action_group = QGroupBox("Paso 3: Analizar y Limpiar")
        action_layout = QHBoxLayout(action_group)
        
        self.btn_analyze = QPushButton("🔍 Analizar Duplicados (Simulación)")
        self.btn_analyze.setEnabled(False)
        self.btn_analyze.clicked.connect(lambda: self.start_cleanup(dry_run=True))
        action_layout.addWidget(self. btn_analyze)
        
        self.btn_clean = QPushButton("🗑️ Eliminar Duplicados (REAL)")
        self.btn_clean.setEnabled(False)
        self.btn_clean.clicked.connect(lambda: self.start_cleanup(dry_run=False))
        self.btn_clean.setStyleSheet("background-color: #ff6b6b; color: white; font-weight: bold;")
        action_layout.addWidget(self.btn_clean)
        
        self.btn_cancel = QPushButton("⏹️ Cancelar")
        self.btn_cancel. setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancel_cleanup)
        action_layout.addWidget(self.btn_cancel)
        
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
    
    def load_credentials(self):
        """Carga credenciales de Firebase desde archivo JSON"""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar archivo de credenciales Firebase",
            "",
            "JSON Files (*.json);;All Files (*.*)"
        )
        
        if not filepath:
            return
        
        try:
            self.log(f"📂 Cargando credenciales desde: {filepath}")
            
            # Inicializar Firebase (eliminar app anterior si existe)
            try:
                firebase_admin.delete_app(firebase_admin.get_app())
            except ValueError:
                pass
            
            cred = credentials.Certificate(filepath)
            firebase_admin.initialize_app(cred)
            self.db = firestore.client()
            
            self.log("✅ Credenciales cargadas exitosamente")
            self.lbl_creds_status.setText(f"✅ {Path(filepath).name}")
            
            # Cargar proyectos
            self. load_projects()
            
        except Exception as e:
            self.log(f"❌ Error cargando credenciales: {e}")
            QMessageBox.critical(self, "Error", f"Error cargando credenciales:\n{e}")
    
    def load_projects(self):
        """Carga lista de proyectos desde Firebase"""
        try:
            self.log("📂 Cargando proyectos...")
            
            projects_ref = self.db.collection('proyectos')
            docs = list(projects_ref.stream())
            
            self.proyectos = []
            self.combo_proyecto.clear()
            
            for doc in docs:
                data = doc.to_dict()
                proyecto_id = doc.id
                proyecto_nombre = data.get('nombre', f'Proyecto {proyecto_id}')
                
                self.proyectos.append({
                    'id': proyecto_id,
                    'nombre':  proyecto_nombre
                })
                
                self. combo_proyecto.addItem(f"{proyecto_nombre} (ID: {proyecto_id})", proyecto_id)
            
            self.log(f"✅ Cargados {len(self.proyectos)} proyectos")
            
            if self.proyectos:
                self.combo_proyecto.setEnabled(True)
                self.btn_analyze.setEnabled(True)
                self.btn_clean. setEnabled(True)
            else:
                self.log("⚠️ No se encontraron proyectos")
            
        except Exception as e: 
            self.log(f"❌ Error cargando proyectos: {e}")
    
    def start_cleanup(self, dry_run: bool = True):
        """Inicia proceso de limpieza"""
        proyecto_id = self.combo_proyecto.currentData()
        
        if not proyecto_id:
            QMessageBox.warning(self, "Aviso", "Selecciona un proyecto primero")
            return
        
        # Confirmación para modo REAL
        if not dry_run:
            reply = QMessageBox.question(
                self,
                "⚠️ CONFIRMAR ELIMINACIÓN",
                "¿Estás seguro de que quieres ELIMINAR los duplicados?\n\n"
                "Esta acción NO se puede deshacer.\n\n"
                "Recomendación: Ejecuta primero en modo Simulación.",
                QMessageBox.StandardButton.Yes | QMessageBox. StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox. StandardButton.No:
                return
        
        # Limpiar log
        self.log_text.clear()
        
        mode = "SIMULACIÓN" if dry_run else "ELIMINACIÓN REAL"
        self.log(f"🚀 Iniciando en modo:  {mode}")
        self.log(f"📁 Proyecto: {self.combo_proyecto.currentText()}")
        self.log("")
        
        # Configurar UI
        self.btn_analyze.setEnabled(False)
        self.btn_clean. setEnabled(False)
        self.btn_load_creds.setEnabled(False)
        self.combo_proyecto.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Iniciar worker
        self.worker = CleanupWorker(self.db, proyecto_id, dry_run)
        self.worker.progress. connect(self.on_progress)
        self.worker.log.connect(self.log)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.worker.start()
    
    def cancel_cleanup(self):
        """Cancela el proceso en curso"""
        if self.worker and self.worker. isRunning():
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
        self.btn_analyze.setEnabled(True)
        self.btn_clean.setEnabled(True)
        self.btn_load_creds.setEnabled(True)
        self.combo_proyecto.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        
        if deleted_count > 0:
            QMessageBox.information(
                self,
                "✅ Completado",
                f"Se eliminaron {deleted_count} transacciones duplicadas.\n\n"
                f"Se encontraron {duplicates_found} grupos de duplicados."
            )
    
    def on_error(self, error_msg: str):
        """Error durante el proceso"""
        self.log(f"❌ ERROR: {error_msg}")
        
        self.progress_bar.setVisible(False)
        self.btn_analyze.setEnabled(True)
        self.btn_clean. setEnabled(True)
        self.btn_load_creds. setEnabled(True)
        self.combo_proyecto.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        
        QMessageBox.critical(self, "Error", f"Error durante el proceso:\n{error_msg}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    dialog = DuplicateCleanerDialog()
    dialog.exec()
    
    sys.exit()