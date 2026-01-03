import pandas as pd
import numpy as np

class GestorAnalisis:
    """
    Especialista Matemático. 
    Transforma precios crudos en indicadores técnicos (RSI, EMA).
    """
    
    def __init__(self):
        pass

    def calcular_rsi(self, precios, periodo=14):
        """
        Calcula el Relative Strength Index (RSI).
        """
        if len(precios) < periodo + 1:
            return None
            
        series = pd.Series(precios)
        delta = series.diff()
        
        # Separar ganancias y pérdidas
        gain = (delta.where(delta > 0, 0)).rolling(window=periodo).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=periodo).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi.iloc[-1]

    def calcular_ema(self, precios, periodo=50):
        """
        Calcula la Media Móvil Exponencial (EMA).
        """
        if len(precios) < periodo:
            return None
            
        series = pd.Series(precios)
        ema = series.ewm(span=periodo, adjust=False).mean()
        
        return ema.iloc[-1]