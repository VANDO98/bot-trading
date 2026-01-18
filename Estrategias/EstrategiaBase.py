from abc import ABC, abstractmethod
import pandas as pd

class EstrategiaBase(ABC):
    """
    Clase Abstracta: Define el 'molde' obligatorio para todas las estrategias.
    Mantiene la lógica de actualización intra-vela y agrega herramientas comunes (ATR).
    """
    
    def __init__(self, nombre, parametros_json):
        self.nombre = nombre
        self.parametros = parametros_json
        self.velas = pd.DataFrame() 
        self.posicion_abierta = False # Memoria de estado para el BotController

        # --- NUEVA VARIABLE ---
        self.atr_actual = 0.0 # Aquí guardaremos el último cálculo

    # Tienes que agregar 'ejecutar_analisis=True' aquí 👇
    def recibir_vela(self, simbolo, kline_data, ejecutar_analisis=True):
        """Procesa la vela entrante y actualiza el DataFrame interno"""
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
            ultimo_idx = self.velas.index[-1]
            ultimo_time = self.velas.iloc[-1]['timestamp']

            if nueva_fila['timestamp'] > ultimo_time:
                # CASO A: Es una vela nueva -> Concatenamos
                self.velas = pd.concat([self.velas, df_nuevo], ignore_index=True)
            else:
                # CASO B: Es la misma vela actualizándose (Intrabarra)
                for col in df_nuevo.columns:
                    if col in self.velas.columns:
                        col_idx = self.velas.columns.get_loc(col)
                        self.velas.iloc[-1, col_idx] = df_nuevo.iloc[0][col]

        # Mantener memoria controlada (1000 velas)
        if len(self.velas) > 1000:
            self.velas = self.velas.iloc[-1000:].reset_index(drop=True)

        # --- CAMBIO IMPORTANTE: MODO HIBERNACIÓN ---
        # Ahora sí funcionará porque la variable viene de los argumentos
        if not ejecutar_analisis:
            return "HIBERNANDO" 

        # Recalcular indicadores (Solo si estamos activos)
        self.calcular_indicadores()
        
        if nueva_fila['cerrada']:
            return self.generar_senal()
            
        return "NEUTRO"

    # --- NUEVO MÉTODO INYECTADO (Fase 6) ---
    def calcular_atr(self, periodo=14):
        """
        Calcula el Average True Range (Volatilidad) manualmente.
        Usado por el BotController para el Trailing Stop.
        """
        if self.velas.empty or len(self.velas) < periodo + 1:
            self.atr_actual = 0.0 # Reset si no hay datos
            return 0.0

        try:
            # Trabajamos con una copia para no ensuciar el DF principal si no queremos
            df = self.velas.copy()
            df['h-l'] = df['high'] - df['low']
            df['h-pc'] = abs(df['high'] - df['close'].shift(1))
            df['l-pc'] = abs(df['low'] - df['close'].shift(1))
            df['tr'] = df[['h-l', 'h-pc', 'l-pc']].max(axis=1)
            atr_val = df['tr'].rolling(window=periodo).mean().iloc[-1]
            
            # --- GUARDADO EN MEMORIA ---
            self.atr_actual = float(atr_val)
            
            return self.atr_actual
        except Exception as e:
            print(f"⚠️ Error calculando ATR en {self.nombre}: {e}")
            self.atr_actual = 0.0
            return 0.0
    # ---------------------------------------

    @abstractmethod
    def calcular_indicadores(self):
        pass

    @abstractmethod
    def generar_senal(self):
        pass