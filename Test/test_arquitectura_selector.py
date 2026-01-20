import sys
import os

# Ajustar path para que encuentre los módulos
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Estrategias.Selector import Selector
from Estrategias.Concretas.EstrategiaBB import EstrategiaBB
from Estrategias.Concretas.EstrategiaTrend import EstrategiaTrend
from Estrategias.Concretas.EstrategiaRSI import EstrategiaRSI
from Estrategias.Concretas.EstrategiaRSI_ADX import EstrategiaRSI_ADX

def test_selector():
    print("🧪 INICIANDO TEST DE ARQUITECTURA (SELECTOR)...")
    
    # CASO 1: Probar Estrategia BB (Memes)
    print("\n1. Probando carga de 'EstrategiaBB'...")
    bot_meme = Selector.obtener_estrategia("EstrategiaBB", "DOGE/USDT", {"bb_length": 20})
    if isinstance(bot_meme, EstrategiaBB):
        print("   ✅ Correcto: Se instanció EstrategiaBB.")
    else:
        print("   ❌ Fallo: No devolvió la clase correcta.")

    # CASO 2: Probar Estrategia Trend (Gigantes)
    print("\n2. Probando carga de 'EstrategiaTrend'...")
    bot_trend = Selector.obtener_estrategia("EstrategiaTrend", "BTC/USDT", {"ema_fast": 9})
    if isinstance(bot_trend, EstrategiaTrend):
        print("   ✅ Correcto: Se instanció EstrategiaTrend.")
    else:
        print("   ❌ Fallo.")

    # CASO 3: Probar Estrategia Vieja (RSI)
    print("\n3. Probando carga de 'EstrategiaRSI' (Retro-compatibilidad)...")
    bot_rsi = Selector.obtener_estrategia("EstrategiaRSI_ADX", "SOL/USDT", {})
    if isinstance(bot_rsi, EstrategiaRSI_ADX):
        print("   ✅ Correcto: Se instanció EstrategiaRSI.")
    else:
        print("   ❌ Fallo.")

    # CASO 4: Probar Error
    print("\n4. Probando estrategia inexistente...")
    bot_fake = Selector.obtener_estrategia("EstrategiaSuperMagica", "FAKE/USDT", {})
    if bot_fake is None:
        print("   ✅ Correcto: El sistema manejó el error y devolvió None.")
    else:
        print("   ❌ Fallo: Debería ser None.")

if __name__ == "__main__":
    test_selector()