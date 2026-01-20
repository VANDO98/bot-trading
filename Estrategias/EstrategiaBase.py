from abc import ABC, abstractmethod
import pandas as pd
from colorama import Fore

class EstrategiaBase(ABC):
    """
    Clase Abstracta: Define el 'molde' obligatorio para todas las estrategias.
    Mantiene la lógica de actualización intra-vela y agrega herramientas comunes (ATR).
    """
    
    def __init__(self, nombre, parametros_json):
        self.nombre = nombre
        self.parametros = parametros_json
        
        # Inicializamos el DataFrame con las columnas correctas para evitar warnings futuros
        self.velas = pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'cerrada'])
        self.posicion_abierta = False # Memoria de estado para el BotController

        # --- Variable para Gestión de Riesgo (Fase 6) ---
        self.atr_actual = 0.0 

    def recibir_vela(self, simbolo, kline_data, ejecutar_analisis=True):
        """Procesa la vela entrante y actualiza el DataFrame interno"""
        try:
            nueva_fila = {
                'timestamp': pd.to_datetime(kline_data['t'], unit='ms'),
                'open': float(kline_data['o']),
                'high': float(kline_data['h']),
                'low': float(kline_data['l']),
                'close': float(kline_data['c']),
                'volume': float(kline_data['v']),
                'cerrada': kline_data['x']
            }
            
            df_nuevo = pd.DataFrame([nueva_fila])
            
            if self.velas.empty:
                self.velas = df_nuevo
            else:
                ultimo_time = self.velas.iloc[-1]['timestamp']

                if nueva_fila['timestamp'] > ultimo_time:
                    # CASO A: Es una vela nueva -> Concatenamos
                    self.velas = pd.concat([self.velas, df_nuevo], ignore_index=True)
                else:
                    # CASO B: Es la misma vela actualizándose (Intrabarra) -> Update Rápido
                    # Usamos los índices directos para mayor velocidad que iterar columnas
                    idx = self.velas.index[-1]
                    self.velas.loc[idx, ['open', 'high', 'low', 'close', 'volume']] = [
                        nueva_fila['open'], nueva_fila['high'], nueva_fila['low'], 
                        nueva_fila['close'], nueva_fila['volume']
                    ]

            # Mantener memoria controlada (Optimización: Solo recortar si excede por mucho para no fragmentar)
            if len(self.velas) > 1050: 
                self.velas = self.velas.iloc[-1000:].reset_index(drop=True)

            # --- MODO HIBERNACIÓN (Warmup) ---
            # Si estamos solo cargando datos históricos, no calculamos indicadores pesados
            if not ejecutar_analisis:
                return "HIBERNANDO" 

            # Recalcular indicadores (Solo si estamos activos)
            self.calcular_indicadores()
            
            # Solo generamos señal si la vela cerró (Evitar repintado)
            if nueva_fila['cerrada']:
                # Actualizamos ATR para que el BotController tenga el dato fresco para el StopLoss
                self.calcular_atr() 
                return self.generar_senal()
                
            return "NEUTRO"
            
        except Exception as e:
            print(f"{Fore.RED}❌ Error crítico en EstrategiaBase ({self.nombre}): {e}")
            return "NEUTRO"

    # --- MÉTODO COMPARTIDO DE GESTIÓN DE RIESGO ---
    def calcular_atr(self, periodo=14):
        """
        Calcula el Average True Range (Volatilidad).
        El BotController lo leerá de 'self.atr_actual' para definir Stop Loss dinámicos.
        """
        if self.velas.empty or len(self.velas) < periodo + 2:
            self.atr_actual = 0.0 
            return 0.0

        try:
            # Cálculo vectorizado eficiente sin copias innecesarias
            high = self.velas['high']
            low = self.velas['low']
            close_prev = self.velas['close'].shift(1)
            
            tr1 = high - low
            tr2 = (high - close_prev).abs()
            tr3 = (low - close_prev).abs()
            
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(window=periodo).mean()
            
            self.atr_actual = float(atr.iloc[-1]) if not pd.isna(atr.iloc[-1]) else 0.0
            return self.atr_actual
            
        except Exception as e:
            # Silencioso para no ensuciar logs, retorna 0 y el bot usará % fijo
            print(f"⚠️ Error calculando ATR en {self.nombre}: {e}")
            self.atr_actual = 0.0
            return 0.0

    @abstractmethod
    def calcular_indicadores(self):
        pass

    @abstractmethod
    def generar_senal(self):
        pass