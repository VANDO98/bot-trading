import sys
import os
import ccxt
from dotenv import load_dotenv
from colorama import init, Fore, Style
from pathlib import Path

# Ajustar rutas para importar Core
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

init(autoreset=True)

def debug_trailing():
    print(Fore.YELLOW + "🕵️ INICIANDO DIAGNÓSTICO DE TRAILING STOP (ZEC) [MODO TESTNET]...")

    # --- 1. CARGA ROBUSTA DE VARIABLES DE ENTORNO ---
    env_path = Path(__file__).parent.parent / '.env'
    print(Fore.CYAN + f"📂 Buscando archivo .env en: {env_path}")
    
    if env_path.exists():
        print(Fore.GREEN + "   ✅ Archivo .env encontrado.")
        load_dotenv(dotenv_path=env_path)
    else:
        print(Fore.RED + "   ❌ NO SE ENCUENTRA EL ARCHIVO .env")
        return

    api_key = os.getenv("BINANCE_API_KEY")
    secret_key = os.getenv("BINANCE_SECRET_KEY")

    if not api_key or not secret_key:
        print(Fore.RED + "   ❌ Faltan las API Keys en el .env")
        return
    
    print(Fore.GREEN + f"   🔑 API Key cargada: {api_key[:4]}...OK")

    # --- 2. CONEXIÓN (CORREGIDO PARA TESTNET) ---
    try:
        exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': secret_key,
            'options': {'defaultType': 'future'}
        })
        
        # 🔥 ESTA ES LA LÍNEA MÁGICA QUE FALTABA 🔥
        exchange.set_sandbox_mode(True) 
        print(Fore.YELLOW + "   ⚠️ MODO SANDBOX (TESTNET) ACTIVADO")

        exchange.load_markets()
        print(Fore.GREEN + "   📡 Conexión con Binance Testnet exitosa.")
    except Exception as e:
        print(Fore.RED + f"❌ Error conectando a Binance: {e}")
        return

    simbolo = "ZEC/USDT" 
    
    print(Fore.CYAN + f"\n3. CONSULTANDO POSICIÓN DE {simbolo}...")
    try:
        # Buscamos coincidencias flexibles
        positions = exchange.fetch_positions()
        pos_data = None
        
        target = simbolo.replace('/', '').upper() # ZECUSDT
        
        for p in positions:
            # Limpieza del símbolo de la API (A veces viene como ZECUSDT, a veces ZEC/USDT:USDT)
            s_api_raw = p['symbol'].replace('/', '').upper()
            s_api = s_api_raw.split(':')[0]
            
            if s_api == target and float(p['contracts']) > 0:
                pos_data = p
                print(Fore.GREEN + f"   ✅ Posición encontrada: {p['symbol']} | Lado: {p['side']} | Entry: {p['entryPrice']} | Amt: {p['contracts']}")
                break
        
        if not pos_data:
            print(Fore.RED + f"   ❌ No se detectó posición abierta en {simbolo} (Revisa si el bot la cerró ya).")
            # Listar qué hay abierto para ayudar
            print(Fore.YELLOW + "   Posiciones abiertas encontradas en tu cuenta:")
            encontradas = 0
            for p in positions:
                if float(p['contracts']) > 0:
                    print(f"    - {p['symbol']}: {p['contracts']}")
                    encontradas += 1
            if encontradas == 0: print("    (Ninguna)")
            return

    except Exception as e:
        print(Fore.RED + f"❌ Error obteniendo posiciones: {e}")
        return

    print(Fore.CYAN + f"\n4. BUSCANDO ÓRDENES DE STOP LOSS...")
    try:
        orders = exchange.fetch_open_orders(simbolo)
        print(f"   Total órdenes encontradas: {len(orders)}")
        
        orden_sl_candidata = None

        for o in orders:
            es_stop = o['type'] == 'STOP_MARKET'
            es_reduce = o['reduceOnly']
            o_id = o['id']
            o_price = o['stopPrice']
            
            print(Fore.WHITE + f"   ➡ Orden ID: {o_id} | Tipo: {o['type']} | Reduce: {es_reduce} | StopPrice: {o_price}")
            
            # Simulación del filtro del Bot
            if es_stop and es_reduce:
                orden_sl_candidata = o
                print(Fore.GREEN + "      ✨ ESTA CUMPLE LOS REQUISITOS DEL BOT")
            else:
                print(Fore.RED + "      ⚠️ EL BOT IGNORARÍA ESTA ORDEN (Revisa Tipo o ReduceOnly)")

    except Exception as e:
        print(Fore.RED + f"❌ Error trayendo órdenes: {e}")
        return

    print(Fore.CYAN + "\n5. SIMULACIÓN DE CÁLCULO DE TRAILING...")
    if not orden_sl_candidata:
        print(Fore.RED + "❌ CONCLUSIÓN: El bot dice 'NO SL' porque no ve ninguna orden STOP_MARKET con reduceOnly=True.")
        return
    else:
        print(Fore.GREEN + "✅ El bot SI debería ver la orden. Validemos matemáticas:")

    # Datos para simulación
    entry = float(pos_data['entryPrice'])
    mark = float(pos_data['markPrice']) if pos_data.get('markPrice') else float(exchange.fetch_ticker(simbolo)['last'])
    sl_actual = float(orden_sl_candidata['stopPrice'])
    
    # ATR Hardcodeado
    atr = 10.0 
    
    # Calcular ROE
    raw_amt = float(pos_data['info']['positionAmt'])
    lado = 'buy' if raw_amt > 0 else 'sell'
    lev = int(pos_data['leverage'])
    
    if lado == 'sell': # SHORT
        delta = (entry - mark) / entry
        roe = delta * lev
        
        print(f"   📉 SHORT | Entry: {entry} | Mark: {mark} | Lev: {lev}x | ROE: {roe*100:.2f}%")
        
        if roe >= 0.10:
            print(Fore.GREEN + "   🚀 ROE > 10% -> Activar lógica ATR/BE")
            dist_atr = 2 * atr
            target_atr = mark + dist_atr
            target_be = entry - (entry * 0.0015)
            
            print(f"      Target ATR: {target_atr:.2f}")
            print(f"      Target BE:  {target_be:.2f}")
            
            nuevo_sl = min(target_atr, target_be)
            print(Fore.YELLOW + f"      NUEVO SL CALCULADO: {nuevo_sl:.2f}")
            
            if nuevo_sl < sl_actual:
                print(Fore.GREEN + f"      ✅ ACCIÓN: El bot MOVERÁ el SL de {sl_actual} a {nuevo_sl}")
            else:
                print(Fore.RED + f"      ⏸ ESPERA: El SL actual ({sl_actual}) ya es mejor o igual al calculado ({nuevo_sl}).")
                print("      (El bot no lo mueve para no 'retroceder' o gastar API calls innecesarios)")
        else:
            print(Fore.YELLOW + "   ⏸ ROE < 10%. Aún no activa trailing dinámico.")
    
    elif lado == 'buy': # LONG
        delta = (mark - entry) / entry
        roe = delta * lev
        print(f"   📈 LONG | Entry: {entry} | Mark: {mark} | Lev: {lev}x | ROE: {roe*100:.2f}%")
        
        if roe >= 0.10:
             print(Fore.GREEN + "   🚀 ROE > 10%")
             dist_atr = 2 * atr
             target_atr = mark - dist_atr
             target_be = entry + (entry * 0.0015)
             nuevo_sl = max(target_atr, target_be)
             
             print(f"      Target ATR: {target_atr:.2f} | BE: {target_be:.2f} | FINAL: {nuevo_sl:.2f}")
             
             if nuevo_sl > sl_actual:
                 print(Fore.GREEN + f"      ✅ ACCIÓN: El bot MOVERÁ el SL de {sl_actual} a {nuevo_sl}")
             else:
                 print(Fore.RED + f"      ⏸ ESPERA: SL actual ({sl_actual}) es mejor.")

if __name__ == "__main__":
    debug_trailing()