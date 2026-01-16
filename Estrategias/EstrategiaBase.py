from abc import ABC, abstractmethod
import pandas as pd

class EstrategiaBase(ABC):
    """
    Clase Abstracta: Define el 'molde' obligatorio para todas las estrategias.
    """
    
    def __init__(self, nombre, parametros_json):
        self.nombre = nombre
        self.parametros = parametros_json
        self.velas = pd.DataFrame() 
        self.posicion_abierta = False

    def recibir_vela(self, simbolo, kline_data):
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
                # CASO A: Es una vela nueva -> Concatenamos (Pandas maneja las columnas nuevas rellenando con NaN)
                self.velas = pd.concat([self.velas, df_nuevo], ignore_index=True)
            else:
                # CASO B: Es la misma vela actualizándose (Intrabarra) -> Actualización Quirúrgica
                # CORRECCIÓN: No reemplazamos la fila entera para no borrar el RSI o fallar por tamaño.
                # Solo actualizamos las columnas que trae df_nuevo (Open, High, Low, Close, etc.)
                for col in df_nuevo.columns:
                    if col in self.velas.columns:
                        # Buscamos el índice numérico de la columna para usar iloc
                        col_idx = self.velas.columns.get_loc(col)
                        self.velas.iloc[-1, col_idx] = df_nuevo.iloc[0][col]

        # Mantener memoria controlada (1000 velas)
        if len(self.velas) > 1000:
            self.velas = self.velas.iloc[-1000:].reset_index(drop=True)

        # Recalcular indicadores (Aquí se rellena la columna RSI de nuevo)
        self.calcular_indicadores()
        
        if nueva_fila['cerrada']:
            return self.generar_senal()
        return "NEUTRO"

    @abstractmethod
    def calcular_indicadores(self):
        pass

    @abstractmethod
    def generar_senal(self):
        pass