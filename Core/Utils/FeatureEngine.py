import pandas as pd
import pandas_ta as ta
import numpy as np

class FeatureEngine:
    """
    Clase centralizada para el cálculo de indicadores (Feature Engineering).
    Diseñada para ser utilizada tanto por el Core (Predicción en Vivo) 
    como por Machine Learning (Entrenamiento), garantizando la integridad de datos.
    """
    
    @staticmethod
    def generar_indicadores(df: pd.DataFrame) -> pd.DataFrame:
        """
        Calcula los indicadores técnicos estándar para el bot.
        Maneja copias para no mutar el dataframe original inesperadamente.
        """
        df = df.copy()

        # 1. Indicadores de Momento
        # RSI
        df['RSI'] = ta.rsi(df['close'], length=14)
        df['RSI'] = df['RSI'].fillna(50) 
        df['RSI_Slope'] = df['RSI'].diff(1) # Velocidad del cambio
        
        # Stochastic
        stoch = ta.stoch(df['high'], df['low'], df['close'])
        if stoch is not None:
            # Pandas TA devuelve columnas como STOCHk_14_3_3, STOCHd_14_3_3
            # Buscamos dinámicamente
            try:
                col_k = [c for c in stoch.columns if c.startswith('STOCHk')][0]
                df['Stoch_K'] = stoch[col_k]
            except IndexError:
                 df['Stoch_K'] = 50
        else:
            df['Stoch_K'] = 50

        # 2. Tendencia
        # EMA 200
        df['EMA_200'] = ta.ema(df['close'], length=200)
        df['Dist_EMA200'] = (df['close'] - df['EMA_200']) / df['close'] 
        
        # ADX
        adx = ta.adx(df['high'], df['low'], df['close'], length=14)
        if adx is not None:
            try:
                # ADX_14
                col_adx = [c for c in adx.columns if c.startswith('ADX') and not c.startswith('ADX_') is False][0]
                df['ADX'] = adx[col_adx]
            except IndexError:
                df['ADX'] = 0
        else:
            df['ADX'] = 0

        # 3. Volatilidad
        # ATR
        df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=14)
        df['ATR_Pct'] = df['ATR'] / df['close'] 
        
        # Bollinger Bands
        bb = ta.bbands(df['close'], length=20, std=2)
        if bb is not None:
            try:
                col_upper = [c for c in bb.columns if c.startswith('BBU')][0]
                col_lower = [c for c in bb.columns if c.startswith('BBL')][0]
                col_mid   = [c for c in bb.columns if c.startswith('BBM')][0]
                df['BB_Width'] = (bb[col_upper] - bb[col_lower]) / bb[col_mid]
            except IndexError:
                df['BB_Width'] = 0
        else:
            df['BB_Width'] = 0

        # 4. Volumen y Velas
        df['Vol_SMA_20'] = ta.sma(df['volume'], length=20)
        # Evitar división por cero
        df['RVOL'] = np.where(df['Vol_SMA_20'] != 0, df['volume'] / df['Vol_SMA_20'], 1.0)
        
        cuerpo = abs(df['close'] - df['open'])
        rango_total = df['high'] - df['low']
        # Evitar división por cero
        df['Cuerpo_Pct'] = np.where(rango_total != 0, cuerpo / rango_total, 0.0)

        # Limpieza final para inferencia (Relleno de NaNs incipientes)
        df.fillna(0, inplace=True)

        return df
