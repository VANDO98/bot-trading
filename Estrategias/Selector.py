# Estrategias/Selector.py
from colorama import Fore

# 1. Importar todas las estrategias disponibles
from Estrategias.Concretas.EstrategiaRSI import EstrategiaRSI
from Estrategias.Concretas.EstrategiaRSI_ADX import EstrategiaRSI_ADX
from Estrategias.Concretas.EstrategiaBB import EstrategiaBB
from Estrategias.Concretas.EstrategiaTrend import EstrategiaTrend

from Estrategias.Concretas.EstrategiaTrend_Candle import EstrategiaTrend_Candle
from Estrategias.Concretas.EstrategiaSqueeze_Momentum import EstrategiaSqueeze_Momentum

class Selector:
    """
    FACTORY PATTERN: Centraliza la creación de estrategias.
    Convierte el string del JSON (ej: "EstrategiaBB") en una Instancia Real.
    """
    
    # Catálogo de Estrategias Registradas
    CATALOGO = {
        "EstrategiaRSI": EstrategiaRSI,
        "EstrategiaRSI_ADX": EstrategiaRSI_ADX,
        "EstrategiaBB": EstrategiaBB,
        "EstrategiaTrend": EstrategiaTrend,
        "EstrategiaTrend_Candle": EstrategiaTrend_Candle,
        "EstrategiaSqueeze_Momentum": EstrategiaSqueeze_Momentum
    }

    @staticmethod
    def obtener_estrategia(nombre_clase, nombre_par, parametros):
        """
        Devuelve una instancia configurada de la estrategia solicitada.
        """
        clase_objetivo = Selector.CATALOGO.get(nombre_clase)
        
        if not clase_objetivo:
            print(f"{Fore.RED}❌ Error: La estrategia '{nombre_clase}' solicitada para {nombre_par} no existe en el Selector.")
            return None
            
        # Instanciamos la clase pasando el par y sus parámetros
        return clase_objetivo(nombre=nombre_par, parametros_json=parametros)