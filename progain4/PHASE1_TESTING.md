# PHASE 1 - Testing Plan

## Objetivo
Verificar que la configuración persistente de credenciales Firebase funciona correctamente.

## Prerrequisitos

1. Python 3.8+ instalado
2. Dependencias instaladas:
   ```bash
   pip install firebase-admin PyQt6
   ```
3. Archivo de credenciales Firebase válido
4. Nombre del bucket de Storage

## Escenarios de Prueba

### Escenario 1: Primer Arranque (Sin Configuración Guardada)

**Pasos:**
1. Asegurar que no hay configuración previa:
   - Windows: Eliminar clave `HKCU\Software\PROGRAIN\PROGRAIN 4.0`
   - macOS: Eliminar `~/Library/Preferences/com.PROGRAIN.PROGRAIN 4.0.plist`
   - Linux: Eliminar `~/.config/PROGRAIN/PROGRAIN 4.0.conf`
2. Ejecutar: `python progain4/main_ynab.py`
3. **Resultado Esperado:**
   - Se muestra el diálogo de configuración de Firebase
   - Usuario ingresa credenciales y bucket
   - Al aceptar, la configuración se guarda
   - La aplicación continúa normalmente

**Verificación:**
```python
# En logs debe aparecer:
# "No saved credentials found, showing configuration dialog"
# "Firebase configuration saved successfully"
# "Firebase initialized successfully"
```

### Escenario 2: Segundo Arranque (Con Configuración Guardada)

**Pasos:**
1. Ejecutar nuevamente: `python progain4/main_ynab.py`
2. **Resultado Esperado:**
   - NO se muestra el diálogo de configuración
   - La aplicación usa la configuración guardada
   - Se conecta a Firebase directamente

**Verificación:**
```python
# En logs debe aparecer:
# "Using Firebase credentials from saved configuration"
# "Firebase initialized successfully"
```

### Escenario 3: Variables de Entorno (Override)

**Pasos:**
1. Definir variables de entorno:
   ```bash
   export FIREBASE_CREDENTIALS="/ruta/a/credenciales.json"
   export FIREBASE_STORAGE_BUCKET="mi-proyecto.appspot.com"
   ```
2. Ejecutar: `python progain4/main_ynab.py`
3. **Resultado Esperado:**
   - Las variables de entorno tienen prioridad
   - NO se usa la configuración guardada
   - NO se muestra el diálogo

**Verificación:**
```python
# En logs debe aparecer:
# "Using Firebase credentials from environment variables"
# "Firebase initialized successfully"
```

### Escenario 4: Credenciales Guardadas Inválidas

**Pasos:**
1. Modificar manualmente la configuración guardada para apuntar a un archivo inexistente
2. Ejecutar: `python progain4/main_ynab.py`
3. **Resultado Esperado:**
   - La configuración guardada se detecta como inválida
   - Se muestra el diálogo para ingresar nueva configuración
   - Al aceptar, se guarda la nueva configuración

**Verificación:**
```python
# En logs debe aparecer:
# "Stored credentials file not found: /ruta/invalida"
# "No saved credentials found, showing configuration dialog"
```

### Escenario 5: Cancelar el Diálogo

**Pasos:**
1. Eliminar configuración guardada
2. Ejecutar: `python progain4/main_ynab.py`
3. Cuando aparece el diálogo, presionar "Cancelar"
4. **Resultado Esperado:**
   - La aplicación se cierra sin error
   - No se guarda ninguna configuración

**Verificación:**
```python
# En logs debe aparecer:
# "Firebase configuration cancelled by user"
# La app termina con código 1 o 0
```

## Orden de Prioridad (Resumen)

La implementación sigue este orden de prioridad:

1. **Variables de Entorno** (más alta)
   - `FIREBASE_CREDENTIALS`
   - `FIREBASE_STORAGE_BUCKET`
2. **Configuración Persistente** (QSettings)
   - Guardada en arranques anteriores
3. **Diálogo de Usuario** (más baja)
   - Si no hay ninguna de las anteriores

## Ubicación de la Configuración Guardada

### Windows
```
HKEY_CURRENT_USER\Software\PROGRAIN\PROGRAIN 4.0
├─ firebase/credentials_path: REG_SZ
└─ firebase/storage_bucket: REG_SZ
```

### macOS
```
~/Library/Preferences/com.PROGRAIN.PROGRAIN 4.0.plist
```

### Linux
```
~/.config/PROGRAIN/PROGRAIN 4.0.conf
```

## Código de Verificación Manual

Para verificar la configuración guardada:

```python
from PyQt6.QtCore import QSettings

settings = QSettings("PROGRAIN", "PROGRAIN 4.0")
print("Config file:", settings.fileName())
print("Credentials:", settings.value("firebase/credentials_path"))
print("Bucket:", settings.value("firebase/storage_bucket"))
```

Para limpiar la configuración:

```python
from PyQt6.QtCore import QSettings

settings = QSettings("PROGRAIN", "PROGRAIN 4.0")
settings.clear()
settings.sync()
print("Configuration cleared")
```

## Notas Importantes

1. **Seguridad**: La configuración guardada NO cifra el path a las credenciales. El archivo JSON de credenciales debe mantenerse seguro por otros medios.

2. **Portabilidad**: Si se mueve el archivo de credenciales, la app detectará que el path guardado es inválido y pedirá la nueva ubicación.

3. **Multi-Usuario**: Cada usuario del sistema tendrá su propia configuración (QSettings es por usuario).

4. **Compatibilidad**: La configuración es compatible entre versiones de la app mientras use la misma organización ("PROGRAIN") y aplicación ("PROGRAIN 4.0").
