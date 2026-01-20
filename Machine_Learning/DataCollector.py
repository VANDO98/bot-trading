import ccxt
import pandas as pd
import json
import os
import time
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- CONFIGURACIÓN ANTI-BAN ---
DIAS_HISTORIAL = 750 
MAX_HILOS = 2  # Bajamos a 2 para evitar el error 429 (Too Many Requests)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CARPETA_DATA = os.path.join(BASE_DIR, "Data_Entrenamiento")
ARCHIVO_CONFIG = os.path.join(BASE_DIR, "..", "config_trading.json")

def cargar_configuracion():
    if not os.path.exists(ARCHIVO_CONFIG):
        print(f"❌ Error: No encuentro config en: {ARCHIVO_CONFIG}")
        exit()
    with open(ARCHIVO_CONFIG, 'r') as f:
        return json.load(f)

def tarea_descarga_par(par_info):
    """
    Descarga historial de un par específico.
    """
    simbolo, timeframe, desde_timestamp = par_info
    
    # Instanciamos CCXT forzando FUTUROS y RATE LIMIT
    exchange = ccxt.binance({
        'enableRateLimit': True, # Gestiona esperas automáticas
        'options': {
            'defaultType': 'future'  # <--- IMPORTANTE: Datos de Futuros
        }
    })
    
    todas_velas = []
    desde = desde_timestamp
    
    print(f"⬇️ Iniciando {simbolo}...", flush=True)
    
    while True:
        try:
            # Pedimos velas (máximo 1000 por petición)
            velas = exchange.fetch_ohlcv(simbolo, timeframe, since=desde, limit=1000)
            if not velas: break
                
            todas_velas += velas
            ultimo_tiempo = velas[-1][0]
            desde = ultimo_tiempo + 1
            
            # Verificar si llegamos al presente (menos 1 minuto)
            tiempo_actual = exchange.milliseconds()
            if ultimo_tiempo >= (tiempo_actual - 60000): break
            
        except ccxt.RateLimitExceeded:
            print(f"⏳ {simbolo}: Límite alcanzado. Pausando 60s...", flush=True)
            time.sleep(60) # Pausa de castigo si nos pasamos
        except Exception as e:
            if "429" in str(e) or "-1003" in str(e):
                print(f"🛑 {simbolo}: Binance 429 (Ban temporal). Pausando 2 min...")
                time.sleep(120)
            else:
                print(f"❌ Error en {simbolo}: {e}")
                break
            
    # Procesar y Guardar
    if todas_velas:
        df = pd.DataFrame(todas_velas, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['fecha'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.drop_duplicates(subset=['timestamp'])
        
        nombre_archivo = f"{simbolo.replace('/', '_')}_{timeframe}.csv"
        ruta_archivo = os.path.join(CARPETA_DATA, nombre_archivo)
        df.to_csv(ruta_archivo, index=False)
        return f"✅ {simbolo}: Guardado ({len(df)} velas)"
    else:
        return f"⚠️ {simbolo}: No se descargaron datos."

def main():
    print(f"🤖 RECOLECCIÓN SEGURA (Hilos: {MAX_HILOS})")
    print("⚠️ Si ves errores 429, el script pausará automáticamente.")
    
    if not os.path.exists(CARPETA_DATA):
        os.makedirs(CARPETA_DATA)
    
    config = cargar_configuracion()
    pares_config = config.get("pares", {})
    
    fecha_inicio = datetime.now() - timedelta(days=DIAS_HISTORIAL)
    timestamp_inicio = int(fecha_inicio.timestamp() * 1000)
    
    # Preparamos la lista de tareas
    lista_tareas = []
    for par, detalles in pares_config.items():
        if not detalles.get("activo", True): continue
        timeframe = detalles.get("timeframe", "5m")
        lista_tareas.append((par, timeframe, timestamp_inicio))

    print(f"📅 Recolectando {len(lista_tareas)} pares desde {fecha_inicio.strftime('%Y-%m-%d')}")
    print("-" * 50)

    # EJECUCIÓN EN PARALELO CONTROLADO
    with ThreadPoolExecutor(max_workers=MAX_HILOS) as executor:
        futuros = []
        for tarea in lista_tareas:
            # Lanzamos la tarea
            futuro = executor.submit(tarea_descarga_par, tarea)
            futuros.append(futuro)
            
            # --- ARRANQUE SUAVE ---
            # Esperamos 3 segundos entre cada lanzamiento para no saturar el inicio
            print(f"💤 Esperando turno para el siguiente par...", end="\r")
            time.sleep(3) 

        # Recolectamos resultados
        for futuro in as_completed(futuros):
            try:
                print(futuro.result())
            except Exception as e:
                print(f"❌ Error crítico en hilo: {e}")

    print("-" * 50)
    print("🚀 PROCESO COMPLETADO.")

if __name__ == "__main__":
    main()