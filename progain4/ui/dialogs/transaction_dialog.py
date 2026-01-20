"""
Transaction Dialog for PROGRAIN 4.0/5.0 - Fixed Version

Dialog for creating and editing transactions with Firebase backend. 
Uses project-specific categories from subcollections. 
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Union

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLabel, QComboBox, QLineEdit, QTextEdit, QDateEdit, QPushButton,
    QMessageBox, QDoubleSpinBox, QCheckBox, QListWidget, QFileDialog
)
from PyQt6.QtCore import QDate, Qt
import logging
import os

logger = logging.getLogger(__name__)


class TransactionDialog(QDialog):
    """
    Dialog for creating or editing a transaction.
    
    Integrated with Firebase for loading and saving data.
    """
    
    def __init__(
        self,
        firebase_client,
        proyecto_id: Union[str, int],
        cuentas: List[Dict[str, Any]] = None,
        categorias:  List[Dict[str, Any]] = None,
        subcategorias: List[Dict[str, Any]] = None,
        parent=None,
        transaction_id: Optional[str] = None
    ):
        """
        Initialize transaction dialog.  
        
        ✅ CORREGIDO: Carga categorías y subcategorías correctamente usando queries. 
        """
        super().__init__(parent)
        
        self.firebase_client = firebase_client
        self.proyecto_id = proyecto_id
        self.transaction_id = transaction_id
        self.transaction_data = None
        
        # Attachment management
        self.attachment_files:  List[str] = []
        self.existing_attachments: List[str] = []
        
        logger.info(f"Inicializando diálogo de transacción para proyecto:  {self.proyecto_id}")
        
        # ===== 1️⃣ CARGAR CUENTAS =====
        if cuentas is None:
            try:
                self.cuentas = self.firebase_client.get_cuentas_by_proyecto(self.proyecto_id)
                logger.info(f"Cuentas cargadas: {len(self.cuentas)}")
            except Exception as e: 
                logger.error(f"Error cargando cuentas: {e}")
                self.cuentas = []
        else:
            self.cuentas = cuentas
        
        # ===== 2️⃣ CARGAR CATEGORÍAS Y SUBCATEGORÍAS DEL PROYECTO =====
        self.categorias = []
        self.subcategorias = []
        
        try:
            # ✅ OBTENER CATEGORÍAS ACTIVAS DEL PROYECTO
            categorias_proyecto = self.firebase_client.get_categorias_por_proyecto(self.proyecto_id)
            logger.info(f"📋 Categorías del proyecto obtenidas: {len(categorias_proyecto)}")
            
            if categorias_proyecto:
                # Ya vienen con nombres resueltos desde firebase_client
                self.categorias = categorias_proyecto
                
                for cat in self.categorias[: 5]: 
                    logger.debug(f"  - {cat. get('nombre')} (ID: {cat.get('id')})")
            
            # ✅ OBTENER SUBCATEGORÍAS ACTIVAS DEL PROYECTO  
            subcategorias_proyecto = self.firebase_client.get_subcategorias_por_proyecto(self.proyecto_id)
            logger.info(f"📋 Subcategorías del proyecto obtenidas: {len(subcategorias_proyecto)}")
            
            if subcategorias_proyecto:
                # Ya vienen con nombres resueltos desde firebase_client
                self.subcategorias = subcategorias_proyecto
                
                for sub in self.subcategorias[:5]:
                    logger. debug(f"  - {sub.get('nombre')} (cat:  {sub.get('categoria_id')})")
                    
        except Exception as e: 
            logger.error(f"❌ Error cargando categorías del proyecto: {e}")
        
        # ===== 3️⃣ FALLBACK:  Cargar catálogo global si no hay asignadas =====
        if not self. categorias: 
            logger.warning("⚠️  No hay categorías asignadas, cargando catálogo global como fallback")
            
            try:
                # ✅ Usar método que ya tiene el mapeo correcto
                self.categorias = self.firebase_client.get_categorias_maestras() or []
                self.subcategorias = self.firebase_client.get_subcategorias_maestras() or []
                
                logger.info(f"Fallback:  {len(self.categorias)} categorías, {len(self.subcategorias)} subcategorías")
                
            except Exception as e: 
                logger.error(f"❌ Error en fallback de catálogo global: {e}")
        
        # ===== 4️⃣ LOG RESUMEN =====
        logger.info("="*50)
        logger.info(f"✅ RESUMEN DE DATOS CARGADOS:")
        logger.info(f"   Cuentas:         {len(self.cuentas)}")
        logger.info(f"   Categorías:     {len(self.categorias)}")
        logger.info(f"   Subcategorías:  {len(self.subcategorias)}")
        logger.info("="*50)
        
        if self.categorias:
            logger.info("📂 Primeras categorías:")
            for cat in self.categorias[:3]: 
                logger.info(f"   • {cat.get('nombre', 'Sin nombre')} (ID: {cat.get('id')})")
        
        # ===== 5️⃣ VALIDACIÓN =====
        if not self.categorias:
            QMessageBox.warning(
                parent,
                "Sin Categorías",
                f"No se encontraron categorías para el proyecto {self.proyecto_id}.\n\n"
                "Puede asignar categorías al proyecto desde:\n"
                "Editar → Gestionar categorías del proyecto"
            )
        
        # Window setup
        self.setWindowTitle("Editar Transacción" if transaction_id else "Nueva Transacción")
        self.setModal(True)
        self.setMinimumWidth(600)
        
        # Initialize UI
        self._init_ui()
        
        # Load transaction data if editing
        if transaction_id: 
            self._load_transaction()
    
    def _init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()
        
        # Title
        title_text = "<h2>Editar Transacción</h2>" if self.transaction_id else "<h2>Nueva Transacción</h2>"
        title = QLabel(title_text)
        title.setAlignment(Qt.AlignmentFlag. AlignCenter)
        layout. addWidget(title)
        
        # Project info
        info_text = f"<small>Proyecto: {self.proyecto_id} | Categorías del proyecto: {len(self.categorias)}</small>"
        info_label = QLabel(info_text)
        info_label.setAlignment(Qt.AlignmentFlag. AlignCenter)
        info_label.setStyleSheet("color: gray;")
        layout.addWidget(info_label)
        
        # Main details group
        main_group = QGroupBox("Detalles Principales")
        main_layout = QFormLayout()
        
        # Transaction type
        self.tipo_combo = QComboBox()
        self.tipo_combo.addItem("Gasto", "gasto")
        self.tipo_combo.addItem("Ingreso", "ingreso")
        main_layout.addRow("Tipo:", self.tipo_combo)
        
        # Account
        self.cuenta_combo = QComboBox()
        if self.cuentas:
            for cuenta in self.cuentas:
                c_id = str(cuenta. get('id', ''))
                c_nombre = cuenta.get('nombre', 'Sin nombre')
                self.cuenta_combo.addItem(c_nombre, c_id)
        else:
            self.cuenta_combo.addItem("(Sin cuentas disponibles)", None)
        main_layout.addRow("Cuenta:", self.cuenta_combo)
        
        # Date
        self.fecha_edit = QDateEdit()
        self.fecha_edit.setCalendarPopup(True)
        self.fecha_edit.setDate(QDate.currentDate())
        self.fecha_edit.setDisplayFormat("yyyy-MM-dd")
        main_layout.addRow("Fecha:", self.fecha_edit)
        
        # Amount
        self.monto_spin = QDoubleSpinBox()
        self.monto_spin.setRange(0.01, 999999999.99)
        self.monto_spin.setDecimals(2)
        self.monto_spin.setPrefix("RD$ ")
        self.monto_spin.setValue(0.00)
        main_layout. addRow("Monto:", self.monto_spin)
        
        main_group.setLayout(main_layout)
        layout.addWidget(main_group)
        
        # Category group
        category_title = "Categorización"
        if len(self.categorias) < 10:  # Si son pocas, es probable que sean las del proyecto
            category_title = f"Categorización (Proyecto: {len(self.categorias)} categorías)"
        else:
            category_title = f"Categorización ({len(self.categorias)} categorías disponibles)"
        
        category_group = QGroupBox(category_title)
        category_layout = QFormLayout()
        
        # Category combo
        self.categoria_combo = QComboBox()
        
        if self.categorias:
            # Ordenar categorías alfabéticamente
            cats_sorted = sorted(self.categorias, key=lambda x: x.get('nombre', ''). upper())
            
            for categoria in cats_sorted:
                cat_id = str(categoria.get('id', ''))
                cat_nombre = categoria.get('nombre', 'Sin nombre')
                self.categoria_combo.addItem(cat_nombre, cat_id)
        else:
            self.categoria_combo.addItem("(Sin categorías disponibles)", None)
            self.categoria_combo.setEnabled(False)
        
        self.categoria_combo.currentIndexChanged.connect(self._on_category_changed)
        category_layout.addRow("Categoría:", self.categoria_combo)
        
        # Subcategory combo
        self.subcategoria_combo = QComboBox()
        self.subcategoria_combo.addItem("(Ninguna)", None)
        category_layout.addRow("Subcategoría:", self.subcategoria_combo)
        
        category_group.setLayout(category_layout)
        layout.addWidget(category_group)
        
        # Description group
        desc_group = QGroupBox("Descripción y Comentarios")
        desc_layout = QVBoxLayout()
        
        desc_layout.addWidget(QLabel("Descripción:"))
        self.descripcion_edit = QLineEdit()
        self.descripcion_edit.setPlaceholderText("Ej: Compra de materiales")
        desc_layout.addWidget(self.descripcion_edit)
        
        desc_layout. addWidget(QLabel("Comentario:"))
        self.comentario_edit = QTextEdit()
        self.comentario_edit. setPlaceholderText("Información adicional (opcional)")
        self.comentario_edit.setMaximumHeight(80)
        desc_layout.addWidget(self.comentario_edit)
        
        desc_group.setLayout(desc_layout)
        layout.addWidget(desc_group)
        
        # Attachments group
        attachments_group = QGroupBox("Adjuntos")
        attachments_layout = QVBoxLayout()
        
        self.attachments_list = QListWidget()
        self.attachments_list.setMaximumHeight(80)
        attachments_layout.addWidget(QLabel("Archivos adjuntos:"))
        attachments_layout.addWidget(self.attachments_list)
        
        # Attachment buttons
        attachment_buttons = QHBoxLayout()
        
        add_attachment_btn = QPushButton("📎 Agregar adjunto...")
        add_attachment_btn. clicked.connect(self._add_attachment)
        attachment_buttons.addWidget(add_attachment_btn)
        
        remove_attachment_btn = QPushButton("🗑️ Quitar seleccionado")
        remove_attachment_btn.clicked.connect(self._remove_attachment)
        attachment_buttons.addWidget(remove_attachment_btn)
        
        attachments_layout.addLayout(attachment_buttons)
        attachments_group.setLayout(attachments_layout)
        layout. addWidget(attachments_group)
        
        # State group
        state_group = QGroupBox("Estado")
        state_layout = QHBoxLayout()
        
        self.cleared_checkbox = QCheckBox("Transacción conciliada")
        state_layout.addWidget(self. cleared_checkbox)
        
        state_group.setLayout(state_layout)
        layout.addWidget(state_group)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("Guardar")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._save_transaction)
        buttons_layout.addWidget(save_btn)
        
        layout.addLayout(buttons_layout)
        self.setLayout(layout)
        
        # Trigger initial subcategory load
        if self.categoria_combo.count() > 0:
            self._on_category_changed(0)
    
    def _on_category_changed(self, index: int):
        """Update subcategories combo when category changes"""
        self.subcategoria_combo.clear()
        self.subcategoria_combo.addItem("(Ninguna)", None)
        
        if index < 0:
            return
        
        categoria_id = self.categoria_combo.currentData()
        if not categoria_id:
            return
        
        logger.debug(f"Category changed to ID: {categoria_id}")
        
        # Filter subcategories for this category
        subs_filtradas = [
            s for s in self.subcategorias 
            if str(s.get('categoria_id', '')) == str(categoria_id)
        ]
        
        logger.debug(f"Found {len(subs_filtradas)} subcategories for category {categoria_id}")
        
        if not subs_filtradas:
            return
        
        # Ordenar alfabéticamente
        subs_filtradas.sort(key=lambda x: x.get('nombre', '').upper())
        
        for subcat in subs_filtradas:
            sub_id = str(subcat. get('id', ''))
            sub_nombre = subcat.get('nombre', 'Sin nombre')
            self.subcategoria_combo.addItem(sub_nombre, sub_id)
    
    def _load_transaction(self):
        """Load transaction data for editing"""
        try:
            self.transaction_data = self.firebase_client.get_transaccion_by_id(
                self.proyecto_id,
                self.transaction_id
            )
            
            if not self.transaction_data:
                QMessageBox.warning(self, "Error", "No se pudo cargar la transacción.")
                return
            
            logger.info(f"Loading transaction {self.transaction_id}")
            
            # Type
            tipo = self.transaction_data.get('tipo', 'gasto')
            if isinstance(tipo, str):
                tipo = tipo.lower()
            index = self.tipo_combo.findData(tipo)
            if index >= 0:
                self.tipo_combo.setCurrentIndex(index)
            
            # Account
            cuenta_id = str(self.transaction_data.get('cuenta_id', ''))
            index = self.cuenta_combo.findData(cuenta_id)
            if index >= 0:
                self.cuenta_combo.setCurrentIndex(index)
            
            # Date
            fecha = self.transaction_data.get('fecha')
            if isinstance(fecha, datetime):
                qdate = QDate(fecha.year, fecha.month, fecha.day)
                self.fecha_edit.setDate(qdate)
            elif isinstance(fecha, str):
                try:
                    fecha_str = fecha[:10] if len(fecha) >= 10 else fecha
                    dt = datetime.strptime(fecha_str, "%Y-%m-%d")
                    self.fecha_edit.setDate(QDate(dt.year, dt.month, dt.day))
                except:
                    pass
            
            # Amount
            monto = self.transaction_data.get('monto', 0.0)
            self.monto_spin.setValue(float(monto))
            
            # Category
            categoria_id = str(self.transaction_data.get('categoria_id', ''))
            index = self.categoria_combo.findData(categoria_id)
            if index >= 0:
                self.categoria_combo.setCurrentIndex(index)
                self._on_category_changed(index)
            
            # Subcategory
            subcategoria_id = str(self.transaction_data.get('subcategoria_id', ''))
            if subcategoria_id and subcategoria_id != 'None':
                index = self.subcategoria_combo.findData(subcategoria_id)
                if index >= 0:
                    self.subcategoria_combo.setCurrentIndex(index)
            
            # Description
            self.descripcion_edit.setText(self.transaction_data.get('descripcion', ''))
            
            # Comments
            self.comentario_edit.setPlainText(self.transaction_data.get('comentario', ''))
            
            # Cleared
            self.cleared_checkbox.setChecked(self.transaction_data.get('cleared', False))
            
            # Attachments
            self. existing_attachments = self.transaction_data.get('adjuntos', [])
            self._update_attachments_list()
            
        except Exception as e:
            logger.error(f"Error loading transaction: {e}")
            QMessageBox.critical(self, "Error", f"Error al cargar la transacción:\n{str(e)}")
    
    def _add_attachment(self):
        """Add attachment files"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Seleccionar archivos adjuntos",
            "",
            "Todos los archivos (*);;PDF (*.pdf);;Imágenes (*.jpg *.jpeg *.png);;Excel (*.xlsx *.xls);;CSV (*.csv)"
        )
        
        if file_paths:
            for file_path in file_paths:
                if file_path not in self.attachment_files:
                    self. attachment_files.append(file_path)
            
            self._update_attachments_list()
            logger.info(f"Added {len(file_paths)} attachments")
    
    def _remove_attachment(self):
        """Remove selected attachment"""
        current_item = self.attachments_list. currentItem()
        if not current_item:
            return
        
        item_text = current_item.text()
        
        if "(nuevo)" in item_text:
            for file_path in self.attachment_files[:]:
                if os.path.basename(file_path) in item_text:
                    self.attachment_files.remove(file_path)
                    break
        elif "(existente)" in item_text:
            reply = QMessageBox.question(
                self,
                "Confirmar",
                "¿Está seguro de que desea eliminar este archivo adjunto?",
                QMessageBox.StandardButton.Yes | QMessageBox. StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton. Yes:
                row = self.attachments_list. row(current_item)
                if row < len(self.existing_attachments):
                    del self.existing_attachments[row]
        
        self._update_attachments_list()
    
    def _update_attachments_list(self):
        """Update attachments list display"""
        self. attachments_list.clear()
        
        for url in self.existing_attachments:
            try:
                from urllib.parse import unquote
                filename = os.path.basename(unquote(url). split('?')[0])
            except:
                filename = "Archivo adjunto"
            self.attachments_list.addItem(f"📎 {filename} (existente)")
        
        for file_path in self.attachment_files:
            filename = os.path.basename(file_path)
            try:
                file_size = os.path.getsize(file_path) / (1024 * 1024)
                self.attachments_list. addItem(f"📎 {filename} ({file_size:. 2f} MB) (nuevo)")
            except:
                self.attachments_list. addItem(f"📎 {filename} (nuevo)")
    
    def _save_transaction(self):
        """Save the transaction to Firebase"""
        # Validate fields
        if self.monto_spin.value() <= 0:
            QMessageBox.warning(self, "Campo requerido", "El monto debe ser mayor que cero.")
            self.monto_spin.setFocus()
            return
        
        if not self.cuentas or self.cuenta_combo.currentData() is None:
            QMessageBox. warning(self, "Campo requerido", "Debe seleccionar una cuenta.")
            self.cuenta_combo.setFocus()
            return
        
        if not self.categorias or self.categoria_combo.currentData() is None:
            QMessageBox.warning(self, "Campo requerido", "Debe seleccionar una categoría.")
            self.categoria_combo.setFocus()
            return
        
        try:
            # Get values
            tipo = self.tipo_combo.currentData()
            cuenta_id = self.cuenta_combo.currentData()
            categoria_id = self.categoria_combo. currentData()
            subcategoria_id = self.subcategoria_combo.currentData()
            
            # Get names for storage
            categoria_nombre = self.categoria_combo.currentText()
            subcategoria_nombre = self.subcategoria_combo.currentText() if subcategoria_id else ""
            
            # Date
            qdate = self.fecha_edit.date()
            fecha_str = qdate.toString("yyyy-MM-dd")
            
            monto = self.monto_spin.value()
            descripcion = self.descripcion_edit.text().strip()
            comentario = self.comentario_edit. toPlainText().strip()
            cleared = self.cleared_checkbox.isChecked()
            
            # Prepare transaction data WITH names included
            transaction_data = {
                'tipo': tipo. capitalize() if tipo else 'Gasto',
                'cuenta_id': cuenta_id,
                'categoria_id': categoria_id,
                'categoriaNombre': categoria_nombre,  # Include name in data
                'subcategoria_id': subcategoria_id,
                'subcategoriaNombre': subcategoria_nombre if subcategoria_nombre != "(Ninguna)" else "",  # Include name in data
                'fecha': fecha_str,
                'monto': monto,
                'descripcion': descripcion,
                'comentario': comentario,
                'cleared': cleared,
                'proyecto_id': self.proyecto_id
            }
            
            # Try to convert IDs to integers if they are numeric strings
            try:
                if cuenta_id and str(cuenta_id).isdigit():
                    transaction_data['cuenta_id'] = int(cuenta_id)
                if categoria_id and str(categoria_id).isdigit():
                    transaction_data['categoria_id'] = int(categoria_id)
                if subcategoria_id and str(subcategoria_id).isdigit():
                    transaction_data['subcategoria_id'] = int(subcategoria_id)
            except:
                pass  # Keep as strings if conversion fails
            
            # Save transaction
            if self.transaction_id:
                # Update existing transaction
                transaction_data['adjuntos'] = self.existing_attachments
                
                success = self.firebase_client.update_transaccion(
                    self.proyecto_id,
                    self.transaction_id,
                    transaction_data
                )
                
                if not success:
                    raise Exception("No se pudo actualizar la transacción")
                
                if self.attachment_files:
                    self._upload_attachments(self.transaction_id)
                
                logger.info(f"Transaction {self.transaction_id} updated successfully")
            else:
                # Create new transaction
                # Call create_transaccion WITHOUT the extra name parameters
                trans_id = self.firebase_client.create_transaccion(
                    proyecto_id=self.proyecto_id,
                    fecha=fecha_str,
                    tipo=tipo.capitalize() if tipo else 'Gasto',
                    cuenta_id=transaction_data['cuenta_id'],
                    categoria_id=transaction_data['categoria_id'],
                    monto=monto,
                    descripcion=descripcion,
                    comentario=comentario,
                    subcategoria_id=transaction_data. get('subcategoria_id'),
                    adjuntos=None
                    # Removed categoriaNombre and subcategoriaNombre from here
                )
                
                if not trans_id:
                    raise Exception("No se pudo crear la transacción")
                
                # After creating, update the transaction to include the names
                if trans_id:
                    # Update the created transaction to add the category names
                    update_data = {
                        'categoriaNombre': categoria_nombre,
                        'subcategoriaNombre': subcategoria_nombre if subcategoria_nombre != "(Ninguna)" else ""
                    }
                    
                    try:
                        self.firebase_client.update_transaccion(
                            self.proyecto_id,
                            trans_id,
                            update_data
                        )
                        logger.debug(f"Updated transaction {trans_id} with category names")
                    except Exception as e:
                        logger.warning(f"Could not update category names: {e}")
                        # No es crítico si falla, la transacción ya fue creada
                
                # Upload attachments if any
                if self.attachment_files:
                    self._upload_attachments(trans_id)
                
                logger.info(f"Transaction {trans_id} created successfully")
            
            # Success
            self.accept()
            
        except Exception as e:
            logger.error(f"Error saving transaction: {e}")
            QMessageBox.critical(self, "Error", f"Error al guardar la transacción:\n{str(e)}")
    
    def _upload_attachments(self, trans_id: str):
        """Upload attachment files to Firebase Storage"""
        if not self.attachment_files:
            return
        
        # Legacy URLs (para compatibilidad temporal)
        uploaded_urls = list(self.existing_attachments)
        
        # ✅ NUEVO: paths relativos (sin tokens, permanentes)
        uploaded_paths = []
        
        # Si ya existen adjuntos_paths en la transacción, cargarlos
        if hasattr(self, 'transaction_data') and self.transaction_data:
            uploaded_paths = list(self.transaction_data.get('adjuntos_paths', []))
        
        for file_path in self.attachment_files:
            try:
                # Check file size
                file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
                if file_size > 10:
                    QMessageBox.warning(
                        self,
                        "Archivo muy grande",
                        f"El archivo {os.path.basename(file_path)} es muy grande ({file_size:.2f} MB).\n"
                        "El límite es 10 MB."
                    )
                    continue
                
                # ✅ CORREGIDO: Capturar AMBOS valores (URL y path)
                result = self. firebase_client.upload_attachment(
                    proyecto_id=self.proyecto_id,
                    transaccion_id=trans_id,
                    file_path=file_path
                )
                
                if result:
                    url, storage_path = result  # ✅ Desempaquetar tupla
                    
                    # Guardar URL legacy (con dominio público pero sin necesidad de token)
                    uploaded_urls.append(url)
                    
                    # ✅ Guardar path relativo (para construir URLs públicas en el futuro)
                    uploaded_paths.append(storage_path)
                    
                    logger.info(f"Uploaded attachment: {file_path}")
                    logger.info(f"  URL: {url}")
                    logger.info(f"  Path: {storage_path}")
                    
            except Exception as e: 
                logger.error(f"Error uploading {file_path}: {e}")
        
        # ✅ Actualizar transacción con AMBOS campos
        if uploaded_urls != self.existing_attachments or uploaded_paths:
            try:
                update_data = {
                    'adjuntos':  uploaded_urls,           # Legacy (URLs públicas)
                    'adjuntos_paths': uploaded_paths     # ✅ NUEVO (paths para construir URLs)
                }
                
                self.firebase_client.update_transaccion(
                    self.proyecto_id,
                    trans_id,
                    update_data
                )
                
                logger.info(f"Updated transaction with {len(uploaded_urls)} attachments")
                logger.info(f"  adjuntos (legacy): {len(uploaded_urls)} URLs")
                logger.info(f"  adjuntos_paths (new): {len(uploaded_paths)} paths")
                
            except Exception as e:
                logger. error(f"Error updating transaction with attachments: {e}")