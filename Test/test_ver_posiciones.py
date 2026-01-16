import sys
import os
from colorama import init, Fore

# Rutas
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from Core.Ejecucion.GestorEjecucion import GestorEjecucion

init(autoreset=True)

def espiar_posiciones():
    print(Fore.YELLOW + "--- 🕵️‍♂️ INSPECTOR DE POSICIONES ABIERTAS ---")
    
    gestor = GestorEjecucion()
    
    try:
        # Pedimos TODAS las posiciones (sin filtrar)
        print("Consultando a Binance (esto puede tardar unos segundos)...")
        todas_posiciones = gestor.exchange.fetch_positions()
        
        encontradas = 0
        for pos in todas_posiciones:
            cantidad = float(pos['contracts']) # O 'positionAmt' según la API
            simbolo_binance = pos['symbol']
            
            # Solo mostramos las que tienen dinero puesto
            if abs(cantidad) > 0:
                encontradas += 1
                print(f"{Fore.GREEN}✅ POSICIÓN DETECTADA:")
                print(f"   - Símbolo (Binance): '{simbolo_binance}'")
                print(f"   - Cantidad: {cantidad}")
                print(f"   - Precio Entrada: {pos.get('entryPrice')}")
                print("-" * 30)

        if encontradas == 0:
            print(Fore.RED + "❌ Binance dice que NO tienes posiciones abiertas.")
            print("Verifica en la web de Testnet si realmente están abiertas o si es en otra cuenta.")
            
    except Exception as e:
        print(Fore.RED + f"💥 Error al consultar: {e}")

if __name__ == "__main__":
    espiar_posiciones()