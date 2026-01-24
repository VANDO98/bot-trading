
import pandas as pd
import numpy as np
import pandas_ta as ta
import os
import sys
import joblib
from colorama import Fore, init, Style

# --- SETUP ---
current_dir = os.path.dirname(os.path.abspath(__file__))
ml_dir = os.path.dirname(current_dir)
root_dir = os.path.dirname(ml_dir)
sys.path.append(root_dir)

from Core.Utils.FeatureEngine import FeatureEngine

init(autoreset=True)

# PARÁMETROS RSI (Estándar)
PARAMS_RSI = {
    'rsi_periodo': 14,
    'rsi_sobreventa': 30,  # Comprar abajo
    'rsi_sobrecompra': 70, # Vender arriba
    'adx_minimo': 20
}

def aplicar_rsi(df):
    rsi = ta.rsi(df['close'], length=PARAMS_RSI['rsi_periodo']).fillna(50)
    adx = df['ADX']
    
    # Estrategia Reversión: 
    # Long si RSI < 30 (Sobreventa)
    # Short si RSI > 70 (Sobrecompra)
    
    mask_long = (rsi < PARAMS_RSI['rsi_sobreventa']) & (adx > PARAMS_RSI['adx_minimo'])
    mask_short = (rsi > PARAMS_RSI['rsi_sobrecompra']) & (adx > PARAMS_RSI['adx_minimo'])
    
    return mask_long | mask_short

def main():
    print(Fore.CYAN + "🔬 TEST: AVAX/USDT con Estrategia RSI_ADX")
    print("-" * 60)
    
    # Cargar Datos
    ruta_csv = os.path.join(ml_dir, "Data", "Historico", "1h", "AVAXUSDT_1h.csv")
    if not os.path.exists(ruta_csv):
        print("❌ No se encontró el archivo de datos de AVAX.")
        return

    df = pd.read_csv(ruta_csv)
    df = FeatureEngine.generar_indicadores(df)
    
    # Calcular Target (Resultado Real)
    ventana_futura = 3
    umb_min = 0.008 # 0.8%
    df['retorno_futuro'] = df['close'].shift(-ventana_futura) / df['close'] - 1
    df['TARGET'] = (df['retorno_futuro'] > umb_min).astype(int)
    df.dropna(subset=['TARGET'], inplace=True)
    
    # Estrategia ANTERIOR (Trend) - Dato de referencia
    # (Ya sabemos que dio ~26% WR con 12,000 ops)
    print(f"📊 Referencia (EstrategiaTrend): {Fore.RED}Win Rate ~26.2%{Style.RESET_ALL} (Muy bajo)")
    print("-" * 60)
    
    # 2. Estrategia NUEVA (RSI)
    mask_rsi = aplicar_rsi(df)
    df_rsi = df[mask_rsi].copy()
    
    ops_rsi = len(df_rsi)
    wr_rsi = (df_rsi['TARGET'].sum() / ops_rsi) * 100 if ops_rsi > 0 else 0
    
    color_wr = Fore.GREEN if wr_rsi > 50 else (Fore.YELLOW if wr_rsi > 40 else Fore.RED)
    
    print(Fore.YELLOW + "🧪 Resultados NUEVA Estrategia (RSI Reversión):")
    print(f"   Ops Totales:   {ops_rsi}")
    print(f"   Win Rate Base: {color_wr}{wr_rsi:.2f}%{Style.RESET_ALL} (Sin ML)")
    
    # 3. Validar con ML existente?
    # El modelo actual de AVAX fue entrenado con señales TREND.
    # Aplicarlo a señales RSI podría no ser 100% válido, pero probemos si filtra algo.
    
    ruta_modelo = os.path.join(ml_dir, "Models", "1h", "modelo_AVAXUSDT.joblib")
    if os.path.exists(ruta_modelo):
        try:
            rf_model = joblib.load(ruta_modelo)
            cols = getattr(rf_model, "feature_names_in_", [])
            if len(cols) > 0:
                missing = [c for c in cols if c not in df_rsi.columns]
                for c in missing: df_rsi[c] = 0
                
                probs = rf_model.predict_proba(df_rsi[cols])[:, 1]
                
                # Probar con umbral 0.60
                th = 0.60
                mask_ml = probs > th
                df_ml = df_rsi[mask_ml]
                ops_ml = len(df_ml)
                wr_ml = (df_ml['TARGET'].sum() / ops_ml) * 100 if ops_ml > 0 else 0
                
                print(f"   Win Rate + ML (Th {th}): {Fore.CYAN}{wr_ml:.2f}%{Style.RESET_ALL} ({ops_ml} ops)")
        except:
            print("   (No se pudo aplicar modelo ML para validación extra)")
            
    print("-" * 60)
    if wr_rsi > 40:
        print(Fore.GREEN + "✅ CONCLUSIÓN: RSI mejora significativamente la base. Se recomienda cambiar.")
    else:
        print(Fore.RED + "❌ CONCLUSIÓN: RSI tampoco funciona bien. El par es difícil.")

if __name__ == "__main__":
    main()
