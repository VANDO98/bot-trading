import sys
import os
import pandas as pd
import numpy as np

# Rutas
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from Estrategias.Concretas.EstrategiaRSI import EstrategiaRSI

def debug_profundo():
    print("--- 🕵️ INICIANDO DIAGNÓSTICO PROFUNDO DE RSI ---")
    
    # 1. Instanciar
    params = {"rsi_periodo": 14, "rsi_sobreventa": 30, "rsi_sobrecompra": 70}
    cerebro = EstrategiaRSI("DebugBot", params)
    
    print(f"📚 Versión Pandas: {pd.__version__}")
    print(f"📚 Versión Numpy: {np.__version__}")
    print("-" * 40)

    # 2. Loop de datos
    precio = 50000
    for i in range(1, 30): # Probamos con 30 velas
        # Creamos vela
        kline = {
            't': 1600000000000 + (i * 60000),
            'o': precio, 'h': precio+10, 'l': precio-10, 'c': precio-50, # Tendencia bajista
            'v': 100, 'x': True
        }
        precio -= 50

        # Inyectamos
        cerebro.recibir_vela("BTC/USDT", kline)
        
        # 3. INSPECCIÓN DIRECTA DE LA MEMORIA
        n_velas = len(cerebro.velas)
        rsi_val = "N/A"
        
        if 'RSI' in cerebro.velas.columns:
            raw = cerebro.velas.iloc[-1]['RSI']
            rsi_val = f"{raw} (Tipo: {type(raw)})"
        
        print(f"Vela #{i:02d} | Total filas: {n_velas} | RSI en DB: {rsi_val}")

if __name__ == "__main__":
    debug_profundo()