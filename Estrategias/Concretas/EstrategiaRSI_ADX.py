import pandas as pd
import pandas_ta as ta
from Estrategias.EstrategiaBase import EstrategiaBase

class EstrategiaRSI_ADX(EstrategiaBase):
    """
    Estrategia Combinada:
    - RSI: Identifica niveles de Sobreventa/Sobrecompra (El Gatillo).
    - ADX: Mide la fuerza de la tendencia (El Filtro).
    
    Lógica: Solo operamos reversiones si el mercado NO tiene una tendencia 
    fuerte en contra (ADX bajo) O si buscamos confirmar fuerza (ADX alto).
    
    En este ejemplo: Operamos RSI solo si hay volatilidad suficiente (ADX > umbral).
    """
    
    def __init__(self, nombre, parametros_json):
        super().__init__(nombre, parametros_json)

    def calcular_indicadores(self):
        """
        Calculamos RSI y ADX.
        """
        p_rsi = self.parametros.get('rsi_periodo', 14)
        p_adx = self.parametros.get('adx_periodo', 14)
        
        # Necesitamos suficientes velas para ambos
        if len(self.velas) > max(p_rsi, p_adx) + 10:
            
            # 1. Calcular RSI
            self.velas['RSI'] = ta.rsi(self.velas['close'], length=p_rsi)
            
            # 2. Calcular ADX
            # Nota: ta.adx devuelve un DataFrame con 3 columnas: ADX, DMP, DMN
            adx_df = ta.adx(self.velas['high'], self.velas['low'], self.velas['close'], length=p_adx)
            
            # Extraemos solo la columna ADX (el nombre suele ser ADX_14)
            col_adx = f"ADX_{p_adx}"
            if col_adx in adx_df.columns:
                self.velas['ADX'] = adx_df[col_adx]

    def generar_senal(self):
        # Validaciones de seguridad
        if self.velas.empty: return "NEUTRO"
        if 'RSI' not in self.velas.columns or 'ADX' not in self.velas.columns: return "NEUTRO"
            
        rsi_actual = self.velas['RSI'].iloc[-1]
        adx_actual = self.velas['ADX'].iloc[-1]
        
        if pd.isna(rsi_actual) or pd.isna(adx_actual): return "NEUTRO"

        # --- PARAMETROS ---
        sobreventa = self.parametros.get('rsi_sobreventa', 30)
        sobrecompra = self.parametros.get('rsi_sobrecompra', 70)
        adx_minimo = self.parametros.get('adx_minimo', 20) # Fuerza mínima requerida
        
        # --- LÓGICA DE DECISIÓN ---
        
        # 1. Filtro ADX: ¿Hay suficiente fuerza para que valga la pena moverse?
        # (Si el mercado está muerto/lateral con ADX < 20, mejor no entrar)
        if adx_actual < adx_minimo:
            return "NEUTRO"

        # 2. Gatillo RSI: Reversión a la media
        if rsi_actual <= sobreventa:
            return "COMPRA"
        elif rsi_actual >= sobrecompra:
            return "VENTA"
            
        return "NEUTRO"