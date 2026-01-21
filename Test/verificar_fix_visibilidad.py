import sys
import os
import ccxt
import json
from dotenv import load_dotenv
from colorama import init, Fore, Style
from pathlib import Path

# Importar tu código base
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from Core.Ejecucion.GestorEjecucion import GestorEjecucion
from Core.Utils.Config import Config

init(autoreset=True)

def verificar_visibilidad_v2():
    print(Fore.YELLOW + "🕵️ VERIFICANDO VISIBILIDAD DE ÓRDENES (V2 - FIX CASE SENSITIVE)...")

    Config.cargar_configuracion()
    
    try:
        gestor = GestorEjecucion()
    except Exception as e:
        print(Fore.RED + f"❌ Error instanciando Gestor: {e}")
        return

    # Pares que mostraron órdenes en tu log anterior
    pares_a_revisar = ['ATOM/USDT', 'DOT/USDT', 'AVAX/USDT', 'ARB/USDT']
    
    print(Fore.CYAN + f"🔎 Revisando pares: {pares_a_revisar}")

    for par in pares_a_revisar:
        print(Fore.WHITE + "-" * 50)
        print(Fore.CYAN + f"Paso 1: Inspección RAW de {par}")
        
        try:
            # A) VERDAD ABSOLUTA (API Directa)
            ordenes = gestor.exchange.fetch_open_orders(par)
            
            sl_encontrado_raw = False
            for o in ordenes:
                # FIX: Convertimos a mayúsculas aquí también para evitar el falso negativo
                tipo = o.get('type', '').upper()
                reduce = o.get('reduceOnly', False)
                precio = o.get('stopPrice')
                lado = o.get('side')
                
                es_candidata = (tipo in ['STOP_MARKET', 'STOP']) and reduce
                
                color = Fore.GREEN if es_candidata else Fore.LIGHTBLACK_EX
                print(f"{color}   ➤ ID: {o['id']} | Tipo: {tipo} | Side: {lado} | Precio: {precio} | ReduceOnly: {reduce}")
                
                if es_candidata:
                    sl_encontrado_raw = True

            if not sl_encontrado_raw:
                print(Fore.RED + f"   ⚠️ OJO: Sigue sin detectarse en RAW. Revisa si es STOP_LIMIT.")
                continue 
            
            # B) PRUEBA DE TU CÓDIGO REAL (GestorEjecucion)
            print(Fore.CYAN + f"Paso 2: Probando GestorEjecucion.obtener_orden_stop_loss('{par}')")
            
            orden_gestor = gestor.obtener_orden_stop_loss(par)
            
            if orden_gestor:
                print(Fore.GREEN + f"   ✅ ÉXITO TOTAL: Tu bot YA VE la orden {orden_gestor['id']} (Stop: {orden_gestor['stopPrice']})")
                print(Fore.GREEN + "      El sistema está listo para hacer Trailing Stop Profit.")
            else:
                print(Fore.RED + f"   ❌ FALLO: Tu código devolvió None. (Verifica GestorEjecucion.py)")

        except Exception as e:
            print(Fore.RED + f"❌ Error revisando {par}: {e}")

if __name__ == "__main__":
    verificar_visibilidad_v2()