import sys
import os
import time
from colorama import init, Fore, Style

# Rutas para importar el Core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from Core.Ejecucion.GestorEjecucion import GestorEjecucion

init(autoreset=True)

def test_stoploss_aislado():
    print(Fore.YELLOW + "--- 🛡️ DIAGNÓSTICO DE STOP LOSS Y TAKE PROFIT ---")
    
    gestor = GestorEjecucion()
    
    # 1. Configuración de prueba
    par = "BTC/USDT"
    cantidad = 0.005 # Mínimo seguro para testnet
    sl_pct = 0.02    # 2%
    tp_pct = 0.04    # 4%
    
    # 2. ABRIR POSICIÓN (Necesario, no se puede poner SL sin posición)
    print(Fore.CYAN + f"\n1. Abriendo posición LONG de prueba en {par}...")
    orden_entrada = gestor.colocar_orden_mercado(par, "buy", cantidad)
    
    if not orden_entrada:
        print(Fore.RED + "❌ Falló la entrada. No se puede probar el SL.")
        return

    precio_entrada = float(orden_entrada['average'])
    print(Fore.GREEN + f"✅ Entrada exitosa a ${precio_entrada}")

    # 3. CÁLCULO MANUAL (Para verificar matemáticas)
    precio_sl_calc = precio_entrada * (1 - sl_pct)
    precio_tp_calc = precio_entrada * (1 + tp_pct)
    print(f"   📐 Objetivo Matemático -> SL: {precio_sl_calc} | TP: {precio_tp_calc}")

    # 4. INTENTO DE COLOCAR PROTECCIONES
    print(Fore.CYAN + "\n2. Intentando colocar SL y TP...")
    
    # Aquí llamamos a tu función, pero capturamos excepciones extras si las hay
    try:
        resultado = gestor.colocar_ordenes_salida(
            simbolo=par,
            lado_entrada="buy",
            cantidad=cantidad,
            precio_entrada=precio_entrada,
            sl_pct=sl_pct,
            tp_pct=tp_pct
        )
        
        if resultado:
            print(Fore.GREEN + "\n🎉 ¡PRUEBA EXITOSA! Las órdenes deberían aparecer en Binance.")
            print(Fore.WHITE + "Nota: Revisa en la web de Testnet pestaña 'Open Orders'.")
        else:
            print(Fore.RED + "\n❌ La función devolvió False (Falló internamente).")
            
    except Exception as e:
        print(Fore.RED + f"\n💥 EXCEPCIÓN NO CONTROLADA EN EL TEST: {e}")

    # 5. LIMPIEZA (Opcional: cerrar la posición para no dejar basura)
    print(Fore.YELLOW + "\n⚠️ Recuerda cerrar esta posición manualmente en la Testnet si el SL no funcionó.")

if __name__ == "__main__":
    test_stoploss_aislado()