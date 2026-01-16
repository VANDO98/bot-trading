import pandas as pd
import pandas_ta as ta
# Ajustamos el import para que encuentre EstrategiaBase en la carpeta superior
from Estrategias.EstrategiaBase import EstrategiaBase

class EstrategiaRSI(EstrategiaBase):
    """
    Estrategia Clásica de RSI (Mean Reversion).
    """

    def calcular_indicadores(self):
        """
        Calcula el RSI manejando incompatibilidades de versiones de Pandas.
        """
        periodo = self.parametros.get('rsi_periodo', 14)

        if len(self.velas) < periodo:
            return

        try:
            # 1. Calculamos RSI usando la función directa (más estable que .ta.rsi)
            rsi_resultado = ta.rsi(self.velas['close'], length=periodo)

            # 2. CORRECCIÓN DE ERROR (Pandas 2.x vs pandas-ta)
            # Si devuelve un DataFrame (tabla), lo convertimos a Serie (columna)
            if isinstance(rsi_resultado, pd.DataFrame):
                rsi_series = rsi_resultado.iloc[:, 0] # Tomamos la primera columna
            else:
                rsi_series = rsi_resultado

            # 3. Asignamos a nuestra columna interna
            self.velas['RSI'] = rsi_series
            
        except Exception as e:
            # Imprimimos el error completo para debug si vuelve a pasar
            print(f"⚠️ Error calculando RSI: {e}")

    def generar_senal(self):
        """
        Analiza el último valor del RSI y emite señal.
        """
        if self.velas.empty or 'RSI' not in self.velas.columns:
            return "NEUTRO"
        
        rsi_actual = self.velas.iloc[-1]['RSI']

        if pd.isna(rsi_actual):
            return "NEUTRO"

        nivel_sobreventa = self.parametros.get('rsi_sobreventa', 30)
        nivel_sobrecompra = self.parametros.get('rsi_sobrecompra', 70)

        # Lógica de Trading
        if rsi_actual < nivel_sobreventa:
            return "COMPRA"
        elif rsi_actual > nivel_sobrecompra:
            return "VENTA"

        return "NEUTRO"