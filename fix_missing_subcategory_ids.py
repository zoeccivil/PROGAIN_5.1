# Script:  fix_missing_subcategory_ids.py
"""
Script de migración para agregar campo 'id' numérico a subcategorías en Firestore.  

Uso: 
    python fix_missing_subcategory_ids.py

El script abrirá un diálogo para seleccionar el archivo de credenciales de Firebase. 
El bucket se configura automáticamente. 
"""

import logging
import sys
from pathlib import Path

# Configurar logging
logging. basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ✅ BUCKET POR DEFECTO (AUTOMÁTICO)
DEFAULT_BUCKET = "progain-25fdf.firebasestorage.app"


def select_credentials_file():
    """Abre un FileDialog para seleccionar el archivo de credenciales JSON."""
    try:
        from tkinter import Tk, filedialog
        
        # Ocultar ventana principal de tkinter
        root = Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        
        logger.info("🔍 Selecciona el archivo de credenciales de Firebase...")
        
        file_path = filedialog.askopenfilename(
            title="Seleccionar archivo de credenciales de Firebase",
            filetypes=[
                ("Archivos JSON", "*.json"),
                ("Todos los archivos", "*.*")
            ],
            initialdir=str(Path.home())
        )
        
        root.destroy()
        
        if not file_path:
            logger.error("❌ No se seleccionó ningún archivo")
            return None
        
        if not Path(file_path).exists():
            logger.error(f"❌ El archivo no existe: {file_path}")
            return None
        
        logger.info(f"✅ Credenciales seleccionadas: {file_path}")
        return file_path
        
    except ImportError:
        logger.error("❌ tkinter no está disponible. Instalando...")
        logger.error("   Ejecuta: pip install tk")
        return None
    except Exception as e: 
        logger.error(f"❌ Error al abrir FileDialog: {e}")
        return None


def fix_missing_subcategory_ids():
    """Agrega campo 'id' numérico a subcategorías que no lo tienen."""
    
    print("\n" + "="*60)
    print("MIGRACIÓN DE SUBCATEGORÍAS - AGREGAR CAMPO 'id'")
    print("="*60 + "\n")
    
    # 1. Seleccionar archivo de credenciales
    creds_path = select_credentials_file()
    if not creds_path: 
        logger.error("❌ No se pudo obtener el archivo de credenciales")
        input("\nPresiona Enter para salir...")
        return
    
    # 2. ✅ Usar bucket automático
    bucket = DEFAULT_BUCKET
    logger.info(f"🪣 Usando bucket de Storage: {bucket}")
    
    # 3. Inicializar Firebase
    logger.info("\n📡 Conectando a Firebase...")
    
    try:
        from progain4.services. firebase_client import FirebaseClient
    except ImportError:
        logger. error("❌ No se pudo importar FirebaseClient")
        logger.error("   Asegúrate de ejecutar desde el directorio raíz del proyecto")
        input("\nPresiona Enter para salir...")
        return
    
    client = FirebaseClient()
    if not client.initialize(creds_path, bucket):
        logger.error("❌ No se pudo inicializar Firebase")
        logger.error("   Verifica que las credenciales y el bucket sean correctos")
        input("\nPresiona Enter para salir...")
        return
    
    logger.info("✅ Conectado a Firebase correctamente\n")
    
    # 4. Obtener todas las subcategorías
    logger. info("📋 Analizando subcategorías en Firestore...")
    
    try:
        sub_ref = client.db.collection("subcategorias")
        all_docs = list(sub_ref.stream())
    except Exception as e:
        logger. error(f"❌ Error al leer subcategorías: {e}")
        input("\nPresiona Enter para salir...")
        return
    
    logger.info(f"📊 Encontradas {len(all_docs)} subcategorías totales\n")
    
    # 5. Analizar subcategorías
    max_id = 0
    docs_sin_id = []
    docs_con_id = []
    docs_id_invalido = []
    
    for doc in all_docs:
        data = doc.to_dict() or {}
        nombre = data.get('nombre', 'Sin nombre')
        categoria_id = data. get('categoria_id', '? ')
        
        # Verificar si tiene campo "id"
        if "id" not in data: 
            docs_sin_id. append((doc, nombre, categoria_id))
            logger.warning(f"⚠️  '{nombre}' (cat: {categoria_id}) → SIN campo 'id'")
        else:
            id_value = data. get("id")
            try:
                current_id = int(id_value)
                docs_con_id.append((doc, nombre, current_id))
                if current_id > max_id:
                    max_id = current_id
            except (ValueError, TypeError):
                docs_id_invalido.append((doc, nombre, id_value))
                logger.warning(f"⚠️  '{nombre}' → 'id' NO numérico: {id_value}")
    
    # 6. Mostrar resumen
    print("\n" + "="*60)
    print("RESUMEN DEL ANÁLISIS")
    print("="*60)
    print(f"✅ Subcategorías con 'id' numérico válido: {len(docs_con_id)}")
    print(f"⚠️  Subcategorías SIN campo 'id':           {len(docs_sin_id)}")
    print(f"❌ Subcategorías con 'id' no numérico:     {len(docs_id_invalido)}")
    print(f"🔢 Máximo ID encontrado:                   {max_id}")
    print("="*60 + "\n")
    
    if not docs_sin_id and not docs_id_invalido:
        logger. info("🎉 Todas las subcategorías ya tienen campo 'id' numérico válido")
        input("\nPresiona Enter para salir...")
        return
    
    # 7. Confirmar operación
    total_a_reparar = len(docs_sin_id) + len(docs_id_invalido)
    print(f"📝 Se agregarán IDs numéricos a {total_a_reparar} subcategorías")
    print(f"   Comenzando desde el ID:  {max_id + 1}\n")
    
    respuesta = input("¿Deseas continuar con la migración? (si/no): ").strip().lower()
    
    if respuesta not in ['si', 's', 'sí', 'yes', 'y']:
        logger.info("❌ Operación cancelada por el usuario")
        input("\nPresiona Enter para salir...")
        return
    
    # 8. Realizar migración
    print("\n" + "="*60)
    print("INICIANDO MIGRACIÓN")
    print("="*60 + "\n")
    
    next_id = max_id + 1
    actualizadas = 0
    errores = 0
    
    # Procesar documentos sin ID
    for doc, nombre, categoria_id in docs_sin_id: 
        try:
            doc. reference.update({"id": next_id})
            logger.info(f"✅ '{nombre}' (cat: {categoria_id}) → id = {next_id}")
            next_id += 1
            actualizadas += 1
        except Exception as e:
            logger.error(f"❌ Error actualizando '{nombre}': {e}")
            errores += 1
    
    # Procesar documentos con ID inválido
    for doc, nombre, id_invalido in docs_id_invalido: 
        try:
            doc. reference.update({"id":  next_id})
            logger. info(f"✅ '{nombre}' (era: {id_invalido}) → id = {next_id}")
            next_id += 1
            actualizadas += 1
        except Exception as e:
            logger.error(f"❌ Error actualizando '{nombre}': {e}")
            errores += 1
    
    # 9. Resumen final
    print("\n" + "="*60)
    print("MIGRACIÓN COMPLETADA")
    print("="*60)
    print(f"✅ Subcategorías actualizadas: {actualizadas}")
    print(f"❌ Errores:                     {errores}")
    print(f"🔢 Siguiente ID disponible:     {next_id}")
    print("="*60 + "\n")
    
    if errores == 0:
        logger.info("🎉 Migración completada exitosamente")
    else:
        logger.warning(f"⚠️  Migración completada con {errores} error(es)")
    
    input("\nPresiona Enter para salir...")


if __name__ == "__main__":
    try:
        fix_missing_subcategory_ids()
    except KeyboardInterrupt:
        print("\n\n❌ Operación interrumpida por el usuario")
        sys.exit(1)
    except Exception as e:
        logger. error(f"\n❌ Error inesperado: {e}", exc_info=True)
        input("\nPresiona Enter para salir...")
        sys.exit(1)