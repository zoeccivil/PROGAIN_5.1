import pandas as pd
import tkinter as tk
from tkinter import filedialog
import os
import sys

def seleccionar_archivo(titulo):
    """Abre un diálogo para seleccionar archivo Excel"""
    root = tk.Tk()
    root.withdraw()  # Ocultar la ventana principal de tkinter
    ruta = filedialog.askopenfilename(
        title=titulo,
        filetypes=[("Archivos Excel", "*.xlsx *.xls")]
    )
    if not ruta:
        print(f"❌ No seleccionaste el {titulo}. Cancelando.")
        sys.exit()
    return ruta

def analizar_dataframe(df, etiqueta):
    print(f"\n{'='*60}")
    print(f"📊 REPORTE DE: {etiqueta}")
    print(f"{'='*60}")
    
    # 1. Estructura
    print(f"🔹 Dimensiones: {df.shape[0]} filas x {df.shape[1]} columnas")
    print(f"🔹 Columnas detectadas:\n   {df.columns.tolist()}")
    
    # 2. Tipos de datos generales
    print(f"\n🔹 Tipos de datos por columna (pandas dtypes):")
    print(df.dtypes)
    
    # 3. Inspección profunda de la PRIMERA FILA DE DATOS
    if not df.empty:
        primer_fila = df.iloc[0]
        print(f"\n🔹 INSPECCIÓN DE LA PRIMERA FILA REAL (Índice 0):")
        print(f"{'-'*60}")
        print(f"{'COLUMNA':<25} | {'VALOR VISUAL':<25} | {'TIPO PYTHON REAL'}")
        print(f"{'-'*60}")
        
        for col in df.columns:
            val = primer_fila[col]
            tipo = type(val).__name__
            # Formateamos el valor para que no sea muy largo en consola
            val_str = str(val)
            if len(val_str) > 22: val_str = val_str[:22] + "..."
            
            print(f"{col:<25} | {val_str:<25} | {tipo}")
            
    else:
        print("⚠️ El archivo parece estar vacío o solo tiene encabezados.")

def simulacion_hash(df, etiqueta):
    """Intenta construir el string raw para ver diferencias"""
    if df.empty: return

    print(f"\n🔍 SIMULACIÓN DE FORMATO PARA HASH ({etiqueta})")
    row = df.iloc[0]
    
    # Intentamos buscar columnas clave independientemente de mayúsculas/minúsculas
    cols_lower = {c.lower(): c for c in df.columns}
    
    # Buscamos columnas probables
    c_fecha = cols_lower.get('fecha') or cols_lower.get('date')
    c_monto = cols_lower.get('monto') or cols_lower.get('amount') or cols_lower.get('débito') or cols_lower.get('debito')
    c_det   = cols_lower.get('detalle') or cols_lower.get('descripcion') or cols_lower.get('concepto')
    
    print("   (Intentando extraer datos de columnas detectadas automáticamente...)")
    
    val_fecha = row[c_fecha] if c_fecha else "NO_ENCONTRADA"
    val_monto = row[c_monto] if c_monto else "NO_ENCONTRADA"
    val_det   = row[c_det] if c_det else "NO_ENCONTRADA"
    
    print(f"   📅 Fecha raw: '{val_fecha}' (Tipo: {type(val_fecha).__name__})")
    print(f"   💰 Monto raw: '{val_monto}' (Tipo: {type(val_monto).__name__})")
    print(f"   📝 Detalle raw: '{val_det}'")
    
    # Alerta específica para tu problema
    if isinstance(val_fecha, str):
        print(f"   ⚠️ ALERTA: La fecha es TEXTO. Tu código `.strftime` fallará o dará error.")
    if isinstance(val_monto, str):
        print(f"   ⚠️ ALERTA: El monto es TEXTO. Si tiene ',' o '$', `float()` fallará.")

def main():
    print("🚀 Iniciando auditoría de archivos Excel...")
    
    # 1. Seleccionar Archivo Bueno
    ruta_ok = seleccionar_archivo("SELECCIONA EL ARCHIVO 1 (EL QUE FUNCIONA)")
    print(f"✅ Archivo 1 seleccionado: {os.path.basename(ruta_ok)}")
    
    # 2. Seleccionar Archivo Malo
    ruta_fail = seleccionar_archivo("SELECCIONA EL ARCHIVO 2 (EL NUEVO/FALLA)")
    print(f"✅ Archivo 2 seleccionado: {os.path.basename(ruta_fail)}")
    
    # Cargar DataFrames
    try:
        df_ok = pd.read_excel(ruta_ok)
        df_fail = pd.read_excel(ruta_fail)
    except Exception as e:
        print(f"\n❌ Error crítico leyendo los Excel: {e}")
        return

    # Ejecutar Análisis
    analizar_dataframe(df_ok, "ARCHIVO 1 (OK)")
    simulacion_hash(df_ok, "ARCHIVO 1")
    
    analizar_dataframe(df_fail, "ARCHIVO 2 (FALLA)")
    simulacion_hash(df_fail, "ARCHIVO 2")

    print(f"\n{'='*60}")
    print("🏁 ANÁLISIS COMPLETADO")
    print("Copia los resultados de arriba y compártelos para ajustar tu código.")

if __name__ == "__main__":
    main()