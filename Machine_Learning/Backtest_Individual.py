import pandas as pd
import pandas_ta as ta
import numpy as np
import joblib
import os
import glob
from colorama import Fore, init

init(autoreset=True)

# --- CONFIGURACIÓN ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CARPETA_DATA = os.path.join(BASE_DIR, "Data_Entrenamiento") # Datos crudos originales
ARCHIVO_MODELO = os.path.join(BASE_DIR, "modelo_rf_trading.joblib")

# Parámetros de Simulación (Deben ser iguales a los del entrenamiento)
UMBRAL_CONFIANZA = 0.55    # Solo entramos si el modelo está 65% seguro
MULTIPLO_TP = 2.0          # Ganancia: 2x ATR
MULTIPLO_SL = 1.0          # Riesgo: 1x ATR
HORIZONTE_VELAS = 24       # Tiempo máximo para ganar

def calcular_indicadores(df):
    """Misma lógica exacta que usamos para entrenar"""
    df = df.copy()
    
    # 1. Momento
    df['RSI'] = ta.rsi(df['close'], length=14)
    df['RSI'] = df['RSI'].fillna(50)
    df['RSI_Slope'] = df['RSI'].diff(1)
    
    stoch = ta.stoch(df['high'], df['low'], df['close'])
    col_k = [c for c in stoch.columns if c.startswith('STOCHk')][0]
    df['Stoch_K'] = stoch[col_k]

    # 2. Tendencia
    df['EMA_200'] = ta.ema(df['close'], length=200)
    df['Dist_EMA200'] = (df['close'] - df['EMA_200']) / df['close']
    
    adx = ta.adx(df['high'], df['low'], df['close'], length=14)
    col_adx = [c for c in adx.columns if c.startswith('ADX') and not c.startswith('ADX_') is False][0]
    df['ADX'] = adx[col_adx]

    # 3. Volatilidad
    df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=14)
    df['ATR_Pct'] = df['ATR'] / df['close']
    
    bb = ta.bbands(df['close'], length=20, std=2)
    col_upper = [c for c in bb.columns if c.startswith('BBU')][0]
    col_lower = [c for c in bb.columns if c.startswith('BBL')][0]
    col_mid   = [c for c in bb.columns if c.startswith('BBM')][0]
    df['BB_Width'] = (bb[col_upper] - bb[col_lower]) / bb[col_mid]

    # 4. Volumen y Velas
    df['Vol_SMA_20'] = ta.sma(df['volume'], length=20)
    df['RVOL'] = df['volume'] / df['Vol_SMA_20']
    
    cuerpo = abs(df['close'] - df['open'])
    rango_total = df['high'] - df['low']
    df['Cuerpo_Pct'] = np.where(rango_total == 0, 0, cuerpo / rango_total)

    # Limpiar nulos generados por indicadores
    df.dropna(inplace=True)
    df.reset_index(drop=True, inplace=True)
    
    return df

def simular_operaciones(df, modelo):
    # 1. Preparamos los datos para el modelo
    features = [
        'RSI', 'RSI_Slope', 'Stoch_K', 'Dist_EMA200', 'ADX', 
        'ATR_Pct', 'BB_Width', 'RVOL', 'Cuerpo_Pct'
    ]
    
    # 2. El modelo predice TODAS las velas a la vez (Vectorizado para velocidad)
    # predict_proba devuelve [[Prob_0, Prob_1], ...] -> Queremos la columna 1
    probabilidades = modelo.predict_proba(df[features])[:, 1]
    
    # 3. Simulamos trading
    capital = 1000 # Capital ficticio inicial
    balance = []
    trades_ganados = 0
    trades_perdidos = 0
    
    # Arrays numpy para velocidad
    closes = df['close'].values
    highs = df['high'].values
    lows = df['low'].values
    atrs = df['ATR'].values
    
    i = 0
    while i < len(df) - HORIZONTE_VELAS:
        # Solo miramos si la confianza supera el umbral
        if probabilidades[i] >= UMBRAL_CONFIANZA:
            
            # Datos de entrada
            precio_entry = closes[i]
            atr_actual = atrs[i]
            
            tp = precio_entry + (atr_actual * MULTIPLO_TP)
            sl = precio_entry - (atr_actual * MULTIPLO_SL)
            
            # Miramos el futuro
            resultado = 0 # 0: Neutro/TimeOut, 1: Win, -1: Loss
            
            for j in range(1, HORIZONTE_VELAS + 1):
                high_futuro = highs[i+j]
                low_futuro = lows[i+j]
                
                # ¿Tocó TP?
                if high_futuro >= tp:
                    resultado = 1
                    break # Salimos del trade
                
                # ¿Tocó SL?
                if low_futuro <= sl:
                    resultado = -1
                    break # Salimos del trade
            
            # Registrar resultado
            if resultado == 1:
                trades_ganados += 1
                # Ganancia aprox: 2 unidades de riesgo
            elif resultado == -1:
                trades_perdidos += 1
                # Pérdida: 1 unidad de riesgo
            
            # Saltar velas para no sobre-operar (opcional, saltamos 1 hora)
            # Para simular trading real, no podemos abrir 5 operaciones en 5 minutos
            i += 12 
            
        else:
            i += 1
            
    total_trades = trades_ganados + trades_perdidos
    win_rate = (trades_ganados / total_trades * 100) if total_trades > 0 else 0
    
    return total_trades, win_rate

def main():
    print(Fore.YELLOW + "🕵️‍♂️ INICIANDO AUDITORÍA INDIVIDUAL POR PAR...")
    
    if not os.path.exists(ARCHIVO_MODELO):
        print(Fore.RED + "❌ No encuentro el modelo .joblib. Entrena primero.")
        return

    modelo = joblib.load(ARCHIVO_MODELO)
    archivos = glob.glob(os.path.join(CARPETA_DATA, "*.csv"))
    
    print(f"🧠 Modelo cargado. Probando en {len(archivos)} pares históricos.")
    print("-" * 60)
    print(f"{'PAR':<15} | {'OPS':<5} | {'WIN RATE':<10} | {'VEREDICTO'}")
    print("-" * 60)
    
    promedio_wr = []

    for archivo in archivos:
        nombre_par = os.path.basename(archivo).replace("_5m.csv", "")
        
        df = pd.read_csv(archivo)
        
        # Generar indicadores (Feature Engineering)
        df_proc = calcular_indicadores(df)
        
        # Simular
        ops, wr = simular_operaciones(df_proc, modelo)
        
        # Colores
        if ops < 10:
            color = Fore.WHITE # Pocos datos
            estado = "Insuficiente Data"
        elif wr > 40:
            color = Fore.GREEN
            estado = "✅ APROBADO"
        elif wr > 33:
            color = Fore.YELLOW
            estado = "⚠️ Aceptable"
        else:
            color = Fore.RED
            estado = "❌ REPROBADO"
            
        if ops > 0: promedio_wr.append(wr)
            
        print(f"{color}{nombre_par:<15} | {ops:<5} | {wr:.2f}%      | {estado}")

    print("-" * 60)
    if promedio_wr:
        media = sum(promedio_wr) / len(promedio_wr)
        print(Fore.CYAN + f"📊 WIN RATE PROMEDIO GLOBAL: {media:.2f}%")
        print(f"ℹ️ (Recuerda: Con Ratio 1:2, necesitas >33% para ser rentable)")

if __name__ == "__main__":
    main()