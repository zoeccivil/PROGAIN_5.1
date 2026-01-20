#!/usr/bin/env python3
"""
Script de migración de adjuntos de PROGRAIN 5.0

Convierte URLs con tokens expirables a storage paths permanentes. 

Uso: 
    python progain4/scripts/migrate_attachments.py [--proyecto-id ID] [--apply]
    
Opciones:
    --proyecto-id ID    Migrar solo un proyecto específico (default: todos)
    --apply             Aplicar cambios (default: dry-run)
    --credentials PATH  Path al archivo de credenciales (default: desde config)
"""

import sys
import os
import argparse
import logging
from pathlib import Path

# Agregar directorio raíz al path
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR. parent. parent
sys.path.insert(0, str(PROJECT_ROOT))

from progain4.services.firebase_client import FirebaseClient
from progain4.services. config import ConfigManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description='Migrar adjuntos de PROGRAIN de URLs expirables a paths permanentes'
    )
    parser.add_argument(
        '--proyecto-id',
        type=str,
        help='ID del proyecto a migrar (default: todos los proyectos)'
    )
    parser.add_argument(
        '--apply',
        action='store_true',
        help='Aplicar cambios (default:  dry-run solo reporta)'
    )
    parser.add_argument(
        '--credentials',
        type=str,
        help='Path al archivo de credenciales Firebase (default: desde config)'
    )
    
    args = parser.parse_args()
    
    # Determinar si es dry-run
    dry_run = not args.apply
    
    if dry_run:
        logger.info("="*70)
        logger.info("🔍 MODO DRY-RUN (solo reporte, no modifica datos)")
        logger.info("   Para aplicar cambios, ejecuta con --apply")
        logger.info("="*70)
    else:
        logger.warning("="*70)
        logger.warning("⚠️  MODO APLICAR - SE MODIFICARÁN LOS DATOS")
        logger.warning("="*70)
        
        respuesta = input("¿Continuar?  (escribe 'SI' para confirmar): ")
        if respuesta != 'SI':
            logger. info("Migración cancelada por el usuario")
            return 0
    
    # Inicializar Firebase
    logger.info("\n1️⃣ Inicializando Firebase...")
    
    if args.credentials:
        credentials_path = args.credentials
        logger.info(f"   Usando credenciales:  {credentials_path}")
        
        # Necesitamos bucket también
        bucket = input("Ingresa el nombre del bucket (ej: progain-25fdf. firebasestorage.app): ")
    else:
        # Cargar desde config
        config = ConfigManager()
        credentials_path, bucket = config.get_firebase_config()
        
        if not credentials_path or not bucket:
            logger.error("❌ No se encontraron credenciales en la configuración")
            logger.error("   Usa --credentials para especificar el archivo")
            return 1
        
        logger.info(f"   Credenciales desde config: {credentials_path}")
    
    # Crear cliente
    firebase_client = FirebaseClient()
    
    if not firebase_client.initialize(credentials_path, bucket):
        logger.error("❌ No se pudo inicializar Firebase")
        return 1
    
    logger.info("   ✓ Firebase inicializado correctamente")
    
    # Obtener proyectos
    logger.info("\n2️⃣ Obteniendo proyectos...")
    
    if args.proyecto_id:
        # Solo un proyecto
        proyectos = [{"id": args.proyecto_id, "nombre": f"Proyecto {args.proyecto_id}"}]
        logger.info(f"   Migrando solo proyecto: {args.proyecto_id}")
    else:
        # Todos los proyectos
        proyectos = firebase_client.get_proyectos()
        logger.info(f"   Encontrados {len(proyectos)} proyectos")
    
    if not proyectos:
        logger.warning("⚠️  No se encontraron proyectos")
        return 0
    
    # Migrar cada proyecto
    logger.info("\n3️⃣ Iniciando migración de adjuntos...")
    
    totales = {
        "proyectos": 0,
        "transacciones": 0,
        "con_adjuntos": 0,
        "migradas": 0,
        "omitidas": 0,
        "errores": 0
    }
    
    for proyecto in proyectos:
        proyecto_id = proyecto. get("id")
        proyecto_nombre = proyecto.get("nombre", f"Proyecto {proyecto_id}")
        
        logger.info(f"\n📁 Proyecto: {proyecto_nombre} (ID: {proyecto_id})")
        logger.info("   " + "-"*60)
        
        try:
            # Ejecutar migración
            stats = firebase_client.migrate_transaction_attachments_to_paths(
                proyecto_id=proyecto_id,
                dry_run=dry_run
            )
            
            if "error" in stats:
                logger.error(f"   ❌ Error: {stats['error']}")
                totales["errores"] += 1
                continue
            
            # Acumular estadísticas
            totales["proyectos"] += 1
            totales["transacciones"] += stats. get("total_transactions", 0)
            totales["con_adjuntos"] += stats.get("with_attachments", 0)
            totales["migradas"] += stats.get("migrated", 0)
            totales["omitidas"] += stats. get("skipped", 0)
            totales["errores"] += stats.get("errors", 0)
            
            # Mostrar resumen del proyecto
            logger.info(f"   Total transacciones: {stats.get('total_transactions', 0)}")
            logger.info(f"   Con adjuntos: {stats.get('with_attachments', 0)}")
            logger.info(f"   {'Migrarían' if dry_run else 'Migradas'}: {stats.get('migrated', 0)}")
            logger.info(f"   Omitidas (ya migradas): {stats.get('skipped', 0)}")
            
            if stats.get("errors", 0) > 0:
                logger. warning(f"   ⚠️  Errores:  {stats.get('errors', 0)}")
            
            # Mostrar detalles si hay (opcional, solo primeros 10)
            detalles = stats.get("details", [])
            if detalles:
                logger.info(f"\n   Detalles (primeros 10):")
                for detalle in detalles[: 10]:
                    logger.info(f"      {detalle}")
                if len(detalles) > 10:
                    logger.info(f"      ...  y {len(detalles) - 10} más")
            
        except Exception as e: 
            logger.error(f"   ❌ Error procesando proyecto:  {e}")
            totales["errores"] += 1
    
    # Resumen final
    logger.info("\n" + "="*70)
    logger.info("📊 RESUMEN FINAL DE MIGRACIÓN")
    logger.info("="*70)
    logger.info(f"Proyectos procesados:         {totales['proyectos']}")
    logger.info(f"Total transacciones:         {totales['transacciones']}")
    logger.info(f"Con adjuntos:                {totales['con_adjuntos']}")
    logger.info(f"{'Migrarían' if dry_run else 'Migradas'}:                {totales['migradas']}")
    logger.info(f"Omitidas (ya migradas):      {totales['omitidas']}")
    
    if totales["errores"] > 0:
        logger.warning(f"⚠️  Errores:                    {totales['errores']}")
    
    logger.info("="*70)
    
    if dry_run:
        logger.info("\n✅ Dry-run completado")
        logger.info("   Para aplicar los cambios, ejecuta con --apply")
    else:
        logger.info("\n✅ Migración completada exitosamente")
        logger.info("   Los adjuntos ahora usan URLs públicas permanentes")
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        logger.info("\n\n⚠️  Migración interrumpida por el usuario")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"❌ Error fatal: {e}")
        sys.exit(1)