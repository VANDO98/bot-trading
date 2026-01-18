import sys
import os
import time
from colorama import Fore

# Configuración de rutas
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Imports del Sistema
from Core.Utils.Logger import activar_logger
from Core.BotController import BotController
from Core.Utils.Dashboard import Dashboard # <--- Importamos la nueva clase

# --- CONFIGURACIÓN ---
# True: Muestra la tabla bonita (Gasta CPU visual)
# False: Modo "Silencioso" / VPS (Solo logs en archivo)
MOSTRAR_DASHBOARD = False

def ciclo_principal():
    """
    Orquestador principal.
    """
    # 1. Inicializar Cerebro del Bot
    bot = BotController()
    
    # 2. Inicializar Sistema Visual (Le pasamos el cerebro)
    dashboard = Dashboard(bot)
    
    try:
        bot.iniciar() # Arranca hilos de trading
        
        print("⏳ Esperando datos de mercado (5 seg)...")
        time.sleep(5)

        if MOSTRAR_DASHBOARD:
            print(Fore.GREEN + "📺 Iniciando Dashboard Visual...")
            while True:
                # El main delega todo el trabajo de dibujo al Dashboard
                dashboard.mostrar()
                time.sleep(5) # Refresco visual cada 5s
        else:
            # MODO SILENCIOSO (Server Mode)
            print(Fore.GREEN + "🔇 Modo Silencioso activado.")
            print(Fore.YELLOW + "Logs disponibles en historial_trading.csv")
            while True:
                time.sleep(60) # Mantener vivo el proceso

    except KeyboardInterrupt:
        bot.detener()
        raise
    except Exception as e:
        bot.detener()
        raise e

def main():
    activar_logger()
    
    while True:
        try:
            print(Fore.YELLOW + "\n🚀 Iniciando Motor del Bot...")
            ciclo_principal()
            
        except KeyboardInterrupt:
            print("\n🛑 Deteniendo bot por usuario...")
            try:
                sys.exit(0)
            except SystemExit:
                os._exit(0)
            
        except Exception as e:
            print(Fore.RED + f"\n💥 ERROR CRÍTICO: {e}")
            print(Fore.YELLOW + "🔄 Reiniciando en 5s...")
            try:
                time.sleep(5)
            except KeyboardInterrupt:
                os._exit(0)

if __name__ == "__main__":
    main()