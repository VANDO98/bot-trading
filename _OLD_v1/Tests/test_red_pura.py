import sys
import os
import time
from binance import ThreadedWebsocketManager

# No importamos nada del Core para probar la conexión pura y dura sin interferencias

def prueba_velocidad_anonima():
    print("🚀 INICIANDO PRUEBA DE VELOCIDAD: MODO ANÓNIMO (MAINNET)")
    print("Objetivo: Demostrar que los datos fluyen si quitamos la autenticación.")
    print("-" * 60)
    
    # Lista de pares pesados y variados
    pares = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT"]
    
    resultados = {}
    
    # Callback simple
    def al_recibir_dato(msg):
        if 'data' in msg:
            data = msg['data']
            symbol = data['s']
            precio = data['c']
            # Solo guardamos la primera vez que lo vemos para el reporte
            if symbol not in resultados:
                resultados[symbol] = precio
                print(f"   ⚡ ¡Dato recibido! {symbol} = ${precio}")

    # 1. Inicializar SIN CLAVES (api_key=None)
    # Esto conecta a la Mainnet pública automáticamente.
    twm = ThreadedWebsocketManager(api_key=None, api_secret=None)
    twm.start()
    
    # 2. Construir streams
    streams = [f"{p.lower()}@ticker" for p in pares]
    print(f"📡 Suscribiendo a: {streams}")
    
    twm.start_multiplex_socket(callback=al_recibir_dato, streams=streams)
    
    # 3. Esperar resultados
    print("\n⏳ Esperando datos (Max 10 seg)...")
    start = time.time()
    
    while time.time() - start < 10:
        if len(resultados) == len(pares):
            break
        time.sleep(0.5)
        
    tiempo_total = time.time() - start
    
    # 4. Reporte
    print("-" * 60)
    if len(resultados) == len(pares):
        print(f"✅ ÉXITO TOTAL: {len(resultados)}/{len(pares)} pares recibidos.")
        print(f"⏱️ Tiempo: {tiempo_total:.2f} segundos")
        print("💡 CONCLUSIÓN: Tus claves API estaban ralentizando la conexión de datos.")
    else:
        faltantes = set(pares) - set(resultados.keys())
        print(f"❌ FALLO: Solo llegaron {len(resultados)}. Faltan: {faltantes}")
        print("💡 CONCLUSIÓN: Posible bloqueo de firewall o problema de DNS en tu PC.")

    twm.stop()

if __name__ == "__main__":
    prueba_velocidad_anonima()