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
        
        # Lógica simple de DataFrame (Concat o Append)
        df_nuevo = pd.DataFrame([nueva_fila])
        if self.velas.empty:
            self.velas = df_nuevo
        else:
            if nueva_fila['timestamp'] > self.velas.iloc[-1]['timestamp']:
                self.velas = pd.concat([self.velas, df_nuevo], ignore_index=True)
            else:
                self.velas.iloc[-1] = df_nuevo.iloc[0]

        if len(self.velas) > 100:
            self.velas = self.velas.iloc[-100:].reset_index(drop=True)

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