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
print("🔓 HACIENDO PÚBLICOS LOS ARCHIVOS DE PROYECTO 13")
print("="*80)

# Listar archivos
blobs = list(client.bucket.list_blobs(prefix="Proyecto/13/2025/12/", max_results=5))

print(f"\n✅ Encontrados {len(blobs)} archivos (procesando primeros 5)")

for i, blob in enumerate(blobs, 1):
    print(f"\n{i}. {blob.name}")
    
    # Hacer público
    try:
        blob.make_public()
        print(f"   ✅ Ahora es público")
        
        # Generar URL pública
        url = blob.public_url
        print(f"   URL: {url}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

print("\n" + "="*80)
print("🧪 Prueba una de las URLs arriba en el navegador")
print("="*80)