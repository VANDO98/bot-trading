import sys
import os
import time
from colorama import init, Fore, Style

# --- 1. CONFIGURACIÓN DE RUTAS ---
# Añadimos la raíz del proyecto al path para poder importar los módulos Core
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Core.Ejecucion.GestorEjecucion import GestorEjecucion
from Core.Utils.Config import Config

# Inicializar colorama
init(autoreset=True)

def calcular_roe_manual(entry_price, mark_price, lado, apalancamiento):
    """
    Aplica la fórmula estándar de futuros para ROE %.
    """
    if lado == 'buy': # LONG
        # (Precio Actual - Entrada) / Entrada
        delta = (mark_price - entry_price) / entry_price
    else: # SHORT
        # (Entrada - Precio Actual) / Entrada
        delta = (entry_price - mark_price) / entry_price
        
    # El ROE es el cambio de precio multiplicado por el apalancamiento
    roe_porcentaje = delta * apalancamiento * 100
    return roe_porcentaje

def main():
    print(Fore.YELLOW + "=================================================")
    print(Fore.YELLOW + "   🕵️  VERIFICADOR DE ROE REAL (Test de Precisión)")
    print(Fore.YELLOW + "=================================================\n")

    # 1. Cargar configuración para saber qué apalancamiento usa cada par
    print(Fore.CYAN + "📂 Cargando configuración de pares...")
    config_global = Config.cargar_configuracion()
    pares_config = config_global.get('pares', {})
    
    # 2. Inicializar Gestor de Ejecución (Conecta a Binance)
    gestor = GestorEjecucion()
    
    print(Fore.CYAN + "📡 Consultando posiciones activas en Binance...\n")
    
    # Cabecera de la tabla
    header = f"{'PAR':<12} | {'LADO':<5} | {'LEV':<4} | {'ENTRADA':<10} | {'MARK PRICE':<10} | {'ROE CALCULADO':<15}"
    print(Fore.WHITE + header)
    print(Fore.WHITE + "-" * len(header))
    
    posiciones_encontradas = 0

    # 3. Recorrer pares configurados
    for par, datos_conf in pares_config.items():
        if not datos_conf.get('activo', False):
            continue
            
        # Obtener datos en vivo del Exchange
        datos_pos = gestor.obtener_datos_posicion(par)
        
        if datos_pos:
            posiciones_encontradas += 1
            
            # Extraer variables
            entry = datos_pos['entryPrice']
            mark = datos_pos['markPrice'] # Binance suele dar esto preciso
            lado = datos_pos['side']      # 'buy' o 'sell'
            
            # Obtener apalancamiento desde tu JSON (Asumimos que coincide con Binance)
            lev = datos_conf.get('apalancamiento', 1)
            
            # --- CÁLCULO CRÍTICO ---
            roe_calc = calcular_roe_manual(entry, mark, lado, lev)
            
            # Formato de color según ganancia/pérdida
            color_roe = Fore.GREEN if roe_calc > 0 else Fore.RED
            lado_str = "LONG" if lado == 'buy' else "SHRT"
            
            print(f"{Fore.CYAN}{par:<12} {Style.RESET_ALL}| "
                  f"{lado_str:<5} | "
                  f"{lev}x   | "
                  f"{entry:<10.4f} | "
                  f"{mark:<10.4f} | "
                  f"{color_roe}{roe_calc:+.2f}%")
            
            # --- INFO ADICIONAL PARA CALIBRAR FEES ---
            # Si el ROE es pequeño, las comisiones impactan más.
            # Binance cobra ~0.05% de fee por market order (Taker).
            # Fee Estimado (Aprox) = Fee% * Leverage
            fee_estimado_roe = 0.05 * lev 
            breakeven_real = roe_calc - (fee_estimado_roe * 2) # Entrada + Salida
            
            print(f"   ↳ ℹ️  Neto estimado (tras fees): {breakeven_real:+.2f}%  "
                  f"(Fee aprox por trade: {fee_estimado_roe:.2f}% ROE)")
            print(Fore.WHITE + "-" * len(header))

    if posiciones_encontradas == 0:
        print(Fore.YELLOW + "\n⚠️  No se encontraron posiciones abiertas en los pares configurados.")
        print("   (Asegúrate de tener operaciones abiertas o abre una manual para probar)")

    print("\n" + Fore.YELLOW + "=================================================")
    print("💡 INSTRUCCIONES:")
    print("1. Compara la columna 'ROE CALCULADO' con el 'ROE' que te muestra la App/Web de Binance.")
    print("2. Deberían ser casi idénticos.")
    print("3. Si hay mucha diferencia, verifica que el apalancamiento en 'config_trading.json'")
    print("   coincida con el que tiene la posición real en Binance.")
    print(Fore.YELLOW + "=================================================")

if __name__ == "__main__":
    main()