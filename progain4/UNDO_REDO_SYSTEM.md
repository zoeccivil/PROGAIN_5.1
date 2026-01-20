# Sistema Undo/Redo - PROGAIN 5.1

## 📋 Resumen

Este documento describe la implementación completa del sistema Undo/Redo para PROGAIN 5.1 usando el patrón Command.

## 🎯 Características

- ✅ **Patrón Command**: Arquitectura limpia y extensible
- ✅ **Batch Operations**: Soporte para operaciones masivas
- ✅ **Stack Limitado**: Límite configurable de historial (default: 25 acciones)
- ✅ **Persistencia**: Guardado de metadatos del historial
- ✅ **Integración UI**: Menú, shortcuts (Ctrl+Z/Ctrl+Y) y toolbar
- ✅ **Logging Completo**: Trazabilidad de todas las operaciones
- ✅ **Confirmación Batch**: Diálogo de confirmación para operaciones masivas

## 📁 Estructura de Archivos

```
progain4/
├── commands/
│   ├── __init__.py                      # Clase base Command
│   ├── transaction_commands.py          # CreateTransactionCommand
│   └── batch_command.py                 # BatchCommand para operaciones masivas
├── services/
│   └── undo_manager.py                  # UndoRedoManager
├── ui/
│   ├── main_window4.py                  # Integración UI (menú, shortcuts, toolbar)
│   └── dialogs/
│       └── importer_window_firebase.py  # Uso de comandos en importador
└── test/
    └── test_undo_redo.py                # Suite de tests
```

## 🔧 Componentes Principales

### 1. Clase Base Command (`progain4/commands/__init__.py`)

```python
class Command(ABC):
    """Clase base para todos los comandos"""
    
    @abstractmethod
    def execute(self) -> bool:
        """Ejecuta el comando"""
        pass
    
    @abstractmethod
    def undo(self) -> bool:
        """Deshace el comando"""
        pass
    
    def get_description(self) -> str:
        """Descripción legible del comando"""
        pass
```

### 2. CreateTransactionCommand

Comando para crear transacciones en Firebase:

```python
cmd = CreateTransactionCommand(
    firebase_client=firebase_client,
    proyecto_id=proyecto_id,
    data={
        "id": str(uuid.uuid4()),
        "proyecto_id": proyecto_id,
        "cuenta_id": cuenta_id,
        "tipo": "Gasto",
        "monto": 1000.0,
        "fecha": "2026-01-20",
        # ... más campos
    }
)
```

**Funcionalidad:**
- `execute()`: Crea documento en Firestore
- `undo()`: Elimina documento de Firestore
- Logging completo de operaciones

### 3. BatchCommand

Agrupa múltiples comandos como una sola operación:

```python
batch = BatchCommand(
    commands=[cmd1, cmd2, cmd3],
    description="Importar 3 transacciones desde archivo"
)
```

**Características:**
- Ejecuta comandos en orden
- Si falla uno, hace rollback de todos los anteriores
- Undo en orden inverso
- Flag `is_batch` para confirmación en UI

### 4. UndoRedoManager

Gestiona el historial de comandos:

```python
manager = UndoRedoManager(
    firebase_client=firebase_client,
    config_manager=config_manager,
    max_stack_size=25
)

# Ejecutar comando
manager.execute_command(command)

# Deshacer
if manager.can_undo():
    manager.undo()

# Rehacer
if manager.can_redo():
    manager.redo()
```

**Funcionalidades:**
- `execute_command()`: Ejecuta y agrega a stack
- `undo()`: Deshace última acción
- `redo()`: Rehace última acción deshecha
- `can_undo()` / `can_redo()`: Verifica disponibilidad
- `get_undo_description()` / `get_redo_description()`: Obtiene descripciones
- `save_to_file()`: Persiste metadatos (no los comandos mismos)

## 🎨 Integración UI

### Menú "Editar"

Se agregaron las siguientes opciones al inicio del menú:

1. **Deshacer** (Ctrl+Z)
   - Deshace la última acción
   - Muestra descripción de la acción
   - Se deshabilita si no hay acciones para deshacer

2. **Rehacer** (Ctrl+Y / Ctrl+Shift+Z)
   - Rehace la última acción deshecha
   - Muestra descripción de la acción
   - Se deshabilita si no hay acciones para rehacer

3. **Ver historial de cambios...**
   - Muestra lista de acciones disponibles para undo/redo

### Shortcuts

- **Ctrl+Z**: Deshacer
- **Ctrl+Y** o **Ctrl+Shift+Z**: Rehacer

### Toolbar

Botones agregados al toolbar:
- **⟲ Deshacer**: Ejecuta undo
- **⟳ Rehacer**: Ejecuta redo

### Estado de Botones

Los botones/menús se actualizan automáticamente:
- Se habilitan/deshabilitan según disponibilidad
- Muestran descripción de la acción en tooltip/texto
- Se actualizan después de cada operación

## 📤 Uso: Importador de Transacciones

El importador ahora usa el sistema de comandos:

### Flujo Anterior (Incorrecto)
```python
# ❌ Llamada directa a Firebase
firebase_client.agregar_transaccion_a_proyecto(proyecto_id, data)
```

### Flujo Nuevo (Correcto)
```python
# ✅ Crear comandos
commands = []
for transaction_data in transactions:
    cmd = CreateTransactionCommand(firebase_client, proyecto_id, transaction_data)
    commands.append(cmd)

# ✅ Ejecutar via batch command
batch = BatchCommand(commands, "Importar N transacciones")
main_window.undo_manager.execute_command(batch)
```

**Beneficios:**
- Todas las transacciones importadas pueden deshacerse con un solo Ctrl+Z
- Se registra en el historial automáticamente
- Confirmación antes de deshacer operaciones masivas

## 📊 Logging

El sistema genera logs detallados:

### Ejemplo de Log Exitoso

```
2026-01-20 01:40:00 - progain4.services.undo_manager - INFO - ✅ UndoRedoManager inicializado (límite: 25 acciones)
2026-01-20 01:40:00 - progain4.ui.main_window4 - INFO - ✅ Menú Editar configurado con Undo/Redo
2026-01-20 01:40:30 - progain4.services.undo_manager - INFO - 🚀 Ejecutando comando: Importar 3 transacciones desde archivo
2026-01-20 01:40:30 - progain4.commands.transaction_commands - INFO - ✅ Transacción creada: aae44e94-82ad...
2026-01-20 01:40:30 - progain4.commands.transaction_commands - INFO - ✅ Transacción creada: bef55fa5-93be...
2026-01-20 01:40:30 - progain4.commands.transaction_commands - INFO - ✅ Transacción creada: cg066gb6-04cf...
2026-01-20 01:40:30 - progain4.services.undo_manager - INFO - ✅ Comando ejecutado y guardado (stack: 1/25)
2026-01-20 01:40:45 - progain4.ui.main_window4 - INFO - 🔄 Ejecutando UNDO...
2026-01-20 01:40:45 - progain4.services.undo_manager - INFO - ⏪ Deshaciendo: Importar 3 transacciones desde archivo
2026-01-20 01:40:46 - progain4.commands.transaction_commands - INFO - ✅ Transacción eliminada (undo): cg066gb6-04cf...
2026-01-20 01:40:46 - progain4.commands.transaction_commands - INFO - ✅ Transacción eliminada (undo): bef55fa5-93be...
2026-01-20 01:40:46 - progain4.commands.transaction_commands - INFO - ✅ Transacción eliminada (undo): aae44e94-82ad...
2026-01-20 01:40:46 - progain4.services.undo_manager - INFO - ✅ Undo exitoso (undo stack: 0, redo stack: 1)
2026-01-20 01:40:46 - progain4.ui.main_window4 - INFO - ✅ Undo exitoso: Importar 3 transacciones desde archivo
```

## 🧪 Tests

Suite de tests en `progain4/test/test_undo_redo.py`:

```bash
# Ejecutar tests
cd /path/to/PROGAIN_5.1
PYTHONPATH=$PWD python3 progain4/test/test_undo_redo.py
```

**Tests incluidos:**
1. ✅ Test básico de undo/redo
2. ✅ Test de batch command
3. ✅ Test de límite de stack
4. ✅ Test de descripciones

**Resultado:**
```
==================================================
✅ ALL TESTS PASSED
==================================================
```

## 🔄 Flujo de Trabajo

### 1. Usuario Importa Transacciones

```
Usuario selecciona filas → Click "Agregar" → Crear comandos → BatchCommand
                                                                    ↓
                                                          UndoRedoManager.execute_command()
                                                                    ↓
                                                          Ejecutar en Firebase
                                                                    ↓
                                                          Agregar a undo_stack
                                                                    ↓
                                                          Actualizar UI (botones)
```

### 2. Usuario Presiona Ctrl+Z

```
Ctrl+Z → perform_undo() → UndoRedoManager.undo() → BatchCommand.undo()
                                                           ↓
                                                    Undo cada comando
                                                           ↓
                                                    Eliminar de Firebase
                                                           ↓
                                                    Agregar a redo_stack
                                                           ↓
                                                    refresh_current_view()
                                                           ↓
                                                    update_undo_redo_state()
```

## 🚀 Extensión Futura

Para agregar más comandos (editar, eliminar, etc.):

1. Crear nueva clase en `progain4/commands/`:

```python
class UpdateTransactionCommand(Command):
    def __init__(self, firebase_client, proyecto_id, transaction_id, new_data):
        self.firebase_client = firebase_client
        self.proyecto_id = proyecto_id
        self.transaction_id = transaction_id
        self.new_data = new_data
        self.old_data = None  # Guardar para undo
        super().__init__(f"Actualizar transacción {transaction_id}")
    
    def execute(self) -> bool:
        # Guardar datos anteriores
        self.old_data = self.firebase_client.get_transaction(...)
        # Actualizar
        return self.firebase_client.update_transaction(...)
    
    def undo(self) -> bool:
        # Restaurar datos anteriores
        return self.firebase_client.update_transaction(..., self.old_data)
```

2. Usar en UI:

```python
cmd = UpdateTransactionCommand(...)
self.undo_manager.execute_command(cmd)
```

## ⚠️ Limitaciones Conocidas

1. **No se persisten los comandos mismos**: Solo se guardan descripciones. Al cerrar la app, se pierde el historial.
2. **Solo transacciones por ahora**: Cuentas, categorías, etc. no tienen comandos aún.
3. **No maneja conflictos**: Si otro usuario modifica la misma transacción, el undo podría fallar.

## 📝 Checklist de Verificación

- [x] Comandos creados y probados
- [x] UndoRedoManager funcionando
- [x] Integración con MainWindow4
- [x] Menú "Editar" configurado
- [x] Shortcuts funcionando
- [x] Toolbar agregado
- [x] Importador usando comandos
- [x] Logging completo
- [x] Tests pasando
- [ ] Testing manual con Firebase real (requiere usuario)

## 🎓 Referencias

- **Patrón Command**: https://refactoring.guru/design-patterns/command
- **Undo/Redo Pattern**: https://sourcemaking.com/design_patterns/command

---

**Fecha de Implementación**: 2026-01-20  
**Versión**: 5.1  
**Estado**: ✅ Implementación Completa
