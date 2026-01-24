
import pandas as pd
import numpy as np
import os
import sys
import pandas_ta as ta
import joblib
from colorama import Fore, init, Style
import datetime
import json

# --- SETUP ---
current_dir = os.path.dirname(os.path.abspath(__file__)) # Scripts/Backtesting
scripts_dir = os.path.dirname(current_dir) # Scripts
ml_dir = os.path.dirname(scripts_dir) # Machine_Learning
root_dir = os.path.dirname(ml_dir) # Root
sys.path.append(root_dir)

from Core.Utils.FeatureEngine import FeatureEngine

init(autoreset=True)

# --- CONFIG ---
CARPETA_DATA = os.path.join(ml_dir, "Data", "Historico")
CONFIG_PATH = os.path.join(ml_dir, "..", "config_trading.json")

# DEFINICIÓN DE ESTRATEGIAS (Lógica Vectorizada para Backtest Rápido)
# Deben coincidir con las clases en Estrategias/Concretas

ESTRATEGIAS_TEST = {
    "EstrategiaTrend": {
        "params": {"ema_fast": 9, "ema_slow": 50, "adx_minimo": 20},
        "tipo": "trend"
    },
    "EstrategiaTrend_Candle": {
        "params": {"ema_fast": 9, "ema_slow": 50, "adx_minimo": 20},
        "tipo": "trend_candle"
    },
    "EstrategiaRSI_ADX": {
        "params": {"rsi_periodo": 14, "rsi_sobreventa": 30, "rsi_sobrecompra": 70, "adx_minimo": 20},
        "tipo": "mean_reversion"
    },
    "EstrategiaSqueeze_Momentum": {
        "params": {"rvol_min": 1.5},
        "tipo": "momentum"
    },
    "EstrategiaBB": { # Esta es la original (Ruptura/Trend)
        "params": {"bb_length": 20, "bb_std": 2.0},
        "tipo": "breakout"
    },
    # --- NUEVAS ---
    "EstrategiaSuperTrend": {
        "params": {"st_length": 10, "st_multiplier": 3.0},
        "tipo": "trend"
    },
    "EstrategiaMACD_ZeroLag": {
        "params": {"macd_fast": 12, "macd_slow": 26, "macd_signal": 9},
        "tipo": "momentum"
    },
    "EstrategiaBollingerReversion": {
        "params": {"bb_length": 20, "bb_std": 2.0},
        "tipo": "mean_reversion"
    }
}

def aplicar_logica_vectorizada(df, nombre_estrat, params):
    """
    Replica la lógica de 'generar_senal' de cada clase pero usando pandas vectorizado.
    Retorna Series bool (mask) de entradas.
    """
    try:
        if nombre_estrat == "EstrategiaTrend":
            ema_f = ta.ema(df['close'], length=params['ema_fast'])
            ema_s = ta.ema(df['close'], length=params['ema_slow'])
            adx = df['ADX']
            # Señal Long (Trend puede ser Short también, aquí simplificamos a Long para la prueba o combinamos)
            # Asumamos Long Only para simplificar el comparativo inicial o Long/Short si Target lo permite
            # Para uniformidad con tests previos: Long/Short Union
            mask = ((ema_f > ema_s) | (ema_f < ema_s)) & (adx > params['adx_minimo'])
            return mask

        elif nombre_estrat == "EstrategiaTrend_Candle":
            ema_f = ta.ema(df['close'], length=params['ema_fast'])
            ema_s = ta.ema(df['close'], length=params['ema_slow'])
            adx = df['ADX']
            patron_bull = (df['CDL_ENGULFING'] == 100) | (df['CDL_HAMMER'] == 100)
            patron_bear = (df['CDL_ENGULFING'] == -100) | (df['CDL_SHOOTING'] == -100)
            mask = (((ema_f > ema_s) & patron_bull) | ((ema_f < ema_s) & patron_bear)) & (adx > params['adx_minimo'])
            return mask

        elif nombre_estrat == "EstrategiaRSI_ADX":
            rsi = ta.rsi(df['close'], length=params['rsi_periodo']).fillna(50)
            adx = df['ADX']
            mask = ((rsi < params['rsi_sobreventa']) | (rsi > params['rsi_sobrecompra'])) & (adx > params['adx_minimo'])
            return mask

        elif nombre_estrat == "EstrategiaBB": # Breakout (Original)
            bb = ta.bbands(df['close'], length=params['bb_length'], std=params['bb_std'])
            if bb is None: return pd.Series(False, index=df.index)
            col_u = bb[f"BBU_{params['bb_length']}_{params['bb_std']}"]
            col_l = bb[f"BBL_{params['bb_length']}_{params['bb_std']}"]
            mask = (df['close'] > col_u) | (df['close'] < col_l)
            return mask

        elif nombre_estrat == "EstrategiaSqueeze_Momentum":
            # Asume columnas ya calculadas por FeatureEngine? No, FeatureEngine hace basics.
            # Necesitamos SQZMI pero FeatureEngine no lo calcula por defecto creo.
            # Use Lreg_Mom
            mom = df['Lreg_Mom'] if 'Lreg_Mom' in df.columns else ta.linreg(df['close'], length=20, slope=True) # Fallback
            rvol = df['RVOL']
            mask = (rvol > params['rvol_min']) & (mom.abs() > 0)
            return mask

        elif nombre_estrat == "EstrategiaSuperTrend":
            st = ta.supertrend(df['high'], df['low'], df['close'], length=params['st_length'], multiplier=params['st_multiplier'])
            if st is None: return pd.Series(False, index=df.index)
            col_dir = f"SUPERTd_{params['st_length']}_{params['st_multiplier']}"
            if col_dir not in st.columns: return pd.Series(False, index=df.index)
            # Señal continua. Tomamos cambio de tendencia? O estar en tendencia?
            # Para "Entrada", mejor detectar el cambio (Cruce).
            # Si st_dir != st_dir.shift(1) -> Cambio
            mask = (st[col_dir] != st[col_dir].shift(1))
            return mask

        elif nombre_estrat == "EstrategiaMACD_ZeroLag":
            fast_ma = ta.zlma(df['close'], length=params['macd_fast'])
            slow_ma = ta.zlma(df['close'], length=params['macd_slow'])
            macd = fast_ma - slow_ma
            signal = ta.ema(macd, length=params['macd_signal'])
            # Cruces
            cross_up = (macd > signal) & (macd.shift(1) <= signal.shift(1))
            cross_down = (macd < signal) & (macd.shift(1) >= signal.shift(1))
            return cross_up | cross_down

        elif nombre_estrat == "EstrategiaBollingerReversion":
            bb = ta.bbands(df['close'], length=params['bb_length'], std=params['bb_std'])
            if bb is None: return pd.Series(False, index=df.index)
            col_u = bb[f"BBU_{params['bb_length']}_{params['bb_std']}"]
            col_l = bb[f"BBL_{params['bb_length']}_{params['bb_std']}"]
            # Close < Lower OR Close > Upper
            mask = (df['close'] < col_l) | (df['close'] > col_u)
            return mask

    except Exception as e:
        # print(f"Err {nombre_estrat}: {e}")
        return pd.Series(False, index=df.index)
    
    return pd.Series(False, index=df.index)

def evaluar_estrategia(df, nombre, params):
    # 1. Aplicar reglas
    mask = aplicar_logica_vectorizada(df, nombre, params)
    df_ops = df[mask].copy()
    
    total_ops = len(df_ops)
    if total_ops < 5: return None # Descartar por irrelevante
    
    # 2. Calcular Win Rate (Base)
    win_rate = (df_ops['TARGET'].sum() / total_ops) * 100
    
    return {
        "estrategia": nombre,
        "ops": total_ops,
        "win_rate": win_rate,
        # Score simple = WR * log(Ops) para premiar consistencia? 
        # Mejor solo WR hoy.
        "score": win_rate 
    }

def main():
    print(Fore.MAGENTA + "\n🏆 TORNEO DE ESTRATEGIAS (8 COMPETIDORES)")
    print("=" * 100)
    
    config = json.load(open(CONFIG_PATH, 'r'))
    
    resultados_finales = []
    
    for par, cfg in config.get('pares', {}).items():
        if not cfg.get('activo', False) and par != "AVAX/USDT": 
            # Permitimos AVAX aunque esté desactivado para probar
            if par != "AVAX/USDT": continue

        simbolo = par.replace('/', '')
        tf = cfg.get('timeframe', '1h') # Default 1h para standard
        
        print(f"\n🥊 Analizando: {Fore.CYAN}{par}{Style.RESET_ALL} ({tf})")
        
        # Cargar Datos
        ruta_csv = os.path.join(CARPETA_DATA, tf, f"{simbolo}_{tf}.csv")
        if not os.path.exists(ruta_csv):
            print("   ❌ Sin datos.")
            continue
            
        df = pd.read_csv(ruta_csv)
        df = FeatureEngine.generar_indicadores(df)
        
        # Calcular Target Global
        df['retorno'] = df['close'].shift(-3) / df['close'] - 1
        df['TARGET'] = (df['retorno'] > 0.008).astype(int)
        df.dropna(subset=['TARGET'], inplace=True)
        
        # Competencia
        scores_par = []
        for nombre, info in ESTRATEGIAS_TEST.items():
            res = evaluar_estrategia(df, nombre, info['params'])
            if res:
                scores_par.append(res)
                
        # Mostrar el Ganador del Par
        if scores_par:
            # Ordenar por Win Rate
            scores_par.sort(key=lambda x: x['win_rate'], reverse=True)
            ganador = scores_par[0]
            
            print(f"   🏆 Ganador: {Fore.GREEN}{ganador['estrategia']}{Style.RESET_ALL}")
            print(f"      WR: {ganador['win_rate']:.1f}% | Ops: {ganador['ops']}")
            
            # Mostrar Top 3
            for i, s in enumerate(scores_par[:3]):
                prefix = "🥇" if i==0 else ("🥈" if i==1 else "🥉")
                print(f"      {prefix} {s['estrategia']:<25} WR: {s['win_rate']:5.1f}% ({s['ops']} ops)")
                
            resultados_finales.append({
                "par": par,
                "mejor_estrategia": ganador['estrategia'],
                "wr": ganador['win_rate'],
                "ops": ganador['ops']
            })
        else:
            print("   ⚠️ Ninguna estrategia generó suficientes operaciones.")

    # Guardar Resultados
    if resultados_finales:
        df_res = pd.DataFrame(resultados_finales)
        out_dir = os.path.join(ml_dir, "Backtest_History", "Tournament_Reports")
        if not os.path.exists(out_dir): os.makedirs(out_dir)
        
        ruta_out = os.path.join(out_dir, f"torneo_resultados_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.csv")
        df_res.to_csv(ruta_out, index=False)
        print(f"\n💾 Resultados guardados en: {ruta_out}")

if __name__ == "__main__":
    main()
