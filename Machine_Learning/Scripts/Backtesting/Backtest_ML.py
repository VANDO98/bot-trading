import pandas as pd
import pandas_ta as ta
import numpy as np
import joblib
import sys
import os

# --- PATH SETUP (Fix imports from Core) ---
current_dir = os.path.dirname(os.path.abspath(__file__)) # Scripts/Backtesting
scripts_dir = os.path.dirname(current_dir) # Scripts
ml_dir = os.path.dirname(scripts_dir) # Machine_Learning
core_dir = os.path.join(ml_dir, '..', 'Core')
sys.path.append(os.path.join(ml_dir, '..')) # Append Root
sys.path.append(core_dir)

import glob
from colorama import Fore, init, Style
from DataProcessor import calcular_features, simular_estrategia_real # Importamos la lógica exacta

init(autoreset=True)

# --- CONFIGURACIÓN ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Datos crudos ahora estan en Machine_Learning/Data/Raw
CARPETA_DATA = os.path.join(ml_dir, "Data", "Raw") 
ARCHIVO_MODELO = os.path.join(ml_dir, "Models", "modelo_rf_trading.joblib")

# UMBRAL A TESTEAR (Debe ser el mismo de tu JSON)
UMBRAL_CONFIANZA = 0.70 

def evaluar_par(archivo_csv, modelo, columnas_modelo):
    """
    Carga un par, genera sus indicadores y simula qué hubiera hecho el bot.
    """
    nombre_par = os.path.basename(archivo_csv).replace("_5m.csv", "").replace("_15m.csv", "")
    
    # 1. Cargar Datos Crudos
    try:
        df = pd.read_csv(archivo_csv)
    except:
        return None

    if len(df) < 500: return None # Muy pocos datos

    # 2. Generar EXACTAMENTE los mismos indicadores que en el entrenamiento
    # Usamos las funciones importadas de DataProcessor para garantizar consistencia
    try:
        df = calcular_features(df)
        df = simular_estrategia_real(df) # Esto nos da la "respuesta correcta" (TARGET) para comparar
    except Exception as e:
        return None
        
    df.dropna(inplace=True)
    
    if df.empty: return None

    # 3. Preparar datos para el modelo (X)
    # Debemos asegurarnos de que las columnas estén en el MISMO ORDEN que cuando se entrenó
    try:
        X = df[columnas_modelo]
        y_real = df['TARGET'] # La realidad (Lo que pasó)
    except KeyError as e:
        print(f"❌ Error de columnas en {nombre_par}: {e}")
        return None

    # 4. Predicción del Modelo
    # predict_proba devuelve array de [[prob_0, prob_1], ...]
    probs = modelo.predict_proba(X)[:, 1] 

    # 5. Simulación de Trading
    # Filtramos solo donde el bot hubiera dicho "SÍ" (Probabilidad > Umbral)
    indices_entrada = np.where(probs >= UMBRAL_CONFIANZA)[0]
    
    total_entradas = len(indices_entrada)
    if total_entradas == 0:
        return {
            "par": nombre_par,
            "trades": 0,
            "win_rate": 0.0,
            "calidad": "N/A"
        }

    # Verificamos si esas entradas fueron ganadoras (TARGET = 1)
    aciertos = y_real.iloc[indices_entrada].sum() # Sumar 1s es contar aciertos
    win_rate = (aciertos / total_entradas) * 100

    return {
        "par": nombre_par,
        "trades": total_entradas,
        "win_rate": win_rate,
        "calidad": "🔥" if win_rate > 60 else "❄️"
    }

def main():
    print(Fore.YELLOW + "🧪 INICIANDO BACKTEST INDIVIDUAL POR PAR")
    print(f"🤖 Modelo: {os.path.basename(ARCHIVO_MODELO)}")
    print(f"🎯 Umbral de Confianza: {UMBRAL_CONFIANZA}")
    print("-" * 60)

    # 1. Cargar Modelo
    if not os.path.exists(ARCHIVO_MODELO):
        print(Fore.RED + "❌ No existe el modelo entrenado. Ejecuta TrainModel.py primero.")
        return
    
    rf_model = joblib.load(ARCHIVO_MODELO)
    
    # Obtener las columnas que el modelo espera (Feature Names)
    # Esto es vital para no enviar datos desordenados
    try:
        columnas_modelo = rf_model.feature_names_in_
    except:
        # Si la versión de scikit-learn es vieja, definimos manual
        columnas_modelo = ['RSI', 'RSI_Slope', 'Stoch_K', 'Dist_EMA200', 'ADX', 
                           'ATR_Pct', 'BB_Width', 'RVOL', 'Cuerpo_Pct']

    # 2. Buscar archivos
    archivos = glob.glob(os.path.join(CARPETA_DATA, "*.csv"))
    print(f"📂 Analizando {len(archivos)} pares...\n")

    resultados = []

    print(f"{'PAR':<15} | {'TRADES':<8} | {'WIN RATE':<10} | {'ESTADO'}")
    print("-" * 50)

    acum_trades = 0
    acum_wins = 0

    for archivo in archivos:
        res = evaluar_par(archivo, rf_model, columnas_modelo)
        if res:
            # Colores dinámicos
            color_wr = Fore.GREEN if res['win_rate'] >= 60 else (Fore.YELLOW if res['win_rate'] >= 50 else Fore.RED)
            
            print(f"{res['par']:<15} | {res['trades']:<8} | {color_wr}{res['win_rate']:6.2f}%{Style.RESET_ALL}   | {res['calidad']}")
            
            # Acumuladores globales
            acum_trades += res['trades']
            acum_wins += (res['win_rate'] / 100) * res['trades']
            
            resultados.append(res)

    print("-" * 50)
    
    if acum_trades > 0:
        win_rate_global = (acum_wins / acum_trades) * 100
        print(Fore.CYAN + f"\n🏆 RESUMEN GLOBAL (Promedio Ponderado):")
        print(f"   Total Señales Generadas: {acum_trades}")
        print(f"   Win Rate Promedio:       {win_rate_global:.2f}%")
        
        if win_rate_global > 60:
            print(Fore.GREEN + "✅ CONCLUSIÓN: El modelo es robusto y generalizable.")
        else:
            print(Fore.YELLOW + "⚠️ CONCLUSIÓN: El modelo es selectivo o requiere ajuste de umbral.")
    else:
        print(Fore.RED + "❌ Ningún par generó entradas con este umbral.")

if __name__ == "__main__":
    main()