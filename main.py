import sys
import os
import time
import pandas as pd
from colorama import init, Fore, Style, Back

# Configuración de rutas
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Logs
from Core.Utils.Logger import activar_logger
from Core.BotController import BotController

# Inicializar colores
init(autoreset=True)

def limpiar_pantalla():
    os.system('cls' if os.name == 'nt' else 'clear')

def obtener_color_rsi(rsi_val, sobreventa, sobrecompra):
    if rsi_val <= sobreventa: return Fore.GREEN + Style.BRIGHT
    elif rsi_val >= sobrecompra: return Fore.RED + Style.BRIGHT
    else: return Fore.WHITE

def formatear_precio(precio):
    if precio < 1.0: return f"{precio:.5f}"
    if precio < 100: return f"{precio:.3f}"
    return f"{precio:.2f}"

def ciclo_principal():
    """Lógica del bot encapsulada."""
    bot = BotController()
    
    # Bloque Try interno para poder detener el bot limpiamente si falla aquí
    try:
        bot.iniciar() # Arranca hilos
        
        print("⏳ Esperando datos de mercado (5 seg)...")
        time.sleep(5)

        # BUCLE DE VISUALIZACIÓN
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
                precio_real = bot.gestor_datos.obtener_precio(par)
                
                # Recuperar datos
                rsi_str = "Calc..."
                color_rsi = Fore.CYAN
                estado_txt = "Esperando..."
                senal_txt = ""

                if not estrategia.velas.empty and 'RSI' in estrategia.velas.columns:
                    val_rsi = estrategia.velas.iloc[-1]['RSI']
                    if pd.notna(val_rsi):
                        # Leemos los parámetros reales de la estrategia para colorear bien
                        s_venta = estrategia.parametros.get('rsi_sobreventa', 30)
                        s_compra = estrategia.parametros.get('rsi_sobrecompra', 70)
                        
                        color_rsi = obtener_color_rsi(val_rsi, s_venta, s_compra)
                        rsi_str = f"{val_rsi:.2f}"
                        
                        # Usamos la memoria de la estrategia para mostrar el estado
                        if estrategia.posicion_abierta:
                             estado_txt = f"{Back.MAGENTA}{Fore.WHITE} EN MERCADO "
                        elif val_rsi <= s_venta:
                            estado_txt = f"{Fore.GREEN}SOBREVENTA"
                            senal_txt = f"{Back.GREEN}{Fore.WHITE} COMPRA "
                        elif val_rsi >= s_compra:
                            estado_txt = f"{Fore.RED}SOBRECOMPRA"
                            senal_txt = f"{Back.RED}{Fore.WHITE} VENTA "
                        else:
                            estado_txt = f"{Fore.WHITE}NEUTRO"

                # Renderizar
                p_str = formatear_precio(precio_real)
                print(f"{Fore.CYAN}{par:<12} {Style.RESET_ALL}| "
                      f"{p_str:<12} | "
                      f"{color_rsi}{rsi_str:<10} {Style.RESET_ALL}| "
                      f"{estado_txt:<24} | " 
                      f"{senal_txt}")

            print("-" * 80)
            print(f"{Fore.YELLOW}Monitor activo. Presiona Ctrl+C para detener.")
            
            time.sleep(1)

    except KeyboardInterrupt:
        # Re-lanzamos la interrupción para que la capture el main
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
            print("\n🛑 Deteniendo bot por usuario (Forzando cierre)...")
            # ESTO ES LO QUE ARREGLA EL CONGELAMIENTO
            # Mata el proceso y todos sus hilos inmediatamente
            try:
                sys.exit(0)
            except SystemExit:
                os._exit(0)
            
        except Exception as e:
            print(Fore.RED + f"\n💥 ERROR CRÍTICO DETECTADO: {e}")
            print(Fore.YELLOW + "🔄 Reiniciando sistema en 5 segundos...")
            try:
                time.sleep(5)
            except KeyboardInterrupt:
                os._exit(0)

if __name__ == "__main__":
    main()