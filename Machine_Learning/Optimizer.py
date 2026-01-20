import pandas as pd
import pandas_ta as ta
import json
import os
import itertools
from colorama import Fore, init

init(autoreset=True)

# --- CONFIGURACIÓN ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Apuntamos a la raíz de Historico
DATA_DIR = os.path.join(BASE_DIR, "..", "Data", "Historico") 
CONFIG_PATH = os.path.join(BASE_DIR, "..", "config_trading.json")
COMISION = 0.0006 

# Timeframes que buscará en sus respectivas carpetas
TIMEFRAMES_COMPETENCIA = ["5m", "15m", "1h"] 

# --- GRID (Igual que antes) ---
GRID_PARAMETROS = {
    "EstrategiaRSI_ADX": {
        "rsi_periodo": [14],
        "rsi_sobreventa": [25, 30],
        "rsi_sobrecompra": [70, 75],
        "adx_minimo": [20, 25]
    },
    "EstrategiaBB": {
        "bb_length": [20],
        "bb_std": [2.0, 2.5]
    },
    "EstrategiaTrend": {
        "ema_fast": [9, 20, 50],
        "ema_slow": [21, 50, 200],
        "adx_minimo": [20, 25]
    }
}

def cargar_config():
    with open(CONFIG_PATH, 'r') as f: return json.load(f)

def guardar_config(config):
    with open(CONFIG_PATH, 'w') as f: json.dump(config, f, indent=2)

def generar_combinaciones(nombre_estrategia):
    params_grid = GRID_PARAMETROS.get(nombre_estrategia, {})
    keys = params_grid.keys()
    values = params_grid.values()
    return [dict(zip(keys, v)) for v in itertools.product(*values)]

def calcular_adx_seguro(df):
    try:
        adx_df = ta.adx(df['high'], df['low'], df['close'], length=14)
        if adx_df is None: return pd.Series(0, index=df.index)
        col = next((c for c in adx_df.columns if c.startswith('ADX')), None)
        return adx_df[col] if col else pd.Series(0, index=df.index)
    except: return pd.Series(0, index=df.index)

def simular_estrategia(df, nombre_estrategia, params):
    # (Misma lógica de simulación que la versión anterior)
    # ... COPIA AQUÍ LA FUNCIÓN simular_estrategia DE LA RESPUESTA ANTERIOR ...
    # ... O UTILIZA ESTA VERSIÓN ABREVIADA SI LA TIENES: ...
    df = df.copy()
    df['senal'] = 0 
    
    if nombre_estrategia == "EstrategiaRSI_ADX":
        df['RSI'] = ta.rsi(df['close'], length=params['rsi_periodo'])
        df['ADX'] = calcular_adx_seguro(df)
        mask_buy = (df['RSI'] < params['rsi_sobreventa']) & (df['ADX'] > params['adx_minimo'])
        mask_sell = (df['RSI'] > params['rsi_sobrecompra']) & (df['ADX'] > params['adx_minimo'])
        df.loc[mask_buy, 'senal'] = 1
        df.loc[mask_sell, 'senal'] = -1

    elif nombre_estrategia == "EstrategiaBB":
        bb = ta.bbands(df['close'], length=params['bb_length'], std=params['bb_std'])
        if bb is not None:
            col_u = next((c for c in bb.columns if c.startswith('BBU')), None)
            col_l = next((c for c in bb.columns if c.startswith('BBL')), None)
            if col_u and col_l:
                df.loc[df['close'] > bb[col_u], 'senal'] = 1
                df.loc[df['close'] < bb[col_l], 'senal'] = -1

    elif nombre_estrategia == "EstrategiaTrend":
        if params['ema_fast'] >= params['ema_slow']: return -9999
        df['EMA_F'] = ta.ema(df['close'], length=params['ema_fast'])
        df['EMA_S'] = ta.ema(df['close'], length=params['ema_slow'])
        df['ADX'] = calcular_adx_seguro(df)
        adx_min = params.get('adx_minimo', 20)
        mask_buy = (df['EMA_F'] > df['EMA_S']) & (df['ADX'] > adx_min)
        mask_sell = (df['EMA_F'] < df['EMA_S']) & (df['ADX'] > adx_min)
        df.loc[mask_buy, 'senal'] = 1
        df.loc[mask_sell, 'senal'] = -1
    else: return -999

    df['posicion'] = df['senal'].shift(1).fillna(0)
    df['retorno_mercado'] = df['close'].pct_change().fillna(0)
    df['retorno_neto'] = (df['posicion'] * df['retorno_mercado']) - (df['posicion'].diff().abs() * COMISION)
    return df['retorno_neto'].sum() * 100

def main():
    print(f"{Fore.MAGENTA}🔬 OPTIMIZER V5.1 (Lectura por Carpetas)...")
    
    config = cargar_config()
    pares_config = config.get('pares', {})
    cambios_totales = 0
    
    print("-" * 120)
    print(f"{'PAR':<10} | {'GANADOR (TF)':<22} | {'PARAMS OPTIMIZADOS':<60} | {'SCORE':<8}")
    print("-" * 120)

    for par, cfg in pares_config.items():
        if not cfg.get('activo', False): continue
        
        simbolo_archivo = par.replace('/', '') 
        mejor_score_par = -9999
        mejor_config_par = None

        # --- BUCLE DE TEMPORALIDADES (POR CARPETAS) ---
        for tf in TIMEFRAMES_COMPETENCIA:
            # AQUI ESTA EL CAMBIO: Busca en Data/Historico/{tf}/{archivo}
            ruta_csv = os.path.join(DATA_DIR, tf, f"{simbolo_archivo}_{tf}.csv")
            
            if not os.path.exists(ruta_csv): continue

            try:
                df = pd.read_csv(ruta_csv)
                if df.empty: continue
                for c in ['close', 'high', 'low', 'open']: df[c] = pd.to_numeric(df[c], errors='coerce')
                df.dropna(subset=['close'], inplace=True)
            except: continue

            for estrategia in GRID_PARAMETROS.keys():
                combinaciones = generar_combinaciones(estrategia)
                for params in combinaciones:
                    try:
                        score = simular_estrategia(df, estrategia, params)
                        if score > mejor_score_par:
                            mejor_score_par = score
                            mejor_config_par = {
                                "estrategia": estrategia, "params": params, "timeframe": tf
                            }
                    except: pass

        if mejor_config_par and mejor_score_par > -60:
            params_str = str(mejor_config_par['params']).replace('{','').replace('}','').replace("'", "")
            ganador_str = f"{mejor_config_par['estrategia']} ({mejor_config_par['timeframe']})"
            
            tf_ant = cfg.get('timeframe')
            estrat_ant = cfg.get('estrategia')
            params_ant = cfg.get('parametros_estrategia')
            
            hubo_cambio = (estrat_ant != mejor_config_par['estrategia'] or 
                           params_ant != mejor_config_par['params'] or
                           tf_ant != mejor_config_par['timeframe'])
            
            color = Fore.GREEN if hubo_cambio else Fore.WHITE
            print(f"{color}{par:<10} | {ganador_str:<22} | {params_str[:60]:<60} | {mejor_score_par:>7.1f}%")

            if hubo_cambio:
                pares_config[par]['estrategia'] = mejor_config_par['estrategia']
                pares_config[par]['parametros_estrategia'] = mejor_config_par['params']
                pares_config[par]['timeframe'] = mejor_config_par['timeframe']
                cambios_totales += 1
        else:
            print(f"{Fore.RED}{par:<10} | {'SIN RESULTADOS':<22} | (Pérdidas exceden -60% o faltan datos)")

    if cambios_totales > 0:
        guardar_config(config)
        print(f"\n{Fore.GREEN}✅ Optimización completada. {cambios_totales} pares actualizados.")
    else:
        print(f"\n{Fore.CYAN}👍 Todo optimizado.")

if __name__ == "__main__":
    main()