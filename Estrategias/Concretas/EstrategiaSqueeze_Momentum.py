from Estrategias.EstrategiaBase import EstrategiaBase
import pandas_ta as ta

class EstrategiaSqueeze_Momentum(EstrategiaBase):
    """
    Estrategia Squeeze Momentum Pro (TTM Squeeze Style)
    
    1. SQUEEZE: Bandas Bollinger (2.0) dentro de Canales Keltner (1.5).
       Indica acumulación/baja volatilidad.
    2. DISPARO:
       - Precio rompe Bollinger Superior + Momentum Positivo -> COMPRA
       - Precio rompe Bollinger Inferior + Momentum Negativo -> VENTA
    3. FILTROS:
       - Volumen Relativo (RVOL) > 1.2
    """

    def generar_senal(self, df):
        if df is None or df.empty: return "NEUTRO"
        
        # Parámetros Custom
        params = self.parametros
        rvol_min = params.get('rvol_min', 1.2)
        
        try:
            last = df.iloc[-1]
            prev = df.iloc[-2] # Necesario para ver si veníamos de squeeze
            
            # Recuperar indicadores avanzados del FeatureEngine
            # Nombres genéricos asumidos (FeatureEngine usa parámetros estándar)
            # BB (20, 2.0)
            # KC (20, 1.5)
            
            # Buscamos columnas dinámicamente o usamos las calculadas
            bb_upper = last.get('BBU_20_2.0', 0)
            bb_lower = last.get('BBL_20_2.0', 0)
            kc_upper = last.get('KC_Upper', 0)
            kc_lower = last.get('KC_Lower', 0)
            
            # Verifica si hay Squeeze HOY (Bandas dentro de Keltner)
            # OJO: La estrategia original busca Squeeze *Previo* y Disparo *Hoy*.
            # Si hoy rompe, ya no estará dentro.
            # squeeze_on = (bb_upper < kc_upper) and (bb_lower > kc_lower)
            
            # Revisamos si la vela ANTERIOR estaba en Squeeze (acumulación lista para romper)
            prev_bb_u = df.iloc[-2].get('BBU_20_2.0', 0)
            prev_kc_u = df.iloc[-2].get('KC_Upper', 0)
            was_squeeze = (prev_bb_u < prev_kc_u) 
            # Simplificamos: Si venimos de un periodo de baja volatilidad (BB Width bajo)
            # FeatureEngine calcula BB_Width. Un width bajo (<0.10 por ej) es similar a squeeze.
            # Pero usemos la lógica Keltner correcta si columnas existen.
            
            momentum = last.get('Lreg_Mom', 0)
            rvol = last.get('RVOL', 1.0)
            close = last['close']

            # Filtros básicos
            if rvol < rvol_min: return "NEUTRO"

            # ---------------- LOGICA LONG ----------------
            # Momentum + y Ruptura BB Superior
            # No exigimos Squeeze estricto previo para ser más flexibles en crypto,
            # pero el Momentum Lineal debe ser fuerte.
            if momentum > 0:
                if close > bb_upper:
                     return "COMPRA"

            # ---------------- LOGICA SHORT ----------------
            # Momentum - y Ruptura BB Inferior
            if momentum < 0:
                if close < bb_lower:
                     return "VENTA"

            return "NEUTRO"

        except Exception as e:
            return "NEUTRO"
