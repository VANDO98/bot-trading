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

    @staticmethod
    def agregar_indicadores_estrategia(df: pd.DataFrame, estrategia: str, params: dict) -> pd.DataFrame:
        """
        Calcula indicadores Específicos según la estrategia seleccionada.
        Centraliza la lógica para que TrainModel y otros scripts no tengan que saber detalles.
        """
        df = df.copy()

        # 1. EstrategiaTrend
        if estrategia == "EstrategiaTrend":
            df['EMA_F'] = ta.ema(df['close'], length=params.get('ema_fast', 9))
            df['EMA_S'] = ta.ema(df['close'], length=params.get('ema_slow', 21))
            df['distancia_emas'] = (df['EMA_F'] - df['EMA_S']) / df['close']

        # 2. EstrategiaBB (Breakout)
        elif estrategia == "EstrategiaBB":
            if 'bb_length' in params:
                bb = ta.bbands(df['close'], length=params.get('bb_length', 20), std=params.get('bb_std', 2.0))
                if bb is not None:
                    col_u = next((c for c in bb.columns if c.startswith('BBU')), None)
                    col_l = next((c for c in bb.columns if c.startswith('BBL')), None)
                    if col_u and col_l:
                        df['dist_upper'] = df['close'] - bb[col_u]
                        df['dist_lower'] = df['close'] - bb[col_l]
        
        # 3. EstrategiaRSI_ADX (Reversion)
        elif estrategia == "EstrategiaRSI_ADX":
            if 'rsi_periodo' in params:
                df['RSI'] = ta.rsi(df['close'], length=params.get('rsi_periodo', 14)).fillna(50)
                df['RSI_Slope'] = df['RSI'].diff(1)
            
            if 'adx_periodo' in params:
                adx = ta.adx(df['high'], df['low'], df['close'], length=params.get('adx_periodo', 14))
                if adx is not None:
                     col_adx = next((c for c in adx.columns if c.startswith('ADX') and not c.startswith('ADX_') is False), None)
                     if col_adx: df['ADX'] = adx[col_adx].fillna(0)

        # 4. EstrategiaTrend_Candle
        elif estrategia == "EstrategiaTrend_Candle":
            df['EMA_F'] = ta.ema(df['close'], length=params.get('ema_fast', 20))
            df['EMA_S'] = ta.ema(df['close'], length=params.get('ema_slow', 50))
            df['distancia_emas'] = (df['EMA_F'] - df['EMA_S']) / df['close']
            # Los patrones de velas ya vienen de generar_indicadores (base)
        
        # 5. EstrategiaSqueeze_Momentum
        elif estrategia == "EstrategiaSqueeze_Momentum":
            # FeatureEngine base ya tiene Lreg_Mom, RVOL. 
            # Recalcular BB localmente para distancias exactas si params custom
            bb = ta.bbands(df['close'], length=20, std=2.0)
            col_u = next((c for c in bb.columns if c.startswith('BBU')), None)
            col_l = next((c for c in bb.columns if c.startswith('BBL')), None)
            
            if col_u and col_l:
                df['dist_BBU'] = df['close'] - bb[col_u] 
                df['dist_BBL'] = df['close'] - bb[col_l]
            else:
                df['dist_BBU'] = 0; df['dist_BBL'] = 0

        # --- NUEVAS ESTRATEGIAS ---

        # 6. EstrategiaSuperTrend
        elif estrategia == "EstrategiaSuperTrend":
            length = params.get('length', 10)
            multiplier = params.get('multiplier', 3.0)
            st = ta.supertrend(df['high'], df['low'], df['close'], length=length, multiplier=multiplier)
            
            if st is not None:
                # Supertrend retorna: SUPERT_l_m.1, SUPERTd_l_m.1, SUPERTl_l_m.1, SUPERTs_l_m.1
                # Queremos la linea principal y la dirección
                col_st = next((c for c in st.columns if c.startswith('SUPERT_')), None)
                col_dir = next((c for c in st.columns if c.startswith('SUPERTd_')), None)
                
                if col_st and col_dir:
                    df['SuperTrend'] = st[col_st]
                    df['ST_Direction'] = st[col_dir] # 1 Bull, -1 Bear
                    # Feature útil: Distancia al precio
                    df['Dist_SuperTrend'] = (df['close'] - df['SuperTrend']) / df['close']

        # 7. EstrategiaMACD_ZeroLag (Usamos MACD normal como proxy o especifico)
        elif estrategia == "EstrategiaMACD_ZeroLag":
            fast = params.get('fast', 12)
            slow = params.get('slow', 26)
            signal = params.get('signal', 9)
            
            macd = ta.macd(df['close'], fast=fast, slow=slow, signal=signal)
            if macd is not None:
                col_macd = next((c for c in macd.columns if c.startswith('MACD_')), None)
                col_sig = next((c for c in macd.columns if c.startswith('MACDs_')), None)
                col_hist = next((c for c in macd.columns if c.startswith('MACDh_')), None)
                
                if col_macd: df['MACD_Line'] = macd[col_macd]
                if col_sig: df['MACD_Signal'] = macd[col_sig]
                if col_hist: df['MACD_Hist'] = macd[col_hist]

        # 8. EstrategiaBollingerReversion (Mean Reversion)
        elif estrategia == "EstrategiaBollingerReversion":
            length = params.get('length', 20)
            std = params.get('std', 2.0)
            
            bb = ta.bbands(df['close'], length=length, std=std)
            if bb is not None:
                col_u = next((c for c in bb.columns if c.startswith('BBU')), None)
                col_l = next((c for c in bb.columns if c.startswith('BBL')), None)
                
                if col_u and col_l:
                    # Distancias relativas (Normalizadas por precio)
                    df['Dist_BBU_Rel'] = (df['close'] - bb[col_u]) / df['close']
                    df['Dist_BBL_Rel'] = (df['close'] - bb[col_l]) / df['close']
                    df['BB_Width_Specific'] = (bb[col_u] - bb[col_l]) / bb[col_u]

        df.fillna(0, inplace=True)
        return df

    @staticmethod
    def generar_senal_estrategia(df: pd.DataFrame, estrategia: str, params: dict) -> pd.Series:
        """
        Genera una serie de Señales de Compra (1) y Venta (-1) basada en la estrategia.
        Centraliza la lógica de decisión (IF/ELSE) para que Optimizer y Training usen la misma definición.
        """
        senal = pd.Series(0, index=df.index)
        
        # 1. EstrategiaTrend
        if estrategia == "EstrategiaTrend":
            if 'EMA_F' in df.columns:
                ema_f = df['EMA_F']
                ema_s = df['EMA_S']
            else:
                ema_f = ta.ema(df['close'], length=params.get('ema_fast', 9))
                ema_s = ta.ema(df['close'], length=params.get('ema_slow', 21))
                
            adx = df['ADX'] if 'ADX' in df.columns else ta.adx(df['high'], df['low'], df['close'], length=14).iloc[:,0]
            
            mask_buy = (ema_f > ema_s) & (adx > params.get('adx_minimo', 20))
            mask_sell = (ema_f < ema_s) & (adx > params.get('adx_minimo', 20))
            
            senal[mask_buy] = 1
            senal[mask_sell] = -1

        # 2. EstrategiaBB (Breakout)
        elif estrategia == "EstrategiaBB":
            if 'dist_upper' in df.columns:
                mask_buy = df['dist_upper'] > 0 
                mask_sell = df['dist_lower'] < 0 
            else:
                bb = ta.bbands(df['close'], length=params.get('bb_length', 20), std=params.get('bb_std', 2.0))
                if bb is not None:
                     col_u = next((c for c in bb.columns if c.startswith('BBU')), None)
                     col_l = next((c for c in bb.columns if c.startswith('BBL')), None)
                     mask_buy = df['close'] > bb[col_u]
                     mask_sell = df['close'] < bb[col_l]
            
            senal[mask_buy] = 1
            senal[mask_sell] = -1

        # 3. EstrategiaRSI_ADX (Reversion)
        elif estrategia == "EstrategiaRSI_ADX":
            rsi = df['RSI'] if 'RSI' in df.columns else ta.rsi(df['close'], length=14)
            adx = df['ADX'] if 'ADX' in df.columns else ta.adx(df['high'], df['low'], df['close'], length=14).iloc[:,0]
            
            mask_buy = (rsi < params.get('rsi_sobreventa', 30)) & (adx > params.get('adx_minimo', 20))
            mask_sell = (rsi > params.get('rsi_sobrecompra', 70)) & (adx > params.get('adx_minimo', 20))
            
            senal[mask_buy] = 1
            senal[mask_sell] = -1

        # 4. EstrategiaTrend_Candle
        elif estrategia == "EstrategiaTrend_Candle":
            if 'EMA_F' in df.columns:
                ema_f = df['EMA_F']; ema_s = df['EMA_S']
            else:
                ema_f = ta.ema(df['close'], length=params.get('ema_fast', 20))
                ema_s = ta.ema(df['close'], length=params.get('ema_slow', 50))
            
            adx = df['ADX']
            patron_bull = (df['CDL_ENGULFING'] == 100) | (df['CDL_HAMMER'] == 100)
            patron_bear = (df['CDL_ENGULFING'] == -100) | (df['CDL_SHOOTING'] == -100)
            
            mask_buy = (ema_f > ema_s) & (adx > params.get('adx_minimo', 20)) & patron_bull
            mask_sell = (ema_f < ema_s) & (adx > params.get('adx_minimo', 20)) & patron_bear
            
            senal[mask_buy] = 1
            senal[mask_sell] = -1
        
        # 5. EstrategiaSqueeze_Momentum
        elif estrategia == "EstrategiaSqueeze_Momentum":
            if 'dist_BBU' in df.columns:
                 rompe_up = df['dist_BBU'] > 0
                 rompe_down = df['dist_BBL'] < 0
            else:
                 bb = ta.bbands(df['close'], length=20, std=2.0)
                 col_u = next((c for c in bb.columns if c.startswith('BBU')), None)
                 col_l = next((c for c in bb.columns if c.startswith('BBL')), None)
                 rompe_up = df['close'] > bb[col_u]
                 rompe_down = df['close'] < bb[col_l]
            
            mom = df['Lreg_Mom']
            rvol = df['RVOL']
            
            mask_buy = rompe_up & (mom > 0) & (rvol > params.get('rvol_min', 1.2))
            mask_sell = rompe_down & (mom < 0) & (rvol > params.get('rvol_min', 1.2))
            
            senal[mask_buy] = 1
            senal[mask_sell] = -1

        # 6. EstrategiaSuperTrend
        elif estrategia == "EstrategiaSuperTrend":
            if 'ST_Direction' in df.columns:
                st_dir = df['ST_Direction']
            else:
                st = ta.supertrend(df['high'], df['low'], df['close'], length=params.get('length', 10), multiplier=params.get('multiplier', 3.0))
                if st is not None:
                     col_dir = next((c for c in st.columns if c.startswith('SUPERTd_')), None)
                     st_dir = st[col_dir] if col_dir else pd.Series(0, index=df.index)
                else: 
                     st_dir = pd.Series(0, index=df.index)

            shift_st = st_dir.shift(1).fillna(0)
            mask_buy = (st_dir == 1) & (shift_st == -1)
            mask_sell = (st_dir == -1) & (shift_st == 1)
            
            senal[mask_buy] = 1
            senal[mask_sell] = -1

        # 7. EstrategiaMACD_ZeroLag
        elif estrategia == "EstrategiaMACD_ZeroLag":
            if 'MACD_Line' in df.columns:
                m_line = df['MACD_Line']
                s_line = df['MACD_Signal']
            else:
                macd = ta.macd(df['close'], fast=params.get('fast',12), slow=params.get('slow',26), signal=params.get('signal',9))
                col_m = next((c for c in macd.columns if c.startswith('MACD_')), None)
                col_s = next((c for c in macd.columns if c.startswith('MACDs_')), None)
                m_line = macd[col_m]; s_line = macd[col_s]
            
            mask_buy = (m_line > s_line) & (m_line.shift(1) <= s_line.shift(1))
            mask_sell = (m_line < s_line) & (m_line.shift(1) >= s_line.shift(1))
            
            senal[mask_buy] = 1
            senal[mask_sell] = -1

        # 8. EstrategiaBollingerReversion
        elif estrategia == "EstrategiaBollingerReversion":
            bb = ta.bbands(df['close'], length=params.get('length', 20), std=params.get('std', 2.0))
            if bb is not None:
                col_u = next((c for c in bb.columns if c.startswith('BBU')), None)
                col_l = next((c for c in bb.columns if c.startswith('BBL')), None)
                
                if col_u and col_l:
                    mask_buy = df['close'] < bb[col_l]
                    mask_sell = df['close'] > bb[col_u]
                    
                    senal[mask_buy] = 1
                    senal[mask_sell] = -1

        return senal
