import pandas as pd
import pandas_ta as ta
from Estrategias.EstrategiaBase import EstrategiaBase

class EstrategiaTrend(EstrategiaBase):
    """
    Estrategia de Seguimiento de Tendencia (Para Perfil: 'Gigantes')
    Lógica:
        - Si EMA Rápida > EMA Lenta -> COMPRA (Tendencia Alcista)
        - Si EMA Rápida < EMA Lenta -> VENTA (Tendencia Bajista)
    """

    def __init__(self, nombre, parametros_json):
        super().__init__(nombre, parametros_json)

    def calcular_indicadores(self):
        # Parámetros por defecto: Rápida 9, Lenta 21
        fast_len = self.parametros.get('ema_fast', 9)
        slow_len = self.parametros.get('ema_slow', 21)

        # Necesitamos data suficiente para la EMA lenta
        if len(self.velas) > slow_len:
            self.velas['EMA_FAST'] = ta.ema(self.velas['close'], length=fast_len)
            self.velas['EMA_SLOW'] = ta.ema(self.velas['close'], length=slow_len)

    def generar_senal(self):
        if self.velas.empty or 'EMA_SLOW' not in self.velas.columns:
            return "NEUTRO"
            
        ema_fast = self.velas['EMA_FAST'].iloc[-1]
        ema_slow = self.velas['EMA_SLOW'].iloc[-1]

        if pd.isna(ema_fast) or pd.isna(ema_slow):
            return "NEUTRO"

        # Lógica de Tendencia Pura
        # Nota: Retornamos la señal constante mientras se mantenga la tendencia.
        # El BotController se encargará de ignorarla si ya estamos dentro ('posicion_abierta').
        
        if ema_fast > ema_slow:
            return "COMPRA"
        elif ema_fast < ema_slow:
            return "VENTA"
            
        return "NEUTRO"