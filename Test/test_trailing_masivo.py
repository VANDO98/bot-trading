import sys
import os
import ccxt
import json
import pandas as pd
import pandas_ta as ta  # Necesitas tener instalado pandas_ta
from dotenv import load_dotenv
from colorama import init, Fore, Style
from pathlib import Path

# --- AJUSTE DE RUTAS PARA IMPORTAR CORE ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from Core.Utils.Config import Config

init(autoreset=True)

def calcular_atr_simple(exchange, simbolo, timeframe='1h', periodo=14):
    """Calcula el ATR descargando las últimas velas."""
    try:
        ohlcv = exchange.fetch_ohlcv(simbolo, timeframe, limit=periodo+5)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=periodo)
        return df['atr'].iloc[-1]
    except Exception:
        return 0.0

def auditar_trailing_masivo():
    print(Fore.YELLOW + "🕵️ INICIANDO AUDITORÍA MASIVA DE TRAILING STOP...")
    
    # 1. CARGAR CONFIGURACIÓN
    config_completa = Config.cargar_configuracion()
    pares_config = config_completa.get('pares', {})
    usar_testnet = config_completa.get('usar_testnet', True)
    
    # 2. CONECTAR EXCHANGE
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(dotenv_path=env_path)
    
    key = os.getenv("BINANCE_API_KEY")
    secret = os.getenv("BINANCE_SECRET_KEY")
    
    try:
        exchange = ccxt.binance({
            'apiKey': key,
            'secret': secret,
            'options': {'defaultType': 'future'}
        })
        if usar_testnet:
            exchange.set_sandbox_mode(True)
            print(Fore.MAGENTA + "⚠️ MODO TESTNET ACTIVADO")
        else:
            print(Fore.CYAN + "💳 MODO REAL ACTIVADO")
            
        exchange.load_markets()
    except Exception as e:
        print(Fore.RED + f"❌ Error de conexión: {e}")
        return

    # 3. OBTENER TODAS LAS POSICIONES DE UNA VEZ
    print(Fore.CYAN + "📥 Descargando posiciones abiertas...")
    todas_posiciones = exchange.fetch_positions()
    mapa_posiciones = {}
    
    # Filtrar solo las que tienen tamaño > 0
    for p in todas_posiciones:
        if float(p['contracts']) > 0:
            # Normalizar símbolo: 'BTC/USDT:USDT' -> 'BTC/USDT'
            simbolo_limpio = p['symbol'].split(':')[0].replace('/', '') # BTCUSDT
            mapa_posiciones[simbolo_limpio] = p

    # 4. ITERAR SOBRE PARES ACTIVOS DEL JSON
    print(Fore.WHITE + "-" * 80)
    print(f"{'PAR':<12} | {'ROE %':<8} | {'SL ACTUAL':<10} | {'SL CALCULADO':<12} | {'ACCIÓN ESPERADA'}")
    print(Fore.WHITE + "-" * 80)

    for par, cfg in pares_config.items():
        if not cfg.get('activo', False):
            continue
            
        # El JSON tiene 'BTC/USDT', Binance usa 'BTCUSDT' o 'BTC/USDT'
        symbol_key = par.replace('/', '') # BTCUSDT para buscar en el mapa
        
        if symbol_key not in mapa_posiciones:
            continue # No hay posición en este par activo

        # --- DATOS DE LA POSICIÓN ---
        pos = mapa_posiciones[symbol_key]
        entry_price = float(pos['entryPrice'])
        amount = float(pos['contracts'])
        mark_price = float(pos.get('markPrice', entry_price)) # Fallback
        lev = cfg.get('apalancamiento', 10) # Sacado del JSON
        
        # Detectar lado (Binance a veces da positivo/negativo en positionAmt)
        raw_amt = float(pos['info']['positionAmt'])
        lado = 'buy' if raw_amt > 0 else 'sell'

        # --- CÁLCULO DE ROE REAL ---
        if lado == 'buy':
            roe = ((mark_price - entry_price) / entry_price) * lev
        else:
            roe = ((entry_price - mark_price) / entry_price) * lev
            
        roe_pct = roe * 100

        # --- BUSCAR SL ACTUAL ---
        sl_actual = 0.0
        try:
            ordenes = exchange.fetch_open_orders(par)
            for o in ordenes:
                if o['type'] == 'STOP_MARKET' and o.get('reduceOnly', False):
                    sl_actual = float(o['stopPrice'])
                    break
        except:
            sl_actual = 0.0

        # --- SIMULAR LÓGICA DEL BOT (BotController.py) ---
        nuevo_sl = 0.0
        motivo = ""
        
        # Lógica ROE > 10% (Trailing Dinámico con ATR)
        if roe >= 0.10:
            atr = calcular_atr_simple(exchange, par)
            dist_atr = 2 * atr
            margen_fee = entry_price * 0.0015
            
            if lado == 'buy':
                target_atr = mark_price - dist_atr
                target_be = entry_price + margen_fee
                nuevo_sl = max(target_atr, target_be)
            else:
                target_atr = mark_price + dist_atr
                target_be = entry_price - margen_fee
                nuevo_sl = min(target_atr, target_be)
            motivo = "ATR (ROE > 10%)"

        # Lógica ROE > 5% (Solo Breakeven)
        elif roe >= 0.05:
            margen_fee = entry_price * 0.0015
            if lado == 'buy':
                nuevo_sl = entry_price + margen_fee
            else:
                nuevo_sl = entry_price - margen_fee
            motivo = "BE (ROE > 5%)"
        
        else:
            motivo = "ROE Insuficiente"

        # --- EVALUAR ACCIÓN ---
        accion = f"{Fore.LIGHTBLACK_EX}Nada que hacer"
        color_sl_calc = Fore.WHITE

        if nuevo_sl > 0:
            distancia_seguridad = mark_price * 0.002
            es_seguro = False
            
            # Verificar si mejora el precio
            mejora = False
            if lado == 'buy':
                if nuevo_sl > sl_actual: mejora = True
                if nuevo_sl < (mark_price - distancia_seguridad): es_seguro = True
            else: # sell
                # En short, un SL más bajo es mejor (más cerca del precio actual que baja)
                # PERO cuidado: stop loss siempre está por ENCIMA del precio en short.
                # Si el precio baja, el SL baja. Entonces: nuevo_sl < sl_actual es MEJORA.
                if sl_actual == 0: mejora = True # Si no hay SL, cualquiera es mejora
                elif nuevo_sl < sl_actual: mejora = True
                
                if nuevo_sl > (mark_price + distancia_seguridad): es_seguro = True

            if mejora and es_seguro:
                accion = f"{Fore.GREEN}✅ ACTUALIZARÁ AL CIERRE"
                color_sl_calc = Fore.GREEN
            elif mejora and not es_seguro:
                accion = f"{Fore.YELLOW}⚠️ Muy cerca del precio"
            elif not mejora:
                accion = f"{Fore.CYAN}🆗 SL ya optimizado"
        
        # Formatear salida
        str_sl_act = f"{sl_actual:.4f}" if sl_actual > 0 else "NO TIENE"
        str_sl_new = f"{nuevo_sl:.4f}" if nuevo_sl > 0 else "---"
        
        print(f"{par:<12} | {roe_pct:>6.2f}% | {str_sl_act:<10} | {color_sl_calc}{str_sl_new:<12}{Style.RESET_ALL} | {accion}")

if __name__ == "__main__":
    auditar_trailing_masivo()