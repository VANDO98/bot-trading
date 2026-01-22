import pandas as pd
import numpy as np
import joblib
import sys
import os

# --- PATH SETUP (Fix imports from Core) ---
current_dir = os.path.dirname(os.path.abspath(__file__)) # Scripts
ml_dir = os.path.dirname(current_dir) # Machine_Learning
core_dir = os.path.join(ml_dir, 'Core')
sys.path.append(core_dir)

import glob
from colorama import Fore, init, Style
from DataProcessor import calcular_features, simular_estrategia_real

init(autoreset=True)

# --- CONFIGURACIÓN ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Data en ML/Data/Raw
CARPETA_DATA = os.path.join(ml_dir, "Data", "Raw")
ARCHIVO_MODELO = os.path.join(ml_dir, "Models", "modelo_rf_trading.joblib")

# Umbral de confianza (Debe coincidir con tu JSON)
ML_THRESHOLD = 0.70

def aplicar_logica_rsi_adx_bidireccional(df):
    """
    Replica tu EstrategiaRSI_ADX completa (Compras y Ventas).
    """
    RSI_SOBREVENTA = 30
    RSI_SOBRECOMPRA = 70
    ADX_MINIMO = 25 
    
    # Señal de COMPRA (Long)
    senales_compra = (df['RSI'] <= RSI_SOBREVENTA) & (df['ADX'] > ADX_MINIMO)
    
    # Señal de VENTA (Short)
    senales_venta = (df['RSI'] >= RSI_SOBRECOMPRA) & (df['ADX'] > ADX_MINIMO)
    
    # Devolvemos True si CUALQUIERA de las dos ocurre
    return senales_compra | senales_venta

def evaluar_par_hibrido(archivo_csv, modelo, columnas_modelo):
    nombre_par = os.path.basename(archivo_csv).replace("_5m.csv", "").replace("_15m.csv", "")
    
    try:
        df = pd.read_csv(archivo_csv)
        if len(df) < 500: return None
        
        # 1. Preparar Datos (Simulación Long/Short ya incluida en DataProcessor)
        df = calcular_features(df)
        df = simular_estrategia_real(df) 
        df.dropna(inplace=True)
        if df.empty: return None

        # 2. FILTRO TÉCNICO (RSI Extremo + ADX)
        mask_tecnica = aplicar_logica_rsi_adx_bidireccional(df)
        df_candidatas = df[mask_tecnica].copy()
        
        total_senales_tecnicas = len(df_candidatas)
        if total_senales_tecnicas == 0: return None

        # 3. FILTRO ML
        X = df_candidatas[columnas_modelo]
        y_real = df_candidatas['TARGET'] # 1 si la simulación (Long o Short) fue exitosa
        
        probs = modelo.predict_proba(X)[:, 1]
        indices_aprobados_ml = np.where(probs >= ML_THRESHOLD)[0]
        total_aprobadas_ml = len(indices_aprobados_ml)

        # 4. Resultados
        # Win Rate Técnico (Sin IA)
        wr_tecnico = (y_real.sum() / total_senales_tecnicas) * 100

        # Win Rate Híbrido (Con IA)
        if total_aprobadas_ml > 0:
            aciertos_ml = y_real.iloc[indices_aprobados_ml].sum()
            wr_hibrido = (aciertos_ml / total_aprobadas_ml) * 100
        else:
            wr_hibrido = 0.0

        return {
            "par": nombre_par,
            "tecnico_ops": total_senales_tecnicas,
            "ml_ops": total_aprobadas_ml,
            "win_rate_tecnico": wr_tecnico,
            "win_rate_hibrido": wr_hibrido
        }
        
    except Exception as e:
        return None

def main():
    print(Fore.YELLOW + "🧬 BACKTEST HÍBRIDO BIDIRECCIONAL (LONG & SHORT)")
    print(f"🎯 Estrategia: RSI<{30} o RSI>{70} + ADX>{25}")
    print(f"🧠 Umbral ML: {ML_THRESHOLD}")
    print("-" * 80)
    print(f"{'PAR':<12} | {'OPS TEC':<7} {'WR TEC':<8} | {'OPS ML':<7} {'WR FINAL':<9} | {'MEJORA'}")
    print("-" * 80)

    if not os.path.exists(ARCHIVO_MODELO):
        print("❌ Faltan archivos.")
        return
    
    rf_model = joblib.load(ARCHIVO_MODELO)
    columnas_modelo = getattr(rf_model, "feature_names_in_", ['RSI', 'RSI_Slope', 'Stoch_K', 'Dist_EMA200', 'ADX', 'ATR_Pct', 'BB_Width', 'RVOL', 'Cuerpo_Pct'])

    archivos = glob.glob(os.path.join(CARPETA_DATA, "*.csv"))
    resultados = []

    for archivo in archivos:
        res = evaluar_par_hibrido(archivo, rf_model, columnas_modelo)
        if res:
            diff = res['win_rate_hibrido'] - res['win_rate_tecnico']
            color_diff = Fore.GREEN if diff > 0 else Fore.RED
            color_final = Fore.GREEN if res['win_rate_hibrido'] >= 60 else (Fore.RED if res['win_rate_hibrido'] < 40 else Fore.YELLOW)
            
            print(f"{res['par']:<12} | {res['tecnico_ops']:<7} {res['win_rate_tecnico']:5.1f}%   | {res['ml_ops']:<7} {color_final}{res['win_rate_hibrido']:5.1f}%{Style.RESET_ALL}    | {color_diff}{diff:+5.1f}%")
            resultados.append(res)

    print("-" * 80)
    # Resumen
    if resultados:
        df = pd.DataFrame(resultados)
        df_ml = df[df['ml_ops'] > 0]
        ops_tec = df['tecnico_ops'].sum()
        ops_ml = df_ml['ml_ops'].sum()
        
        # Promedio ponderado real
        if ops_tec > 0: wr_tec_glob = (df['win_rate_tecnico'] * df['tecnico_ops']).sum() / ops_tec
        else: wr_tec_glob = 0
            
        if ops_ml > 0: wr_ml_glob = (df_ml['win_rate_hibrido'] * df_ml['ml_ops']).sum() / ops_ml
        else: wr_ml_glob = 0

        print(Fore.CYAN + "\n🏆 CONCLUSIÓN GLOBAL:")
        print(f"   Sin IA: {wr_tec_glob:.2f}% ({ops_tec} ops)")
        print(f"   Con IA: {Fore.GREEN}{wr_ml_glob:.2f}% ({ops_ml} ops)")

if __name__ == "__main__":
    main()