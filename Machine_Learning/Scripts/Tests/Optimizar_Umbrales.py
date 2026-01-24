
import pandas as pd
import numpy as np
import joblib
import sys
import os
import json
import pandas_ta as ta
from colorama import Fore, init, Style
import datetime

# --- PATH SETUP ---
current_dir = os.path.dirname(os.path.abspath(__file__)) # Scripts/Tests
scripts_dir = os.path.dirname(current_dir) # Scripts
ml_dir = os.path.dirname(scripts_dir) # Machine_Learning
root_dir = os.path.dirname(ml_dir) # Root (bot-trading)
sys.path.append(root_dir)

# Importamos utilidades existentes
from Core.Utils.FeatureEngine import FeatureEngine
from Core.Utils.Config import Config

init(autoreset=True)

# --- CONFIGURACIÓN ---
CARPETA_DATA = os.path.join(ml_dir, "Data", "Historico")
CONFIG_PATH = os.path.join(ml_dir, "..", "config_trading.json")

# Rango de umbrales a probar
UMBRALES_TEST = [0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90]

def cargar_config():
    with open(CONFIG_PATH, 'r') as f: return json.load(f)

def aplicar_estrategia_base(df, estrategia, params):
    """
    Wrapper para usar la lógica centralizada de FeatureEngine.
    Retorna una mascara booleana (True si hay señal de Compra o Venta).
    """
    senal = FeatureEngine.generar_senal_estrategia(df, estrategia, params)
    return senal != 0

def evaluar_par_multi_umbral(archivo_csv, modelo, columnas_modelo, estrategia_nombre, params):
    try:
        if not os.path.exists(archivo_csv): return None

        df = pd.read_csv(archivo_csv)
        if len(df) < 500: return None
        
        # 1. Preparar Datos (Feature Engineering GLOBAL)
        df = FeatureEngine.generar_indicadores(df)
        
        # 2. Agregar Features Específicas (CRÍTICO: El modelo necesita estas columnas)
        df = FeatureEngine.agregar_indicadores_estrategia(df, estrategia_nombre, params)
        
        # 3. Calcular Target Real (Validación)
        # Usamos la misma lógica que en el entrenamiento: Ganancia > 0.8% en 3 velas
        ventana_futura = 3
        umb_min = 0.008 # 0.8%
        
        df['retorno_futuro'] = df['close'].shift(-ventana_futura) / df['close'] - 1
        df['TARGET'] = (df['retorno_futuro'] > umb_min).astype(int)
        df.dropna(subset=['TARGET'], inplace=True)
        
        if df.empty: return None

        # 3. Filtrar por Estrategia Base
        mask_tecnica = aplicar_estrategia_base(df, estrategia_nombre, params)
        df_candidatas = df[mask_tecnica].copy()
        
        total_ops_base = len(df_candidatas)
        if total_ops_base == 0: return None
        
        wr_base = (df_candidatas['TARGET'].sum() / total_ops_base) * 100
        
        # 4. Predicción ML (Probabilidades)
        missing_cols = [c for c in columnas_modelo if c not in df_candidatas.columns]
        for c in missing_cols: df_candidatas[c] = 0
             
        X = df_candidatas[columnas_modelo]
        probs = modelo.predict_proba(X)[:, 1] # Probabilidad de ser clase 1 (Ganadora)
        y_real = df_candidatas['TARGET'].values
        
        resultados_par = []
        
        # 5. Iterar Umbrales
        for th in UMBRALES_TEST:
            # Seleccionar operaciones que superan el umbral th
            indices_aprobados = np.where(probs >= th)[0]
            num_ops_ml = len(indices_aprobados)
            
            if num_ops_ml > 0:
                aciertos = y_real[indices_aprobados].sum()
                wr_ml = (aciertos / num_ops_ml) * 100
            else:
                wr_ml = 0.0
                
            resultados_par.append({
                "umbral": th,
                "ops": num_ops_ml,
                "win_rate": wr_ml,
                "mejora": wr_ml - wr_base,
                "wr_base": wr_base,
                "ops_base": total_ops_base
            })
            
        return resultados_par

    except Exception as e:
        # print(f"Error evaluando: {e}")
        return None

def seleccionar_mejor_umbral(resultados_par):
    """
    Lógica de selección del ganador:
    1. Filtrar ops >= 10 (Muestra mínima). Si no hay, permitir ops >= 5.
    2. Ordenar por Win Rate descendente.
    3. Retornar el mejor.
    """
    if not resultados_par: return None
    
    # Convertir a DataFrame para fácil manejo
    df_res = pd.DataFrame(resultados_par)
    
    # Filtro de seguridad: Mínimo 10 operaciones para considerar el dato fiable
    candidatos = df_res[df_res['ops'] >= 10]
    
    # Si somos muy estrictos y no queda nada, bajamos la vara a 5 ops
    if candidatos.empty:
        candidatos = df_res[df_res['ops'] >= 5]
        
    # Si aun así no hay nada, devolvemos el que tenga ops > 0
    if candidatos.empty:
        candidatos = df_res[df_res['ops'] > 0]
        
    if candidatos.empty:
        # Si de verdad no hubo ninguna operación en ningún umbral
        return None
        
    # Ordenar: Prioridad 1: Win Rate, Prioridad 2: Mejora
    mejor = candidatos.sort_values(by=['win_rate', 'mejora'], ascending=[False, False]).iloc[0]
    return mejor

import argparse

def main():
    parser = argparse.ArgumentParser(description="Optimizar Umbrales")
    parser.add_argument("--auto", action="store_true", help="Actualizar config automáticamente sin preguntar")
    args = parser.parse_args()

    print(Fore.CYAN + "\n🔬 OPTIMIZADOR DE UMBRALES DE CONFIANZA (SCANNER)")
    print(f"Rango a testear: {UMBRALES_TEST}")
    print("=" * 120)
    print(f"{'PAR':<12} | {'ESTRATEGIA':<20} | {'BASE WR':<8} | {'MEJOR TH':<9} | {'OPS':<5} | {'NUEVO WR':<9} | {'MEJORA'}")
    print("=" * 120)
    
    config = cargar_config()
    todos_resultados = []
    
    for par, cfg in config.get('pares', {}).items():
        if not cfg.get('activo', False): continue
        
        simbolo = par.replace('/', '')
        tf = cfg.get('timeframe', '5m')
        
        # Cargar Modelo
        ruta_modelo = os.path.join(ml_dir, "Models", tf, f"modelo_{simbolo}.joblib")
        if not os.path.exists(ruta_modelo): continue
        
        try:
            rf_model = joblib.load(ruta_modelo)
            columnas = getattr(rf_model, "feature_names_in_", [])
            if len(columnas) == 0:
                 # Fallback
                 columnas = ['RSI', 'RSI_Slope', 'Stoch_K', 'Dist_EMA200', 'ADX', 'ATR_Pct', 'BB_Width', 'RVOL', 'Cuerpo_Pct']
        except: continue
        
        # Cargar Datos
        ruta_csv = os.path.join(CARPETA_DATA, tf, f"{simbolo}_{tf}.csv")
        
        # Evaluar
        res_list = evaluar_par_multi_umbral(ruta_csv, rf_model, columnas, cfg['estrategia'], cfg['parametros_estrategia'])
        
        # Seleccionar Mejor
        mejor = seleccionar_mejor_umbral(res_list)
        
        if mejor is not None:
            # Colores para la tabla
            color_th = Fore.YELLOW
            color_wr = Fore.GREEN if mejor['win_rate'] >= 60 else (Fore.RED if mejor['win_rate'] < 40 else Fore.WHITE)
            diff = mejor['mejora']
            color_diff = Fore.GREEN if diff > 0 else Fore.RED
            
            estrat_short = cfg['estrategia'].replace("Estrategia", "")[:20]
            
            print(f"{par:<12} | {estrat_short:<20} | {mejor['wr_base']:5.1f}%   | {color_th}{mejor['umbral']:<9}{Style.RESET_ALL} | {mejor['ops']:<5} | {color_wr}{mejor['win_rate']:5.1f}%{Style.RESET_ALL}    | {color_diff}{diff:+5.1f}%")
            
            todos_resultados.append({
                "par": par,
                "estrategia": cfg['estrategia'],
                "base_wr": mejor['wr_base'],
                "base_ops": mejor['ops_base'],
                "mejor_umbral": mejor['umbral'],
                "ml_ops": mejor['ops'],
                "ml_wr": mejor['win_rate'],
                "mejora": mejor['mejora']
            })
    
    print("-" * 120)
    
    if todos_resultados:
        df_final = pd.DataFrame(todos_resultados)
        
        # Guardar CSV
        history_dir = os.path.join(ml_dir, "Backtest_History", "Optimization_Reports")
        if not os.path.exists(history_dir): os.makedirs(history_dir)
        
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"optimization_report_{timestamp}.csv"
        filepath = os.path.join(history_dir, filename)
        
        df_final.to_csv(filepath, index=False)
        print(Fore.CYAN + f"\n💾 Reporte detallado guardado en: {filepath}")
        
        # Resumen Promedio
        prom_mejora = df_final['mejora'].mean()
        print(f"\n📈 Mejora Promedio Global: {Fore.GREEN if prom_mejora > 0 else Fore.RED}{prom_mejora:.2f}%")

        # --- AUTO UPDATE CONFIG ---
        proceder = False
        if args.auto:
            print(f"\n{Fore.MAGENTA}🤖 Modo Automático: Aplicando cambios sin preguntar...{Style.RESET_ALL}")
            proceder = True
        else:
            print("\n" + "="*60)
            print(f"{Fore.YELLOW}🔮 ¿Deseas aplicar estos UMBRALES al config_trading.json?{Style.RESET_ALL}")
            respuesta = input("Escribe 's' para confirmar: ").strip().lower()
            if respuesta == 's': proceder = True
        
        if proceder:
            try:
                with open(CONFIG_PATH, 'r') as f:
                    data = json.load(f)
                
                cambios = 0
                for item in todos_resultados:
                    par = item['par']
                    nuevo_th = item['mejor_umbral']
                    
                    if par in data['pares']:
                        data['pares'][par]['ml_threshold'] = float(nuevo_th)
                        print(f"✅ {par}: Threshold actualizado a {nuevo_th}")
                        cambios += 1
                
                with open(CONFIG_PATH, 'w') as f:
                    json.dump(data, f, indent=2)
                    
                print(f"\n✨ {Fore.GREEN}Configuración actualizada con éxito ({cambios} cambios).{Style.RESET_ALL}")
                
            except Exception as e:
                print(f"\n❌ Error actualizando config: {e}")
        else:
            print("\n👋 Operación cancelada. No se hicieron cambios en el config.")

if __name__ == "__main__":
    main()
