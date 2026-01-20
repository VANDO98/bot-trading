import pandas as pd
import pandas_ta as ta
import os
import sys

# Ajuste de rutas
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# ⚠️ Asegúrate de apuntar al archivo de 1h o 1h que prefieras probar
RUTAS_DATA = os.path.join(os.path.dirname(__file__), '..', 'Data', 'Historico', 'BTCUSDT_1h.csv')
COMISION = 0.0006 # 0.06%

def debug_con_filtro_adx():
    print(f"🔍 DIAGNÓSTICO: ESTRATEGIA TREND vs TREND+ADX...")
    
    if not os.path.exists(RUTAS_DATA):
        print(f"❌ Error: No encuentro {RUTAS_DATA}")
        return

    try:
        df = pd.read_csv(RUTAS_DATA)
        # Limpieza datos
        cols = ['open', 'high', 'low', 'close', 'volume']
        for c in cols: df[c] = pd.to_numeric(df[c], errors='coerce')
        df.dropna(inplace=True)
    except Exception as e:
        print(f"❌ Error datos: {e}")
        return

    # --- 1. CÁLCULO DE INDICADORES ---
    # Tendencia (EMAs)
    df['EMA_F'] = ta.ema(df['close'], length=9)
    df['EMA_S'] = ta.ema(df['close'], length=21)
    
    # Fuerza (ADX)
    adx_df = ta.adx(df['high'], df['low'], df['close'], length=14)
    # Extraer columna correcta (pandas_ta a veces devuelve ADX_14, DMP_14, etc)
    col_adx = next((c for c in adx_df.columns if c.startswith('ADX')), None)
    df['ADX'] = adx_df[col_adx] if col_adx else 0

    # --- 2. ESCENARIO A: TREND CLÁSICA (LO QUE TIENES AHORA) ---
    df['senal_A'] = 0
    df.loc[df['EMA_F'] > df['EMA_S'], 'senal_A'] = 1
    df.loc[df['EMA_F'] < df['EMA_S'], 'senal_A'] = -1
    
    # --- 3. ESCENARIO B: TREND + FILTRO ADX (LA SOLUCIÓN) ---
    # Lógica: Solo entramos si hay cruce Y el ADX > 25 (Tendencia fuerte)
    # Si ADX < 25, mantenemos la posición anterior o nos quedamos neutros (0)
    
    df['senal_B'] = 0
    # Condición de entrada LONG: Cruce Alcista + Fuerza
    mask_long = (df['EMA_F'] > df['EMA_S']) & (df['ADX'] > 25)
    # Condición de entrada SHORT: Cruce Bajista + Fuerza
    mask_short = (df['EMA_F'] < df['EMA_S']) & (df['ADX'] > 25)
    
    df.loc[mask_long, 'senal_B'] = 1
    df.loc[mask_short, 'senal_B'] = -1
    
    # Rellenar ceros: Si ADX < 25, no hacemos nada nuevo. 
    # (En simulación simple esto equivale a cerrar o no entrar. 
    # Para ser estrictos: Si no hay señal fuerte, Senal = 0 -> Flat)

    # --- 4. COMPARACIÓN DE RESULTADOS ---
    for nombre, col_senal in [("SIN FILTRO", "senal_A"), ("CON ADX (>25)", "senal_B")]:
        df['pos'] = df[col_senal].shift(1).fillna(0)
        df['ret_mercado'] = df['close'].pct_change().fillna(0)
        
        # PnL
        df['ret_neto'] = (df['pos'] * df['ret_mercado']) - (df['pos'].diff().abs() * COMISION)
        
        ops = df['pos'].diff().abs().sum()
        pnl_final = df['ret_neto'].sum() * 100
        
        print(f"\n📊 ESTRATEGIA {nombre}:")
        print(f"   🔢 Operaciones: {ops:.0f}")
        print(f"   💰 PnL Neto: {pnl_final:.2f}%")
        
        if ops > 0:
            print(f"   📉 PnL por Trade: {pnl_final/ops:.4f}%")

if __name__ == "__main__":
    debug_con_filtro_adx()