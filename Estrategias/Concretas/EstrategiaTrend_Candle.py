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

    def calcular_indicadores(self):
        """
        Calcula indicadores técnicos sobre self.velas (DataFrame).
        """
        if self.velas.empty: return

        # 1. EMAs
        # Usamos nombres específicos para no colisionar si hubiera otras
        self.velas['EMA_F'] = ta.ema(self.velas['close'], length=self.parametros.get('ema_fast', 20))
        self.velas['EMA_S'] = ta.ema(self.velas['close'], length=self.parametros.get('ema_slow', 50))
        
        # 2. ADX
        # ADX retorna un DF con ADX_14, DMP_14, DMN_14. Tomamos la columna ADX.
        adx_df = ta.adx(self.velas['high'], self.velas['low'], self.velas['close'], length=14)
        if adx_df is not None:
             # Buscar la columna que empiece con ADX_
            col_adx = [c for c in adx_df.columns if c.startswith('ADX')][0]
            self.velas['ADX'] = adx_df[col_adx]
        else:
            self.velas['ADX'] = 0

        # 3. Patrones de Velas
        # Engulfing
        self.velas['CDL_ENGULFING'] = ta.cdl_pattern(self.velas['open'], self.velas['high'], self.velas['low'], self.velas['close'], name="engulfing")
        # Hammer
        self.velas['CDL_HAMMER'] = ta.cdl_pattern(self.velas['open'], self.velas['high'], self.velas['low'], self.velas['close'], name="hammer")
        # Shooting Star
        self.velas['CDL_SHOOTING'] = ta.cdl_pattern(self.velas['open'], self.velas['high'], self.velas['low'], self.velas['close'], name="shootingstar")

    def generar_senal(self):
        """
        Evalúa la última vela cerrada para decidir Compra/Venta.
        """
        if self.velas.empty: return "NEUTRO"
        
        try:
            # Última vela (la acabada de cerrar)
            last = self.velas.iloc[-1]
            
            # Parámetros
            adx_min = self.parametros.get('adx_minimo', 20)
            
            # Recuperar valores con manejo robusto de Nones
            # Si last.get devuelve None, forzamos 0.0
            val_fast = float(last.get('EMA_F') or 0.0)
            val_slow = float(last.get('EMA_S') or 0.0)
            val_adx = float(last.get('ADX') or 0.0)
            
            # Patrones (0, 100, -100)
            engulfing = int(last.get('CDL_ENGULFING') or 0)
            hammer = int(last.get('CDL_HAMMER') or 0)
            shooting = int(last.get('CDL_SHOOTING') or 0)

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
            patron_bear = (engulfing == -100) or (shooting == -100)
             
            if tendencia_bajista and fuerza and patron_bear:
                return "VENTA"

            return "NEUTRO"

        except Exception as e:
            print(f"Error EstrategiaTrend_Candle: {e}")
            return "NEUTRO"
