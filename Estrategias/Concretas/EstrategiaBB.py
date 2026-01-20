import pandas as pd
import pandas_ta as ta
from Estrategias.EstrategiaBase import EstrategiaBase

class EstrategiaBB(EstrategiaBase):
    """
    Estrategia Bollinger Breakout (Para Perfil: 'Memes' / Alta Volatilidad)
    """
    
    def __init__(self, nombre, parametros_json):
        super().__init__(nombre, parametros_json)

    def calcular_indicadores(self):
        # Parámetros por defecto: Periodo 20, Desviación 2.0
        length = self.parametros.get('bb_length', 20)
        std = self.parametros.get('bb_std', 2.0)

        if len(self.velas) > length:
            # Calculamos las bandas
            bb = ta.bbands(self.velas['close'], length=length, std=std)
            
            if bb is not None and not bb.empty:
                # --- CORRECCIÓN DE ERROR "KEYERROR" ---
                # En lugar de adivinar el nombre exacto (ej. 'BBU_20_2.0'), 
                # buscamos dinámicamente la columna que empiece por BBU (Upper) y BBL (Lower).
                cols = bb.columns.tolist()
                
                col_upper = next((c for c in cols if c.startswith('BBU')), None)
                col_lower = next((c for c in cols if c.startswith('BBL')), None)
                
                if col_upper and col_lower:
                    self.velas['BBU'] = bb[col_upper]
                    self.velas['BBL'] = bb[col_lower]

    def generar_senal(self):
        # 1. Validaciones de seguridad
        if self.velas.empty or 'BBU' not in self.velas.columns:
            return "NEUTRO"
            
        close_actual = self.velas['close'].iloc[-1]
        bbu = self.velas['BBU'].iloc[-1]
        bbl = self.velas['BBL'].iloc[-1]

        # Evitar falsos positivos con NaNs
        if pd.isna(bbu) or pd.isna(bbl):
            return "NEUTRO"

        # 2. Lógica de Disparo (Breakout)
        # Rompe techo -> Momentum Alcista
        if close_actual > bbu:
            return "COMPRA"
        
        # Rompe piso -> Momentum Bajista
        elif close_actual < bbl:
            return "VENTA"
            
        return "NEUTRO"