from typing import Dict, Any, List, Optional
from datetime import date, datetime
import traceback

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QFileDialog,
    QMessageBox,
    QGroupBox,
    QTextEdit,
    QHeaderView,
)
from PyQt6.QtCore import Qt
import pandas as pd
import os
import uuid
import hashlib
import json

HISTORY_FILE = "historial_importaciones.json"

class ImporterWindowFirebaseQt(QDialog):
    """
    Asistente de Importación V7 (Precision Fix):
    - Preserva tipos de datos nativos de Excel (fechas/montos) para evitar errores de conversión.
    - Lógica de Descripción mejorada (Prioridad a Detalle).
    """

    def __init__(self, parent, firebase_client, proyecto_id:  str, proyecto_nombre: str, moneda: str = "RD$"):
        super().__init__(parent)
        self.firebase_client = firebase_client
        self.proyecto_id = str(proyecto_id)
        self.proyecto_nombre = proyecto_nombre
        self.moneda = moneda or "RD$"

        self.setWindowTitle(f"Asistente de Importación - Proyecto: {self.proyecto_nombre}")
        self.resize(1200, 750)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMinMaxButtonsHint)

        self.df_data:  Optional[pd.DataFrame] = None
        self.categorias_map: Dict[str, str] = {}
        self.cuentas_map: Dict[str, str] = {}
        self. subcategorias_map: Dict[str, str] = {}
        
        self.imported_hashes = self._load_history()

        # ✅ NUEVO: Usar QSplitter para permitir redimensionar secciones
        from PyQt6.QtWidgets import QSplitter, QWidget
        
        main_layout = QVBoxLayout(self)
        
        # Crear splitter vertical (divide arriba/abajo)
        splitter = QSplitter(Qt. Orientation.Vertical)
        
        # ===== SECCIÓN SUPERIOR (Paso 1) =====
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        
        # --- Cargar archivo ---
        file_group = QGroupBox("Paso 1: Cargar Archivo de Transacciones")
        file_layout = QHBoxLayout(file_group)
        self.btn_load_file = QPushButton("Cargar Archivo (XLS, XLSX, CSV)")
        self.lbl_file = QLabel("Ningún archivo cargado.")
        file_layout.addWidget(self. btn_load_file)
        file_layout.addWidget(self.lbl_file)
        top_layout.addWidget(file_group)

        # --- Tabla ---
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Fecha", "Concepto (Banco)", "Descripción (Real)", "Monto", "Tipo"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior. SelectRows)
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode. Stretch)
        
        top_layout.addWidget(self.table)
        
        # Agregar al splitter
        splitter.addWidget(top_widget)
        
        # ===== SECCIÓN INFERIOR (Paso 2 + Log) =====
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        
        # --- Asignar datos ---
        assign_group = QGroupBox("Paso 2: Asignar Datos y Añadir al Proyecto")
        assign_layout = QHBoxLayout(assign_group)
        assign_layout.addWidget(QLabel("Cuenta Destino*:"))
        self.combo_cuenta = QComboBox()
        assign_layout.addWidget(self. combo_cuenta)

        assign_layout.addWidget(QLabel("Categoría*:"))
        self.combo_categoria = QComboBox()
        assign_layout.addWidget(self.combo_categoria)

        assign_layout.addWidget(QLabel("Subcategoría*:"))
        self.combo_subcategoria = QComboBox()
        assign_layout.addWidget(self.combo_subcategoria)

        self.btn_add = QPushButton("Añadir Transacciones Seleccionadas")
        self.btn_add.setEnabled(False)
        assign_layout.addWidget(self.btn_add)
        bottom_layout.addWidget(assign_group)

        # --- Log ---
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(80)  # ✅ Reducido mínimo para dar más espacio a tabla
        bottom_layout.addWidget(self.log_text)
        
        # Agregar al splitter
        splitter.addWidget(bottom_widget)
        
        # ✅ CONFIGURAR PROPORCIONES INICIALES (70% tabla, 30% paso2+log)
        splitter.setSizes([525, 225])  # Total = 750 (altura inicial)
        splitter.setStretchFactor(0, 7)  # Paso 1 tiene prioridad al expandir
        splitter.setStretchFactor(1, 3)
        
        # Agregar splitter al layout principal
        main_layout.addWidget(splitter)

        # --- Conexiones ---
        self.btn_load_file.clicked.connect(self.load_data_file)
        self.combo_categoria.currentIndexChanged.connect(self.update_subcategories)
        self.btn_add.clicked.connect(self.add_selected_to_project)

        self.cargar_datos_iniciales()

    # ----------------------------------------------------------- HISTORIAL



    
    def _load_history(self) -> set:
        """Carga historial de importaciones desde archivo JSON"""
        import logging
        logger = logging.getLogger(__name__)
        
        if not os.path.exists(HISTORY_FILE):
            logger.info(f"Historial no existe, creando nuevo:  {HISTORY_FILE}")
            return set()
        
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                hashes_list = json.load(f)
                hashes_set = set(hashes_list)
                logger.info(f"✅ Historial cargado:  {len(hashes_set)} hashes desde {HISTORY_FILE}")
                return hashes_set
        except Exception as e:
            logger. error(f"Error cargando historial: {e}")
            return set()
    
    def _save_history(self):
        """Guarda historial de importaciones en archivo JSON"""
        import logging
        logger = logging.getLogger(__name__)
        
        try: 
            with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(list(self.imported_hashes), f, indent=2)
            logger.info(f"💾 Historial guardado:  {len(self.imported_hashes)} hashes en {HISTORY_FILE}")
        except Exception as e:
            logger.error(f"⚠️ Error guardando historial: {e}")
            self.log(f"⚠️ Error guardando historial: {e}")

    def _generate_row_hash(self, row) -> str:
        """
        Genera hash único para detectar duplicados.  
        
        ✅ CORREGIDO:  Normaliza fechas/montos para máxima compatibilidad.  
        """
        import re
        
        # ✅ FECHA:  Normalizar SIEMPRE a string YYYY-MM-DD
        try:
            fecha_val = row. get('Fecha_dt')
            if pd.isna(fecha_val):
                d_str = "0000-00-00"
            elif isinstance(fecha_val, (pd.Timestamp, datetime, date)):
                d_str = pd.to_datetime(fecha_val).strftime('%Y-%m-%d')
            elif isinstance(fecha_val, str):
                d_str = pd.to_datetime(fecha_val).strftime('%Y-%m-%d')
            else:
                d_str = pd.to_datetime(fecha_val).strftime('%Y-%m-%d')
        except Exception as e:
            self.log(f"⚠️ Error parseando fecha para hash: {e}")
            d_str = "0000-00-00"
        
        # ✅ MONTO: Normalizar a float 2 decimales (CORREGIDO)
        try:
            monto_val = row. get('Monto', 0)
            if pd.isna(monto_val):
                m_str = "0.00"
            else:
                monto = abs(float(monto_val))
                m_str = f"{monto:.2f}"  # ✅ CRÍTICO: 'f' al inicio
        except Exception as e:
            self.log(f"⚠️ Error parseando monto para hash:  {e}")
            m_str = "0.00"
        
        # ✅ DETALLE: Normalizar texto
        try:
            detalle = str(row.get('Detalle', '')).strip().lower()
            detalle = re.sub(r'\s+', ' ', detalle)
            detalle = re.sub(r'[^\w\s-]', '', detalle)
        except Exception as e:
            self.log(f"⚠️ Error parseando detalle para hash: {e}")
            detalle = ""
        
        # ✅ TIPO: Normalizar
        try:
            tipo = str(row.get('Tipo', 'Gasto')).strip().capitalize()
        except:
            tipo = "Gasto"
        
        # Generar hash
        raw = f"{d_str}|{detalle}|{m_str}|{tipo}"
        hash_val = hashlib.md5(raw.encode('utf-8')).hexdigest()
        
        return hash_val

    # ----------------------------------------------------------- UTILIDADES

    def log(self, msg: str):
        self.log_text.append(f"[{pd.Timestamp.now().strftime('%H:%M:%S')}] {msg}")

    # ----------------------------------------------------------- CARGA DATOS

    def cargar_datos_iniciales(self):
        """
        Carga cuentas, categorías y subcategorías del proyecto.
        
        ✅ CORREGIDO:  Usa los mismos métodos que los diálogos de gestión. 
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # ===== 1️⃣ CARGAR CUENTAS =====
        try:
            cuentas = self.firebase_client.get_cuentas_by_proyecto(self.proyecto_id) or []
            logger.info(f"Importador: Cargadas {len(cuentas)} cuentas")
        except Exception as e:
            logger.error(f"Error cargando cuentas: {e}")
            cuentas = []
        
        self.cuentas_map = {
            c. get("nombre", str(c. get("id"))): str(c["id"]) 
            for c in cuentas if "id" in c
        }
        self.combo_cuenta.clear()
        self.combo_cuenta.addItems(sorted(self.cuentas_map.keys(), key=lambda x: x.upper()))
        
        # ===== 2️⃣ CARGAR CATEGORÍAS DEL PROYECTO =====
        try:
            # ✅ USAR EL MISMO MÉTODO QUE USA GestionCategoriasProyectoDialog
            categorias_proyecto = self.firebase_client. get_categorias_por_proyecto(self.proyecto_id) or []
            logger.info(f"Importador: Categorías del proyecto obtenidas:  {len(categorias_proyecto)}")
            
            if categorias_proyecto:
                # ✅ Ya vienen con nombres resueltos desde firebase_client
                self.categorias_map = {
                    cat.get("nombre", f"Cat {cat.get('id')}"): str(cat["id"])
                    for cat in categorias_proyecto
                    if "id" in cat and cat. get("nombre")
                }
                
                logger.info(f"Importador: {len(self.categorias_map)} categorías disponibles")
                for nombre in list(self.categorias_map. keys())[:5]: 
                    logger.debug(f"  - {nombre}")
            else:
                logger.warning("⚠️ No hay categorías asignadas al proyecto")
                self.categorias_map = {}
        
        except Exception as e:
            logger.error(f"Error cargando categorías:  {e}")
            self.categorias_map = {}
        
        self.combo_categoria.clear()
        if self.categorias_map:
            self.combo_categoria.addItems(sorted(self.categorias_map.keys(), key=lambda x: x.upper()))
        else:
            self.combo_categoria.addItem("(Sin categorías configuradas)")
        
        # ===== 3️⃣ CARGAR SUBCATEGORÍAS (se actualizarán al cambiar categoría) =====
        self.update_subcategories()
        
        self.log("✅ Sistema listo.")

    def update_subcategories(self):
        """
        Actualiza subcategorías según la categoría seleccionada.
        
        ✅ CORREGIDO: Usa subcategorías del proyecto, no todas las maestras.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        cat_name = self.combo_categoria.currentText()
        cat_id = self.categorias_map.get(cat_name)
        
        if not cat_id:
            self.subcategorias_map = {}
            self.combo_subcategoria.clear()
            self.combo_subcategoria.addItem("(Selecciona categoría primero)")
            return
        
        try:
            # ✅ OBTENER SUBCATEGORÍAS DEL PROYECTO
            subcategorias_proyecto = self.firebase_client. get_subcategorias_por_proyecto(self.proyecto_id) or []
            logger.info(f"Importador: Subcategorías del proyecto obtenidas:  {len(subcategorias_proyecto)}")
            
            # ✅ FILTRAR POR CATEGORÍA ACTUAL
            self.subcategorias_map = {
                sub. get("nombre", f"Sub {sub.get('id')}"): str(sub["id"])
                for sub in subcategorias_proyecto
                if str(sub. get("categoria_id")) == str(cat_id) and "id" in sub and sub.get("nombre")
            }
            
            logger.info(f"Importador: {len(self.subcategorias_map)} subcategorías para categoría {cat_name}")
            
        except Exception as e:
            logger.error(f"Error cargando subcategorías: {e}")
            self.subcategorias_map = {}
        
        self.combo_subcategoria. clear()
        if self.subcategorias_map:
            self.combo_subcategoria.addItems(sorted(self.subcategorias_map.keys(), key=lambda x: x.upper()))
        else:
            self.combo_subcategoria.addItem(f"(Sin subcategorías en {cat_name})")

    # ----------------------------------------------------------- PROCESAMIENTO ARCHIVO

    def load_data_file(self):
        """
        Carga archivo de transacciones y lo procesa.  
        
        ✅ CORREGIDO: Logging detallado para debug de filtrado por historial.  
        """
        filepath, _ = QFileDialog.getOpenFileName(
            self, 
            "Abrir", 
            "", 
            "Archivos (*. xls *.xlsx *.csv *.txt);;Todos (*.*)"
        )
        if not filepath: 
            return

        try: 
            filename = os.path.basename(filepath)
            self.log(f"📂 Leyendo: {filename}")
            self.lbl_file.setText("Procesando...")
            
            # 1. Leer Raw (Preservando tipos de Excel si es posible)
            df_raw = self._read_file_flexible(filepath)
            if df_raw is None or df_raw.empty:
                raise ValueError("Archivo vacío/ilegible")

            # 2. Extraer tabla real (SIN convertir todo a string prematuramente)
            df_clean = self._extract_table_from_raw(df_raw)
            
            # 3. Mapeo
            df_mapped = self._normalize_columns(df_clean)

            # 4. Procesar Tipos (Fechas y Montos)
            df_proc = self._process_data_types(df_mapped)

            # 5. Filtrar por historial
            df_proc['row_hash'] = df_proc.apply(self._generate_row_hash, axis=1)
            total = len(df_proc)
            
            # ✅ NUEVO: Log detallado para debugging
            self.log(f"🔍 Total de transacciones procesadas: {total}")
            self.log(f"🔍 Hashes en historial:  {len(self.imported_hashes)}")
            
            # ✅ NUEVO:   Mostrar muestra de hashes del archivo
            if total > 0:
                muestra_archivo = df_proc['row_hash'].head(3).tolist()
                self.log(f"🔍 Muestra hashes del archivo: {[h[: 12] + '...' for h in muestra_archivo]}")
            
            # ✅ NUEVO:   Mostrar muestra de hashes del historial
            if len(self.imported_hashes) > 0:
                muestra_historial = list(self.imported_hashes)[:3]
                self.log(f"🔍 Muestra hashes del historial:  {[h[:12] + '...' for h in muestra_historial]}")
            
            # Filtrar duplicados
            df_final = df_proc[~df_proc['row_hash'].isin(self.imported_hashes)].copy()
            
            ocultos = total - len(df_final)
            
            # ✅ NUEVO:   Verificar coincidencias
            if len(self.imported_hashes) > 0 and total > 0:
                coincidencias = df_proc['row_hash'].isin(self.imported_hashes).sum()
                self.log(f"🔍 Coincidencias encontradas: {coincidencias}/{total}")
            
            if ocultos > 0:
                self.log(f"ℹ️ Ocultadas {ocultos} duplicadas del historial.")
            else:
                if len(self.imported_hashes) > 0:
                    self.log(f"⚠️ No se encontraron duplicados (los hashes pueden no coincidir)")

            if df_final.empty:
                self.log("✅ Todo el archivo ya fue importado antes.")
                self.df_data = pd.DataFrame()
                self.btn_add.setEnabled(False)
            else:
                self.df_data = df_final
                self.log(f"✅ Encontradas {len(self.df_data)} transacciones nuevas.")
                self.btn_add.setEnabled(True)

            self._populate_table_widget()
            self.lbl_file.setText(f"✅ {filename}")

        except Exception as e:
            self.log(f"❌ Error: {e}")
            import traceback
            self.log(f"🔍 Traceback: {traceback.format_exc()}")
            QMessageBox.critical(self, "Error", f"{e}")
            self.lbl_file.setText("❌ Error al cargar")

    def _read_file_flexible(self, filepath):
        # Detección de binario XLS
        try:
            with open(filepath, 'rb') as f: sig = f.read(8)
            is_bin = sig == b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'
        except: is_bin = False

        if is_bin:
            self.log("...Excel Binario (.xls)")
            # engine='xlrd' devuelve fechas como datetime directamente (muy bueno)
            try: return pd.read_excel(filepath, header=None, engine='xlrd')
            except ImportError: raise ImportError("Instalar xlrd: pip install xlrd")
            except: pass

        if filepath.lower().endswith('.xlsx'):
            return pd.read_excel(filepath, header=None)

        # CSV Fallback
        for enc in ['utf-16', 'utf-8', 'latin-1', 'cp1252']:
            try:
                # Prueba rápida
                pd.read_csv(filepath, sep=',', encoding=enc, nrows=5)
                return pd.read_csv(filepath, sep=',', encoding=enc, header=None, on_bad_lines='skip')
            except: pass
            try:
                pd.read_csv(filepath, sep='\t', encoding=enc, nrows=5)
                return pd.read_csv(filepath, sep='\t', encoding=enc, header=None, on_bad_lines='skip')
            except: pass
        
        return None

    def _extract_table_from_raw(self, df):
        # Buscamos encabezados convirtiendo a string SOLO para buscar,
        # pero devolvemos el DataFrame original preservando tipos (fechas/floats)
        
        # Copia para búsqueda (todo string, minusculas)
        df_search = df.astype(str).apply(lambda x: x.str.lower())
        
        idx = -1
        # Buscamos fila con fecha y dinero
        for i, row in df_search.head(50).iterrows():
            txt = " ".join(row.values)
            if 'desde:' in txt or 'saldo inicial' in txt: continue
            if any(k in txt for k in ['fecha','date']) and any(k in txt for k in ['débito','debito','crédito','monto']):
                idx = i
                break
        
        if idx == -1: idx = 0
        else: self.log(f"📍 Encabezados en fila {idx}")

        # Usamos el DataFrame ORIGINAL (df) para no perder los tipos de dato (fechas xls)
        new_header = df.iloc[idx].astype(str).str.replace('\x00','').str.strip()
        df_out = df.iloc[idx+1:].copy()
        df_out.columns = new_header
        
        # Limpieza básica de columnas vacías
        df_out = df_out.loc[:, df_out.columns.notna()]
        df_out = df_out.loc[:, ~df_out.columns.str.contains('^Unnamed', case=False)]
        return df_out

    def _normalize_columns(self, df):
        col_map = {}
        cols_lower = {str(c).lower().strip(): c for c in df.columns}
        
        def find(tags, exclude=[]):
            for t in tags:
                for low, orig in cols_lower.items():
                    if orig in exclude: continue
                    if t == low or (len(low)>3 and t in low): return orig
            return None

        c_date = find(['fecha', 'date'])
        if c_date: col_map[c_date] = 'Fecha'

        c_deb = find(['débito', 'debito', 'retiro'])
        if c_deb: col_map[c_deb] = 'Débito'

        c_cred = find(['crédito', 'credito', 'depósito', 'deposito'])
        if c_cred: col_map[c_cred] = 'Crédito'

        # Primero buscamos Concepto (Suele ser corto)
        c_conc = find(['concepto', 'transaccion', 'tipo'])
        if c_conc: col_map[c_conc] = 'Concepto'

        # Luego buscamos Descripción/Detalle (Suele ser largo)
        # Excluimos la columna que ya se usó para Concepto
        used = list(col_map.keys())
        c_desc = find(['descripción', 'descripcion', 'detalle', 'referencia'], exclude=used)
        if c_desc: col_map[c_desc] = 'Detalle'

        if 'Fecha' not in col_map.values():
            raise ValueError("No se encontró columna Fecha.")

        self.log(f"🔗 Columnas: {col_map}")
        return df.rename(columns=col_map).loc[:, ~df.columns.duplicated()]

    def _process_data_types(self, df):
        # Limpieza Numérica
        def clean_num(val):
            if isinstance(val, (int, float)): return float(val)
            s = str(val).replace('"','').replace("'",'').replace(',','').strip()
            try: return float(s)
            except: return 0.0

        if 'Débito' in df.columns and 'Crédito' in df.columns:
            df['Débito'] = df['Débito'].apply(clean_num)
            df['Crédito'] = df['Crédito'].apply(clean_num)
            df['Monto'] = df.apply(lambda r: r['Débito'] if r['Débito']>0 else r['Crédito'], axis=1)
            df['Tipo'] = df.apply(lambda r: "Gasto" if r['Débito']>0 else "Ingreso", axis=1)
        else:
            m_col = 'Monto_Raw' if 'Monto_Raw' in df.columns else df.columns[-1]
            df['Monto'] = df[m_col].apply(clean_num).abs()
            df['Tipo'] = "Gasto"

        # Limpieza Fechas (CRÍTICO: Manejar datetime nativo vs string)
        def parse_dt(val):
            if pd.isna(val): return pd.NaT
            # Si ya es fecha (gracias a xlrd/pandas), devolverla
            if isinstance(val, (pd.Timestamp, date, datetime)):
                return pd.to_datetime(val)
            
            # Si es número serial (excel raw)
            try:
                f = float(val)
                if f > 30000: return pd.to_datetime(f, unit='D', origin='1899-12-30')
            except: pass

            # Si es texto
            s = str(val).strip()
            try: return pd.to_datetime(s, dayfirst=True) # Intento dia/mes/año
            except: pass
            try: return pd.to_datetime(s) # Intento estandar
            except: return pd.NaT

        df['Fecha_dt'] = df['Fecha'].apply(parse_dt)
        df = df.dropna(subset=['Fecha_dt'])
        df = df[df['Monto'] > 0]

        # Textos
        if 'Concepto' not in df.columns: df['Concepto'] = ""
        if 'Detalle' not in df.columns: df['Detalle'] = ""
        
        df['Concepto'] = df['Concepto'].fillna("").astype(str).str.strip()
        df['Detalle'] = df['Detalle'].fillna("").astype(str).str.strip()
        
        # Si Detalle está vacío, usar Concepto
        df['Detalle'] = df.apply(lambda x: x['Concepto'] if x['Detalle'] == '' else x['Detalle'], axis=1)

        return df

    def _populate_table_widget(self):
        """Poblar tabla con datos del DataFrame"""
        self.table.setRowCount(0)
        self.table.setSortingEnabled(False)
        
        for df_idx, row in self.df_data.iterrows():
            table_row = self.table.rowCount()
            self.table. insertRow(table_row)
            
            # ✅ COLUMNA 0: Fecha (GUARDAR HASH EN UserRole)
            fecha_item = QTableWidgetItem(row["Fecha_dt"]. strftime("%Y-%m-%d"))
            fecha_item.setData(Qt. ItemDataRole.UserRole, row['row_hash'])  # ✅ CRÍTICO
            self.table.setItem(table_row, 0, fecha_item)
            
            # Columna 1: Concepto
            self.table.setItem(table_row, 1, QTableWidgetItem(row["Concepto"]))
            
            # Columna 2:  Detalle
            self.table.setItem(table_row, 2, QTableWidgetItem(row["Detalle"]))
            
            # Columna 3: Monto
            m = QTableWidgetItem(f"{self.moneda} {row['Monto']: ,.2f}")
            m.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(table_row, 3, m)
            
            # Columna 4: Tipo
            t = QTableWidgetItem(row["Tipo"])
            t.setForeground(Qt.GlobalColor. darkRed if row["Tipo"]=="Gasto" else Qt.GlobalColor.darkGreen)
            self.table.setItem(table_row, 4, t)
        
        self.table.setSortingEnabled(True)

    def add_selected_to_project(self):
        """
        Añade transacciones seleccionadas al proyecto. 
        
        ✅ CORREGIDO: Usa hash de la celda en lugar de índice del DataFrame. 
        ✅ Detecta y advierte sobre duplicados en la selección.
        """
        if self.df_data is None or self.df_data.empty:
            QMessageBox.warning(self, "Sin datos", "No hay transacciones cargadas.")
            return
        
        # ✅ OBTENER FILAS ÚNICAS SELECCIONADAS
        selected_rows = sorted(list(set([i. row() for i in self.table.selectedIndexes()])))
        
        if not selected_rows:
            QMessageBox. warning(self, "Aviso", "Selecciona al menos una fila para importar.")
            return

        # ✅ EXTRAER HASHES DE LAS FILAS SELECCIONADAS (desde la tabla, no del DataFrame)
        selected_hashes = []
        for row_idx in selected_rows:
            fecha_item = self.table.item(row_idx, 0)  # Columna Fecha
            if fecha_item: 
                h = fecha_item.data(Qt.ItemDataRole.UserRole)
                if h:
                    selected_hashes.append(h)
        
        if not selected_hashes:
            QMessageBox.warning(self, "Error", "No se pudieron obtener los hashes de las filas seleccionadas.")
            return
        
        # ✅ NUEVO:  Detectar duplicados en selección
        unique_hashes = list(set(selected_hashes))
        duplicates_count = len(selected_hashes) - len(unique_hashes)
        
        self.log(f"🔍 Filas seleccionadas: {len(selected_hashes)}")
        self.log(f"🔍 Hashes únicos: {len(unique_hashes)}")
        
        if duplicates_count > 0:
            self.log(f"⚠️ ADVERTENCIA:  Hay {duplicates_count} transacciones duplicadas en tu selección")
            self.log(f"⚠️ Esto es normal si el banco registra la misma comisión múltiples veces")
            self.log(f"⚠️ Se eliminarán TODAS las filas con el mismo hash del DataFrame")
            self.log(f"")
        
        # Usar hashes únicos para procesar
        selected_hashes = unique_hashes

        # Obtener valores de los combos
        c_nom = self.combo_cuenta.currentText()
        c_id = self.cuentas_map. get(c_nom)
        cat_nom = self.combo_categoria.currentText()
        cat_id = self.categorias_map.get(cat_nom)
        sub_nom = self.combo_subcategoria.currentText()
        sub_id = self.subcategorias_map.get(sub_nom)

        # ✅ LOG de validación
        self.log(f"🔍 VALIDACIÓN DE DATOS:")
        self.log(f"   📁 Cuenta seleccionada: '{c_nom}'")
        self.log(f"   🔑 ID de cuenta: '{c_id}' (tipo: {type(c_id).__name__ if c_id else 'None'})")
        self.log(f"   📋 Categoría: '{cat_nom}' → ID: '{cat_id}'")
        self.log(f"   📌 Subcategoría: '{sub_nom}' → ID: '{sub_id}'")
        self.log(f"")

        # Validar datos obligatorios
        if not all([c_id, cat_id, sub_id]):
            error_msg = "Faltan datos obligatorios:\n"
            if not c_id:
                error_msg += "  • Cuenta no seleccionada o inválida\n"
            if not cat_id:
                error_msg += "  • Categoría no seleccionada o inválida\n"
            if not sub_id:
                error_msg += "  • Subcategoría no seleccionada o inválida\n"
            
            self.log(f"❌ ERROR DE VALIDACIÓN:")
            self.log(error_msg)
            QMessageBox.warning(self, "Error", error_msg)
            return

        # Contadores
        count = 0
        err = 0
        hashes_remove = []

        self.log(f"🔄 Procesando {len(selected_hashes)} transacciones únicas...")
        self.log(f"📍 Destino → Cuenta: {c_nom} (ID: {c_id}) | Categoría: {cat_nom} | Subcategoría: {sub_nom}")
        self.log(f"")

        # ✅ PROCESAR USANDO HASHES (no índices)
        for i, h in enumerate(selected_hashes, 1):
            try:
                # ✅ BUSCAR FILA EN DATAFRAME POR HASH
                matching_rows = self.df_data[self.df_data['row_hash'] == h]
                
                if matching_rows.empty:
                    self.log(f"⚠️ Hash {h[: 12]}... no encontrado en DataFrame (ya eliminado? )")
                    continue
                
                row = matching_rows.iloc[0]
                
                self.log(f"🔑 Transacción {i}/{len(selected_hashes)}: Hash = {h[:12]}...")
                
                # Construir descripción
                desc = row['Detalle']
                if row['Concepto'] and row['Concepto'].lower() not in desc.lower():
                    desc = f"{row['Concepto']} - {desc}"

                # Normalizar cuenta_id
                try:
                    cuenta_id_int = int(c_id)
                except (ValueError, TypeError):
                    cuenta_id_int = str(c_id)

                # Preparar datos
                data = {
                    "id": str(uuid.uuid4()),
                    "proyecto_id": self.proyecto_id,
                    "cuenta_id": cuenta_id_int,
                    "cuentaNombre": c_nom,
                    "categoria_id": str(cat_id),
                    "categoriaNombre": cat_nom,
                    "subcategoria_id": str(sub_id),
                    "subcategoriaNombre": sub_nom,
                    "tipo":  row["Tipo"],
                    "descripcion": desc[: 200],
                    "comentario": "Importado Automáticamente",
                    "monto": float(row["Monto"]),
                    "fecha": row["Fecha_dt"]. strftime("%Y-%m-%d")
                }
                
                self.log(f"   📤 {data['fecha']} | {row['Tipo']} | Cuenta ID: {data['cuenta_id']} | RD$ {data['monto']: ,.2f}")
                self.log(f"      {desc[: 50]}...")
                
                # Guardar en Firebase
                if self.firebase_client. agregar_transaccion_a_proyecto(self.proyecto_id, data):
                    count += 1
                    hashes_remove.append(h)
                    self.imported_hashes.add(h)
                    self.log(f"   ✅ Guardada exitosamente")
                else:
                    err += 1
                    self.log(f"   ❌ Error: Firebase retornó False")
                    
            except Exception as e:
                err += 1
                self. log(f"   ❌ Error procesando hash {h[: 12]}.. .: {e}")
                import traceback
                self.log(f"   🔍 Traceback: {traceback.format_exc()}")

        # Resumen y actualización
        self.log(f"")
        self.log(f"📊 RESUMEN DEL PROCESO:")
        self.log(f"   ✅ Importadas exitosas: {count}")
        self.log(f"   ❌ Errores:  {err}")
        self.log(f"   🔑 Hashes únicos para eliminar: {len(hashes_remove)}")
        self.log(f"")

        if count > 0:
            # Guardar historial
            try:
                self._save_history()
                self.log(f"💾 Historial guardado ({len(self.imported_hashes)} hashes totales)")
            except Exception as e:
                self.log(f"⚠️ Error guardando historial: {e}")
            
            # Filtrar DataFrame
            df_antes = len(self.df_data)
            self.log(f"📊 Filas en tabla ANTES de filtrar: {df_antes}")
            
            # ✅ Mostrar muestra de hashes a eliminar
            if len(hashes_remove) > 0:
                muestra = hashes_remove[:3] if len(hashes_remove) > 3 else hashes_remove
                self.log(f"🔍 Hashes a eliminar (muestra): {[h[:12] + '...' for h in muestra]}")
            
            # ✅ Eliminar por hash (incluye duplicados en DataFrame)
            self.df_data = self.df_data[~self.df_data['row_hash'].isin(hashes_remove)]
            df_despues = len(self. df_data)
            eliminadas = df_antes - df_despues
            
            self.log(f"📊 Filas en tabla DESPUÉS de filtrar: {df_despues}")
            self.log(f"🗑️ Filas eliminadas: {eliminadas}")
            
            # ✅ Explicación mejorada de la diferencia
            if eliminadas > count:
                extra = eliminadas - count
                self.log(f"ℹ️ Se eliminaron {extra} filas adicionales (duplicados con mismo hash en el DataFrame)")
            elif eliminadas < count:
                self.log(f"⚠️ ALERTA: Se esperaba eliminar más filas.  Posible inconsistencia.")
            
            # Repoblar tabla
            self._populate_table_widget()
            self.log(f"🔄 Tabla repoblada correctamente")
            self.log(f"")
            
            # Mensaje final
            msg = f"✅ Importación Completada\n\n"
            msg += f"Transacciones importadas: {count}\n"
            msg += f"Cuenta destino: {c_nom} (ID: {c_id})\n"
            msg += f"Eliminadas de la tabla: {eliminadas}\n"
            
            if eliminadas > count:
                msg += f"\nℹ️ Nota: Se eliminaron {eliminadas - count} duplicados adicionales\n"
                msg += f"(misma fecha/monto/descripción que aparecían múltiples veces)"
            
            if err > 0:
                msg += f"\n⚠️ Errores: {err}"
            
            QMessageBox.information(self, "Listo", msg)
            self.log(f"🎉 Proceso de importación completado")
            
        else:
            msg = f"❌ No se pudo importar ninguna transacción.\n\n"
            if err > 0:
                msg += f"Errores encontrados: {err}\n\n"
            msg += f"Revisa el log para más detalles."
            
            QMessageBox.warning(self, "Error", msg)
            self.log(f"❌ Importación fallida:  0 transacciones guardadas")