import pandas as pd  # <--- ESTO FALTABA
import pandas_ta as ta
from Estrategias.EstrategiaBase import EstrategiaBase

class EstrategiaRSI(EstrategiaBase):
    
    def __init__(self, nombre, parametros_json):
        # Inicializa la clase madre correctamente
        super().__init__(nombre, parametros_json)

    def calcular_indicadores(self):
        """
        Implementación concreta: Calcula solo el RSI.
        Se llama automáticamente desde 'recibir_vela' de la clase madre.
        """
        periodo = self.parametros.get('rsi_periodo', 14)
        
        # Necesitamos mínimas velas
        if len(self.velas) > periodo:
            # Usamos pandas_ta sobre la columna 'close'
            # (Aseguramos que sea una serie de pandas)
            self.velas['RSI'] = ta.rsi(self.velas['close'], length=periodo)

    def generar_senal(self):
        """
        Implementación concreta: Decide si COMPRA o VENDE.
        Se llama automáticamente si la vela cerró.
        """
        # Verificar si existe la columna RSI
        if self.velas.empty or 'RSI' not in self.velas.columns:
            return "NEUTRO"
            
        rsi_actual = self.velas['RSI'].iloc[-1]
        
        # Validar que el RSI no sea NaN (pasa al inicio o si faltan datos)
        # AQUÍ ES DONDE DABA EL ERROR ANTES
        if pd.isna(rsi_actual):
            return "NEUTRO"

        sobreventa = self.parametros.get('rsi_sobreventa', 30)
        sobrecompra = self.parametros.get('rsi_sobrecompra', 70)
        
        if rsi_actual <= sobreventa:
            return "COMPRA"
        elif rsi_actual >= sobrecompra:
            return "VENTA"
            
        return "NEUTRO"