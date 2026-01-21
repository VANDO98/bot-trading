import sys
import os
import time
import datetime
from colorama import init, Fore, Style

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from Core.API.GestorWebsocket import GestorWebsocket

init(autoreset=True)

# --- MEMORIA COMPARTIDA ---
# Aquí guardaremos lo que llega del WebSocket de Velas
info_velas = {}

def limpiar_pantalla():
    os.system('cls' if os.name == 'nt' else 'clear')

def callback_vela(symbol, kline_data):
    """
    Guarda la última vela recibida para mostrarla en la tabla.
    """
    info_velas[symbol] = {
        'cierre': float(kline_data['c']), # Precio actual de la vela
        'volumen': float(kline_data['v']), # Volumen acumulado
        'cerrada': kline_data['x']        # True si la vela ya cerró
    }

def formatear_precio(precio):
    """Ayuda visual para precios pequeños (PEPE, SHIB) vs grandes (BTC)"""
    if precio < 0.01: return f"{precio:.7f}"
    if precio < 1.0:  return f"{precio:.5f}"
    if precio < 100:  return f"{precio:.3f}"
    return f"{precio:.2f}"

def test_dashboard_completo():
    # LISTA DE PARES (Con POL corregido)
    pares_prueba = {
        'BTC/USDT': {'activo': True, 'timeframe': '1m'},
        'ETH/USDT': {'activo': True, 'timeframe': '1m'},
        'BNB/USDT': {'activo': True, 'timeframe': '1m'},
        'XRP/USDT': {'activo': True, 'timeframe': '1m'},
        'ADA/USDT': {'activo': True, 'timeframe': '1m'},
        'DOGE/USDT': {'activo': True, 'timeframe': '1m'},
        'DOT/USDT': {'activo': True, 'timeframe': '1m'},
        'POL/USDT': {'activo': True, 'timeframe': '1m'}, 
        'LTC/USDT': {'activo': True, 'timeframe': '1m'},
        'LINK/USDT': {'activo': True, 'timeframe': '1m'},
        'ZEC/USDT': {'activo': True, 'timeframe': '1m'},
        '1000PEPE/USDT': {'activo': True, 'timeframe': '1m'},
        'SOL/USDT': {'activo': True, 'timeframe': '1m'}
    }

    print(Fore.YELLOW + "--- INICIANDO MONITOR HÍBRIDO (TICKER + VELAS) ---")
    gestor = GestorWebsocket()
    
    # Pasamos nuestro callback real
    gestor.iniciar_flujo_hibrido(pares_prueba, callback_vela)
    
    print("⏳ Llenando buffer de velas (5s)...")
    time.sleep(5)

    total_rondas = 100
    for ronda in range(1, total_rondas + 1):
        limpiar_pantalla()
        
        print(Fore.GREEN + Style.BRIGHT + f"=== DASHBOARD COMPLETO (Ronda {ronda}/{total_rondas}) ===")
        print(f"Hora: {datetime.datetime.now().strftime('%H:%M:%S')}")
        print("-" * 75)
        # Encabezados alineados
        print(f"{'PAR':<14} | {'TICKER (Rápido)':<16} | {'VELA (Lento)':<16} | {'VOLUMEN':<10} | {'ESTADO'}")
        print("-" * 75)

        activos = 0
        for par in pares_prueba.keys():
            # 1. Datos del Ticker (GestorHibrido interno)
            precio_ticker = gestor.obtener_precio(par)
            
            # 2. Datos de la Vela (Nuestro callback)
            datos_vela = info_velas.get(par, {})
            precio_vela = datos_vela.get('cierre', 0.0)
            volumen = datos_vela.get('volumen', 0.0)
            
            # --- FORMATO VISUAL ---
            p_tick_str = formatear_precio(precio_ticker)
            p_vela_str = formatear_precio(precio_vela)
            
            # Color del Estado
            # Consideramos "VIVO" si tenemos precio Ticker Y precio Vela
            if precio_ticker > 0 and precio_vela > 0:
                estado = f"{Fore.GREEN}✅ FULL"
                activos += 1
            elif precio_ticker > 0:
                estado = f"{Fore.YELLOW}⚠️ SOLO TICKER"
            else:
                estado = f"{Fore.RED}❌ OFF"

            # Imprimir Fila
            print(f"{Fore.CYAN}{par:<14} {Style.RESET_ALL}| "
                  f"{p_tick_str:<16} | "
                  f"{p_vela_str:<16} | "
                  f"{Fore.MAGENTA}{volumen:<10.1f} {Style.RESET_ALL}| "
                  f"{estado}")

        print("-" * 75)
        print(f"Sincronización Total: {activos}/{len(pares_prueba)} pares recibiendo doble flujo.")
        print(Fore.YELLOW + "Actualizando en 2 segundos...")
        
        time.sleep(2)

    gestor.detener_todo()

if __name__ == "__main__":
    test_dashboard_completo()