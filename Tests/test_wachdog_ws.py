import sys
import os
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Core.Datos.GestorMercado import GestorMercado

def test_simulacro_desconexion():
    print("🕵️ INICIANDO SIMULACRO DE FALLO DE RED (WATCHDOG)")
    print("-" * 60)
    
    mercado = GestorMercado()
    par = "BTCUSDT"
    
    # 1. Iniciamos normal
    mercado.iniciar_flujo_multiples_pares([par])
    print("⏳ Esperando primeros datos reales...")
    time.sleep(5)
    
    # Verificamos que todo esté bien al inicio
    if mercado.verificar_salud_datos(par):
        precio = mercado.obtener_precio(par)
        print(f"✅ Inicio correcto. Precio: {precio}")
    else:
        print("❌ Error al iniciar. Algo falla.")
        return

    # 2. EL SABOTAJE
    print("\n✂️  SABOTEANDO LA CONEXIÓN (Simulación)...")
    print("   Vamos a reescribir la fecha del último dato para que parezca viejo.")
    
    # "Hackeamos" la variable interna poniéndole una fecha de hace 2 minutos
    hace_dos_minutos = time.time() - 120 
    mercado.ultimas_actualizaciones[par] = hace_dos_minutos
    
    print("   Fecha manipulada. Preguntando al Watchdog...")
    
    # 3. Probamos si el Watchdog ladra
    es_saludable = mercado.verificar_salud_datos(par)
    
    if not es_saludable:
        print("\n✅✅ ¡PRUEBA SUPERADA!")
        print("   El Watchdog detectó que los datos eran obsoletos y lanzó la alerta.")
    else:
        print("\n❌ FALLO: El Watchdog no se dio cuenta del retraso.")

    mercado.detener_todo()

if __name__ == "__main__":
    test_simulacro_desconexion()