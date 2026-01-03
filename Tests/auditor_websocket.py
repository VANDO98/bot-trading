import sys
import os
import time
from datetime import datetime

# Ajuste de ruta para encontrar la carpeta Core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Core.Datos.GestorMercado import GestorMercado
from Core.Utils.Config import Config

def limpiar_pantalla():
    """Limpia la consola para efecto de dashboard."""
    os.system('cls' if os.name == 'nt' else 'clear')

def auditar_websocket_infinito():
    print("📡 INICIANDO MONITOR DE MERCADO (FUTURES)")
    print("-" * 60)
    
    mercado = None
    try:
        # 1. Configuración
        try:
            Config.validar_config()
        except:
            pass # Si falla validación, seguimos en modo anónimo si el Gestor lo permite

        # 2. Instanciar Gestor
        mercado = GestorMercado()
        
        # 3. Lista de pares a vigilar
        pares_prueba = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT"]
        
        # 4. Iniciar conexión (Multiplex Futures)
        mercado.iniciar_flujo_multiples_pares(pares_prueba)
        
        print("⏳ Estableciendo enlace satelital con Binance...")
        time.sleep(3) # Espera inicial para llenar datos
        
        # 5. Bucle Infinito (Dashboard)
        while True:
            limpiar_pantalla()
            
            # Encabezado
            print(f"🔴 MONITOR EN VIVO - BINANCE FUTURES")
            print(f"⏱️  Hora sistema: {datetime.now().strftime('%H:%M:%S')}")
            
            if Config.BINANCE_API_KEY:
                print("🔒 Estado: AUTENTICADO (Datos de Contratos Reales)")
            else:
                print("🔓 Estado: PÚBLICO (Datos de Referencia)")
                
            print("-" * 60)
            print(f"{'PAR':<10} | {'PRECIO (USDT)':<18} | {'ESTADO'}")
            print("-" * 60)
            
            datos_recibidos = 0
            
            for par in pares_prueba:
                precio = mercado.obtener_precio(par)
                
                if precio > 0:
                    datos_recibidos += 1
                    # Formato de precio con comas y decimales
                    precio_fmt = f"${precio:,.4f}" 
                    estado = "🟢 Operativo"
                else:
                    precio_fmt = "Cargando..."
                    estado = "🟡 Esperando..."
                
                print(f"{par:<10} | {precio_fmt:<18} | {estado}")
            
            print("-" * 60)
            print(f"📡 Señal: {datos_recibidos}/{len(pares_prueba)} pares activos.")
            print("\n[Presiona Ctrl + C para detener el bot]")
            
            # Actualizar cada 0.5 segundos para ver la velocidad real
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\n\n🛑 DETENIENDO SISTEMA...")
        if mercado:
            mercado.detener_todo()
        print("✅ Conexión cerrada correctamente. Hasta luego.")

    except Exception as e:
        print(f"\n❌ ERROR CRÍTICO: {e}")
        if mercado:
            mercado.detener_todo()

if __name__ == "__main__":
    auditar_websocket_infinito()