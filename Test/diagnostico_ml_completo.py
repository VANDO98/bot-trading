import sys
import os
import joblib
import pandas as pd
import numpy as np
from colorama import Fore, Style, init

# Inicializar colores
init(autoreset=True)

# Ajustar ruta para importar módulos
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)

from Machine_Learning.Core.FeatureEngineering import FeatureEngineering

def diagnostico_ml():
    print(Fore.YELLOW + "🔍 INICIANDO DIAGNÓSTICO FORENSE DE MACHINE LEARNING")
    print("=======================================================")

    # 1. CARGAR MODELO Y VER SU ADN
    ruta_modelo = os.path.join(root_dir, "Machine_Learning", "Models", "modelo_rf_trading.joblib")
    
    if not os.path.exists(ruta_modelo):
        print(Fore.RED + "❌ CRÍTICO: No existe el archivo .joblib")
        return

    try:
        modelo = joblib.load(ruta_modelo)
        print(Fore.GREEN + "✅ Modelo cargado correctamente.")
        
        # Obtener nombres de features esperados (si el modelo lo soporta)
        if hasattr(modelo, "feature_names_in_"):
            features_modelo = list(modelo.feature_names_in_)
            print(Fore.CYAN + f"🧠 El Modelo fue entrenado con {len(features_modelo)} columnas:")
            print(features_modelo)
        else:
            print(Fore.RED + "⚠️ El modelo no tiene guardados los nombres de las features (versión vieja de scikit-learn?).")
            return
            
    except Exception as e:
        print(Fore.RED + f"❌ Error leyendo el modelo: {e}")
        return

    # 2. SIMULAR DATOS DE ENTRADA (Como llegan del WebSocket)
    print(Fore.YELLOW + "\n🧪 Generando datos simulados (Input del Bot)...")
    
    # Simulamos 200 velas para que se calculen los indicadores
    datos_mock = {
        'timestamp': pd.date_range(start='2024-01-01', periods=200, freq='5min'),
        'open': np.random.uniform(100, 200, 200),
        'high': np.random.uniform(100, 200, 200),
        'low': np.random.uniform(100, 200, 200),
        'close': np.random.uniform(100, 200, 200),
        'volume': np.random.uniform(1000, 5000, 200)
    }
    df_raw = pd.DataFrame(datos_mock)
    
    # 3. EJECUTAR TU FEATURE ENGINEERING
    print(Fore.YELLOW + "⚙️ Ejecutando FeatureEngineering actual...")
    fe = FeatureEngineering()
    try:
        df_procesado = fe.aplicar_features(df_raw.copy())
        print(Fore.GREEN + "✅ Indicadores calculados.")
    except Exception as e:
        print(Fore.RED + f"❌ FeatureEngineering falló: {e}")
        return

    # 4. COMPARACIÓN FINAL (LA VERDAD)
    print(Fore.YELLOW + "\n⚖️ COMPARATIVA: MODELO vs CÓDIGO ACTUAL")
    
    # Tomamos la última fila y filtramos columnas basura
    ultima_fila = df_procesado.iloc[[-1]]
    cols_codigo = list(ultima_fila.columns)
    
    # Normalización para reporte (ignoramos mayúsculas/minúsculas para ver si es solo eso)
    faltantes = [f for f in features_modelo if f not in cols_codigo]
    sobrantes = [c for c in cols_codigo if c not in features_modelo and c not in ['timestamp', 'target', 'TARGET']]
    
    if not faltantes:
        print(Fore.GREEN + "🎉 ¡PERFECTO! Tu código genera exactamente lo que el modelo pide.")
        
        # Prueba de predicción real
        try:
            # Filtramos solo las columnas que el modelo quiere
            X_test = ultima_fila[features_modelo]
            pred = modelo.predict_proba(X_test)
            print(Fore.GREEN + f"✅ Prueba de Predicción exitosa: {pred}")
        except Exception as e:
            print(Fore.RED + f"❌ Error en predicción final: {e}")
            
    else:
        print(Fore.RED + f"⛔ ERROR: Faltan {len(faltantes)} columnas que el modelo NECESITA.")
        print(Fore.RED + "🔴 FALTAN (El modelo las pide):")
        print(faltantes)
        
        print(Fore.YELLOW + "🟡 SOBRAN (Tu código las genera pero el modelo no las conoce):")
        print(sobrantes)
        
        print(Fore.WHITE + "\n💡 DIAGNÓSTICO:")
        if any(f.lower() in [c.lower() for c in cols_codigo] for f in faltantes):
            print("👉 Es un problema de MAYÚSCULAS/minúsculas. (Ej: 'rsi' vs 'RSI')")
        else:
            print("👉 Las columnas tienen nombres totalmente diferentes o no se están calculando.")

if __name__ == "__main__":
    diagnostico_ml()