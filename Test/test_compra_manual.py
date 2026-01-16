import sys
import os

# Rutas
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from Core.Ejecucion.GestorEjecucion import GestorEjecucion

def probar_compra_ccxt():
    print("--- 🧪 TEST DE EJECUCIÓN CON CCXT (TESTNET) ---")
    
    gestor = GestorEjecucion()
    
    # 1. Ver saldo
    saldo = gestor.obtener_balance()
    print(f"💰 Balance USDT Disponible: {saldo:.2f}")
    
    if saldo < 10:
        print("⚠️ Saldo bajo. ¿Necesitas recargar el Faucet?")
        # Nota: Si es 0, el test de compra fallará.

    # 2. Intentar una compra PEQUEÑA (Long de BTC)
    # En Testnet, mínimos de BTC pueden variar, 0.005 es seguro.
    cantidad_prueba = 0.005
    par_prueba = "BTC/USDT"
    
    print(f"\n🛒 Intentando LONG en {par_prueba} x {cantidad_prueba}...")
    
    # 'buy' = Long, 'sell' = Short
    respuesta = gestor.colocar_orden_mercado(par_prueba, "buy", cantidad_prueba)
    
    if respuesta:
        print("🎉 ¡ÉXITO! Orden confirmada por CCXT.")
        # print(respuesta) # Descomenta para ver el JSON gigante de la orden
    else:
        print("💀 La orden falló.")

if __name__ == "__main__":
    probar_compra_ccxt()