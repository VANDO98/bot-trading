import pandas as pd
import pandas_ta as ta
from Estrategias.EstrategiaBase import EstrategiaBase

class EstrategiaSuperTrend(EstrategiaBase):
    """
    Estrategia SuperTrend (Tendencia + Volatilidad)
    Ideal para capturar grandes movimientos y filtrar ruido lateral.
    
    Parámetros típicos:
        - length: 10 (Periodo ATR)
        - multiplier: 3.0 (Factor de multiplicación)
    """

    def __init__(self, nombre, parametros_json):
        super().__init__(nombre, parametros_json)

    def calcular_indicadores(self):
        length = self.parametros.get('st_length', 10)
        multiplier = self.parametros.get('st_multiplier', 3.0)

        if len(self.velas) > length:
            # pandas_ta.supertrend retorna 3 columnas: SUPERT_length_multiplier, SUPERTd_..., SUPERTl_...
            # SUPERTd_... es la dirección (1: Bullish/Green, -1: Bearish/Red)
            st = ta.supertrend(self.velas['high'], self.velas['low'], self.velas['close'], length=length, multiplier=multiplier)
            
            if st is not None:
                # Concatenamos al df principal para tenerlo disponible
                self.velas = pd.concat([self.velas, st], axis=1)
                
                # Identificamos el nombre dinámico de la columna de dirección 'SUPERTd_...'
                # Usualmente es la segunda columna retornada, pero mejor buscarla
                col_dir = next((c for c in st.columns if c.startswith('SUPERTd_')), None)
                if col_dir:
                    self.velas['ST_DIR'] = self.velas[col_dir] # -1 (Short), 1 (Long)

    def generar_senal(self):
        if self.velas.empty or 'ST_DIR' not in self.velas.columns:
            return "NEUTRO"
            
        st_dir = self.velas['ST_DIR'].iloc[-1]

        if pd.isna(st_dir):
            return "NEUTRO"

        # SuperTrend da señal continua.
        if st_dir == 1:
            return "COMPRA"
        elif st_dir == -1:
            return "VENTA"
            
        return "NEUTRO"
