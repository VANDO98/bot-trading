import sys
import os
import time
from colorama import Fore
from dotenv import load_dotenv # Necesario para leer tus claves

# Configuración de rutas
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Imports del Sistema
from Core.Utils.Logger import activar_logger
from Core.BotController import BotController
from Core.Utils.Dashboard import Dashboard 
from Core.Interfaz.Telegram.TelegramManager import TelegramManager # <--- Importamos el Módulo de Telegram

# --- CONFIGURACIÓN ---
# True: Muestra la tabla bonita (Gasta CPU visual)
# False: Modo "Silencioso" / VPS (Solo logs en archivo)
MOSTRAR_DASHBOARD = False

def ciclo_principal():
    """
    Orquestador principal dinámico.
    """
    # 1. Inicializar Cerebro
    bot = BotController()
    
    # 2. Inicializar Telegram
    telegram_token = os.getenv("TELEGRAM_TOKEN")
    telegram_id = os.getenv("TELEGRAM_ID")
    telegram_bot = None

    if telegram_token and telegram_id:
        try:
            print(Fore.CYAN + "📡 Conectando Telegram...")
            telegram_bot = TelegramManager(telegram_token, telegram_id, bot)
            telegram_bot.iniciar()
        except Exception as e:
            print(Fore.RED + f"⚠️ Error Telegram: {e}")
    else:
        print(Fore.YELLOW + "⚠️ Telegram omitido.")

    # 3. Inicializar Dashboard
    dashboard = Dashboard(bot)
    
    try:
        bot.iniciar()
        print("⏳ Esperando datos de mercado (5 seg)...")
        time.sleep(5)

        # 4. BUCLE INFINITO DINÁMICO
        # Ya no hay "if MOSTRAR_DASHBOARD" afuera, ahora se chequea adentro.
        
        ultimo_estado_dash = False # Para detectar cambios y limpiar pantalla
        print(Fore.GREEN + "✅ Sistema en línea. Esperando comandos...")

        while True:
            # A. Si el usuario activó el Dashboard (/dash on)
            if bot.mostrar_dashboard:
                if not ultimo_estado_dash:
                    print(Fore.GREEN + "📺 Iniciando transmisión visual...")
                    ultimo_estado_dash = True
                
                dashboard.mostrar()
                time.sleep(5) # Refresco visual (5s)

            # B. Si está apagado (/dash off) - Modo Silencioso
            else:
                if ultimo_estado_dash:
                    # Si acabamos de apagarlo, limpiamos o avisamos
                    os.system('cls' if os.name == 'nt' else 'clear')
                    print(Fore.GREEN + "🔇 Modo Silencioso Activado (Logs en CSV).")
                    ultimo_estado_dash = False
                
                # Pausa más larga para ahorrar CPU en modo servidor
                time.sleep(5) 

    except KeyboardInterrupt:
        print(Fore.YELLOW + "\n🛑 Interrupción de usuario...")
        bot.detener()
        if telegram_bot: telegram_bot.detener()
        raise
    except Exception as e:
        print(Fore.RED + f"❌ Error crítico: {e}")
        bot.detener()
        if telegram_bot: telegram_bot.detener()
        raise e

def main():
    # Cargar variables de entorno antes de nada
    load_dotenv()
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