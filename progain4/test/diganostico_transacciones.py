"""
Script de diagnóstico para entender el problema con las transacciones en Firebase
"""

import sys
import os
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import tkinter as tk
from tkinter import filedialog

# Ajustar path para importar módulos de progain4 si fuera necesario
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def diagnosticar_transacciones():
    print("=" * 80)
    print("DIAGNÓSTICO DE TRANSACCIONES EN FIREBASE")
    print("=" * 80)
    
    # 1. Buscar Credenciales con File Dialog
    print("\n⏳ Abriendo ventana para seleccionar credenciales...")
    
    root = tk.Tk()
    root.withdraw()
    
    cred_path = filedialog. askopenfilename(
        title="Selecciona tu archivo de credenciales Firebase JSON",
        filetypes=[("Archivos JSON", "*.json"), ("Todos los archivos", "*.*")],
        initialdir=os.getcwd()
    )
    
    root.destroy()

    if not cred_path:
        print("❌ Operación cancelada: No se seleccionó ningún archivo.")
        return

    print(f"📂 Archivo seleccionado: {cred_path}")

    # 2. Inicializar Firebase
    try:
        cred = credentials. Certificate(cred_path)
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
        else:
            print("ℹ️ Firebase ya estaba inicializado, usando instancia existente.")
            
        db = firestore.client()
        print("✅ Conexión a Firestore exitosa.")
    except Exception as e:
        print(f"❌ Error conectando a Firebase: {e}")
        return

    print("\n" + "=" * 80)
    print("PARTE 1: ANÁLISIS GLOBAL DE TRANSACCIONES")
    print("=" * 80)

    print("\n🔍 Analizando colección 'transacciones'...")
    
    try:
        trans_ref = db.collection('transacciones')
        
        # Obtener muestra de transacciones
        all_transactions = list(trans_ref.limit(20).stream())
        
        print(f"📊 Total de documentos encontrados (muestra): {len(all_transactions)}")
        
        if not all_transactions:
            print("❌ No hay transacciones en la colección 'transacciones'")
            return
        
        # Análisis de estructura
        print("\n📋 ANÁLISIS DE ESTRUCTURA:")
        
        # Analizar primera transacción en detalle
        first_trans = all_transactions[0]
        first_data = first_trans.to_dict()
        
        print(f"\n🔍 Primera transacción (ID: {first_trans.id}):")
        print(f"   Campos disponibles ({len(first_data)}):")
        for campo, valor in first_data.items():
            tipo = type(valor).__name__
            valor_str = str(valor)[:50] if len(str(valor)) > 50 else str(valor)
            print(f"   - {campo}: ({tipo}) {valor_str}")
        
        # Análisis de proyecto_ids
        print("\n📊 ANÁLISIS DE PROYECTO_IDs:")
        proyecto_ids = {}
        campos_deleted = {'deleted': 0, 'activo': 0, 'sin_campo': 0}
        
        for trans_doc in all_transactions:
            trans_data = trans_doc. to_dict()
            
            # Analizar proyecto_id
            proyecto_id = trans_data.get('proyecto_id')
            if proyecto_id is not None:
                tipo = type(proyecto_id).__name__
                key = f"{proyecto_id} ({tipo})"
                proyecto_ids[key] = proyecto_ids.get(key, 0) + 1
            
            # Analizar campos de eliminación
            if 'deleted' in trans_data:
                campos_deleted['deleted'] += 1
                print(f"   - Transacción {trans_doc.id}: deleted={trans_data['deleted']}")
            if 'activo' in trans_data:
                campos_deleted['activo'] += 1
                print(f"   - Transacción {trans_doc.id}: activo={trans_data['activo']}")
            if 'deleted' not in trans_data and 'activo' not in trans_data:
                campos_deleted['sin_campo'] += 1
        
        print("\n   Resumen de proyecto_ids únicos:")
        for pid, count in proyecto_ids.items():
            print(f"   - {pid}: {count} transacciones")
        
        print("\n   Resumen de campos de eliminación:")
        print(f"   - Con campo 'deleted': {campos_deleted['deleted']}")
        print(f"   - Con campo 'activo': {campos_deleted['activo']}")
        print(f"   - Sin campos de estado: {campos_deleted['sin_campo']}")
        
    except Exception as e:
        print(f"❌ Error analizando transacciones: {e}")

    print("\n" + "=" * 80)
    print("PARTE 2: BÚSQUEDA ESPECÍFICA PROYECTO 10")
    print("=" * 80)

    print("\n🔍 Buscando transacciones del proyecto 10...")
    
    try:
        # Intentar con proyecto_id = 10 (entero)
        print("\n📝 Intento 1: proyecto_id == 10 (entero)")
        query_int = trans_ref.where('proyecto_id', '==', 10)
        trans_int = list(query_int.stream())
        print(f"   Resultado: {len(trans_int)} transacciones encontradas")
        
        if trans_int:
            for i, t in enumerate(trans_int[:3]):
                data = t.to_dict()
                print(f"   - Trans {i+1}: ID={t.id}, fecha={data.get('fecha')}, monto={data.get('monto')}")
                print(f"     deleted={data.get('deleted', 'NO_EXISTE')}, activo={data.get('activo', 'NO_EXISTE')}")
        
        # Intentar con proyecto_id = '10' (string)
        print("\n📝 Intento 2: proyecto_id == '10' (string)")
        query_str = trans_ref.where('proyecto_id', '==', '10')
        trans_str = list(query_str.stream())
        print(f"   Resultado: {len(trans_str)} transacciones encontradas")
        
        if trans_str:
            for i, t in enumerate(trans_str[:3]):
                data = t.to_dict()
                print(f"   - Trans {i+1}: ID={t.id}, fecha={data.get('fecha')}, monto={data.get('monto')}")
                
    except Exception as e:
        print(f"❌ Error en búsqueda específica: {e}")

    print("\n" + "=" * 80)
    print("PARTE 3: BÚSQUEDA PROYECTO 23AzdMPQMpmE1UHbUzhL")
    print("=" * 80)

    print("\n🔍 Buscando transacciones del proyecto '23AzdMPQMpmE1UHbUzhL'...")
    
    try:
        query_test = trans_ref.where('proyecto_id', '==', '23AzdMPQMpmE1UHbUzhL')
        trans_test = list(query_test.stream())
        print(f"   Resultado: {len(trans_test)} transacciones encontradas")
        
        if trans_test:
            print("\n   Detalles de transacciones encontradas:")
            for i, t in enumerate(trans_test[:5]):
                data = t.to_dict()
                print(f"\n   📄 Transacción {i+1} (ID: {t.id}):")
                print(f"      - fecha: {data.get('fecha')}")
                print(f"      - monto: {data.get('monto')}")
                print(f"      - descripcion: {data.get('descripcion')}")
                print(f"      - deleted: {data.get('deleted', 'NO_EXISTE')}")
                print(f"      - activo: {data.get('activo', 'NO_EXISTE')}")
                print(f"      - cuenta_id: {data.get('cuenta_id')} (tipo: {type(data.get('cuenta_id')).__name__})")
                
    except Exception as e:
        print(f"❌ Error buscando proyecto de prueba: {e}")

    print("\n" + "=" * 80)
    print("PARTE 4: VERIFICACIÓN DE SUBCOLECCIONES")
    print("=" * 80)

    print("\n🔍 Verificando si las transacciones están en subcolecciones...")
    
    try:
        # Obtener un proyecto para verificar
        proyectos_ref = db.collection('proyectos')
        proyectos = list(proyectos_ref. limit(3).stream())
        
        for proyecto_doc in proyectos:
            proyecto_id = proyecto_doc. id
            proyecto_data = proyecto_doc.to_dict()
            proyecto_nombre = proyecto_data.get('nombre', 'Sin nombre')
            
            print(f"\n📁 Proyecto: {proyecto_nombre} (ID: {proyecto_id})")
            
            # Verificar subcolección
            sub_trans_ref = db.collection('proyectos').document(proyecto_id).collection('transacciones')
            sub_trans = list(sub_trans_ref. limit(5).stream())
            
            if sub_trans:
                print(f"   ✅ Tiene {len(sub_trans)} transacciones en SUBCOLECCIÓN")
                for t in sub_trans[:2]:
                    data = t.to_dict()
                    print(f"      - ID: {t.id}, fecha: {data.get('fecha')}, monto: {data.get('monto')}")
            else:
                print(f"   ❌ NO tiene transacciones en subcolección")
                
    except Exception as e:
        print(f"❌ Error verificando subcolecciones: {e}")

    print("\n" + "=" * 80)
    print("DIAGNÓSTICO Y RECOMENDACIONES")
    print("=" * 80)
    
    print("\n🔍 DIAGNÓSTICO:")
    print("1.  Verificar si las transacciones están en la colección principal o en subcolecciones")
    print("2. Confirmar el tipo de dato de proyecto_id (int vs string)")
    print("3.  Revisar si las transacciones tienen campos 'deleted' o 'activo'")
    print("4.  Asegurar que el filtrado no está excluyendo transacciones válidas")
    
    print("\n💡 SOLUCIONES POSIBLES:")
    print("1.  Si no hay transacciones del proyecto 10, crear nuevas")
    print("2. Si las transacciones están marcadas como eliminadas, actualizar el campo")
    print("3. Si el proyecto_id es diferente tipo, ajustar las queries")
    
    print("\n✅ Diagnóstico completado")

if __name__ == "__main__":
    diagnosticar_transacciones()