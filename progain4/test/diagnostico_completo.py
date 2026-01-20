"""
Script de diagnóstico COMPLETO para encontrar dónde están las transacciones
"""

import sys
import os
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import tkinter as tk
from tkinter import filedialog

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def diagnosticar_completo():
    print("=" * 80)
    print("DIAGNÓSTICO COMPLETO DE FIREBASE - BÚSQUEDA DE TRANSACCIONES")
    print("=" * 80)
    
    # 1. Buscar Credenciales
    print("\n⏳ Abriendo ventana para seleccionar credenciales...")
    
    root = tk.Tk()
    root.withdraw()
    
    cred_path = filedialog. askopenfilename(
        title="Selecciona tu archivo de credenciales Firebase JSON",
        filetypes=[("Archivos JSON", "*.json"), ("Todos los archivos", "*.*")],
        initialdir=os. getcwd()
    )
    
    root.destroy()

    if not cred_path:
        print("❌ Operación cancelada.")
        return

    print(f"📂 Archivo seleccionado: {cred_path}")

    # 2. Inicializar Firebase
    try:
        cred = credentials. Certificate(cred_path)
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
        else:
            print("ℹ️ Firebase ya inicializado.")
            
        db = firestore.client()
        print("✅ Conexión exitosa.")
    except Exception as e:
        print(f"❌ Error: {e}")
        return

    print("\n" + "=" * 80)
    print("PARTE 1: BÚSQUEDA EN COLECCIONES PRINCIPALES")
    print("=" * 80)

    # Listar TODAS las colecciones de nivel superior
    print("\n📋 Listando TODAS las colecciones de nivel superior:")
    try:
        collections = db.collections()
        collection_names = []
        for collection in collections:
            name = collection.id
            collection_names.append(name)
            # Contar documentos
            docs = list(collection.limit(1).stream())
            print(f"   - {name}: {'✅ Tiene documentos' if docs else '❌ Vacía'}")
            
            # Si el nombre sugiere transacciones, investigar más
            if 'trans' in name.lower():
                sample_docs = list(collection.limit(3).stream())
                print(f"     🔍 Encontrada colección relacionada: {len(sample_docs)} documentos (muestra)")
                for doc in sample_docs[:1]:
                    data = doc.to_dict()
                    print(f"     Ejemplo - ID: {doc.id}")
                    print(f"     Campos: {list(data.keys())[:10]}")
        
        print(f"\n📊 Total de colecciones encontradas: {len(collection_names)}")
        
    except Exception as e:
        print(f"❌ Error listando colecciones: {e}")

    print("\n" + "=" * 80)
    print("PARTE 2: BÚSQUEDA EN SUBCOLECCIONES DE PROYECTOS")
    print("=" * 80)

    print("\n🔍 Buscando transacciones en subcolecciones de cada proyecto...")
    
    try:
        proyectos_ref = db.collection('proyectos')
        proyectos = list(proyectos_ref.stream())
        
        print(f"📁 Analizando {len(proyectos)} proyectos...")
        
        transacciones_encontradas = {}
        
        for proyecto_doc in proyectos:
            proyecto_id = proyecto_doc. id
            proyecto_data = proyecto_doc.to_dict()
            proyecto_nombre = proyecto_data.get('nombre', 'Sin nombre')
            
            # Buscar transacciones en subcolección
            trans_subcol_ref = db.collection('proyectos').document(proyecto_id).collection('transacciones')
            trans_subcol = list(trans_subcol_ref.limit(100).stream())
            
            if trans_subcol:
                transacciones_encontradas[proyecto_id] = {
                    'nombre': proyecto_nombre,
                    'count': len(trans_subcol),
                    'samples': trans_subcol[:3]
                }
                print(f"\n✅ PROYECTO: {proyecto_nombre} (ID: {proyecto_id})")
                print(f"   - Transacciones en subcolección: {len(trans_subcol)}")
                
                # Mostrar ejemplos
                for i, t in enumerate(trans_subcol[:2]):
                    data = t. to_dict()
                    print(f"   - Ejemplo {i+1}: fecha={data.get('fecha')}, monto={data.get('monto')}")
        
        if not transacciones_encontradas:
            print("\n❌ No se encontraron transacciones en ninguna subcolección")
        else:
            print(f"\n✅ Se encontraron transacciones en {len(transacciones_encontradas)} proyectos")
            
    except Exception as e:
        print(f"❌ Error buscando en subcolecciones: {e}")

    print("\n" + "=" * 80)
    print("PARTE 3: BÚSQUEDA ESPECÍFICA PROYECTO 10 (FEDASA)")
    print("=" * 80)

    print("\n🔍 Buscando específicamente el proyecto 10...")
    
    try:
        # Buscar el proyecto 10
        proyecto_10 = db.collection('proyectos').document('10'). get()
        
        if proyecto_10.exists:
            proyecto_data = proyecto_10.to_dict()
            print(f"✅ Proyecto 10 encontrado: {proyecto_data.get('nombre', 'Sin nombre')}")
            
            # Buscar en subcolección
            trans_ref = db.collection('proyectos').document('10').collection('transacciones')
            transacciones = list(trans_ref.stream())
            
            print(f"📊 Transacciones en subcolección: {len(transacciones)}")
            
            if transacciones:
                print("\nPrimeras 5 transacciones:")
                for i, t in enumerate(transacciones[:5]):
                    data = t.to_dict()
                    print(f"{i+1}. ID: {t.id}")
                    print(f"   - fecha: {data.get('fecha')}")
                    print(f"   - monto: {data. get('monto')}")
                    print(f"   - descripcion: {data.get('descripcion')}")
                    print(f"   - proyecto_id en doc: {data.get('proyecto_id', 'NO TIENE')}")
        else:
            print("❌ Proyecto 10 no encontrado como documento")
            
    except Exception as e:
        print(f"❌ Error: {e}")

    print("\n" + "=" * 80)
    print("PARTE 4: ANÁLISIS DE ESTRUCTURA DE DATOS")
    print("=" * 80)

    # Si encontramos transacciones, analizar su estructura
    if transacciones_encontradas:
        print("\n📊 Analizando estructura de transacciones encontradas...")
        
        for proyecto_id, info in list(transacciones_encontradas. items())[:1]:  # Analizar el primero
            print(f"\nProyecto: {info['nombre']}")
            
            if info['samples']:
                trans_sample = info['samples'][0]
                data = trans_sample.to_dict()
                
                print(f"\n📄 Estructura de transacción (ID: {trans_sample.id}):")
                print("Campos disponibles:")
                for campo, valor in data.items():
                    tipo = type(valor).__name__
                    valor_str = str(valor)[:50] if len(str(valor)) > 50 else str(valor)
                    print(f"   - {campo}: ({tipo}) {valor_str}")

    print("\n" + "=" * 80)
    print("CONCLUSIONES Y RECOMENDACIONES")
    print("=" * 80)
    
    print("\n📋 RESUMEN:")
    print("1. La colección principal 'transacciones' está VACÍA")
    print("2. Las transacciones están en SUBCOLECCIONES: proyectos/{id}/transacciones")
    print("3. Tu código está buscando en el lugar equivocado")
    
    print("\n🔧 SOLUCIÓN NECESARIA:")
    print("Modificar firebase_client.py para que busque transacciones en:")
    print("   db.collection('proyectos'). document(proyecto_id).collection('transacciones')")
    print("en lugar de:")
    print("   db.collection('transacciones')")
    
    print("\n✅ Diagnóstico completado")

if __name__ == "__main__":
    diagnosticar_completo()