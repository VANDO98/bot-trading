import sys
import os
import time
from colorama import Fore, Style, init

# Ajustar ruta para importar módulos del Core
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Core.Ejecucion.GestorEjecucion import GestorEjecucion

# Inicializar colores
init(autoreset=True)

def test_limpieza_fantasma():
    print(Fore.YELLOW + "🧹 INICIANDO TEST DE LIMPIEZA DE TPs FANTASMA")
    print("==================================================")
    
    # 1. Conectar
    try:
        gestor = GestorEjecucion()
        exchange = gestor.exchange
        print(Fore.GREEN + "✅ Conexión con Exchange exitosa.")
    except Exception as e:
        print(Fore.RED + f"❌ Error conectando: {e}")
        return

    # Usaremos BTC/USDT para la prueba
    simbolo = "BTC/USDT"
    
    # 2. Obtener precio actual para poner una orden LEJOS (Seguridad)
    try:
        ticker = exchange.fetch_ticker(simbolo)
        precio_actual = ticker['last']
        # Ponemos un TP falso un 50% arriba (si es Long) para que no toque
        precio_fantasma = int(precio_actual * 1.5) 
        print(f"📊 Precio Actual: {precio_actual} | Precio Fantasma: {precio_fantasma}")
    except Exception as e:
        print(Fore.RED + f"❌ Error obteniendo precio: {e}")
        return

    # 3. CREAR ORDEN FANTASMA (Simulando un TP colgado)
    print(Fore.CYAN + "\n👻 Paso 1: Creando Take Profit Fantasma...")
    try:
        # Creamos una orden condicional (TAKE_PROFIT_MARKET) que es la que suele quedarse pegada
        params = {
            'stopPrice': precio_fantasma, 
            'reduceOnly': True
        }
        
        # Ojo: Cantidad mínima permitida (ajustar según par, 0.001 para BTC suele servir en testnet)
        cantidad = 0.002 
        
        orden = exchange.create_order(
            symbol=simbolo,
            type='TAKE_PROFIT_MARKET',
            side='sell',
            amount=cantidad,
            price=None, # Es market
            params=params
        )
        print(Fore.GREEN + f"✅ Orden Fantasma creada ID: {orden['id']}")
        
    except Exception as e:
        print(Fore.RED + f"❌ No se pudo crear la orden de prueba: {e}")
        print(Fore.YELLOW + "💡 Intenta con un 'LIMIT' simple si el error es por filtros de precio/cantidad.")
        return

    # 4. VERIFICAR QUE EXISTE
    time.sleep(2)
    pendientes = exchange.fetch_open_orders(simbolo)
    if len(pendientes) > 0:
        print(Fore.GREEN + f"✅ Verificado: Hay {len(pendientes)} orden(es) pendiente(s) en Binance.")
        for o in pendientes:
            print(f"   - ID: {o['id']} | Tipo: {o['type']} | Gatillo: {o['info'].get('stopPrice', 'N/A')}")
    else:
        print(Fore.RED + "❌ Error: La orden no aparece en pendientes. El test no puede continuar.")
        return

    # 5. EJECUTAR LIMPIEZA (La función que queremos probar)
    print(Fore.CYAN + "\n🧹 Paso 2: Ejecutando 'cancelar_ordenes_pendientes'...")
    
    try:
        # Llamamos a tu función
        gestor.cancelar_ordenes_pendientes(simbolo)
        print("⏳ Esperando respuesta de Binance...")
        time.sleep(3)
    except Exception as e:
        print(Fore.RED + f"❌ La función de limpieza falló con error: {e}")
        return

    # 6. VERIFICAR RESULTADO FINAL
    print(Fore.CYAN + "\n🔍 Paso 3: Auditoría final...")
    pendientes_final = exchange.fetch_open_orders(simbolo)
    
    if len(pendientes_final) == 0:
        print(Fore.GREEN + "✨ ÉXITO TOTAL: No quedan órdenes pendientes. El borrado funciona.")
    else:
        print(Fore.RED + f"⚠️ FALLO: Aún quedan {len(pendientes_final)} orden(es) fantasma(s).")
        print(Fore.YELLOW + "🔎 Detalles de lo que sobrevivió:")
        for o in pendientes_final:
            print(f"   - ID: {o['id']} | Tipo: {o['type']} | Estado: {o['status']}")

if __name__ == "__main__":
    test_limpieza_fantasma()