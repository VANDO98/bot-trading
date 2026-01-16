import sys
import os
import pandas as pd
import random
import time

# Importar módulos del proyecto
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from Estrategias.Concretas.EstrategiaRSI import EstrategiaRSI

def test_logica_rsi_realista():
    print("--- 🧪 TEST DE ESTRATEGIA RSI (MERCADO SIMULADO) ---")
    
    # 1. Configuración: RSI de 14 periodos
    params = {
        "rsi_periodo": 14,
        "rsi_sobreventa": 30,  # Comprar si baja de 30
        "rsi_sobrecompra": 70  # Vender si sube de 70
    }
    
    cerebro = EstrategiaRSI("BotTest", params)
    
    # 2. Generar Mercado
    print("📉 Iniciando simulación de mercado con ruido...")
    
    precio = 50000
    tendencia = -1 # 1 sube, -1 baja
    
    # Simulamos 100 velas
    for i in range(1, 101):
        # CAMBIO: Movimiento aleatorio para que el RSI fluctúe
        # A veces sube, a veces baja, pero sigue la tendencia general
        variacion = random.randint(-50, 30) 
        
        # Cada 30 velas cambiamos la tendencia para ver compra Y venta
        if i % 30 == 0:
            tendencia *= -1
            print(f"🔄 CAMBIO DE TENDENCIA: {'ALCISTA' if tendencia > 0 else 'BAJISTA'}")

        # Aplicamos tendencia
        precio += (variacion + (tendencia * 20))
        
        kline = {
            't': 1600000000000 + (i * 60000),
            'o': precio, 
            'h': precio + 20, 
            'l': precio - 20, 
            'c': precio,
            'v': random.randint(100, 1000), 
            'x': True
        }
        
        # 3. Inyectar al cerebro
        senal = cerebro.recibir_vela("BTC/USDT", kline)
        
        # 4. Leer RSI (con seguridad)
        rsi_str = "N/A"
        color_rsi = ""
        
        if 'RSI' in cerebro.velas.columns and not cerebro.velas.empty:
            val = cerebro.velas.iloc[-1]['RSI']
            if pd.notna(val):
                rsi_val = float(val)
                rsi_str = f"{rsi_val:.2f}"
                
                # Colores para ver mejor en consola
                if rsi_val < 30: color_rsi = "\033[92m" # Verde (Sobreventa)
                elif rsi_val > 70: color_rsi = "\033[91m" # Rojo (Sobrecompra)
                else: color_rsi = "\033[0m" # Blanco

        # 5. Imprimir solo si tenemos RSI calculado
        if rsi_str != "N/A":
            # Si hay señal, la resaltamos mucho
            if senal == "COMPRA":
                print(f"🕯️ Vela {i:03d} | Precio: {precio:.1f} | RSI: {color_rsi}{rsi_str}\033[0m | 🚀 \033[92m¡SEÑAL DE COMPRA!\033[0m")
            elif senal == "VENTA":
                print(f"🕯️ Vela {i:03d} | Precio: {precio:.1f} | RSI: {color_rsi}{rsi_str}\033[0m | 🔻 \033[91m¡SEÑAL DE VENTA!\033[0m")
            else:
                # Imprimir normal para ver el seguimiento
                print(f"   Vela {i:03d} | Precio: {precio:.1f} | RSI: {color_rsi}{rsi_str}\033[0m | ...")

if __name__ == "__main__":
    test_logica_rsi_realista()