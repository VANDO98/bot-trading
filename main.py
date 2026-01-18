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

def obtener_color_adx(adx_val, minimo):
    """
    Verde si hay tendencia fuerte (> min), Gris si está lateral.
    """
    if adx_val >= minimo: return Fore.GREEN + Style.BRIGHT
    return Fore.LIGHTBLACK_EX 

def formatear_precio(precio):
    if precio < 1.0: return f"{precio:.5f}"
    if precio < 100: return f"{precio:.3f}"
    return f"{precio:.2f}"

def ciclo_principal():
    """Lógica del bot encapsulada."""
    bot = BotController()
    
    try:
        bot.iniciar() # Arranca hilos
        
        print("⏳ Esperando datos de mercado (5 seg)...")
        time.sleep(5)

        # BUCLE DE VISUALIZACIÓN
        while True:
            limpiar_pantalla()
            
            # --- HEADER --- (Ampliado a 125 caracteres para nueva columna)
            ancho = 125
            print(Back.BLUE + Fore.WHITE + f" 🤖 BOT TRADING V2.9 | RSI + ADX + PNL($) | {time.strftime('%H:%M:%S')} ".center(ancho))
            print(Back.BLACK + "-" * ancho)
            # Añadida columna PNL $
            print(f"{'PAR':<12} | {'PRECIO':<10} | {'RSI':<6} | {'ADX':<6} | {'ROE %':<10} | {'PNL $':<10} | {'ESTADO':<18} | {'SEÑAL'}")
            print("-" * ancho)

            # --- FILAS ---
            pares_ordenados = sorted(bot.estrategias_activas.keys())
            
            for par in pares_ordenados:
                estrategia = bot.estrategias_activas[par]
                precio_real = bot.gestor_datos.obtener_precio(par)
                
                # Variables por defecto
                rsi_str = "Calc.."
                adx_str = "N/A"
                roe_str = f"{Fore.LIGHTBLACK_EX}   --   "
                pnl_usd_str = f"{Fore.LIGHTBLACK_EX}   --   " # Nueva variable
                
                color_rsi = Fore.CYAN
                color_adx = Fore.WHITE
                estado_txt = "Esperando..."
                senal_txt = ""

                # --- 1. PROCESAMIENTO DE INDICADORES (RSI / ADX) ---
                if not estrategia.velas.empty:
                    # RSI
                    if 'RSI' in estrategia.velas.columns:
                        val_rsi = estrategia.velas.iloc[-1]['RSI']
                        if pd.notna(val_rsi):
                            s_venta = estrategia.parametros.get('rsi_sobreventa', 30)
                            s_compra = estrategia.parametros.get('rsi_sobrecompra', 70)
                            color_rsi = obtener_color_rsi(val_rsi, s_venta, s_compra)
                            rsi_str = f"{val_rsi:.1f}"
                            
                            if val_rsi <= s_venta: estado_txt = f"{Fore.GREEN}SOBREVENTA"
                            elif val_rsi >= s_compra: estado_txt = f"{Fore.RED}SOBRECOMPRA"
                            else: estado_txt = f"{Fore.WHITE}NEUTRO"

                    # ADX
                    if 'ADX' in estrategia.velas.columns:
                        val_adx = estrategia.velas.iloc[-1]['ADX']
                        if pd.notna(val_adx):
                            min_adx = estrategia.parametros.get('adx_minimo', 25)
                            color_adx = obtener_color_adx(val_adx, min_adx)
                            adx_str = f"{val_adx:.1f}"

                    # --- 2. CÁLCULO DE PNL (Si hay posición) ---
                    if estrategia.posicion_abierta:
                        estado_txt = f"{Back.MAGENTA}{Fore.WHITE} EN MERCADO "
                        
                        # Consultar datos reales de la posición
                        datos_pos = bot.gestor_ejecucion.obtener_datos_posicion(par)
                        
                        if datos_pos:
                            entry = datos_pos['entryPrice']
                            side = datos_pos['side']
                            amount = datos_pos['amount'] # Cantidad de monedas
                            mark = datos_pos.get('markPrice', precio_real) 
                            lev = bot.config_pares[par].get('apalancamiento', 1)

                            # A) Cálculo ROE %
                            if side == 'buy':
                                delta_pct = (mark - entry) / entry
                                diff_precio = mark - entry
                            else:
                                delta_pct = (entry - mark) / entry
                                diff_precio = entry - mark
                            
                            roe_val = delta_pct * lev * 100
                            
                            # B) Cálculo PNL USD Real
                            # Ganancia = Diferencia de precio * Cantidad de monedas
                            pnl_usd_val = diff_precio * amount

                            # Colores Dinámicos
                            if roe_val > 0: 
                                color_pnl = Fore.GREEN + Style.BRIGHT
                            elif roe_val < 0: 
                                color_pnl = Fore.RED + Style.BRIGHT
                            else: 
                                color_pnl = Fore.WHITE
                            
                            roe_str = f"{color_pnl}{roe_val:+.2f}%"
                            pnl_usd_str = f"{color_pnl}${pnl_usd_val:+.2f}"
                    
                    # --- 3. SEÑALES ---
                    elif 'RSI' in estrategia.velas.columns and 'ADX' in estrategia.velas.columns:
                         v_rsi = estrategia.velas.iloc[-1]['RSI']
                         v_adx = estrategia.velas.iloc[-1]['ADX']
                         
                         if pd.notna(v_rsi) and pd.notna(v_adx):
                            s_venta = estrategia.parametros.get('rsi_sobreventa', 30)
                            s_compra = estrategia.parametros.get('rsi_sobrecompra', 70)
                            min_adx = estrategia.parametros.get('adx_minimo', 25)
                            
                            if v_adx > min_adx: 
                                if v_rsi < s_venta:
                                    senal_txt = f"{Back.GREEN}{Fore.WHITE} COMPRA "
                                elif v_rsi > s_compra:
                                    senal_txt = f"{Back.RED}{Fore.WHITE} VENTA "

                # Renderizar Fila
                p_str = formatear_precio(precio_real)
                
                print(f"{Fore.CYAN}{par:<12} {Style.RESET_ALL}| "
                      f"{p_str:<10} | "
                      f"{color_rsi}{rsi_str:<6} {Style.RESET_ALL}| "
                      f"{color_adx}{adx_str:<6} {Style.RESET_ALL}| "
                      f"{roe_str:<10} {Style.RESET_ALL}| " # ROE
                      f"{pnl_usd_str:<10} {Style.RESET_ALL}| " # PNL $
                      f"{estado_txt:<27} | " 
                      f"{senal_txt}")

            print("-" * ancho)
            print(f"{Fore.YELLOW}Monitor activo. Ctrl+C para salir.")
            
            time.sleep(3) 

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