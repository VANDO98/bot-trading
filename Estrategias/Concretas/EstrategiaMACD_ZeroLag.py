import pandas as pd
import pandas_ta as ta
from Estrategias.EstrategiaBase import EstrategiaBase

class EstrategiaMACD_ZeroLag(EstrategiaBase):
    """
    Estrategia MACD con Zero Lag Mas (ZLMA)
    Reduce el retraso del MACD tradicional para entradas más rápidas.
    
    Lógica:
        - Construimos el MACD usando ZLMA en lugar de EMA.
    """

    def __init__(self, nombre, parametros_json):
        super().__init__(nombre, parametros_json)

    def calcular_indicadores(self):
        fast = self.parametros.get('macd_fast', 12)
        slow = self.parametros.get('macd_slow', 26)
        signal = self.parametros.get('macd_signal', 9)

        if len(self.velas) > slow + 5:
            # Calcular ZLMA (Zero Lag Moving Average)
            self.velas['zlma_fast'] = ta.zlma(self.velas['close'], length=fast)
            self.velas['zlma_slow'] = ta.zlma(self.velas['close'], length=slow)
            
            # Construcción manual del MACD ZeroLag
            self.velas['macd_zl'] = self.velas['zlma_fast'] - self.velas['zlma_slow']
            self.velas['signal_zl'] = ta.ema(self.velas['macd_zl'], length=signal)
            
            # Histograma para ver momentum (opcional, útil para filtros)
            self.velas['hist_zl'] = self.velas['macd_zl'] - self.velas['signal_zl']

    def generar_senal(self):
        if self.velas.empty or 'macd_zl' not in self.velas.columns:
            return "NEUTRO"
            
        macd_now = self.velas['macd_zl'].iloc[-1]
        sig_now = self.velas['signal_zl'].iloc[-1]
        
        macd_prev = self.velas['macd_zl'].iloc[-2]
        sig_prev = self.velas['signal_zl'].iloc[-2]
        
        if pd.isna(macd_now) or pd.isna(macd_prev):
            return "NEUTRO"

        # Cruce Alcista (Golden Cross)
        if macd_prev <= sig_prev and macd_now > sig_now:
            return "COMPRA"
        
        # Cruce Bajista (Death Cross)
        if macd_prev >= sig_prev and macd_now < sig_now:
            return "VENTA"
            
        return "NEUTRO"
