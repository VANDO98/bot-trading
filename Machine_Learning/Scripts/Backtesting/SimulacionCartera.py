
import pandas as pd
import numpy as np
import sys
import os
import json
import datetime
import joblib
import warnings
from colorama import Fore, init, Style

warnings.filterwarnings("ignore", category=UserWarning)

# --- PATH SETUP ---
current_dir = os.path.dirname(os.path.abspath(__file__)) # Scripts/Backtesting
scripts_dir = os.path.dirname(current_dir) # Scripts
ml_dir = os.path.dirname(scripts_dir) # Machine_Learning
root_dir = os.path.dirname(ml_dir) # Root (bot-trading)
sys.path.append(root_dir)

from Core.Utils.Config import Config
from Core.Utils.FeatureEngine import FeatureEngine
from Core.Utils.GestorPrediccion import GestorPrediccion

init(autoreset=True)

class SimuladorCartera:
    def __init__(self):
        self.config = Config.cargar_configuracion()
        self.saldo_inicial = 200.0
        self.saldo_actual = self.saldo_inicial
        self.historial_trades = []
        
        # Estado de Cartera
        self.trades_abiertos = [] # Lista de objetos trade
        self.max_trades = self.config['configuracion_global'].get('max_trades_abiertos', 5)
        
        # Cargar Modelos (Usamos GestorPrediccion para esto)
        self.gestor = GestorPrediccion()
        
        print(f"{Fore.CYAN}🧪 INICIANDO SCANNERS DE CARTERA V3")
        print(f"💰 Capital Inicial: {self.saldo_inicial} USDT")
        print(f"🚦 Max Trades Simultáneos: {self.max_trades}")
        print("="*80)

    def cargar_datos_par(self, par, config_par):
        """Carga y Prepara datos para un par específico"""
        try:
            simbolo = par.replace('/', '')
            tf = config_par['timeframe']
            
            # Ruta Historico
            ruta_csv = os.path.join(ml_dir, "Data", "Historico", tf, f"{simbolo}_{tf}.csv")
            if not os.path.exists(ruta_csv): return None
            
            df = pd.read_csv(ruta_csv)
            if len(df) < 500: return None
            
            # 1. Feature Engineering (Igual que en Training)
            df = FeatureEngine.generar_indicadores(df)
            df = FeatureEngine.agregar_indicadores_estrategia(df, config_par['estrategia'], config_par['parametros_estrategia'])
            
            # 2. Generar Señal Técnica
            # Usamos generar_senal_estrategia que devuelve 1 (Buy), -1 (Sell), 0 (Nada)
            df['senal'] = FeatureEngine.generar_senal_estrategia(df, config_par['estrategia'], config_par['parametros_estrategia'])
            
            # Convertir timestamp a datetime para ordenar eventos
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # --- FIX CRÍTICO: Reset Index ---
            # Para garantizar que df.iloc[idx] coincida con la fila correcta (idx posicional)
            df.reset_index(drop=True, inplace=True)
            
            return df
        except Exception as e:
            print(f"Error cargando {par}: {e}")
            return None

    def ejecutar_simulacion(self):
        # 1. RECOLECTAR TODAS LAS SEÑALES POTENCIALES
        eventos_mercado = [] 
        mapa_datos = {}
        
        print(f"📥 Cargando datos históricos y generando señales...")
        
        pares_activos = {k: v for k, v in self.config['pares'].items() if v.get('activo', False)}
        
        for par, cfg in pares_activos.items():
            df = self.cargar_datos_par(par, cfg)
            if df is not None:
                mapa_datos[par] = df
                
                # Recolectar señales (df ya tiene index limpio 0..N)
                señales = df[df['senal'] != 0]
                
                for idx, row in señales.iterrows():
                    # idx es ahora posicional gracias a reset_index
                    eventos_mercado.append({
                        'timestamp': row['timestamp'],
                        'par': par,
                        'tipo': 'ENTRY_SIGNAL',
                        'senal': row['senal'],
                        'idx_df': idx, 
                        'data_row': row
                    })
        
        # Ordenar cronológicamente
        eventos_mercado.sort(key=lambda x: x['timestamp'])
        print(f"⚡ {len(eventos_mercado)} señales técnicas detectadas. Filtrando con IA...")
        
        # 2. BUCLE TEMPORAL
        trades_cerrados_historia = []
        total_eventos = len(eventos_mercado)
        
        for i, evento in enumerate(eventos_mercado):
            if i % 100 == 0:
                print(f"⏳ Procesando evento {i}/{total_eventos} (Trades activos: {len(self.trades_abiertos)})...", end='\r')
            
            timestamp_actual = evento['timestamp']
            par = evento['par']
            
            # A. GESTIÓN DE SALIDAS (Trades Abiertos)
            # Revisar si algún trade abierto termina antes de este momento
            for trade in self.trades_abiertos[:]: 
                if timestamp_actual >= trade['fecha_salida_estimada']:
                    self.trades_abiertos.remove(trade)
                    self.saldo_actual += trade['pnl_usdt']
                    trades_cerrados_historia.append(trade)

            # B. GESTIÓN DE ENTRADAS (Si hay cupo)
            if len(self.trades_abiertos) < self.max_trades:
                
                cfg_par = self.config['pares'][par]
                umbral = cfg_par.get('ml_threshold', 0.65)
                
                # Obtener modelo (Usando el monkey patch corregido)
                modelo = self.gestor._cargar_modelo_fast(par, cfg_par['timeframe'])
                
                if modelo:
                    features_modelo = getattr(modelo, "feature_names_in_", [])
                    if len(features_modelo) > 0:
                        try:
                            # Extraer X
                            row = evento['data_row']
                            # Reordenar columnas para coincidir con modelo y crear DataFrame para evitar warnings
                            X_array = row[features_modelo].values.reshape(1, -1)
                            X_input = pd.DataFrame(X_array, columns=features_modelo)
                            
                            prob = modelo.predict_proba(X_input)[0][1]
                            
                            if prob >= umbral:
                                # ENTRADA APROBADA
                                res_trade = self.simular_outcome_trade(
                                    par, 
                                    evento['idx_df'], 
                                    mapa_datos[par], 
                                    evento['senal'],
                                    cfg_par
                                )
                                
                                monto_entrada = self.calcular_tamano_posicion(par, self.saldo_actual)
                                pnl_usdt = monto_entrada * res_trade['roi_pct'] * cfg_par.get('apalancamiento', 1)
                                
                                nuevo_trade = {
                                    'par': par,
                                    'timestamp_entrada': timestamp_actual,
                                    'fecha_salida_estimada': res_trade['timestamp_salida'],
                                    'pnl_usdt': pnl_usdt,
                                    'roi': res_trade['roi_pct'],
                                    'tipo': 'LONG' if evento['senal'] == 1 else 'SHORT'
                                }
                                
                                self.trades_abiertos.append(nuevo_trade)
                                
                        except Exception:
                            pass 

        # Cierre final
        for trade in self.trades_abiertos:
            self.saldo_actual += trade['pnl_usdt']
            trades_cerrados_historia.append(trade)

        self.generar_reporte(trades_cerrados_historia)

    def simular_outcome_trade(self, par, idx_entrada, df, senal, config):
        """Simula trade futuro"""
        riesgo = self.config['sistema_riesgo']
        sl_pct = riesgo.get('stop_loss_pct', 0.02)
        tp_pct = riesgo.get('take_profit_pct', 0.50) 
        ts_trigger = riesgo.get('activacion_break_even_roe', 0.05) 
        
        ventana_max = 200 
        subset = df.iloc[idx_entrada+1 : idx_entrada+1+ventana_max]
        
        entry_price = df.iloc[idx_entrada]['close'] 
        fecha_entrada = df.iloc[idx_entrada]['timestamp']
        
        es_long = (senal == 1)
        
        sl_precio = entry_price * (1 - sl_pct) if es_long else entry_price * (1 + sl_pct)
        
        for i, row in subset.iterrows():
            current_low = row['low']
            current_high = row['high']
            
            roi_flotante = (current_high - entry_price)/entry_price if es_long else (entry_price - current_low)/entry_price
            
            # SL Check
            if es_long:
                if current_low <= sl_precio:
                    return {'timestamp_salida': row['timestamp'], 'roi_pct': (sl_precio - entry_price)/entry_price}
            else:
                if current_high >= sl_precio:
                    return {'timestamp_salida': row['timestamp'], 'roi_pct': (entry_price - sl_precio)/entry_price}
            
            # Trailing Simple
            if roi_flotante > ts_trigger:
                if es_long:
                    nuevo_sl = entry_price + (current_high - entry_price) * 0.5
                    if nuevo_sl > sl_precio: sl_precio = nuevo_sl
                else:
                    nuevo_sl = entry_price - (entry_price - current_low) * 0.5
                    if nuevo_sl < sl_precio: sl_precio = nuevo_sl

        # Time Limit
        if len(subset) > 0:
            last_close = subset.iloc[-1]['close']
            roi_final = (last_close - entry_price)/entry_price if es_long else (entry_price - last_close)/entry_price
            return {'timestamp_salida': subset.iloc[-1]['timestamp'], 'roi_pct': roi_final}
        else:
            return {'timestamp_salida': fecha_entrada, 'roi_pct': 0.0}

    def calcular_tamano_posicion(self, par, saldo):
        regla = self.config['pares'][par].get('cantidad_operacion', '10%')
        if isinstance(regla, str) and '%' in regla:
            pct = float(regla.replace('%', '')) / 100
            return saldo * pct
        else:
            return float(regla)

    def generar_reporte(self, trades):
        print("\n" + "="*80)
        print(f"📊 REPORTE FINAL DE SIMULACIÓN (BACKTEST REALISTA)")
        print("="*80)
        
        total_trades = len(trades)
        if total_trades == 0:
            print("No hubo operaciones.")
            return
            
        ganadoras = [t for t in trades if t['pnl_usdt'] > 0]
        perdedoras = [t for t in trades if t['pnl_usdt'] <= 0]
        
        win_rate = len(ganadoras) / total_trades * 100
        pnl_total = self.saldo_actual - self.saldo_inicial
        roi_total = (pnl_total / self.saldo_inicial) * 100
        
        color_pnl = Fore.GREEN if pnl_total > 0 else Fore.RED
        
        print(f"🔹 Saldo Inicial:   {self.saldo_inicial:.2f} USDT")
        print(f"🔹 Saldo Final:     {color_pnl}{self.saldo_actual:.2f} USDT{Style.RESET_ALL}")
        print(f"📈 ROI Total:       {color_pnl}{roi_total:.2f}%{Style.RESET_ALL}")
        print(f"🔢 Total Trades:    {total_trades}")
        print(f"🎯 Win Rate:        {win_rate:.1f}%")
        print(f"✅ Ganadoras:       {len(ganadoras)}")
        print(f"❌ Perdedoras:      {len(perdedoras)}")
        
        trades.sort(key=lambda x: x['pnl_usdt'], reverse=True)
        print("\n🏆 Top 3 Mejores Operaciones:")
        for t in trades[:3]:
            print(f"   {t['par']} ({t['tipo']}): +{t['pnl_usdt']:.2f} USDT")

# --- MONKEY PATCHING ---
# Definido fuera de la clase
def _cargar_modelo_fast(self, simbolo, timeframe):
    import joblib 
    clave = f"{simbolo}_{timeframe}"
    if clave in self.modelos_cache: return self.modelos_cache[clave]
    
    clean_sym = simbolo.replace('/', '')
    path = os.path.join(self.model_dir, timeframe, f"modelo_{clean_sym}.joblib")
    if os.path.exists(path):
        try:
            m = joblib.load(path)
            self.modelos_cache[clave] = m
            return m
        except: return None
    return None

# Asignar al Gestor
GestorPrediccion._cargar_modelo_fast = _cargar_modelo_fast

if __name__ == "__main__":
    sim = SimuladorCartera()
    sim.ejecutar_simulacion()
