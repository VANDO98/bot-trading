import sys
import os

# Truco para que Python encuentre la carpeta 'Core' desde la carpeta 'Tests'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Core.API.BinanceBase import BinanceBase
from Core.Utils.Config import Config

def correr_test():
    print("🧪 INICIANDO TEST UNITARIO: CONEXIÓN Y SALDO")
    print("-" * 50)
    
    try:
        # 1. Intentar instanciar la clase (Valida API Keys)
        bot_api = BinanceBase()
        
        # 2. Probar Ping
        if bot_api.validar_conectividad():
            print("✅ PING exitoso a Binance Futures.")
        else:
            print("❌ FALLO el PING.")
            return

        # 3. Probar Saldo (Valida permisos de lectura y firma HMAC)
        saldo_total, saldo_disp = bot_api.obtener_saldo_usdt()
        if saldo_total is not None:
            print(f"💰 Saldo Total en Cuenta: {saldo_total} USDT")
            print(f"💵 Disponible para operar: {saldo_disp} USDT")
        else:
            print("❌ Error leyendo saldo.")
            return
            
        # 4. Probar configuración de un par (Ej: BTCUSDT)
        print("\n⚙️ Probando configuración de cuenta (Cross/Lev)...")
        bot_api.configurar_cuenta("BTCUSDT")
        
        print("-" * 50)
        print("✅✅ TEST SUPERADO: El motor base funciona correctamente.")

    except Exception as e:
        print(f"\n❌❌ TEST FALLIDO: {e}")
        # Si falla por claves, recordamos revisar el .env
        if "API Key" in str(e) or "Signature" in str(e):
            print("💡 Pista: Revisa que tus claves en .env sean correctas y correspondan a TESTNET.")

if __name__ == "__main__":
    correr_test()