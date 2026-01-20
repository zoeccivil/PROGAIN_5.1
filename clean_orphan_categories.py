# Script:  clean_orphan_categories.py
"""
Limpia referencias huérfanas de categorías en proyectos.
Elimina documentos en proyectos/{id}/categorias_proyecto que apuntan a categorías inexistentes.
"""

import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DEFAULT_BUCKET = "progain-25fdf. firebasestorage.app"


def select_credentials_file():
    """Abre FileDialog para seleccionar credenciales."""
    try:
        from tkinter import Tk, filedialog
        
        root = Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        
        logger.info("🔍 Selecciona el archivo de credenciales de Firebase...")
        
        file_path = filedialog.askopenfilename(
            title="Seleccionar archivo de credenciales de Firebase",
            filetypes=[("Archivos JSON", "*.json"), ("Todos los archivos", "*.*")],
            initialdir=str(Path.home())
        )
        
        root.destroy()
        
        if not file_path or not Path(file_path).exists():
            logger.error("❌ Archivo de credenciales no válido")
            return None
        
        logger.info(f"✅ Credenciales:  {file_path}")
        return file_path
        
    except Exception as e:
        logger. error(f"❌ Error al abrir FileDialog: {e}")
        return None


def clean_orphan_categories():
    """Elimina categorías huérfanas de todos los proyectos."""
    
    print("\n" + "="*60)
    print("LIMPIEZA DE CATEGORÍAS HUÉRFANAS")
    print("="*60 + "\n")
    
    # 1. Seleccionar credenciales
    creds_path = select_credentials_file()
    if not creds_path: 
        input("\nPresiona Enter para salir...")
        return
    
    # 2. Inicializar Firebase
    bucket = DEFAULT_BUCKET
    logger.info(f"🪣 Bucket:  {bucket}")
    
    try:
        from progain4.services.firebase_client import FirebaseClient
    except ImportError:
        logger. error("❌ No se pudo importar FirebaseClient")
        input("\nPresiona Enter para salir...")
        return
    
    client = FirebaseClient()
    if not client.initialize(creds_path, bucket):
        logger.error("❌ No se pudo conectar a Firebase")
        input("\nPresiona Enter para salir...")
        return
    
    logger.info("✅ Conectado a Firebase\n")
    
    try:
        # 3. Obtener catálogo maestro de categorías
        logger.info("📋 Cargando catálogo maestro de categorías...")
        categorias_maestras = client.get_categorias_maestras() or []
        
        # Crear set de IDs válidos (ambos formatos)
        ids_validos = set()
        for cat in categorias_maestras:
            cid = cat["id"]
            ids_validos.add(cid)
            ids_validos.add(str(cid))
            ids_validos.add(int(cid) if isinstance(cid, str) and cid.isdigit() else cid)
        
        logger.info(f"✅ {len(categorias_maestras)} categorías maestras válidas")
        logger.info(f"   IDs válidos (todos formatos): {sorted([str(i) for i in ids_validos if isinstance(i, int)])[: 10]}...")
        
        # 4. Obtener todos los proyectos
        logger. info("\n📂 Cargando proyectos...")
        proyectos = client.get_proyectos() or []
        logger.info(f"✅ {len(proyectos)} proyectos encontrados\n")
        
        # 5. Analizar cada proyecto
        print("="*60)
        print("ANÁLISIS DE PROYECTOS")
        print("="*60 + "\n")
        
        total_huerfanas = 0
        proyectos_con_huerfanas = []
        docs_a_eliminar = []
        
        for proyecto in proyectos: 
            proyecto_id = proyecto. get("id")
            proyecto_nombre = proyecto.get("nombre", f"Proyecto {proyecto_id}")
            
            try:
                # Obtener categorías del proyecto
                proj_ref = client.db.collection("proyectos").document(str(proyecto_id))
                cat_coll = proj_ref. collection("categorias_proyecto")
                docs = list(cat_coll.stream())
                
                if not docs:
                    continue
                
                huerfanas_proyecto = []
                
                for doc in docs:
                    data = doc.to_dict() or {}
                    cat_id_raw = (
                        data.get("categoria_maestra_id") or 
                        data.get("categoria_id") or 
                        doc.id
                    )
                    
                    # Verificar si existe en catálogo maestro
                    cat_id_str = str(cat_id_raw)
                    
                    try:
                        cat_id_int = int(cat_id_raw)
                    except: 
                        cat_id_int = None
                    
                    # Verificar en todos los formatos
                    existe = (
                        cat_id_raw in ids_validos or
                        cat_id_str in ids_validos or
                        (cat_id_int and cat_id_int in ids_validos)
                    )
                    
                    if not existe:
                        huerfanas_proyecto.append((doc, cat_id_str))
                        docs_a_eliminar.append((proyecto_id, proyecto_nombre, doc, cat_id_str))
                
                if huerfanas_proyecto:
                    total_huerfanas += len(huerfanas_proyecto)
                    proyectos_con_huerfanas.append(proyecto_nombre)
                    
                    logger.warning(
                        f"⚠️  {proyecto_nombre} ({proyecto_id}): "
                        f"{len(huerfanas_proyecto)} categorías huérfanas"
                    )
                    for doc, cat_id in huerfanas_proyecto:
                        logger.warning(f"     - Categoría ID: {cat_id} (doc: {doc.id})")
                
            except Exception as e:
                logger.error(f"❌ Error analizando proyecto {proyecto_id}:  {e}")
        
        # 6. Resumen
        print("\n" + "="*60)
        print("RESUMEN DEL ANÁLISIS")
        print("="*60)
        print(f"📊 Total proyectos analizados:        {len(proyectos)}")
        print(f"⚠️  Proyectos con huérfanas:          {len(proyectos_con_huerfanas)}")
        print(f"❌ Total categorías huérfanas:       {total_huerfanas}")
        print("="*60 + "\n")
        
        if not docs_a_eliminar:
            logger.info("🎉 No se encontraron categorías huérfanas")
            input("\nPresiona Enter para salir...")
            return
        
        # 7. Confirmar eliminación
        print("📝 Se eliminarán las siguientes referencias:\n")
        for proyecto_id, proyecto_nombre, doc, cat_id in docs_a_eliminar[: 10]:
            print(f"   • {proyecto_nombre}:  Categoría {cat_id}")
        
        if len(docs_a_eliminar) > 10:
            print(f"   ... y {len(docs_a_eliminar) - 10} más")
        
        print()
        respuesta = input("¿Deseas eliminar estas referencias huérfanas? (si/no): ").strip().lower()
        
        if respuesta not in ['si', 's', 'sí', 'yes', 'y']:
            logger.info("❌ Operación cancelada")
            input("\nPresiona Enter para salir...")
            return
        
        # 8. Eliminar referencias huérfanas
        print("\n" + "="*60)
        print("ELIMINANDO REFERENCIAS HUÉRFANAS")
        print("="*60 + "\n")
        
        eliminadas = 0
        errores = 0
        
        for proyecto_id, proyecto_nombre, doc, cat_id in docs_a_eliminar:
            try: 
                doc. reference.delete()
                logger.info(f"✅ Eliminada:  {proyecto_nombre} → Categoría {cat_id}")
                eliminadas += 1
            except Exception as e:
                logger.error(f"❌ Error eliminando {cat_id} de {proyecto_nombre}: {e}")
                errores += 1
        
        # 9. Resumen final
        print("\n" + "="*60)
        print("LIMPIEZA COMPLETADA")
        print("="*60)
        print(f"✅ Referencias eliminadas: {eliminadas}")
        print(f"❌ Errores:                  {errores}")
        print("="*60 + "\n")
        
        if errores == 0:
            logger.info("🎉 Limpieza completada exitosamente")
        else:
            logger. warning(f"⚠️  Limpieza completada con {errores} error(es)")
        
        input("\nPresiona Enter para salir...")
        
    except Exception as e:
        logger.error(f"❌ Error inesperado: {e}", exc_info=True)
        input("\nPresiona Enter para salir...")


if __name__ == "__main__":
    try:
        clean_orphan_categories()
    except KeyboardInterrupt:
        print("\n\n❌ Operación interrumpida")
    except Exception as e:
        logger.error(f"❌ Error:  {e}", exc_info=True)
        input("\nPresiona Enter para salir...")