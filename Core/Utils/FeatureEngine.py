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

        # 5. Indicadores Avanzados (Estrategias Mixtas)
        # -----------------------------------------------------
        
        # A. Canales de Keltner (Para Squeeze)
        # KC = EMA_20 +/- (1.5 * ATR)
        if 'ATR' in df.columns:
            ema_20 = ta.ema(df['close'], length=20)
            atr = df['ATR']
            df['KC_Upper'] = ema_20 + (1.5 * atr)
            df['KC_Lower'] = ema_20 - (1.5 * atr)
            
            # Squeeze: Bandas Bollinger DENTRO de Keltner
            if 'BBU_20_2.0' in df.columns and 'BBL_20_2.0' in df.columns:
                 # Nota: pandas-ta nombra columnas como BBU_20_2.0
                 pass 
            else:
                 # Recalcular si no existen (a veces FeatureEngine limpia nombres)
                 # Ya calculamos bb arriba, intentamos recuperar
                 pass

        # B. Momentum (Regresión Lineal) - TTM Squeeze Style
        # Delta = Close - Media(High, Low, SMA_20)
        # Momentum = LinReg(Delta, length=20)
        sma_20 = ta.sma(df['close'], length=20)
        avg_price = (df['high'] + df['low'] + sma_20) / 3
        delta_price = df['close'] - avg_price
        df['Lreg_Mom'] = ta.linreg(delta_price, length=20)

        # C. Patrones de Velas (Price Action)
        # C. Patrones de Velas (Price Action)
        try:
            # Engulfing (0=No, 100=Bull, -100=Bear)
            cdl_engulfing = ta.cdl_pattern(df['open'], df['high'], df['low'], df['close'], name="engulfing")
            if cdl_engulfing is not None and not cdl_engulfing.empty:
                 df['CDL_ENGULFING'] = cdl_engulfing.iloc[:, 0]
            else:
                 df['CDL_ENGULFING'] = 0

            # Hammer (100)
            cdl_hammer = ta.cdl_pattern(df['open'], df['high'], df['low'], df['close'], name="hammer")
            if cdl_hammer is not None and not cdl_hammer.empty:
                 df['CDL_HAMMER'] = cdl_hammer.iloc[:, 0]
            else:
                 df['CDL_HAMMER'] = 0

            # Shooting Star (-100)
            cdl_shooting = ta.cdl_pattern(df['open'], df['high'], df['low'], df['close'], name="shootingstar")
            if cdl_shooting is not None and not cdl_shooting.empty:
                 df['CDL_SHOOTING'] = cdl_shooting.iloc[:, 0]
            else:
                 df['CDL_SHOOTING'] = 0
        except Exception as e:
            # Fallback si falla TA-Lib
            df['CDL_ENGULFING'] = 0
            df['CDL_HAMMER'] = 0
            df['CDL_SHOOTING'] = 0

        # Limpieza final para inferencia (Relleno de NaNs incipientes)
        df.fillna(0, inplace=True)

        return df
