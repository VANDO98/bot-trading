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
# Apuntamos a la raíz de Historico
DATA_DIR = os.path.join(BASE_DIR, "..", "Data", "Historico") 
# Configuración está en la raíz del proyecto (dos niveles arriba de Core)
CONFIG_PATH = os.path.join(BASE_DIR, "..", "..", "config_trading.json")
COMISION = 0.0006 

# Timeframes que buscará en sus respectivas carpetas
TIMEFRAMES_COMPETENCIA = ["5m", "15m", "1h"] 

# --- GRID (Igual que antes) ---
# GRID AMPLIADO
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
        "ema_fast": [9, 20],
        "ema_slow": [50, 200],
        "adx_minimo": [20]
    },
    # NUEVAS ESTRATEGIAS
    "EstrategiaTrend_Candle": {
        "ema_fast": [20, 50],
        "ema_slow": [50, 200],
        "adx_minimo": [20, 25] # Requiere ADX fuerte y Patrón
    },
    "EstrategiaSqueeze_Momentum": {
        "mult_kc": [1.5], # Defecto squeeze
        "rvol_min": [1.2, 1.5]
    }
}

# Import relativo
import sys
sys.path.append(os.path.join(BASE_DIR, "..", "..")) # Root
from Core.Utils.FeatureEngine import FeatureEngine

def cargar_config():
    with open(CONFIG_PATH, 'r') as f: return json.load(f)

def guardar_config(config):
    with open(CONFIG_PATH, 'w') as f: json.dump(config, f, indent=2)

def generar_combinaciones(nombre_estrategia):
    params_grid = GRID_PARAMETROS.get(nombre_estrategia, {})
    keys = params_grid.keys()
    values = params_grid.values()
    return [dict(zip(keys, v)) for v in itertools.product(*values)]

def simular_estrategia(df, nombre_estrategia, params):
    # Usamos FeatureEngine para calcular TODOS los indicadores de una vez
    # Esto incluye Patrones, LinReg, etc.
    df = FeatureEngine.generar_indicadores(df)
    
    # Rellenar NaNs tras cálculo
    df.fillna(0, inplace=True)
    
    df['senal'] = 0 
    
    if nombre_estrategia == "EstrategiaRSI_ADX":
        # Recalculo específico si params custom
        rsi = ta.rsi(df['close'], length=params.get('rsi_periodo', 14)).fillna(50)
        adx = df['ADX'] # Ya viene del FeatureEngine (std 14)
        
        mask_buy = (rsi < params['rsi_sobreventa']) & (adx > params['adx_minimo'])
        mask_sell = (rsi > params['rsi_sobrecompra']) & (adx > params['adx_minimo'])
        df.loc[mask_buy, 'senal'] = 1
        df.loc[mask_sell, 'senal'] = -1

    elif nombre_estrategia == "EstrategiaBB":
        # FeatureEngine da BB std 2. Si grid pide 2.5, recalculamos
        bb = ta.bbands(df['close'], length=params['bb_length'], std=params['bb_std'])
        if bb is not None:
            col_u = next((c for c in bb.columns if c.startswith('BBU')), None)
            col_l = next((c for c in bb.columns if c.startswith('BBL')), None)
            if col_u and col_l:
                df.loc[df['close'] > bb[col_u], 'senal'] = 1 # Rompe arriba (Momentum)
                df.loc[df['close'] < bb[col_l], 'senal'] = -1 # Rompe abajo

    elif nombre_estrategia == "EstrategiaTrend":
        if params['ema_fast'] >= params['ema_slow']: return -9999
        # Recalcular EMAs según grid
        ema_f = ta.ema(df['close'], length=params['ema_fast'])
        ema_s = ta.ema(df['close'], length=params['ema_slow'])
        adx = df['ADX']
        adx_min = params.get('adx_minimo', 20)
        
        mask_buy = (ema_f > ema_s) & (adx > adx_min)
        mask_sell = (ema_f < ema_s) & (adx > adx_min)
        df.loc[mask_buy, 'senal'] = 1
        df.loc[mask_sell, 'senal'] = -1

    # --- NUEVAS ---
    elif nombre_estrategia == "EstrategiaTrend_Candle":
        if params['ema_fast'] >= params['ema_slow']: return -9999
        ema_f = ta.ema(df['close'], length=params['ema_fast'])
        ema_s = ta.ema(df['close'], length=params['ema_slow'])
        adx = df['ADX']
        
        # Patrones (FeatureEngine ya los calculó: 100/-100)
        patron_bull = (df['CDL_ENGULFING'] == 100) | (df['CDL_HAMMER'] == 100)
        patron_bear = (df['CDL_ENGULFING'] == -100) | (df['CDL_SHOOTING'] == -100)
        
        mask_buy = (ema_f > ema_s) & (adx > params['adx_minimo']) & patron_bull
        mask_sell = (ema_f < ema_s) & (adx > params['adx_minimo']) & patron_bear
        
        df.loc[mask_buy, 'senal'] = 1
        df.loc[mask_sell, 'senal'] = -1
        
    elif nombre_estrategia == "EstrategiaSqueeze_Momentum":
        # FeatureEngine ya tiene KC, Lreg_Mom, RVOL
        # Requisito: Bollinger fuera de KC (Disparo) + Momentum Alineado
        
        # Calcular BB localmente para asegurar existencia
        bb = ta.bbands(df['close'], length=20, std=2.0)
        col_u = next((c for c in bb.columns if c.startswith('BBU')), None)
        col_l = next((c for c in bb.columns if c.startswith('BBL')), None)
        
        if col_u and col_l:
            bb_u = bb[col_u]
            bb_l = bb[col_l]
            mom = df['Lreg_Mom']
            rvol = df['RVOL']
            
            mask_long = (df['close'] > bb_u) & (mom > 0) & (rvol > params['rvol_min'])
            mask_short = (df['close'] < bb_l) & (mom < 0) & (rvol > params['rvol_min'])
            
            df.loc[mask_long, 'senal'] = 1
            df.loc[mask_short, 'senal'] = -1

    else: return -999

    df['posicion'] = df['senal'].shift(1).fillna(0)
    df['retorno_mercado'] = df['close'].pct_change().fillna(0)
    df['retorno_neto'] = (df['posicion'] * df['retorno_mercado']) - (df['posicion'].diff().abs() * COMISION)
    return df['retorno_neto'].sum() * 100

import argparse

def main():
    parser = argparse.ArgumentParser(description='Optimizador de Estrategias con GridSearchCV')
    parser.add_argument('--auto', action='store_true', help='Aceptar cambios automáticamente sin preguntar')
    args = parser.parse_args()

    print(f"{Fore.MAGENTA}🔬 OPTIMIZER V6.0 (Safety First)...")
    
    config = cargar_config()
    pares_config = config.get('pares', {})
    cambios_pendientes = []
    
    print("-" * 140)
    print(f"{'PAR':<10} | {'ESTRATEGIA GANADORA':<30} | {'SCORE':<8} | {'ESTADO'}")
    print("-" * 140)

    for par, cfg in pares_config.items():
        if not cfg.get('activo', False): continue
        
        simbolo_archivo = par.replace('/', '') 
        mejor_score_par = -9999
        mejor_config_par = None

        datos_encontrados = False

        # --- BUCLE DE TEMPORALIDADES ---
        for tf in TIMEFRAMES_COMPETENCIA:
            ruta_csv = os.path.join(DATA_DIR, tf, f"{simbolo_archivo}_{tf}.csv")
            
            if not os.path.exists(ruta_csv): 
                continue

            try:
                df = pd.read_csv(ruta_csv)
                if df.empty: 
                     print(f"DEBUG: {par} {tf} vacio")
                     continue
                     
                for c in ['close', 'high', 'low', 'open']: df[c] = pd.to_numeric(df[c], errors='coerce')
                df.dropna(subset=['close'], inplace=True)
                
                if not df.empty:
                    datos_encontrados = True

            except Exception as e: 
                print(f"DEBUG ERROR leyendo {par}: {e}")
                continue

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
                    except Exception as e:
                        print(f"DEBUG ERROR simular {estrategia}: {e}")

        if mejor_config_par and mejor_score_par > -999:
            tf_ant = cfg.get('timeframe')
            estrat_ant = cfg.get('estrategia')
            params_ant = cfg.get('parametros_estrategia')
            
            # Detectar si hay diferencias
            diff = (estrat_ant != mejor_config_par['estrategia'] or 
                    params_ant != mejor_config_par['params'] or
                    tf_ant != mejor_config_par['timeframe'])
            
            ganador_str = f"{mejor_config_par['estrategia']} ({mejor_config_par['timeframe']})"
            
            if diff:
                print(f"{Fore.GREEN}{par:<10} | {ganador_str:<30} | {mejor_score_par:>7.1f}% | ⚡ MEJORA DETECTADA")
                cambios_pendientes.append({
                    'par': par,
                    'new': mejor_config_par,
                    'old': {'estrategia': estrat_ant, 'params': params_ant, 'timeframe': tf_ant}
                })
            else:
                print(f"{Fore.WHITE}{par:<10} | {ganador_str:<30} | {mejor_score_par:>7.1f}% | = Mantiene")
        else:
            if not datos_encontrados:
                print(f"{Fore.RED}{par:<10} | {'SIN DATOS (Archivo no encontrado)':<30} | ---")
            else:
                score_str = f"{mejor_score_par:.1f}%" if mejor_score_par > -9000 else "---"
                print(f"{Fore.YELLOW}{par:<10} | {'BAJO RENDIMIENTO / PÉRDIDAS':<30} | {score_str}")

    # --- RESUMEN Y CONFIRMACIÓN ---
    if not cambios_pendientes:
        print(f"\n{Fore.CYAN}👍 Todo optimizado. No se requieren cambios.")
        return

    print(f"\n{Fore.YELLOW}⚠️  SE PROPONEN {len(cambios_pendientes)} CAMBIOS:")
    print("-" * 80)
    for c in cambios_pendientes:
        par = c['par']
        old = c['old']
        new = c['new']
        print(f"🔹 {par}:")
        print(f"   🔴 ANTES: {old['estrategia']} ({old['timeframe']}) {old['params']}")
        print(f"   🟢 AHORA: {new['estrategia']} ({new['timeframe']}) {new['params']}")
        print("-" * 80)

    # Decisión
    if args.auto:
        confirmacion = 's'
        print(f"{Fore.MAGENTA}🤖 Modo Auto: Aplicando cambios...")
    else:
        confirmacion = input(f"{Fore.CYAN}¿Aplicar estas actualizaciones a config_trading.json? [s/N]: ").strip().lower()

    if confirmacion == 's':
        for c in cambios_pendientes:
            par = c['par']
            nuevo_cfg = c['new']
            pares_config[par]['estrategia'] = nuevo_cfg['estrategia']
            pares_config[par]['parametros_estrategia'] = nuevo_cfg['params']
            pares_config[par]['timeframe'] = nuevo_cfg['timeframe']
        
        guardar_config(config)
        print(f"\n{Fore.GREEN}✅ Configuración actualizada con éxito.")
    else:
        print(f"\n{Fore.RED}❌ Cambios cancelados.")

if __name__ == "__main__":
    main()