import sys
import os
import time

# --- Truco para importar módulos desde la carpeta raíz ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Core.API.GestorWebsocket import GestorWebsocket
from Core.Utils.Config import Config

def callback_prueba(symbol, kline_data):
    """Esta función se ejecutará cada vez que llegue una vela nueva"""
    cierre = kline_data['c']
    print(f"📩 [CALLBACK] Vela recibida para {symbol}: Precio {cierre}")

def test_flujo_datos():
    print("--- INICIANDO TEST DE GESTOR HÍBRIDO (UNICORN) ---")
    
    # 1. Instanciar
    gestor = GestorWebsocket()
    
    # 2. Preparar configuración falsa para el test
    # Simulamos que queremos leer BTC y ETH
    config_prueba = {
        'BTC/USDT': {'activo': True, 'timeframe': '1m'},
        'ETH/USDT': {'activo': True, 'timeframe': '1m'}
    }
    
    # 3. Iniciar el flujo
    print("🚀 Iniciando suscripción a WebSockets...")
    gestor.iniciar_flujo_hibrido(config_prueba, callback_prueba)
    
    # 4. Mantener vivo el test unos segundos para ver datos
    print("⏳ Esperando datos por 10 segundos...")
    for i in range(10):
        time.sleep(1)
        # Verificar salud del 'watchdog'
        btc_ok = gestor.verificar_salud_datos('BTC/USDT')
        precio_btc = gestor.obtener_precio('BTC/USDT')
        print(f"   Seg {i+1}: Salud BTC={btc_ok} | Precio Cache={precio_btc}")
    
    # 5. Apagar
    print("🛑 Deteniendo WebSockets...")
    gestor.detener_todo()
    print("✅ Test finalizado.")

if __name__ == "__main__":
    test_flujo_datos()