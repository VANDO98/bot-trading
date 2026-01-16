import sys
import os
import time
import pandas as pd
from colorama import init, Fore, Style, Back

# Configuración de rutas
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from Core.BotController import BotController

# Inicializar colores
init(autoreset=True)

def limpiar_pantalla():
    os.system('cls' if os.name == 'nt' else 'clear')

def obtener_color_rsi(rsi_val, sobreventa, sobrecompra):
    """Devuelve el color del RSI según su estado."""
    if rsi_val <= sobreventa:
        return Fore.GREEN + Style.BRIGHT  # Verde Brillante (Oportunidad Compra)
    elif rsi_val >= sobrecompra:
        return Fore.RED + Style.BRIGHT    # Rojo Brillante (Oportunidad Venta)
    else:
        return Fore.WHITE                 # Neutro

def formatear_precio(precio):
    if precio < 1.0: return f"{precio:.5f}"
    if precio < 100: return f"{precio:.3f}"
    return f"{precio:.2f}"

def main():
    # 1. Instanciar y Arrancar el Bot
    print(Fore.YELLOW + "🤖 Cargando Sistema de Trading v2.3...")
    bot = BotController()
    bot.iniciar() # Ahora esto no bloquea, los WebSockets corren de fondo

    # Esperamos un poco a que lleguen los primeros datos
    print("⏳ Esperando datos de mercado (5 seg)...")
    time.sleep(5)

    try:
        # 2. BUCLE INFINITO DE VISUALIZACIÓN (Dashboard)
        while True:
            limpiar_pantalla()
            
            # --- HEADER ---
            print(Back.BLUE + Fore.WHITE + f" 🤖 BOT TRADING V2.3 | ESTRATEGIA: RSI | {time.strftime('%H:%M:%S')} ".center(80))
            print(Back.BLACK + "-" * 80)
            print(f"{'PAR':<12} | {'PRECIO':<12} | {'RSI (14)':<10} | {'ESTADO':<15} | {'SEÑAL'}")
            print("-" * 80)

            # --- FILAS ---
            pares_ordenados = sorted(bot.estrategias_activas.keys())
            
            for par in pares_ordenados:
                estrategia = bot.estrategias_activas[par]
                
                # A) Datos del Ticker (Precio Real)
                precio_real = bot.gestor_datos.obtener_precio(par)
                
                # B) Datos de la Estrategia (RSI)
                rsi_str = "Calc..."
                color_rsi = Fore.CYAN
                estado_txt = "Esperando..."
                senal_txt = ""

                # Accedemos de forma segura al DataFrame de la estrategia
                if not estrategia.velas.empty and 'RSI' in estrategia.velas.columns:
                    val_rsi = estrategia.velas.iloc[-1]['RSI']
                    
                    if pd.notna(val_rsi):
                        # Obtenemos parámetros para colorear
                        s_venta = estrategia.parametros.get('rsi_sobreventa', 30)
                        s_compra = estrategia.parametros.get('rsi_sobrecompra', 70)
                        
                        color_rsi = obtener_color_rsi(val_rsi, s_venta, s_compra)
                        rsi_str = f"{val_rsi:.2f}"
                        
                        # Definir Estado Texto
                        if val_rsi <= s_venta:
                            estado_txt = f"{Fore.GREEN}SOBREVENTA"
                            senal_txt = f"{Back.GREEN}{Fore.WHITE} COMPRA "
                        elif val_rsi >= s_compra:
                            estado_txt = f"{Fore.RED}SOBRECOMPRA"
                            senal_txt = f"{Back.RED}{Fore.WHITE} VENTA "
                        else:
                            estado_txt = f"{Fore.WHITE}NEUTRO"

                # Imprimir Fila
                p_str = formatear_precio(precio_real)
                print(f"{Fore.CYAN}{par:<12} {Style.RESET_ALL}| "
                      f"{p_str:<12} | "
                      f"{color_rsi}{rsi_str:<10} {Style.RESET_ALL}| "
                      f"{estado_txt:<24} | " # Espacio extra por los códigos de color
                      f"{senal_txt}")

            print("-" * 80)
            print(f"{Fore.YELLOW}Monitor activo. Presiona Ctrl+C para detener.")
            
            # Refresco de pantalla (cada 1 segundo para sensación de tiempo real)
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n🛑 Deteniendo bot...")
        bot.detener()
        print("✅ Hasta luego.")

if __name__ == "__main__":
    main()