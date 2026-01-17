import pandas as pd
import pandas_ta as ta
import numpy as np
import glob
import os

# --- RUTAS INTELIGENTES ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CARPETA_INPUT = os.path.join(BASE_DIR, "Data_Entrenamiento")
CARPETA_OUTPUT = os.path.join(BASE_DIR, "Data_Procesada")

# Configuración Target (Triple Barrera)
HORIZONTE_VELAS = 24
MULTIPLO_TP = 2.0
MULTIPLO_SL = 1.0

def calcular_indicadores(df):
    """Calcula los 10 Jinetes del Apocalipsis (Features)"""
    # Evitar warnings de copia
    df = df.copy()

    # 1. Indicadores de Momento
    df['RSI'] = ta.rsi(df['close'], length=14)
    # Rellenar NaN iniciales del RSI para evitar errores en diff
    df['RSI'] = df['RSI'].fillna(50) 
    df['RSI_Slope'] = df['RSI'].diff(1) # Velocidad del cambio
    
    stoch = ta.stoch(df['high'], df['low'], df['close'])
    # Pandas TA devuelve k, d. Buscamos la columna K dinámicamente
    col_k = [c for c in stoch.columns if c.startswith('STOCHk')][0]
    df['Stoch_K'] = stoch[col_k]

    # 2. Tendencia
    df['EMA_200'] = ta.ema(df['close'], length=200)
    df['Dist_EMA200'] = (df['close'] - df['EMA_200']) / df['close'] # Normalizado
    
    adx = ta.adx(df['high'], df['low'], df['close'], length=14)
    # Buscamos la columna ADX dinámicamente (suele ser ADX_14)
    col_adx = [c for c in adx.columns if c.startswith('ADX') and not c.startswith('ADX_') is False][0]
    df['ADX'] = adx[col_adx]

    # 3. Volatilidad
    df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=14)
    df['ATR_Pct'] = df['ATR'] / df['close'] # Volatilidad relativa
    
    # --- CORRECCIÓN DE BOLLINGER BANDS ---
    bb = ta.bbands(df['close'], length=20, std=2)
    
    # En lugar de adivinar el nombre (BBU_20_2.0), lo buscamos:
    col_upper = [c for c in bb.columns if c.startswith('BBU')][0] # Banda Superior
    col_lower = [c for c in bb.columns if c.startswith('BBL')][0] # Banda Inferior
    col_mid   = [c for c in bb.columns if c.startswith('BBM')][0] # Banda Media (SMA)

    # Calculamos el ancho manualmente para estar seguros
    df['BB_Width'] = (bb[col_upper] - bb[col_lower]) / bb[col_mid]
    # -------------------------------------

    # 4. Volumen y Velas
    df['Vol_SMA_20'] = ta.sma(df['volume'], length=20)
    df['RVOL'] = df['volume'] / df['Vol_SMA_20'] # Volumen Relativo
    
    # Tamaño del cuerpo (Absoluto convertido a relativo)
    cuerpo = abs(df['close'] - df['open'])
    rango_total = df['high'] - df['low']
    # Evitar división por cero
    df['Cuerpo_Pct'] = np.where(rango_total == 0, 0, cuerpo / rango_total)

    return df

def etiquetar_triple_barrera(df):
    df['TARGET'] = 0
    tp_dist = df['ATR'] * MULTIPLO_TP
    sl_dist = df['ATR'] * MULTIPLO_SL
    
    closes = df['close'].values
    highs = df['high'].values
    lows = df['low'].values
    targets = np.zeros(len(df))
    
    print(f"   🧠 Etiquetando {len(df)} velas...")
    
    for i in range(len(df) - HORIZONTE_VELAS):
        entrada = closes[i]
        tp = entrada + tp_dist.values[i]
        sl = entrada - sl_dist.values[i]
        
        vent_h = highs[i+1 : i+1+HORIZONTE_VELAS]
        vent_l = lows[i+1 : i+1+HORIZONTE_VELAS]
        
        idx_tp = np.argmax(vent_h >= tp) if np.any(vent_h >= tp) else -1
        idx_sl = np.argmax(vent_l <= sl) if np.any(vent_l <= sl) else -1
            
        if idx_tp != -1:
            if idx_sl == -1 or idx_tp < idx_sl:
                targets[i] = 1 # Win
            else:
                targets[i] = 0 # Loss (tocó SL antes)
        else:
            targets[i] = 0 # Time out
            
    df['TARGET'] = targets
    return df

def main():
    if not os.path.exists(CARPETA_OUTPUT): os.makedirs(CARPETA_OUTPUT)
        
    archivos = glob.glob(os.path.join(CARPETA_INPUT, "*.csv"))
    print(f"📂 Encontrados {len(archivos)} pares en {CARPETA_INPUT}")
    
    dfs = []
    for archivo in archivos:
        print(f"⚡ Procesando {os.path.basename(archivo)}...")
        df = pd.read_csv(archivo)
        
        df = calcular_indicadores(df)
        df.dropna(inplace=True)
        df.reset_index(drop=True, inplace=True)
        
        df = etiquetar_triple_barrera(df)
        
        features = ['RSI', 'RSI_Slope', 'Stoch_K', 'Dist_EMA200', 'ADX', 
                    'ATR_Pct', 'BB_Width', 'RVOL', 'Cuerpo_Pct', 'TARGET']
        
        dfs.append(df[features].copy())
        
    if dfs:
        master = pd.concat(dfs, ignore_index=True)
        ruta = os.path.join(CARPETA_OUTPUT, "DATASET_ENTRENAMIENTO_V1.csv")
        master.to_csv(ruta, index=False)
        print(f"✅ DATASET FINAL CREADO: {ruta}")
        print(f"📊 Filas: {len(master)} | Win Rate: {master['TARGET'].mean()*100:.2f}%")
    else:
        print("⚠️ No se encontraron datos para procesar.")

if __name__ == "__main__":
    main()