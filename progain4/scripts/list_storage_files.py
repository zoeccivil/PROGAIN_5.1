#!/usr/bin/env python3
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from progain4.services. firebase_client import FirebaseClient
from progain4.services.config import ConfigManager

# Inicializar
config = ConfigManager()
creds, bucket = config.get_firebase_config()

client = FirebaseClient()
client.initialize(creds, bucket)

print("="*80)
print("📁 ARCHIVOS EN STORAGE - Proyecto/13/2025/12/")
print("="*80)

# Listar archivos
blobs = list(client.bucket.list_blobs(prefix="Proyecto/13/2025/12/"))

if not blobs:
    print("\n⚠️ NO se encontraron archivos en Proyecto/13/2025/12/")
    print("\nProbando con Proyecto/13/2025/...")
    blobs = list(client.bucket. list_blobs(prefix="Proyecto/13/2025/"))
    
    if not blobs: 
        print("⚠️ NO se encontraron archivos en Proyecto/13/2025/")
        print("\nProbando con Proyecto/13/...")
        blobs = list(client.bucket.list_blobs(prefix="Proyecto/13/"))

if blobs:
    print(f"\n✅ Encontrados {len(blobs)} archivos:\n")
    for i, blob in enumerate(blobs[: 20], 1):  # Primeros 20
        print(f"{i}.  {blob.name}")
        print(f"   URL pública: https://firebasestorage.googleapis.com/v0/b/{client.bucket.name}/o/{blob.name. replace('/', '%2F')}?alt=media")
        print()
else:
    print("\n❌ NO se encontraron archivos en Proyecto/13/")

print("="*80)