import sys
import os
import time
import ccxt
from dotenv import load_dotenv
from colorama import init, Fore, Style
from pathlib import Path

# Configuración de rutas
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

init(autoreset=True)

def prueba_cancelar_reemplazar_lenta():
    print(Fore.YELLOW + "\n🧪 TEST VISUAL: CANCELAR Y REEMPLAZAR (Con Pausa)\n")

    # --- 1. CONFIGURACIÓN ---
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(dotenv_path=env_path)
    
    exchange = ccxt.binance({
        'apiKey': os.getenv("BINANCE_API_KEY"),
        'secret': os.getenv("BINANCE_SECRET_KEY"),
        'options': {'defaultType': 'future'}
    })
    exchange.set_sandbox_mode(True)
    
    simbolo = "BTC/USDT"
    cantidad = 0.005

    try:
        # --- 2. PREPARACIÓN ---
        print(Fore.CYAN + "🧹 Preparando terreno...")
        exchange.cancel_all_orders(simbolo)
        exchange.create_market_buy_order(simbolo, cantidad)
        precio_entrada = float(exchange.fetch_ticker(simbolo)['last'])
        print(Fore.GREEN + f"   ✅ Long abierto en {precio_entrada}")

        # Crear SL Inicial
        sl_inicial = precio_entrada - 200
        sl_inicial = float(exchange.price_to_precision(simbolo, sl_inicial))
        
        orden_sl = exchange.create_order(
            symbol=simbolo,
            type='STOP_MARKET',
            side='sell',
            amount=cantidad,
            params={'stopPrice': sl_inicial, 'reduceOnly': True}
        )
        print(Fore.GREEN + f"   ✅ SL Inicial ({sl_inicial}): ID {orden_sl['id']}")
        print(Fore.WHITE + "   👀 Ve a Binance AHORA. Deberías ver esta orden activa.")
        
        print(Fore.YELLOW + "\n⏳ Esperando 10 segundos antes de comenzar la modificación...")
        time.sleep(10)

        # --- 3. PROCESO DE REEMPLAZO ---
        nuevo_precio_sl = precio_entrada - 100
        nuevo_precio_sl = float(exchange.price_to_precision(simbolo, nuevo_precio_sl))
        
        print(Fore.MAGENTA + f"\n🔄 INICIANDO PROCESO DE CAMBIO A: {nuevo_precio_sl}...")
        
        # PASO A: OBTENER DATOS
        try:
            orden_vieja = exchange.fetch_order(orden_sl['id'], simbolo)
            cantidad_recuperada = float(orden_vieja['amount'])
            print(Fore.BLUE + f"   1. Datos recuperados: Cantidad {cantidad_recuperada}")
        except Exception as e:
            print(Fore.RED + f"   ❌ Error leyendo orden vieja: {e}")
            return

        # PASO B: CANCELAR
        try:
            exchange.cancel_order(orden_sl['id'], simbolo)
            print(Fore.BLUE + "   2. Orden vieja CANCELADA.")
        except Exception as e:
            print(Fore.RED + f"   ❌ Error cancelando: {e}")
            return

        # --- PAUSA PARA VERIFICACIÓN VISUAL ---
        print(Fore.YELLOW + "\n⏸️  PAUSA DE 20 SEGUNDOS ⏸️")
        print(Fore.YELLOW + "👉 Mira Binance: La orden de Stop Loss debería haber DESAPARECIDO.")
        print(Fore.YELLOW + "   (Esperando...)")
        time.sleep(20) 
        print(Fore.YELLOW + "▶️  Continuando...")

        # PASO C: CREAR NUEVA
        try:
            nueva_orden = exchange.create_order(
                symbol=simbolo,
                type='STOP_MARKET',
                side='sell',
                amount=cantidad_recuperada,
                params={
                    'stopPrice': nuevo_precio_sl,
                    'reduceOnly': True
                }
            )
            print(Fore.GREEN + f"\n   3. ✅ NUEVA ORDEN CREADA: ID {nueva_orden['id']} | Precio {nueva_orden['stopPrice']}")
            print(Fore.GREEN + "   👀 Mira Binance: Ahora debería aparecer la NUEVA orden.")
            
        except Exception as e:
            print(Fore.RED + f"   ❌ Error creando nueva orden: {e}")

    except Exception as e:
        print(Fore.RED + f"❌ Error general en el script: {e}")

    finally:
        print(Fore.WHITE + "\n🧹 Limpieza final en 10 segundos...")
        time.sleep(10)
        try:
            exchange.cancel_all_orders(simbolo)
            exchange.create_market_sell_order(simbolo, cantidad)
            print("   ✅ Posición cerrada y limpia.")
        except: pass

if __name__ == "__main__":
    prueba_cancelar_reemplazar_lenta()