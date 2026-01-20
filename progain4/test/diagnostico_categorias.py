"""
Script de diagnóstico para entender la estructura de categorías en Firebase
"""

import sys
import os
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import tkinter as tk
from tkinter import filedialog
import json

# Ajustar path para importar módulos de progain4 si fuera necesario
sys.path. append(os.path.dirname(os. path.dirname(os.path.abspath(__file__))))

def diagnosticar_categorias():
    print("=" * 80)
    print("DIAGNÓSTICO DE ESTRUCTURA DE CATEGORÍAS EN FIREBASE")
    print("=" * 80)
    
    # 1. Buscar Credenciales con File Dialog
    print("\n⏳ Abriendo ventana para seleccionar credenciales...")
    
    # Inicializar una ventana oculta de tkinter para el diálogo
    root = tk. Tk()
    root.withdraw()
    
    cred_path = filedialog. askopenfilename(
        title="Selecciona tu archivo de credenciales Firebase JSON",
        filetypes=[("Archivos JSON", "*.json"), ("Todos los archivos", "*.*")],
        initialdir=os.getcwd()
    )
    
    root. destroy()

    if not cred_path:
        print("❌ Operación cancelada: No se seleccionó ningún archivo.")
        return

    print(f"📂 Archivo seleccionado: {cred_path}")

    # 2. Inicializar Firebase
    try:
        cred = credentials.Certificate(cred_path)
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
    print("PARTE 1: ANÁLISIS DE COLECCIONES PRINCIPALES")
    print("=" * 80)

    # 3. Verificar si existen las colecciones principales
    print("\n🔍 Buscando colecciones principales...")
    
    # Categorías globales
    print("\n📁 COLECCIÓN 'categorias' (Catálogo Global):")
    try:
        categorias_ref = db.collection('categorias')
        categorias = list(categorias_ref. limit(3).stream())
        print(f"   ✅ Encontradas {len(categorias)} categorías (mostrando máx 3)")
        if categorias:
            for cat_doc in categorias:
                cat_data = cat_doc.to_dict()
                print(f"   - ID: {cat_doc.id} | Nombre: {cat_data.get('nombre', 'Sin nombre')}")
                print(f"     Campos: {list(cat_data.keys())}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Subcategorías globales
    print("\n📁 COLECCIÓN 'subcategorias' (Catálogo Global):")
    try:
        subcategorias_ref = db. collection('subcategorias')
        subcategorias = list(subcategorias_ref.limit(3). stream())
        print(f"   ✅ Encontradas {len(subcategorias)} subcategorías (mostrando máx 3)")
        if subcategorias:
            for sub_doc in subcategorias:
                sub_data = sub_doc.to_dict()
                print(f"   - ID: {sub_doc.id} | Nombre: {sub_data.get('nombre', 'Sin nombre')}")
                print(f"     Campos: {list(sub_data.keys())}")
                print(f"     categoria_id: {sub_data. get('categoria_id', 'No especificado')}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    print("\n" + "=" * 80)
    print("PARTE 2: ANÁLISIS DE ESTRUCTURA DE PROYECTOS")
    print("=" * 80)

    # 4. Listar Proyectos
    print("\n🔍 Consultando colección 'proyectos'...")
    try:
        proyectos_ref = db.collection('proyectos')
        proyectos = list(proyectos_ref.stream())
        
        if not proyectos:
            print("⚠️ No se encontraron documentos en la colección 'proyectos'.")
            return

        print(f"✅ Se encontraron {len(proyectos)} proyectos.\n")
        
        # Analizar los primeros 3 proyectos o el que tenga el ID específico
        proyectos_a_analizar = []
        
        # Buscar proyecto específico si existe
        proyecto_especifico = None
        for p in proyectos:
            if p.id == '23AzdMPQMpmE1UHbUzhL':  # El ID de tu proyecto de prueba
                proyecto_especifico = p
                break
        
        if proyecto_especifico:
            proyectos_a_analizar = [proyecto_especifico]
            print("📍 Encontrado proyecto específico '23AzdMPQMpmE1UHbUzhL'")
        else:
            proyectos_a_analizar = proyectos[:3]
            print(f"📋 Analizando los primeros {len(proyectos_a_analizar)} proyectos")
        
        for proyecto_doc in proyectos_a_analizar:
            proyecto_id = proyecto_doc.id
            proyecto_data = proyecto_doc. to_dict()
            
            print("\n" + "-" * 60)
            print(f"📌 PROYECTO: {proyecto_data.get('nombre', 'Sin nombre')}")
            print(f"   ID: {proyecto_id}")
            print(f"   Tipo de ID: {'Numérico' if proyecto_id. isdigit() else 'String/Firestore'}")
            
            # Analizar estructura del documento
            print(f"\n   📊 ESTRUCTURA DEL DOCUMENTO:")
            print(f"   Total de campos: {len(proyecto_data)}")
            print(f"   Campos disponibles:")
            
            # Listar todos los campos
            for campo, valor in proyecto_data.items():
                tipo = type(valor).__name__
                
                # Formatear el valor para mostrar
                if isinstance(valor, list):
                    valor_str = f"Lista con {len(valor)} elementos"
                    if len(valor) > 0 and len(valor) <= 5:
                        valor_str += f": {valor}"
                elif isinstance(valor, dict):
                    valor_str = f"Diccionario con {len(valor)} claves"
                    if len(valor) <= 3:
                        valor_str += f": {list(valor.keys())}"
                else:
                    valor_str = str(valor)
                    if len(valor_str) > 50:
                        valor_str = valor_str[:50] + "..."
                
                print(f"     - {campo}: ({tipo}) {valor_str}")
            
            # Buscar específicamente campos relacionados con categorías
            print(f"\n   🔎 CAMPOS RELACIONADOS CON CATEGORÍAS:")
            campos_categorias = [
                'categorias', 'categories', 'categorias_asignadas', 'categories_assigned',
                'project_categories', 'selected_categories', 'categoria_ids',
                'subcategorias', 'subcategories', 'subcategorias_asignadas',
                'project_subcategories', 'selected_subcategories', 'subcategoria_ids'
            ]
            
            campos_encontrados = []
            for campo in campos_categorias:
                if campo in proyecto_data:
                    campos_encontrados. append(campo)
                    valor = proyecto_data[campo]
                    print(f"     ✅ '{campo}' encontrado:")
                    print(f"        Tipo: {type(valor).__name__}")
                    if isinstance(valor, list):
                        print(f"        Contenido: {valor[:5] if len(valor) > 5 else valor}")
                    elif isinstance(valor, dict):
                        print(f"        Claves: {list(valor.keys())[:5]}")
                    else:
                        print(f"        Valor: {valor}")
            
            if not campos_encontrados:
                print("     ⚠️ No se encontraron campos obvios de categorías")
                print("     📝 Posibles campos candidatos:")
                for campo, valor in proyecto_data.items():
                    if isinstance(valor, (list, dict)) and 'categ' in campo.lower():
                        print(f"        - {campo}: {type(valor).__name__}")

    except Exception as e:
        print(f"❌ Error analizando proyectos: {e}")

    print("\n" + "=" * 80)
    print("PARTE 3: ANÁLISIS DE TRANSACCIONES")
    print("=" * 80)

    # 5. Analizar estructura de transacciones
    if proyectos_a_analizar:
        proyecto = proyectos_a_analizar[0]
        proyecto_id = proyecto.id
        proyecto_data = proyecto.to_dict()
        
        print(f"\n🔍 Analizando transacciones del proyecto: {proyecto_data.get('nombre', proyecto_id)}")
        
        # Intentar diferentes ubicaciones de transacciones
        ubicaciones_transacciones = [
            ('transacciones', f"proyectos/{proyecto_id}/transacciones"),  # Subcolección
            ('transacciones', "transacciones")  # Colección principal con filtro
        ]
        
        for nombre, path in ubicaciones_transacciones:
            print(f"\n   📂 Intentando ubicación: {path}")
            try:
                if '/' in path:
                    # Es una subcolección
                    trans_ref = db.collection('proyectos').document(proyecto_id).collection('transacciones')
                    transacciones = list(trans_ref.limit(2).stream())
                else:
                    # Es una colección principal, filtrar por proyecto_id
                    trans_ref = db.collection('transacciones')
                    
                    # Intentar con proyecto_id como string
                    query = trans_ref.where('proyecto_id', '==', proyecto_id). limit(2)
                    transacciones = list(query.stream())
                    
                    if not transacciones:
                        # Intentar con proyecto_id como número si es posible
                        if proyecto_id.isdigit():
                            query = trans_ref. where('proyecto_id', '==', int(proyecto_id)).limit(2)
                            transacciones = list(query.stream())
                
                if transacciones:
                    print(f"   ✅ Encontradas {len(transacciones)} transacciones en esta ubicación")
                    
                    # Analizar primera transacción
                    trans_doc = transacciones[0]
                    trans_data = trans_doc.to_dict()
                    
                    print(f"\n   📄 Análisis de transacción ejemplo (ID: {trans_doc.id}):")
                    
                    # Campos relacionados con categorías
                    campos_cat_trans = ['categoria_id', 'categoriaNombre', 'category_id', 'category_name',
                                       'subcategoria_id', 'subcategoriaNombre', 'subcategory_id', 'subcategory_name']
                    
                    print("   Campos de categorización encontrados:")
                    for campo in campos_cat_trans:
                        if campo in trans_data:
                            valor = trans_data[campo]
                            print(f"     - {campo}: {valor} (tipo: {type(valor).__name__})")
                    
                    # Verificar proyecto_id en la transacción
                    if 'proyecto_id' in trans_data:
                        pid_trans = trans_data['proyecto_id']
                        print(f"\n   📌 proyecto_id en transacción: {pid_trans} (tipo: {type(pid_trans).__name__})")
                    
                    break
                else:
                    print(f"   ⚠️ No hay transacciones en esta ubicación")
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")

    print("\n" + "=" * 80)
    print("RESUMEN Y RECOMENDACIONES")
    print("=" * 80)
    
    print("\n📋 RESUMEN DEL DIAGNÓSTICO:")
    print("1. Las categorías globales están en la colección 'categorias'")
    print("2. Las subcategorías globales están en la colección 'subcategorias'")
    print("3. Los proyectos deben tener un campo que indique qué categorías tienen asignadas")
    print("4. Las transacciones pueden estar en una colección principal o como subcolección")
    
    print("\n💡 RECOMENDACIÓN:")
    print("Basado en este análisis, el campo donde se guardan las categorías del proyecto es:")
    if campos_encontrados:
        print(f"   ➡️ '{campos_encontrados[0]}' en el documento del proyecto")
    else:
        print("   ⚠️ No se encontró un campo obvio, puede necesitar implementarse")
    
    print("\n✅ Diagnóstico completado")

if __name__ == "__main__":
    diagnosticar_categorias()