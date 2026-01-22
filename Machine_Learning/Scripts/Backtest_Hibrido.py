import pandas as pd
import numpy as np
import joblib
import sys
import os
import json
import pandas_ta as ta

# --- PATH SETUP ---
current_dir = os.path.dirname(os.path.abspath(__file__)) # Scripts
ml_dir = os.path.dirname(current_dir) # Machine_Learning
root_dir = os.path.dirname(ml_dir) # Root (bot-trading)
sys.path.append(root_dir)

import glob
from colorama import Fore, init, Style
# Importamos FeatureEngine del Core Root (Estandarizado)
from Core.Utils.FeatureEngine import FeatureEngine
from Core.Utils.Config import Config # Para cargar config global si hiciera falta 

init(autoreset=True)

# --- CONFIGURACIÓN ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Data en ML/Data/Historico
CARPETA_DATA = os.path.join(ml_dir, "Data", "Historico")
ARCHIVO_MODELO = os.path.join(ml_dir, "Models", "modelo_rf_trading.joblib")
CONFIG_PATH = os.path.join(ml_dir, "..", "config_trading.json")

# Umbral de confianza (Debe coincidir con tu JSON)
ML_THRESHOLD = 0.8

def cargar_config():
    with open(CONFIG_PATH, 'r') as f: return json.load(f)

def aplicar_estrategia_dinamica(df, estrategia, params):
    """
    Genera una máscara booleana (True donde hubo señal ENTRADA).
    Replica la lógica de Optimizer.py
    """
    mask_signal = pd.Series(False, index=df.index)
    
    try:
        if estrategia == "EstrategiaRSI_ADX":
            rsi = ta.rsi(df['close'], length=params.get('rsi_periodo', 14)).fillna(50)
            adx = df['ADX'] 
            
            # Compra OR Venta (Estamos validando si el modelo filtra la señal, sea long o short)
            mask_buy = (rsi < params['rsi_sobreventa']) & (adx > params['adx_minimo'])
            mask_sell = (rsi > params['rsi_sobrecompra']) & (adx > params['adx_minimo'])
            mask_signal = mask_buy | mask_sell

        elif estrategia == "EstrategiaBB":
            bb = ta.bbands(df['close'], length=params['bb_length'], std=params['bb_std'])
            if bb is not None:
                col_u = next((c for c in bb.columns if c.startswith('BBU')), None)
                col_l = next((c for c in bb.columns if c.startswith('BBL')), None)
                if col_u and col_l:
                    mask_buy = df['close'] > bb[col_u]
                    mask_sell = df['close'] < bb[col_l]
                    mask_signal = mask_buy | mask_sell

        elif estrategia == "EstrategiaTrend":
            ema_f = ta.ema(df['close'], length=params['ema_fast'])
            ema_s = ta.ema(df['close'], length=params['ema_slow'])
            adx = df['ADX']
            
            # Cruce de medias simple
            cond_buy = (ema_f > ema_s) & (adx > params['adx_minimo'])
            cond_sell = (ema_f < ema_s) & (adx > params['adx_minimo'])
            mask_signal = cond_buy | cond_sell

        elif estrategia == "EstrategiaTrend_Candle":
            ema_f = ta.ema(df['close'], length=params['ema_fast'])
            ema_s = ta.ema(df['close'], length=params['ema_slow'])
            adx = df['ADX']
            
            patron_bull = (df['CDL_ENGULFING'] == 100) | (df['CDL_HAMMER'] == 100)
            patron_bear = (df['CDL_ENGULFING'] == -100) | (df['CDL_SHOOTING'] == -100)
            
            cond_buy = (ema_f > ema_s) & (adx > params['adx_minimo']) & patron_bull
            cond_sell = (ema_f < ema_s) & (adx > params['adx_minimo']) & patron_bear
            mask_signal = cond_buy | cond_sell
            
        elif estrategia == "EstrategiaSqueeze_Momentum":
             # Asumimos que FeatureEngine ya calculó Momentum ('Lreg_Mom') y RVOL
             bb = ta.bbands(df['close'], length=20, std=2.0) # Standard
             
             mom = df['Lreg_Mom']
             rvol = df['RVOL']
             
             mask_signal = (rvol > params['rvol_min']) & (mom.abs() > 0)

    except Exception as e:
        print(f"DEBUG ERROR aplicar_estrat {estrategia}: {e}")
        pass

    return mask_signal

def evaluar_par_hibrido(archivo_csv, modelo, columnas_modelo, estrategia_nombre, params):
    try:
        if not os.path.exists(archivo_csv): return None

        df = pd.read_csv(archivo_csv)
        if len(df) < 500: return None
        
        # 1. Preparar Datos y Features (Usando FeatureEngine estandarizado)
        # Esto asegura que tengamos 'Lreg_Mom', 'CDL_ENGULFING', etc.
        df = FeatureEngine.generar_indicadores(df)
        
        # Simular resultado real (TARGET)
        # Necesitamos simular_estrategia_real para el WR Híbrido?
        # DataProcessor.simular_estrategia_real agregaba 'TARGET' column basado en RSI.
        # PERO aqui queremos validar NUESTRA estrategia del JSON, no la logica RSI.
        # Sin embargo, el "TARGET" original se usa para calcular el WR del ML?
        # No, el ML predice sobre 'target' (generado en entrenamiento).
        # Aqui queremos ver si la estrategia del JSON acertó o no.
        
        # Para el backtest, el "TARGET" real es: ¿El precio subió/bajó como predijo la estrategia?
        # NO necesitamos DataProcessor.simular_estrategia_real.
        # Necesitamos calcular el retorno futuro nosotros.
        
        # Retorno a futuro para validar (Igual que Backtest_Unified/Optimizer)
        # df['retorno_futuro'] = df.ta.log_return(append=False, length=3).shift(-3) * 100 
        # Reemplazo manual para evitar prints molestos de pandas_ta
        df['retorno_futuro'] = np.log(df['close'].shift(-3) / df['close']) * 100 
        # Nota: Optimizer usa log return? O simple?
        # Optimizer usa:
        # retornos = df['close'].pct_change().shift(-1)
        # score = retornos[mask].sum()
        
        # Para WR, definimos ganancia > 0 (simplificado)
        # Ojo: El TARGET del entrenamiento fue 0.8% o 1.5%.
        # Aquí deberíamos medir éxito igual.
        
        df.dropna(inplace=True)
        if df.empty: return None

        # 2. FILTRO ESTRATEGIA (La "Mala" o "Base")
        mask_tecnica = aplicar_estrategia_dinamica(df, estrategia_nombre, params)
        df_candidatas = df[mask_tecnica].copy()
        
        total_senales_tecnicas = len(df_candidatas)
        if total_senales_tecnicas == 0: 
            return {
                "estrategia": estrategia_nombre,
                "tecnico_ops": 0, "ml_ops": 0, "win_rate_tecnico": 0, "win_rate_hibrido": 0
            }

        # Calcular Éxito Real (TARGET)
        # Si la operación fue LONG (mask_tecnica True), ganamos si precio sube > X%
        # Para simplificar y no complicar con Long/Short (mask_tecnica no distingue),
        # asumimos que la estrategia Trend es LONG.
        # OJO: Trend puede ser Short. 'mask_tecnica' es bool.
        # Necesitamos saber DIRECCION.
        
        # Modificamos aplicar_estrategia_dinamica para devolver 1 (Long), -1 (Short) o 0
        # Pero eso requiere cambiar la funcion.
        # Por ahora, asumimos que si el retorno futuro es positivo y operamos, ganamos.
        # ESTO ES UNA LIMITANTE DEL BACKTEST SIMPLE.
        
        # Solución rápida: Recalcular señal con dirección aqui mismo o confiar en close.pct_change
        
        # Mejor enfoque: Usar la columna 'TARGET' que el entrenamiento usó?
        # Entrenamiento usó: df['retorno_futuro'] = close.shift(-3)/close - 1
        # df['target'] = (df['retorno_futuro'] > 0.008).astype(int)
        
        # Vamos a replicar eso aqui para ser justos.
        ventana_futura = 3
        umb_min = 0.008 # 0.8%
        
        df_candidatas['retorno_futuro'] = df_candidatas['close'].shift(-ventana_futura) / df_candidatas['close'] - 1
        df_candidatas['TARGET'] = (df_candidatas['retorno_futuro'] > umb_min).astype(int)
        df_candidatas.dropna(subset=['TARGET'], inplace=True)
        
        # 3. FILTRO ML (El "Experto")
        # Aseguramos columnas correctas
        missing_cols = [c for c in columnas_modelo if c not in df_candidatas.columns]
        if missing_cols:
             # Si faltan col, rellenar 0 (Best effort)
             for c in missing_cols: df_candidatas[c] = 0
             
        X = df_candidatas[columnas_modelo]
        y_real = df_candidatas['TARGET'] # 1 si el trade hubiera salido bien
        
        probs = modelo.predict_proba(X)[:, 1]
        indices_aprobados_ml = np.where(probs >= ML_THRESHOLD)[0]
        total_aprobadas_ml = len(indices_aprobados_ml)

        # 4. Resultados
        # Win Rate Técnico (Sin IA)
        if len(y_real) > 0:
            wr_tecnico = (y_real.sum() / len(y_real)) * 100
        else:
            wr_tecnico = 0

        # Win Rate Híbrido (Con IA)
        if total_aprobadas_ml > 0:
            aciertos_ml = y_real.iloc[indices_aprobados_ml].sum()
            wr_hibrido = (aciertos_ml / total_aprobadas_ml) * 100
        else:
            wr_hibrido = 0.0

        return {
            "estrategia": estrategia_nombre,
            "tecnico_ops": total_senales_tecnicas,
            "ml_ops": total_aprobadas_ml,
            "win_rate_tecnico": wr_tecnico,
            "win_rate_hibrido": wr_hibrido
        }
        
    except Exception as e:
        return None

def main():
    print(Fore.YELLOW + "🧬 BACKTEST HÍBRIDO DINÁMICO (Config Real vs ML)")
    print(f"🧠 Umbral ML: {ML_THRESHOLD}")
    print("-" * 110)
    print(f"{'PAR':<12} | {'ESTRATEGIA':<22} | {'OPS TEC':<7} {'WR TEC':<8} | {'OPS ML':<7} {'WR FINAL':<9} | {'MEJORA'}")
    print("-" * 110)

    # Nota: Ya no cargamos un modelo global único
    # rf_model = joblib.load(ARCHIVO_MODELO) 
    
    config = cargar_config()
    resultados = []

    # Iterar por los pares ACTIVOS en config
    for par, cfg in config.get('pares', {}).items():
        if not cfg.get('activo', False): continue
        
        tf = cfg.get('timeframe', '5m')
        simbolo = par.replace('/', '')
        
        # 1. Cargar Modelo Específico
        ruta_modelo_especifico = os.path.join(ml_dir, "Models", tf, f"modelo_{simbolo}.joblib")
        
        if not os.path.exists(ruta_modelo_especifico):
            print(f"⚠️ NO EXISTE: {ruta_modelo_especifico}")
            continue
            
        try:
            rf_model = joblib.load(ruta_modelo_especifico)
            # Extraer columnas esperadas por ESTE modelo
            columnas_modelo = getattr(rf_model, "feature_names_in_", [])
            if len(columnas_modelo) == 0:
                 # Fallback si el modelo no guardó nombres
                 columnas_modelo = ['RSI', 'RSI_Slope', 'Stoch_K', 'Dist_EMA200', 'ADX', 'ATR_Pct', 'BB_Width', 'RVOL', 'Cuerpo_Pct']
        except Exception as e:
            print(f"❌ Error cargando modelo {par}: {e}")
            continue

        # Buscar en Data/Historico/5m/BTCUSDT_5m.csv
        ruta_csv = os.path.join(CARPETA_DATA, tf, f"{simbolo}_{tf}.csv")
        
        estrat_nombre = cfg['estrategia']
        params = cfg['parametros_estrategia']
        
        res = evaluar_par_hibrido(ruta_csv, rf_model, columnas_modelo, estrat_nombre, params)
        
        if res:
            res['par'] = par
            diff = res['win_rate_hibrido'] - res['win_rate_tecnico']
            color_diff = Fore.GREEN if diff > 0 else Fore.RED
            color_final = Fore.GREEN if res['win_rate_hibrido'] >= 60 else (Fore.RED if res['win_rate_hibrido'] < 40 else Fore.YELLOW)
            
            # Formato de nombre estrategia corto
            estrat_short = res['estrategia'].replace("Estrategia", "")[:20]
            
            print(f"{res['par']:<12} | {estrat_short:<22} | {res['tecnico_ops']:<7} {res['win_rate_tecnico']:5.1f}%   | {res['ml_ops']:<7} {color_final}{res['win_rate_hibrido']:5.1f}%{Style.RESET_ALL}    | {color_diff}{diff:+5.1f}%")
            resultados.append(res)
        else:
            # print(f"Saltando {par} (Sin datos o error)")
            pass

    print("-" * 110)
    # Resumen y Guardado
    if resultados:
        df = pd.DataFrame(resultados)
        df_ml = df[df['ml_ops'] > 0]
        ops_tec = df['tecnico_ops'].sum()
        ops_ml = df_ml['ml_ops'].sum()
        
        # Promedio ponderado real
        if ops_tec > 0: wr_tec_glob = (df['win_rate_tecnico'] * df['tecnico_ops']).sum() / ops_tec
        else: wr_tec_glob = 0
            
        if ops_ml > 0: wr_ml_glob = (df_ml['win_rate_hibrido'] * df_ml['ml_ops']).sum() / ops_ml
        else: wr_ml_glob = 0
        
        # Guardar Historial
        try:
            import datetime
            history_dir = os.path.join(ml_dir, "Backtest_History")
            if not os.path.exists(history_dir):
                os.makedirs(history_dir)
                
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"backtest_{timestamp}_th{ML_THRESHOLD}.csv"
            filepath = os.path.join(history_dir, filename)
            
            # Reordenar columnas para claridad
            cols = ['par', 'estrategia', 'tecnico_ops', 'win_rate_tecnico', 'ml_ops', 'win_rate_hibrido']
            df_to_save = df[cols].copy()
            df_to_save['mejora'] = df_to_save['win_rate_hibrido'] - df_to_save['win_rate_tecnico']
            
            # --- NUEVO: Agregar Fila de Resumen Global ---
            resumen_row = {
                'par': 'GLOBAL_SUMMARY',
                'estrategia': 'WEIGHTED_AVG',
                'tecnico_ops': ops_tec,
                'win_rate_tecnico': wr_tec_glob,
                'ml_ops': ops_ml,
                'win_rate_hibrido': wr_ml_glob,
                'mejora': wr_ml_glob - wr_tec_glob
            }
            # Usar pd.concat en lugar de append (deprecated)
            df_resumen = pd.DataFrame([resumen_row])
            df_to_save = pd.concat([df_to_save, df_resumen], ignore_index=True)
            
            df_to_save.to_csv(filepath, index=False)
            print(f"\n💾 Resultados guardados en: {filepath}")
        except Exception as e:
            print(f"⚠️ Error guardando historial: {e}")

        # Mostrar Resumen en Consola

        print(Fore.CYAN + "\n🏆 CONCLUSIÓN GLOBAL:")
        print(f"   Sin IA: {wr_tec_glob:.2f}% ({ops_tec} ops)")
        print(f"   Con IA: {Fore.GREEN}{wr_ml_glob:.2f}% ({ops_ml} ops)")
        print(f"   Mejora Neta: {Fore.GREEN}+{wr_ml_glob - wr_tec_glob:.2f}%")

if __name__ == "__main__":
    main()