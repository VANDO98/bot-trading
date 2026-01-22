import pandas as pd
import pandas_ta as ta
import numpy as np
import os
import glob
from colorama import Fore, init

init(autoreset=True)

# --- CONFIGURACIÓN DE RUTAS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# BASE_DIR es Core/. Data esta en ../Data
CORE_DIR = os.path.dirname(os.path.abspath(__file__))
# Data/Raw y Data/Processed
CARPETA_ENTRADA = os.path.join(CORE_DIR, "..", "Data", "Raw")
CARPETA_SALIDA = os.path.join(CORE_DIR, "..", "Data", "Processed")
ARCHIVO_SALIDA = os.path.join(CARPETA_SALIDA, "DATASET_ENTRENAMIENTO_V1.csv")

# ==============================================================================
# ⚙️ CONFIGURACIÓN DE SIMULACIÓN (Sincronizada con tu JSON)
# ==============================================================================

STOP_LOSS_PCT = 0.015       # 1.5% distancia inicial
TAKE_PROFIT_PCT = 0.35      # 35% techo (casi inalcanzable, confiamos en Trailing)

# Lógica del Trailing Stop
LEVERAGE_ESTIMADO = 10.0    
ACTIVACION_TRAILING_PRICE = 0.07 / LEVERAGE_ESTIMADO  # 0.7% movimiento a favor
DISTANCIA_TRAILING_PRICE = 0.10 / LEVERAGE_ESTIMADO   # 1.0% distancia trailing

# Mínimo para considerar Éxito (Ratio 1:1)
MIN_PROFIT_PARA_EXITO = STOP_LOSS_PCT 

# Ventana de tiempo (4 horas)
VENTANA_FUTURO = 48 

def calcular_features(df):
    """
    Calcula los indicadores técnicos.
    """
    df = df.copy()

    # 1. RSI
    df['RSI'] = df.ta.rsi(length=14)
    df['RSI_Slope'] = df['RSI'].diff(1)
    
    # 2. Estocástico
    stoch = df.ta.stoch(k=14, d=3, smooth_k=3)
    col_k = [c for c in stoch.columns if c.startswith('STOCHk')][0]
    df['Stoch_K'] = stoch[col_k]
    
    # 3. EMA 200
    ema200 = df.ta.ema(length=200)
    df['Dist_EMA200'] = (df['close'] - ema200) / ema200
    
    # 4. ADX
    adx = df.ta.adx(length=14)
    col_adx = [c for c in adx.columns if c.startswith('ADX')][0]
    df['ADX'] = adx[col_adx]
    
    # 5. ATR %
    atr = df.ta.atr(length=14)
    df['ATR_Pct'] = atr / df['close']
    
    # 6. BB Width
    bbands = df.ta.bbands(length=20, std=2)
    col_bbw = [c for c in bbands.columns if c.startswith('BBB') or c.endswith('BBB')][0]
    df['BB_Width'] = bbands[col_bbw] / 100 
    
    # 7. RVOL
    vol_ma = df['volume'].rolling(window=20).mean()
    df['RVOL'] = df['volume'] / vol_ma
    
    # 8. Price Action
    rango = df['high'] - df['low']
    cuerpo = np.abs(df['close'] - df['open'])
    df['Cuerpo_Pct'] = np.where(rango == 0, 0, cuerpo / rango)
    
    return df

def simular_estrategia_real(df):
    """
    SIMULADOR BIDIRECCIONAL (LONG & SHORT)
    Dependiendo del RSI, simula una compra o una venta.
    """
    # Convertimos a Numpy
    opens = df['open'].values
    closes = df['close'].values
    highs = df['high'].values
    lows = df['low'].values
    rsis = df['RSI'].values # Necesitamos RSI para decidir dirección
    
    n = len(df)
    targets = np.zeros(n)
    
    print(f"{Fore.CYAN}⏳ Simulando LONG/SHORT en {n} velas...")
    
    for i in range(n - VENTANA_FUTURO):
        
        entry_price = closes[i]
        rsi_val = rsis[i]
        
        if np.isnan(rsi_val): continue
        
        # --- DECISIÓN DE DIRECCIÓN ---
        # Si RSI < 50 simulamos LONG. Si RSI >= 50 simulamos SHORT.
        # Esto alinea el entrenamiento con la naturaleza de 'Reversión a la media'.
        es_long = rsi_val < 50
        
        # Configuración Inicial
        trailing_activo = False
        resultado_trade = 0.0
        
        if es_long:
            # === LÓGICA LONG ===
            stop_loss = entry_price * (1 - STOP_LOSS_PCT)
            take_profit = entry_price * (1 + TAKE_PROFIT_PCT)
            highest_price = entry_price # Para Long rastreamos el máximo
        else:
            # === LÓGICA SHORT ===
            stop_loss = entry_price * (1 + STOP_LOSS_PCT) # SL arriba
            take_profit = entry_price * (1 - TAKE_PROFIT_PCT) # TP abajo
            lowest_price = entry_price # Para Short rastreamos el mínimo
        
        # BUCLE FUTURO
        for j in range(1, VENTANA_FUTURO + 1):
            idx = i + j
            current_low = lows[idx]
            current_high = highs[idx]
            current_close = closes[idx]
            
            if es_long:
                # ---------------- LONG ----------------
                # 1. Check SL
                if current_low <= stop_loss:
                    resultado_trade = (stop_loss - entry_price) / entry_price
                    break 
                # 2. Check TP
                if current_high >= take_profit:
                    resultado_trade = (take_profit - entry_price) / entry_price
                    break
                
                # 3. Trailing Stop Long
                if current_high > highest_price:
                    highest_price = current_high
                
                ganancia_flotante = (highest_price - entry_price) / entry_price
                
                if not trailing_activo and ganancia_flotante >= ACTIVACION_TRAILING_PRICE:
                    trailing_activo = True
                    # Al activar, SL sube
                    nuevo_sl = highest_price * (1 - DISTANCIA_TRAILING_PRICE)
                    if nuevo_sl > stop_loss: stop_loss = nuevo_sl
                
                if trailing_activo:
                    nuevo_sl = highest_price * (1 - DISTANCIA_TRAILING_PRICE)
                    if nuevo_sl > stop_loss: stop_loss = nuevo_sl
                    
                # Cierre final ventana
                if j == VENTANA_FUTURO:
                    resultado_trade = (current_close - entry_price) / entry_price
            
            else:
                # ---------------- SHORT ----------------
                # 1. Check SL (Short pierde si sube)
                if current_high >= stop_loss:
                    # PnL Short: (Entrada - Salida) / Entrada
                    resultado_trade = (entry_price - stop_loss) / entry_price
                    break 
                # 2. Check TP (Short gana si baja)
                if current_low <= take_profit:
                    resultado_trade = (entry_price - take_profit) / entry_price
                    break
                
                # 3. Trailing Stop Short
                # Rastreamos el precio MÁS BAJO alcanzado
                if current_low < lowest_price:
                    lowest_price = current_low
                
                # Ganancia Short: (Entrada - PrecioBajo) / Entrada
                ganancia_flotante = (entry_price - lowest_price) / entry_price
                
                if not trailing_activo and ganancia_flotante >= ACTIVACION_TRAILING_PRICE:
                    trailing_activo = True
                    # Al activar, SL BAJA (se acerca al precio actual)
                    # SL = PrecioBajo * (1 + Distancia)
                    nuevo_sl = lowest_price * (1 + DISTANCIA_TRAILING_PRICE)
                    if nuevo_sl < stop_loss: stop_loss = nuevo_sl
                
                if trailing_activo:
                    nuevo_sl = lowest_price * (1 + DISTANCIA_TRAILING_PRICE)
                    # En Short, queremos que el SL sea cada vez menor
                    if nuevo_sl < stop_loss: stop_loss = nuevo_sl

                # Cierre final ventana
                if j == VENTANA_FUTURO:
                    resultado_trade = (entry_price - current_close) / entry_price

        # --- TARGET ---
        if resultado_trade >= MIN_PROFIT_PARA_EXITO:
            targets[i] = 1.0
        else:
            targets[i] = 0.0

    df['TARGET'] = targets
    return df

def main():
    print(Fore.YELLOW + "⚙️  INICIANDO PROCESADOR (BIDIRECCIONAL LONG/SHORT)")
    print(f"🎯 Simulando LONG si RSI<50 | SHORT si RSI>=50")
    
    if not os.path.exists(CARPETA_SALIDA):
        os.makedirs(CARPETA_SALIDA)

    archivos = glob.glob(os.path.join(CARPETA_ENTRADA, "*.csv"))
    print(f"📂 Archivos encontrados: {len(archivos)}")
    
    datasets_procesados = []
    columnas_finales = ['RSI', 'RSI_Slope', 'Stoch_K', 'Dist_EMA200', 'ADX', 'ATR_Pct', 'BB_Width', 'RVOL', 'Cuerpo_Pct', 'TARGET']

    for archivo in archivos:
        try:
            nombre = os.path.basename(archivo)
            print(f"🔨 Procesando: {nombre}...", end="\r")
            df = pd.read_csv(archivo)
            if len(df) < 200: continue 
            
            df = calcular_features(df)
            df = simular_estrategia_real(df) # Ahora maneja Shorts!
            
            df.dropna(inplace=True)
            df_final = df[columnas_finales].copy()
            datasets_procesados.append(df_final)
            
        except Exception as e:
            print(f"\n❌ Error en {archivo}: {e}")

    if not datasets_procesados:
        print(Fore.RED + "\n❌ No se generaron datos.")
        return

    print(Fore.YELLOW + "\n🔗 Unificando datasets...")
    dataset_master = pd.concat(datasets_procesados, ignore_index=True)
    dataset_master = dataset_master.sample(frac=1, random_state=42).reset_index(drop=True)
    dataset_master.to_csv(ARCHIVO_SALIDA, index=False)
    
    print("-" * 50)
    print(Fore.GREEN + f"✅ DATASET GENERADO: {ARCHIVO_SALIDA}")
    print(f"📊 Muestras Totales: {len(dataset_master)}")
    conteo = dataset_master['TARGET'].value_counts(normalize=True)
    print(f"⚖️  Ganadoras (1): {conteo.get(1.0, 0):.2%} | Perdedoras (0): {conteo.get(0.0, 0):.2%}")
    print("-" * 50)

if __name__ == "__main__":
    main()