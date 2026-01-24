import pandas as pd
import pandas_ta as ta
from Estrategias.EstrategiaBase import EstrategiaBase

class EstrategiaBollingerReversion(EstrategiaBase):
    """
    Estrategia de Reversión a la Media con Bandas de Bollinger.
    Ideal para mercados laterales.
    
    Lógica:
        - COMPRA: Precio cierra POR DEBAJO de la Banda Inferior (Se espera rebote al centro).
        - VENTA: Precio cierra POR ENCIMA de la Banda Superior (Se espera caída al centro).
    """

    def __init__(self, nombre, parametros_json):
        super().__init__(nombre, parametros_json)

    def calcular_indicadores(self):
        length = self.parametros.get('bb_length', 20)
        std = self.parametros.get('bb_std', 2.0)

        if len(self.velas) > length:
            bb = ta.bbands(self.velas['close'], length=length, std=std)
            
            if bb is not None:
                self.velas = pd.concat([self.velas, bb], axis=1)
                
                # Identificar nombres de columnas dinámicos (BBL_20_2.0, BBU_20_2.0)
                self.velas['BBL'] = bb[f"BBL_{length}_{std}"]
                self.velas['BBU'] = bb[f"BBU_{length}_{std}"]
                # BBM es la media, útil si quisiéramos filtrar
                self.velas['BBM'] = bb[f"BBM_{length}_{std}"]

    def generar_senal(self):
        if self.velas.empty or 'BBL' not in self.velas.columns:
            return "NEUTRO"
            
        close = self.velas['close'].iloc[-1]
        bbl = self.velas['BBL'].iloc[-1]
        bbu = self.velas['BBU'].iloc[-1]
        
        if pd.isna(close) or pd.isna(bbl):
            return "NEUTRO"

        # Señal de Reversión (Rebote)
        if close < bbl:
            return "COMPRA" # Está barato / sobrevendido en rango
        elif close > bbu:
            return "VENTA" # Está caro / sobrecomprado en rango
            
        return "NEUTRO"
