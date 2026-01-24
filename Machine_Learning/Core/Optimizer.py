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
    # --- ESTRATEGIAS EXISTENTES ---
    "EstrategiaRSI_ADX": {
        "rsi_periodo": [14],
        "rsi_sobreventa": [25, 30],
        "rsi_sobrecompra": [70, 75],
        "adx_minimo": [20, 25]
    },
    "EstrategiaBB": { # Bollinger Breakout
        "bb_length": [20],
        "bb_std": [2.0, 2.5]
    },
    "EstrategiaTrend": { # Cruce EMAs
        "ema_fast": [9, 20],
        "ema_slow": [50, 200],
        "adx_minimo": [20]
    },
    # --- NUEVAS ESTRATEGIAS ---
    "EstrategiaSuperTrend": {
        "length": [10, 14],
        "multiplier": [2.0, 3.0]
    },
    "EstrategiaMACD_ZeroLag": {
        "fast": [12],
        "slow": [26],
        "signal": [9]
    },
    "EstrategiaBollingerReversion": { # Mean Reversion
        "length": [20],
        "std": [2.0, 2.5]
    }
}

import sys
sys.path.append(os.path.join(BASE_DIR, "..", "..")) # Root
from Core.Utils.FeatureEngine import FeatureEngine
from Machine_Learning.Core.DataProcessor import simular_estrategia_real

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
    # NOTA: df ya viene con FeatureEngine y Targets calculados desde fuera
    
    df['senal'] = 0 
    
    # 2. Generar Señales (Lógica Vectorizada)
    # 2. Generar Señales (Lógica Vectorizada Centralizada)
    df['senal'] = FeatureEngine.generar_senal_estrategia(df, nombre_estrategia, params)
    
    # 3. Calcular WIN RATE usando lógica de Etiquetado Real
    # df ya tiene la columna 'TARGET' calculada en el bucle principal
    
    # 4. Filtrar solo las velas donde hubo señal
    señales = df[df['senal'] != 0]
    
    total_ops = len(señales)
    if total_ops < 5: return -999 # Descartar si opera muy poco
    
    win_rate = (señales['TARGET'].sum() / total_ops) * 100
    
    return win_rate

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
    print(f"{'PAR':<10} | {'ESTRATEGIA GANADORA':<30} | {'WR (%)':<8} | {'ESTADO'}")
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
                    
                # --- OPTIMIZACIÓN: Pre-calcular Feature Engineering y Targets ---
                # Calculamos esto UNA VEZ por par/tf, no por cada estrategia
                df = FeatureEngine.generar_indicadores(df)
                df.fillna(0, inplace=True)
                
                # Calculamos el "Ground Truth" (TARGET) una sola vez
                # Esto define si cada vela ERA una oportunidade ganadora (independiente de la estrategia)
                df = simular_estrategia_real(df)

            except Exception as e: 
                print(f"DEBUG ERROR leyendo {par}: {e}")
                continue

            for estrategia in GRID_PARAMETROS.keys():
                combinaciones = generar_combinaciones(estrategia)
                for params in combinaciones:
                    try:
                        # Pasamos el DF ya procesado
                        score = simular_estrategia(df.copy(), estrategia, params)
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
                print(f"{Fore.YELLOW}{par:<10} | {'BAJO WR / PÉRDIDAS':<30} | {score_str}")

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