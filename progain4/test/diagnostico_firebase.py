import sys
import os
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import tkinter as tk
from tkinter import filedialog

# Ajustar path para importar módulos de progain4 si fuera necesario
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def diagnosticar():
    print("--- INICIANDO DIAGNÓSTICO FIREBASE ---")
    
    # 1. Buscar Credenciales con File Dialog
    print("⏳ Abriendo ventana para seleccionar credenciales...")
    
    # Inicializar una ventana oculta de tkinter para el diálogo
    root = tk.Tk()
    root.withdraw() # Ocultar la ventana principal
    
    cred_path = filedialog.askopenfilename(
        title="Selecciona tu archivo serviceAccountKey.json",
        filetypes=[("Archivos JSON", "*.json"), ("Todos los archivos", "*.*")],
        initialdir=os.getcwd() # Empezar en el directorio actual
    )
    
    root.destroy() # Limpiar recursos de tkinter

    if not cred_path:
        print("❌ Operación cancelada: No se seleccionó ningún archivo.")
        return

    print(f"📂 Archivo seleccionado: {cred_path}")

    # 2. Inicializar Firebase
    try:
        cred = credentials.Certificate(cred_path)
        # Verificar si ya existe una app inicializada para no duplicar
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
        else:
            # Si ya existe, forzamos usar la nueva credencial (útil en entornos de test)
            # Nota: firebase_admin suele ser singleton, esto es un manejo básico
            print("ℹ️ Firebase ya estaba inicializado, usando instancia existente.")
            
        db = firestore.client()
        print("✅ Conexión a Firestore exitosa.")
    except Exception as e:
        print(f"❌ Error conectando a Firebase: {e}")
        return

    # 3. Listar Proyectos (Colección 'proyectos')
    print("🔍 Consultando colección 'proyectos'...")
    proyectos_ref = db.collection('proyectos')
    proyectos = list(proyectos_ref.stream())
    
    if not proyectos:
        print("⚠️ No se encontraron documentos en la colección 'proyectos'.")
        return

    print(f"✅ Se encontraron {len(proyectos)} proyectos.")
    
    # Tomamos el primer proyecto para analizar
    primer_proyecto = proyectos[0]
    pid = primer_proyecto.id
    pdata = primer_proyecto.to_dict()
    print(f"\n--- ANÁLISIS DEL PROYECTO: {pdata.get('nombre', pid)} (ID: {pid}) ---")

    # 4. Analizar Transacciones (Subcolección)
    transacciones_ref = proyectos_ref.document(pid).collection('transacciones')
    
    # Traer las últimas 3 transacciones
    print("🔍 Consultando últimas transacciones...")
    docs = list(transacciones_ref.limit(3).stream())
    
    if not docs:
        print("⚠️ Este proyecto no tiene transacciones o la subcolección se llama diferente.")
    else:
        print(f"✅ Se encontraron transacciones (mostrando muestra de {len(docs)}):")
        for doc in docs:
            data = doc.to_dict()
            print(f"\n📄 ID Transacción: {doc.id}")
            print(f"   Campos encontrados ({len(data)}):")
            for k, v in data.items():
                tipo = type(v).__name__
                # Manejo seguro para imprimir valores
                valor_str = str(v)
                valor_muestra = (valor_str[:75] + '..') if len(valor_str) > 75 else valor_str
                print(f"   - {k}: ({tipo}) {valor_muestra}")
                
            # Verificación específica para filtros
            print("   --- Verificación de campos clave para filtros ---")
            print(f"   ¿Tiene 'fecha'? -> {'fecha' in data} (Tipo: {type(data.get('fecha')).__name__})")
            print(f"   ¿Tiene 'date'?  -> {'date' in data}")
            print(f"   ¿Tiene 'cuenta_id'?  -> {'cuenta_id' in data}")
            print(f"   ¿Tiene 'account_id'? -> {'account_id' in data}")

    print("\n--- FIN DEL DIAGNÓSTICO ---")

if __name__ == "__main__":
    diagnosticar()