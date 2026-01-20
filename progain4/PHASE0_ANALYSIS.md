# FASE 0 - ANÁLISIS DEL ESTADO ACTUAL

## 📋 Resumen Ejecutivo

La aplicación PROGRAIN 4.0/5.0 ha sido estructurada como una aplicación PyQt6 moderna con backend 100% Firebase (Firestore + Storage). La arquitectura sigue el patrón de separación clara entre servicios (backend), UI (frontend), y lógica de aplicación.

**Estado**: ✅ Estructura base creada y funcional

## 🏗️ Arquitectura General

### 1. Punto de Entrada: `main_ynab.py`

**Clase Principal**: `PROGRAIN4App`

**Flujo de Inicialización**:
```
1. Crear QApplication con High DPI pre-configurado ✅
2. initialize_firebase() → Conectar con Firebase
3. select_project() → Seleccionar/crear proyecto
4. Crear MainWindow4 con proyecto seleccionado
5. Iniciar event loop (app.exec())
```

**Detalles de Implementación**:
- High DPI: Líneas 46-47, `AA_EnableHighDpiScaling` + `AA_UseHighDpiPixmaps` (NO MODIFICAR)
- Metadata: Nombre="PROGRAIN 4.0", Versión="4.0.0", Org="PROGRAIN"
- Logging configurado a nivel INFO

### 2. Servicio Firebase: `services/firebase_client.py`

**Propósito**: Único punto de acceso a Firebase (Firestore + Storage)

#### Inicialización

```python
def initialize(credentials_path: str, storage_bucket: str) -> bool
```

- Verifica que `credentials_path` existe
- Maneja re-inicialización sin error
- Crea `firestore.client()` y `storage.bucket()`
- Retorna `True/False` según éxito

#### Métodos Implementados

**Proyectos**:
```python
get_proyectos() -> List[Dict]
    # Retorna: [{'id': str, 'nombre': str, 'descripcion': str, ...}]
    # Colección: 'proyectos'

create_proyecto(nombre: str, descripcion: str) -> Optional[str]
    # Retorna: proyecto_id o None
```

**Cuentas**:
```python
get_cuentas_by_proyecto(proyecto_id: str) -> List[Dict]
    # Ruta: proyectos/{proyecto_id}/cuentas/{cuenta_id}
    # Retorna: [{'id', 'nombre', 'tipo', 'is_principal', 'saldo_inicial', 'moneda'}]
```

**Transacciones**:
```python
get_transacciones_by_proyecto(
    proyecto_id: str,
    cuenta_id: Optional[str] = None,  # Filtro por cuenta
    periodo: Optional[str] = None,    # No implementado aún
    texto: Optional[str] = None       # Filtro in-memory
) -> List[Dict]
    # Ruta: proyectos/{proyecto_id}/transacciones/{transaccion_id}
    # Orden: fecha descendente
    # Retorna: [{'id', 'fecha', 'tipo', 'cuenta_id', 'categoria_id', 
    #            'monto', 'descripcion', 'comentario', ...}]
```

**Categorías**:
```python
get_categorias_by_proyecto(proyecto_id: str) -> List[Dict]
    # Ruta: proyectos/{proyecto_id}/categorias/{categoria_id}
```

#### Pendiente en FirebaseClient
- ❌ CRUD completo (Create, Update, Delete) para cuentas
- ❌ CRUD completo para transacciones
- ❌ CRUD completo para categorías
- ❌ Soporte para adjuntos en Storage
- ❌ Subcategorías
- ❌ Filtro de transacciones por periodo

### 3. Ventana Principal: `ui/main_window4.py`

**Clase**: `MainWindow4`

**Constructor**:
```python
def __init__(
    self,
    firebase_client: FirebaseClient,
    proyecto_id: str,
    proyecto_nombre: str
)
```

#### Layout de la Ventana

```
┌─────────────────────────────────────────────────────────────┐
│ [Toolbar]                                                   │
│ Cuenta: [Todas las cuentas ▼] | 🔄 Actualizar | ➕ Nueva  │
├─────────────┬───────────────────────────────────────────────┤
│  SIDEBAR    │          TABLA TRANSACCIONES                  │
│             │                                                │
│ Cuentas     │ Fecha | Tipo | Descripción | Cat. | Cta | $  │
│ ─────────   │ ───────────────────────────────────────────── │
│ 📊 Todas... │ 2024-01-15 | Ingreso | Salario | ... | ...   │
│ 💵 Efectivo │ 2024-01-14 | Gasto | Compra | ... | ...      │
│ 🏦 Banco    │ ...                                           │
│ 💳 Tarjeta  │                                                │
│             │                                                │
└─────────────┴───────────────────────────────────────────────┘
│ [Status Bar: "Mostrando X transacciones"]                  │
└─────────────────────────────────────────────────────────────┘
```

#### Flujo de Datos

**Carga Inicial** (`_load_initial_data()`):
```python
1. cuentas = firebase_client.get_cuentas_by_proyecto(proyecto_id)
2. categorias = firebase_client.get_categorias_by_proyecto(proyecto_id)
3. _populate_accounts() → Llena sidebar y combo
4. transactions_widget.set_cuentas_map(cuentas)
5. transactions_widget.set_categorias_map(categorias)
6. _refresh_transactions() → Carga transacciones
```

**Población de Cuentas** (`_populate_accounts()`):
```python
# Sidebar (QListWidget)
1. Agregar item: "📊 Todas las cuentas" (data=None)
2. Para cada cuenta:
   - Obtener icono según tipo (💵/🏦/💳/📈/💰)
   - Crear item: "{icono} {nombre}"
   - Guardar cuenta_id en UserRole

# Combo (QComboBox)
1. Agregar: "Todas las cuentas" (data=None)
2. Para cada cuenta:
   - Agregar: "{nombre}" (data=cuenta_id)
```

**Sincronización Sidebar ↔ Combo**:
- `_on_account_list_clicked(item)`: Sidebar → Combo
- `_on_account_combo_changed(index)`: Combo → Sidebar
- Ambos actualizan `self.current_cuenta_id`
- Ambos llaman `_refresh_transactions()`

**Recarga de Transacciones** (`_refresh_transactions()`):
```python
1. transactions = firebase_client.get_transacciones_by_proyecto(
       proyecto_id,
       cuenta_id=self.current_cuenta_id  # None = todas
   )
2. transactions_widget.load_transactions(transactions)
3. Actualizar status bar con contador
```

#### Estado de Cuenta Seleccionada

- **Variable**: `self.current_cuenta_id: Optional[str]`
- **Valores**:
  - `None`: "Todas las cuentas" (sin filtro)
  - `"cuenta_id_123"`: Cuenta específica
- **Uso**: Se pasa como parámetro `cuenta_id` a `get_transacciones_by_proyecto()`

### 4. Widget de Transacciones: `ui/widgets/transactions_widget.py`

**Clase**: `TransactionsWidget`

#### Estructura de la Tabla

| Columna | Tipo | Alineación | Resize Mode |
|---------|------|------------|-------------|
| Fecha | Text | Left | ResizeToContents |
| Tipo | Text (color) | Left | ResizeToContents |
| Descripción | Text | Left | Stretch |
| Categoría | Text | Left | ResizeToContents |
| Cuenta | Text | Left | ResizeToContents |
| Monto | Number ($) | Right | ResizeToContents |

#### Mapeos de Datos

```python
cuentas_map: Dict[str, str]      # {cuenta_id: nombre_cuenta}
categorias_map: Dict[str, str]   # {categoria_id: nombre_categoria}
```

**Propósito**: Convertir IDs de Firebase a nombres legibles para el usuario

**Configuración**:
```python
set_cuentas_map(cuentas: List[Dict])
set_categorias_map(categorias: List[Dict])
```

#### Carga de Transacciones

```python
def load_transactions(transactions: List[Dict[str, Any]]):
    self.transactions_data = transactions
    self._populate_table()
```

**Proceso de `_populate_table()`**:
```python
Para cada transacción:
    1. Fecha: Convertir datetime → "YYYY-MM-DD"
    2. Tipo: Capitalizar y colorear (verde=ingreso, rojo=gasto)
    3. Descripción: Mostrar directamente
    4. Categoría: categoria_id → nombre (usando categorias_map)
    5. Cuenta: cuenta_id → nombre (usando cuentas_map)
    6. Monto: Formatear como "$X,XXX.XX" alineado a la derecha
```

#### Señales

```python
transaction_selected = pyqtSignal(str)          # trans_id
transaction_double_clicked = pyqtSignal(str)    # trans_id
```

**Uso**: Para futuras funcionalidades de edición/visualización

### 5. Diálogos

#### FirebaseConfigDialog (`ui/dialogs/firebase_config_dialog.py`)

**Propósito**: Configurar credenciales de Firebase

**Campos**:
- Archivo de credenciales (JSON): `QLineEdit` + botón "Examinar"
- Storage Bucket: `QLineEdit` (placeholder: "proyecto.appspot.com")

**Validación**:
- Verifica que campos no estén vacíos
- Verifica que archivo de credenciales existe

**Retorno**: `(credentials_path, storage_bucket)` vía `get_config()`

**Extras**:
- Hint sobre variables de entorno
- Pre-población si se pasan valores por defecto

#### ProjectDialog (`ui/dialogs/project_dialog.py`)

**Propósito**: Seleccionar proyecto existente o crear nuevo

**UI**:
- Lista de proyectos (QListWidget)
- Botón "Nuevo Proyecto"
- Botones "Seleccionar" / "Cancelar"

**Flujo "Nuevo Proyecto"**:
```python
1. QInputDialog.getText() → Nombre
2. QInputDialog.getText() → Descripción (opcional)
3. Retorna: (None, nombre, descripcion)
```

**Flujo "Seleccionar Existente"**:
```python
1. Usuario selecciona de la lista
2. Retorna: (proyecto_id, nombre)
```

**Extras**:
- Doble clic para selección rápida
- Mensaje si no hay proyectos disponibles

## 🔄 Flujo Completo de la Aplicación

### Arranque

```
┌─ main() ─────────────────────────────────────────────────┐
│                                                            │
│  1. Crear PROGRAIN4App()                                  │
│     └─ Crear QApplication con High DPI                   │
│                                                            │
│  2. app.run()                                             │
│     ├─ initialize_firebase()                              │
│     │  ├─ Leer env vars (FIREBASE_CREDENTIALS, ...)      │
│     │  ├─ Si no definidas → FirebaseConfigDialog         │
│     │  ├─ FirebaseClient.initialize(creds, bucket)       │
│     │  └─ Retorna True/False                              │
│     │                                                      │
│     ├─ select_project()                                   │
│     │  ├─ firebase_client.get_proyectos()                │
│     │  ├─ ProjectDialog(proyectos)                        │
│     │  ├─ Si crea nuevo → firebase_client.create_proyecto│
│     │  └─ Retorna (proyecto_id, nombre)                   │
│     │                                                      │
│     ├─ MainWindow4(firebase_client, proyecto_id, nombre) │
│     │  ├─ _init_ui() → Crear toolbar, sidebar, tabla     │
│     │  └─ _load_initial_data()                            │
│     │     ├─ get_cuentas_by_proyecto()                    │
│     │     ├─ get_categorias_by_proyecto()                 │
│     │     ├─ _populate_accounts()                         │
│     │     └─ _refresh_transactions()                      │
│     │                                                      │
│     ├─ main_window.show()                                 │
│     │                                                      │
│     └─ app.exec() → Event loop                            │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### Filtrado de Transacciones por Cuenta

```
Usuario selecciona cuenta en sidebar/combo
    ↓
_on_account_list_clicked() / _on_account_combo_changed()
    ↓
self.current_cuenta_id = cuenta_id_seleccionado (o None)
    ↓
_refresh_transactions()
    ↓
firebase_client.get_transacciones_by_proyecto(
    proyecto_id,
    cuenta_id=self.current_cuenta_id  ← FILTRO APLICADO AQUÍ
)
    ↓
FirebaseClient consulta Firestore:
    Si cuenta_id != None:
        query = trans_ref.where('cuenta_id', '==', cuenta_id)
    Else:
        query = trans_ref  (todas las transacciones)
    ↓
Retorna lista filtrada
    ↓
transactions_widget.load_transactions(lista)
    ↓
_populate_table() → Muestra en tabla
```

## 🗂️ Organización del Panel Lateral y Combo

### Panel Lateral de Cuentas

**Widget**: `QListWidget` en sidebar

**Contenido**:
```
┌─────────────────┐
│ 📊 Todas las... │ ← Primera opción (cuenta_id=None)
│ 💵 Efectivo     │ ← Icono según tipo + nombre
│ 🏦 Banco Nación │
│ 💳 Visa Gold    │
│ 📈 Inversiones  │
└─────────────────┘
```

**Iconos por Tipo de Cuenta**:
- `efectivo` → 💵
- `banco` → 🏦
- `tarjeta` → 💳
- `inversion` → 📈
- `ahorro` → 🏦
- Otros → 💰

**Almacenamiento de Datos**:
```python
item.setData(Qt.ItemDataRole.UserRole, cuenta_id)
```

### Combo "Cuenta" (Toolbar)

**Widget**: `QComboBox` en toolbar

**Contenido**:
```
[ Todas las cuentas     ▼ ]
  Todas las cuentas         ← Primera opción
  Efectivo                  ← Solo nombre (sin icono)
  Banco Nación
  Visa Gold
  Inversiones
```

**Almacenamiento de Datos**:
```python
combo.addItem(nombre, userData=cuenta_id)
# Recuperar: combo.itemData(index)
```

### Sincronización

**Sidebar → Combo**:
```python
def _on_account_list_clicked(self, item):
    cuenta_id = item.data(Qt.ItemDataRole.UserRole)
    self.current_cuenta_id = cuenta_id
    
    # Buscar índice en combo con mismo cuenta_id
    for i in range(self.account_combo.count()):
        if self.account_combo.itemData(i) == cuenta_id:
            self.account_combo.setCurrentIndex(i)
            break
    
    self._refresh_transactions()
```

**Combo → Sidebar**:
```python
def _on_account_combo_changed(self, index):
    cuenta_id = self.account_combo.itemData(index)
    self.current_cuenta_id = cuenta_id
    
    # Buscar item en sidebar con mismo cuenta_id
    for i in range(self.accounts_list.count()):
        item = self.accounts_list.item(i)
        if item.data(Qt.ItemDataRole.UserRole) == cuenta_id:
            self.accounts_list.setCurrentItem(item)
            break
    
    self._refresh_transactions()
```

## 🔐 Configuración de Credenciales

### Estado Actual: ⚠️ NO PERSISTENTE

**En `main_ynab.py`, método `initialize_firebase()`**:

```python
1. credentials_path = os.environ.get('FIREBASE_CREDENTIALS', '')
2. storage_bucket = os.environ.get('FIREBASE_STORAGE_BUCKET', '')
3. 
4. if not credentials_path or not storage_bucket:
5.     # Mostrar FirebaseConfigDialog
6.     dialog = FirebaseConfigDialog(credentials_path, storage_bucket)
7.     if dialog.exec() == Accepted:
8.         credentials_path, storage_bucket = dialog.get_config()
9.         # ⚠️ NO SE GUARDAN para el próximo arranque
10.
11. firebase_client.initialize(credentials_path, storage_bucket)
```

**Comportamiento Actual**:
- ✅ Lee variables de entorno si están definidas
- ✅ Si no: muestra diálogo para ingresar manualmente
- ❌ **NO guarda** la configuración ingresada
- ❌ En cada arranque, si no hay env vars, pide credenciales nuevamente

### Pendiente en PHASE 1

**Objetivo**: Guardar configuración de manera persistente

**Opciones de Implementación**:
1. `QSettings` (PyQt6):
   - Windows: Registry
   - macOS: plist
   - Linux: ~/.config/
   
2. Archivo JSON en directorio de configuración:
   - `~/.config/prograin4/config.json`
   - `%APPDATA%/prograin4/config.json` (Windows)

**Flujo Esperado**:
```python
1. Al iniciar app:
   a. Leer configuración persistente
   b. Si válida y archivo existe → usar
   c. Si no → mostrar diálogo
   
2. Al aceptar diálogo:
   a. Validar credenciales
   b. Guardar en configuración persistente
   c. Usar para inicializar Firebase
   
3. En arranques posteriores:
   a. Usar configuración guardada
   b. Solo mostrar diálogo si:
      - No hay configuración guardada
      - Credenciales inválidas
      - Usuario quiere cambiar (opción en menú)
```

**Variables de Entorno**:
- Deben seguir siendo respetadas como **override**
- Si `FIREBASE_CREDENTIALS` está definida, usarla en lugar de config persistente
- Si `FIREBASE_STORAGE_BUCKET` está definida, usarla en lugar de config persistente

## 📊 Llenado de Tabla de Transacciones

### Estado Actual: Datos REALES de Firebase

**NO hay datos dummy**. La tabla muestra:
- Datos reales de Firestore si existen
- Tabla vacía si no hay datos

### Flujo Completo

```
_refresh_transactions()
    ↓
transactions = firebase_client.get_transacciones_by_proyecto(
    proyecto_id="abc123",
    cuenta_id=self.current_cuenta_id  # None o "cuenta_xyz"
)
    ↓
FirebaseClient:
    trans_ref = db.collection('proyectos')
                  .document('abc123')
                  .collection('transacciones')
    
    if cuenta_id:
        query = trans_ref.where('cuenta_id', '==', cuenta_id)
    else:
        query = trans_ref
    
    query = query.order_by('fecha', direction=DESCENDING)
    
    docs = query.stream()
    
    transacciones = []
    for doc in docs:
        data = doc.to_dict()
        data['id'] = doc.id
        transacciones.append(data)
    
    return transacciones
    ↓
transactions_widget.load_transactions(transacciones)
    ↓
TransactionsWidget:
    self.transactions_data = transacciones
    self._populate_table()
    ↓
    Para cada trans en transactions_data:
        row = nueva fila en tabla
        
        # Columna 0: Fecha
        fecha_str = trans['fecha'].strftime('%Y-%m-%d')
        
        # Columna 1: Tipo (con color)
        tipo = trans['tipo'].capitalize()
        color = verde si 'ingreso', rojo si 'gasto'
        
        # Columna 2: Descripción
        descripcion = trans['descripcion']
        
        # Columna 3: Categoría (mapear ID → nombre)
        categoria_id = trans['categoria_id']
        categoria_nombre = self.categorias_map[categoria_id]
        
        # Columna 4: Cuenta (mapear ID → nombre)
        cuenta_id = trans['cuenta_id']
        cuenta_nombre = self.cuentas_map[cuenta_id]
        
        # Columna 5: Monto (formatear)
        monto = f"${trans['monto']:,.2f}"
        alineación = derecha
```

### Datos Necesarios de Firestore

**Estructura Mínima de Transacción**:
```json
{
  "id": "trans_001",
  "fecha": "2024-01-15T10:30:00",
  "tipo": "ingreso",
  "cuenta_id": "cuenta_xyz",
  "categoria_id": "cat_salario",
  "monto": 50000.00,
  "descripcion": "Salario de enero",
  "comentario": "Pago quincenal"
}
```

**Colecciones Auxiliares Necesarias**:
- `proyectos/{proyecto_id}/cuentas` → Para mapear cuenta_id → nombre
- `proyectos/{proyecto_id}/categorias` → Para mapear categoria_id → nombre

## ✅ Verificación de Requisitos

### Requisitos Clave

| Requisito | Estado | Ubicación |
|-----------|--------|-----------|
| Comando de arranque: `python progain4/main_ynab.py` | ✅ | `main_ynab.py` línea 195-202 |
| Sin dependencias de SQLite en runtime | ✅ | Ninguna referencia a SQLite en código |
| High DPI pre-configurado | ✅ | `main_ynab.py` líneas 46-47 |
| No romper credenciales Firebase | ✅ | Config en `FirebaseConfigDialog` |
| Backend 100% Firebase | ✅ | Todo pasa por `FirebaseClient` |

### Dependencias (requirements.txt)

```
firebase-admin>=6.0.0   # Firebase Admin SDK
PyQt6>=6.4.0            # UI Framework
python-dateutil>=2.8.2  # Utilidades de fecha
```

**Nota**: NO incluye `sqlite3` ni bibliotecas relacionadas

### High DPI Configuration

**Ubicación**: `progain4/main_ynab.py`, líneas 45-47

```python
# Enable High DPI scaling (DO NOT MODIFY - already configured)
QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling)
QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)
```

**⚠️ ADVERTENCIA**: Esta configuración **NO DEBE MODIFICARSE** según requisitos

## 📝 Conclusiones del Análisis

### Lo que Funciona

1. ✅ **Estructura base completa y modular**
2. ✅ **Separación clara backend (Firebase) / frontend (PyQt6)**
3. ✅ **Inicialización de Firebase con manejo de errores**
4. ✅ **Selección/creación de proyectos funcional**
5. ✅ **Lectura de cuentas desde Firestore**
6. ✅ **Lectura de transacciones con filtro por cuenta**
7. ✅ **Sincronización sidebar ↔ combo de cuentas**
8. ✅ **Tabla de transacciones con mapeo de IDs a nombres**
9. ✅ **Logging configurado para debugging**

### Pendiente de Implementar

#### PHASE 1: Configuración Persistente
- ❌ Guardar credenciales Firebase en QSettings o JSON
- ❌ Recordar configuración entre sesiones
- ❌ Solo pedir credenciales en primera ejecución

#### PHASE 2-5: CRUD Completo
- ❌ Crear, editar, eliminar cuentas
- ❌ Crear, editar, eliminar transacciones
- ❌ Crear, editar, eliminar categorías
- ❌ Diálogos de transacción completos

#### PHASE 6-9: Funcionalidades Avanzadas
- ❌ Menú superior con estructura completa
- ❌ Herramienta de inspección de Firebase
- ❌ Reportes y dashboards
- ❌ Soporte para adjuntos en Storage

### Compatibilidad con PROGRAIN 3.0

**Referencia Funcional**:
- La app anterior (raíz del repo) usa SQLite
- Sirve como **referencia** para:
  - Funcionalidades esperadas
  - Diseño de diálogos
  - Reportes a migrar
  - UX general

**Separación**:
- `progain4/` es completamente independiente
- NO comparte código con la app anterior
- NO usa SQLite en runtime (solo Firebase)

## 🎯 Próximos Pasos

Con el análisis de PHASE 0 completo, estamos listos para:

1. **PHASE 1**: Implementar configuración persistente de credenciales
2. **PHASE 2**: Completar métodos de cuentas en FirebaseClient
3. **PHASE 3**: Mejorar UI de cuentas si es necesario
4. **PHASE 4**: Completar métodos de transacciones en FirebaseClient
5. **PHASE 5**: Validar flujo completo de transacciones en UI

---

**Documento generado**: 2025-11-22
**Versión**: PROGRAIN 4.0/5.0
**Autor**: Análisis automatizado PHASE 0
