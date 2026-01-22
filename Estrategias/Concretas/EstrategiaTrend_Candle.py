from Estrategias.EstrategiaBase import EstrategiaBase
import pandas_ta as ta

class EstrategiaTrend_Candle(EstrategiaBase):
    """
    Estrategia Mixta: TENDENCIA + PRICE ACTION
    
    1. Define tendencia con doble EMA (Rápida vs Lenta).
    2. Filtra fuerza con ADX.
    3. Confirma entrada SOLO si la vela de cierre muestra un patrón:
       - Engulfing Bullish/Bearish
       - Hammer (para Long)
       - Shooting Star (para Short)
    """

    def generar_senal(self, df):
        if df is None or df.empty: return "NEUTRO"
        
        # Parámetros Custom
        params = self.parametros
        ema_fast = params.get('ema_fast', 20)
        ema_slow = params.get('ema_slow', 50)
        adx_min = params.get('adx_minimo', 20)
        
        # Última vela cerrada (índice -1)
        # Nota: Los indicadores ya vienen calculados del FeatureEngine si se usó
        # pero para seguridad recalculamos lo específico si falta
        
        try:
            # 1. Recuperar valores clave de la última fila
            last = df.iloc[-1]
            
            # Chequeos de seguridad por si faltan columnas
            if 'EMA_F' not in df.columns:
                 # Si el FeatureEngine no calculó estas EMAs específicas, las calculamos al vuelo (menos eficiente pero robusto)
                 # Idealmente usar FeatureEngine antes
                 ema_f_series = ta.ema(df['close'], length=ema_fast)
                 ema_s_series = ta.ema(df['close'], length=ema_slow)
                 val_fast = ema_f_series.iloc[-1]
                 val_slow = ema_s_series.iloc[-1]
            else:
                 val_fast = last['EMA_F']
                 val_slow = last['EMA_S']
            
            val_adx = last.get('ADX', 0)
            
            # Patrones (FeatureEngine devuelve 100, -100 o 0)
            engulfing = last.get('CDL_ENGULFING', 0)
            hammer = last.get('CDL_HAMMER', 0)
            shooting = last.get('CDL_SHOOTING', 0)

            # ---------------- LOGICA LONG ----------------
            # Tendencia Alcista + ADX + (Engulfing Bull o Hammer)
            tendencia_alcista = val_fast > val_slow
            fuerza = val_adx > adx_min
            patron_bull = (engulfing == 100) or (hammer == 100)
            
            if tendencia_alcista and fuerza and patron_bull:
                return "COMPRA"

            # ---------------- LOGICA SHORT ----------------
            # Tendencia Bajista + ADX + (Engulfing Bear o Shooting Star)
            tendencia_bajista = val_fast < val_slow
            patron_bear = (engulfing == -100) or (shooting == -100) # Shooting Star devuelve -100
             
            if tendencia_bajista and fuerza and patron_bear:
                return "VENTA"

            return "NEUTRO"

        except Exception as e:
            # print(f"Error EstrategiaTrend_Candle: {e}")
            return "NEUTRO"
