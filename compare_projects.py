"""
Script para comparar la estructura de datos entre dos proyectos de Firebase.
Usa file dialog para seleccionar las credenciales. 
"""

import json
import firebase_admin
from firebase_admin import credentials, firestore
from tkinter import Tk, filedialog
from typing import Dict, Any, List
from collections import defaultdict


def select_credentials_file():
    """Abre un file dialog para seleccionar el archivo de credenciales."""
    root = Tk()
    root.withdraw()  # Ocultar ventana principal
    root.attributes('-topmost', True)  # Traer al frente
    
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


def get_project_info(db, project_id: str) -> Dict[str, Any]:
    """Obtiene información completa de un proyecto."""
    info = {
        "proyecto_id": project_id,
        "documento_proyecto": None,
        "cuentas":  [],
        "transacciones": [],
        "transacciones_tipos": defaultdict(int),
        "transacciones_con_cuenta_id": 0,
        "tipos_cuenta_id": defaultdict(int),
        "transacciones_activas": 0,
        "transacciones_eliminadas": 0,
    }
    
    try: 
        # 1. Obtener documento del proyecto
        proyecto_ref = db.collection("proyectos").document(project_id)
        proyecto_doc = proyecto_ref.get()
        
        if proyecto_doc.exists:
            info["documento_proyecto"] = proyecto_doc.to_dict()
            print(f"\n📁 Proyecto:  {info['documento_proyecto']. get('nombre', 'Sin nombre')}")
        else:
            print(f"\n❌ Proyecto {project_id} NO EXISTE")
            return info
        
        # 2. Obtener cuentas del proyecto
        cuentas_ref = proyecto_ref.collection("cuentas_proyecto")
        cuentas_docs = list(cuentas_ref.stream())
        
        for cuenta_doc in cuentas_docs:
            cuenta_data = cuenta_doc.to_dict()
            cuenta_data["_doc_id"] = cuenta_doc. id
            info["cuentas"].append(cuenta_data)
        
        print(f"💳 Cuentas encontradas: {len(info['cuentas'])}")
        
        # 3. Obtener transacciones
        trans_ref = proyecto_ref.collection("transacciones")
        trans_docs = list(trans_ref.stream())
        
        for trans_doc in trans_docs: 
            trans_data = trans_doc.to_dict()
            trans_data["_doc_id"] = trans_doc.id
            info["transacciones"].append(trans_data)
            
            # Analizar tipo
            tipo = trans_data.get("tipo", "Sin tipo")
            info["transacciones_tipos"][tipo] += 1
            
            # Analizar cuenta_id
            cuenta_id = trans_data.get("cuenta_id")
            if cuenta_id is not None:
                info["transacciones_con_cuenta_id"] += 1
                tipo_cuenta = type(cuenta_id).__name__
                info["tipos_cuenta_id"][tipo_cuenta] += 1
            
            # Analizar estado
            activo = trans_data.get("activo", True)
            eliminado = trans_data.get("eliminado", False)
            
            if not activo or eliminado:
                info["transacciones_eliminadas"] += 1
            else:
                info["transacciones_activas"] += 1
        
        print(f"📊 Transacciones encontradas: {len(info['transacciones'])}")
        print(f"   ✅ Activas: {info['transacciones_activas']}")
        print(f"   ❌ Eliminadas/Inactivas: {info['transacciones_eliminadas']}")
        
    except Exception as e:
        print(f"❌ Error obteniendo información del proyecto {project_id}: {e}")
    
    return info


def print_comparison(info1: Dict, info2: Dict):
    """Imprime una comparación detallada entre dos proyectos."""
    
    print("\n" + "="*80)
    print("COMPARACIÓN DE PROYECTOS")
    print("="*80)
    
    # Información básica
    print(f"\n{'CONCEPTO':<40} {'PROYECTO 1':<20} {'PROYECTO 2':<20}")
    print("-"*80)
    
    nombre1 = info1.get("documento_proyecto", {}).get("nombre", "N/A") if info1.get("documento_proyecto") else "N/A"
    nombre2 = info2.get("documento_proyecto", {}).get("nombre", "N/A") if info2.get("documento_proyecto") else "N/A"
    
    print(f"{'Nombre':<40} {nombre1:<20} {nombre2:<20}")
    print(f"{'ID':<40} {info1['proyecto_id']:<20} {info2['proyecto_id']:<20}")
    print(f"{'Número de cuentas':<40} {len(info1['cuentas']):<20} {len(info2['cuentas']):<20}")
    print(f"{'Total transacciones':<40} {len(info1['transacciones']):<20} {len(info2['transacciones']):<20}")
    print(f"{'Transacciones activas':<40} {info1['transacciones_activas']:<20} {info2['transacciones_activas']:<20}")
    print(f"{'Transacciones eliminadas':<40} {info1['transacciones_eliminadas']:<20} {info2['transacciones_eliminadas']:<20}")
    
    # Tipos de transacciones
    print(f"\n{'TIPOS DE TRANSACCIONES':<40} {'PROYECTO 1':<20} {'PROYECTO 2': <20}")
    print("-"*80)
    
    todos_tipos = set(info1["transacciones_tipos"].keys()) | set(info2["transacciones_tipos"].keys())
    for tipo in sorted(todos_tipos):
        count1 = info1["transacciones_tipos"]. get(tipo, 0)
        count2 = info2["transacciones_tipos"].get(tipo, 0)
        print(f"{tipo:<40} {count1:<20} {count2:<20}")
    
    # Tipos de cuenta_id
    print(f"\n{'TIPOS DE CUENTA_ID':<40} {'PROYECTO 1':<20} {'PROYECTO 2':<20}")
    print("-"*80)
    
    todos_tipos_cta = set(info1["tipos_cuenta_id"].keys()) | set(info2["tipos_cuenta_id"].keys())
    for tipo in sorted(todos_tipos_cta):
        count1 = info1["tipos_cuenta_id"]. get(tipo, 0)
        count2 = info2["tipos_cuenta_id"].get(tipo, 0)
        marca1 = "⚠️" if tipo == "str" else ""
        marca2 = "⚠️" if tipo == "str" else ""
        print(f"{tipo:<40} {count1:<20} {marca1} {count2:<20} {marca2}")
    
    # Detalles de cuentas
    print(f"\n{'DETALLES DE CUENTAS - PROYECTO 1'}")
    print("-"*80)
    for cuenta in info1["cuentas"]:
        cuenta_id = cuenta. get("cuenta_id", "N/A")
        nombre = cuenta.get("nombre", "Sin nombre")
        tipo_id = type(cuenta_id).__name__
        print(f"  ID: {cuenta_id} ({tipo_id}) - {nombre}")
    
    print(f"\n{'DETALLES DE CUENTAS - PROYECTO 2'}")
    print("-"*80)
    for cuenta in info2["cuentas"]:
        cuenta_id = cuenta.get("cuenta_id", "N/A")
        nombre = cuenta.get("nombre", "Sin nombre")
        tipo_id = type(cuenta_id).__name__
        print(f"  ID: {cuenta_id} ({tipo_id}) - {nombre}")
    
    # Muestra de transacciones
    print(f"\n{'MUESTRA DE TRANSACCIONES (primeras 3) - PROYECTO 1'}")
    print("-"*80)
    for i, trans in enumerate(info1["transacciones"][:3]):
        print(f"\nTransacción {i+1}:")
        print(f"  ID Doc: {trans.get('_doc_id')}")
        print(f"  Tipo: {trans.get('tipo')}")
        print(f"  Cuenta ID: {trans.get('cuenta_id')} (tipo: {type(trans.get('cuenta_id')).__name__})")
        print(f"  Categoría ID: {trans.get('categoria_id')} (tipo: {type(trans.get('categoria_id')).__name__})")
        print(f"  Fecha: {trans.get('fecha')}")
        print(f"  Monto: {trans.get('monto')}")
        print(f"  Activo: {trans.get('activo', True)}")
        print(f"  Eliminado: {trans. get('eliminado', False)}")
    
    print(f"\n{'MUESTRA DE TRANSACCIONES (primeras 3) - PROYECTO 2'}")
    print("-"*80)
    for i, trans in enumerate(info2["transacciones"][:3]):
        print(f"\nTransacción {i+1}:")
        print(f"  ID Doc: {trans.get('_doc_id')}")
        print(f"  Tipo: {trans.get('tipo')}")
        print(f"  Cuenta ID: {trans.get('cuenta_id')} (tipo: {type(trans.get('cuenta_id')).__name__})")
        print(f"  Categoría ID: {trans.get('categoria_id')} (tipo: {type(trans.get('categoria_id')).__name__})")
        print(f"  Fecha: {trans.get('fecha')}")
        print(f"  Monto: {trans. get('monto')}")
        print(f"  Activo: {trans.get('activo', True)}")
        print(f"  Eliminado: {trans.get('eliminado', False)}")


def main():
    """Función principal."""
    print("="*80)
    print("COMPARADOR DE PROYECTOS FIREBASE - PROGRAIN 5.0")
    print("="*80)
    
    # Seleccionar credenciales
    print("\n📂 Selecciona el archivo de credenciales de Firebase...")
    cred_path = select_credentials_file()
    
    if not cred_path: 
        print("❌ No se seleccionó ningún archivo.  Saliendo...")
        return
    
    print(f"✅ Archivo seleccionado: {cred_path}")
    
    # Inicializar Firebase
    db = initialize_firebase(cred_path)
    if not db:
        return
    
    # IDs de proyectos a comparar
    project_id_nuevo = "6xrAnYzdu2Ar639Udtow"  # Proyecto nuevo (con problemas)
    project_id_viejo = "10"  # Proyecto viejo (funciona)
    
    print(f"\n🔍 Analizando proyecto NUEVO:  {project_id_nuevo}")
    info_nuevo = get_project_info(db, project_id_nuevo)
    
    print(f"\n🔍 Analizando proyecto VIEJO: {project_id_viejo}")
    info_viejo = get_project_info(db, project_id_viejo)
    
    # Comparar
    print_comparison(info_nuevo, info_viejo)
    
    print("\n" + "="*80)
    print("ANÁLISIS COMPLETADO")
    print("="*80)


if __name__ == "__main__":
    main()