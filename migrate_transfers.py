"""
Script para migrar transferencias antiguas al nuevo formato. 

Convierte: 
- "transferencia_salida" → "Gasto" (con es_transferencia=True)
- "transferencia_entrada" → "Ingreso" (con es_transferencia=True)

Uso:
    python migrate_transfers. py
"""

import firebase_admin
from firebase_admin import credentials, firestore
from tkinter import Tk, filedialog, messagebox
from typing import Dict, Any, List
from datetime import datetime
import logging

logging.basicConfig(level=logging. INFO)
logger = logging.getLogger(__name__)


def select_credentials_file():
    """Abre un file dialog para seleccionar el archivo de credenciales."""
    root = Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    
    file_path = filedialog.askopenfilename(
        title="Selecciona el archivo de credenciales de Firebase",
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
    )
    
    root.destroy()
    return file_path


def initialize_firebase(cred_path: str):
    """Inicializa Firebase con las credenciales proporcionadas."""
    try:
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        print(f"✅ Firebase inicializado correctamente")
        return db
    except Exception as e:
        print(f"❌ Error inicializando Firebase: {e}")
        return None


def get_all_projects(db) -> List[Dict[str, Any]]:
    """Obtiene todos los proyectos."""
    try:
        proyectos_ref = db.collection("proyectos")
        docs = proyectos_ref.stream()
        
        proyectos = []
        for doc in docs:
            data = doc.to_dict()
            data["_doc_id"] = doc.id
            proyectos.append(data)
        
        return proyectos
    except Exception as e: 
        logger.error(f"Error getting projects: {e}")
        return []


def migrate_project_transfers(db, proyecto_id:  str, dry_run: bool = True) -> Dict[str, int]:
    """
    Migra las transferencias de un proyecto.
    
    Returns:
        Dict con estadísticas:  {
            "salidas_migradas": int,
            "entradas_migradas": int,
            "errores": int
        }
    """
    stats = {
        "salidas_migradas": 0,
        "entradas_migradas": 0,
        "salidas_ya_migradas": 0,
        "entradas_ya_migradas": 0,
        "errores": 0,
    }
    
    try: 
        trans_ref = (
            db.collection("proyectos")
            .document(str(proyecto_id))
            .collection("transacciones")
        )
        
        # Buscar transferencias antiguas (minúsculas)
        docs_salida = list(trans_ref.where("tipo", "==", "transferencia_salida").stream())
        docs_entrada = list(trans_ref.where("tipo", "==", "transferencia_entrada").stream())
        
        # Buscar también con guion bajo y mayúsculas
        docs_salida += list(trans_ref.where("tipo", "==", "Transferencia Salida").stream())
        docs_entrada += list(trans_ref.where("tipo", "==", "Transferencia Entrada").stream())
        docs_salida += list(trans_ref.where("tipo", "==", "Transferencia_Salida").stream())
        docs_entrada += list(trans_ref.where("tipo", "==", "Transferencia_Entrada").stream())
        
        logger.info(f"Proyecto {proyecto_id}:  Encontradas {len(docs_salida)} salidas y {len(docs_entrada)} entradas")
        
        # Migrar salidas
        for doc in docs_salida:
            try: 
                data = doc.to_dict()
                
                # Verificar si ya fue migrada
                if data.get("es_transferencia") == True:
                    stats["salidas_ya_migradas"] += 1
                    continue
                
                # Preparar actualización
                updates = {
                    "tipo": "Gasto",
                    "es_transferencia": True,
                    "transferencia_tipo": "salida",
                    "updatedAt": datetime.now(),
                }
                
                # Migrar campos antiguos al nuevo formato
                if "transferencia_destino" in data:
                    updates["transferencia_cuenta_relacionada"] = data["transferencia_destino"]
                
                if "transferencia_par_id" in data:
                    updates["transferencia_par_id"] = data["transferencia_par_id"]
                
                # Asegurar que tiene categoria_id y subcategoria_id
                if "categoria_id" not in data or data. get("categoria_id") is None:
                    updates["categoria_id"] = "0"
                
                if "subcategoria_id" not in data: 
                    updates["subcategoria_id"] = "0"
                
                # Asegurar que tiene campo eliminado
                if "eliminado" not in data:
                    updates["eliminado"] = False
                
                if not dry_run:
                    doc.reference.update(updates)
                
                stats["salidas_migradas"] += 1
                logger. info(f"  ✅ Migrada salida: {doc.id}")
                
            except Exception as e: 
                logger.error(f"  ❌ Error migrando salida {doc.id}: {e}")
                stats["errores"] += 1
        
        # Migrar entradas
        for doc in docs_entrada:
            try:
                data = doc.to_dict()
                
                # Verificar si ya fue migrada
                if data.get("es_transferencia") == True:
                    stats["entradas_ya_migradas"] += 1
                    continue
                
                # Preparar actualización
                updates = {
                    "tipo": "Ingreso",
                    "es_transferencia": True,
                    "transferencia_tipo": "entrada",
                    "updatedAt":  datetime.now(),
                }
                
                # Migrar campos antiguos al nuevo formato
                if "transferencia_origen" in data:
                    updates["transferencia_cuenta_relacionada"] = data["transferencia_origen"]
                
                if "transferencia_par_id" in data:
                    updates["transferencia_par_id"] = data["transferencia_par_id"]
                
                # Asegurar que tiene categoria_id y subcategoria_id
                if "categoria_id" not in data or data.get("categoria_id") is None:
                    updates["categoria_id"] = "0"
                
                if "subcategoria_id" not in data:
                    updates["subcategoria_id"] = "0"
                
                # Asegurar que tiene campo eliminado
                if "eliminado" not in data:
                    updates["eliminado"] = False
                
                if not dry_run: 
                    doc.reference.update(updates)
                
                stats["entradas_migradas"] += 1
                logger.info(f"  ✅ Migrada entrada: {doc.id}")
                
            except Exception as e:
                logger.error(f"  ❌ Error migrando entrada {doc.id}: {e}")
                stats["errores"] += 1
        
    except Exception as e:
        logger.error(f"Error migrando proyecto {proyecto_id}:  {e}")
        stats["errores"] += 1
    
    return stats


def main():
    """Función principal."""
    print("="*80)
    print("MIGRACIÓN DE TRANSFERENCIAS - PROGRAIN 5.0")
    print("="*80)
    print("\nEste script convertirá las transferencias antiguas al nuevo formato:")
    print("  • 'transferencia_salida' → 'Gasto' (con es_transferencia=True)")
    print("  • 'transferencia_entrada' → 'Ingreso' (con es_transferencia=True)")
    print("\n" + "="*80 + "\n")
    
    # Seleccionar credenciales
    print("📂 Selecciona el archivo de credenciales de Firebase...")
    cred_path = select_credentials_file()
    
    if not cred_path: 
        print("❌ No se seleccionó ningún archivo.  Saliendo...")
        return
    
    print(f"✅ Archivo seleccionado: {cred_path}")
    
    # Inicializar Firebase
    db = initialize_firebase(cred_path)
    if not db:
        return
    
    # Obtener proyectos
    print("\n🔍 Obteniendo lista de proyectos...")
    proyectos = get_all_projects(db)
    print(f"✅ Encontrados {len(proyectos)} proyectos")
    
    # Confirmar ejecución
    root = Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    
    respuesta = messagebox.askyesnocancel(
        "Modo de Ejecución",
        f"¿Cómo deseas ejecutar la migración?\n\n"
        f"Proyectos a procesar: {len(proyectos)}\n\n"
        f"• SÍ: Ejecutar migración REAL (modifica la base de datos)\n"
        f"• NO: Ejecutar en modo DRY-RUN (solo muestra qué se haría)\n"
        f"• CANCELAR: Salir sin hacer nada"
    )
    
    root.destroy()
    
    if respuesta is None:  # Cancelar
        print("\n❌ Migración cancelada por el usuario")
        return
    
    dry_run = not respuesta  # True si es NO (dry-run), False si es SÍ (real)
    
    if dry_run:
        print("\n⚠️ MODO DRY-RUN: No se modificará la base de datos")
    else:
        print("\n🚀 MODO REAL: Se modificará la base de datos")
    
    print("\n" + "="*80)
    print("INICIANDO MIGRACIÓN")
    print("="*80 + "\n")
    
    # Estadísticas globales
    total_stats = {
        "salidas_migradas": 0,
        "entradas_migradas": 0,
        "salidas_ya_migradas": 0,
        "entradas_ya_migradas": 0,
        "errores": 0,
    }
    
    # Procesar cada proyecto
    for i, proyecto in enumerate(proyectos, 1):
        proyecto_id = proyecto["_doc_id"]
        nombre = proyecto. get("nombre", "Sin nombre")
        
        print(f"\n[{i}/{len(proyectos)}] Procesando: {nombre} ({proyecto_id})")
        
        stats = migrate_project_transfers(db, proyecto_id, dry_run=dry_run)
        
        # Acumular estadísticas
        for key in total_stats:
            total_stats[key] += stats[key]
        
        # Mostrar resumen del proyecto
        if stats["salidas_migradas"] + stats["entradas_migradas"] > 0:
            print(f"  📊 Salidas migradas: {stats['salidas_migradas']}")
            print(f"  📊 Entradas migradas: {stats['entradas_migradas']}")
        
        if stats["salidas_ya_migradas"] + stats["entradas_ya_migradas"] > 0:
            print(f"  ℹ️ Ya migradas: {stats['salidas_ya_migradas'] + stats['entradas_ya_migradas']}")
        
        if stats["errores"] > 0:
            print(f"  ❌ Errores: {stats['errores']}")
        
        if stats["salidas_migradas"] + stats["entradas_migradas"] + stats["salidas_ya_migradas"] + stats["entradas_ya_migradas"] == 0:
            print(f"  ✓ Sin transferencias para migrar")
    
    # Resumen final
    print("\n" + "="*80)
    print("RESUMEN FINAL")
    print("="*80)
    print(f"\n{'Concepto':<40} {'Cantidad': >10}")
    print("-"*80)
    print(f"{'Proyectos procesados':<40} {len(proyectos):>10}")
    print(f"{'Salidas migradas':<40} {total_stats['salidas_migradas']: >10}")
    print(f"{'Entradas migradas':<40} {total_stats['entradas_migradas']:>10}")
    print(f"{'Total migradas':<40} {total_stats['salidas_migradas'] + total_stats['entradas_migradas']:>10}")
    print(f"{'Ya estaban migradas':<40} {total_stats['salidas_ya_migradas'] + total_stats['entradas_ya_migradas']:>10}")
    print(f"{'Errores': <40} {total_stats['errores']:>10}")
    print("="*80)
    
    if dry_run:
        print("\n⚠️ MODO DRY-RUN: No se modificó la base de datos")
        print("Ejecuta nuevamente y selecciona SÍ para aplicar los cambios")
    else:
        print("\n✅ MIGRACIÓN COMPLETADA")
        print("Las transferencias han sido actualizadas al nuevo formato")
    
    print("\n" + "="*80)


if __name__ == "__main__":
    main()