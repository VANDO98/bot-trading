import ccxt
import pandas as pd
import json
import os
import time
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from colorama import Fore, init

init(autoreset=True)

# --- CONFIGURACIÓN ---
DIAS_HISTORIAL = 730   # 2 Años (Cantidad ideal para que el bot aprenda tendencias reales)
MAX_HILOS = 3          # Mantenemos 3 para no saturar la IP y evitar BAN
TIMEFRAMES_A_BAJAR = ["5m", "15m", "1h"] # <--- LAS 3 DIMENSIONES QUE NECESITAMOS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Ahora apuntamos a la raíz de históricos, las subcarpetas se crearán dinámicamente
RAIZ_DATA = os.path.join(BASE_DIR, "..", "Data", "Historico") 
ARCHIVO_CONFIG = os.path.join(BASE_DIR, "..", "config_trading.json")

def cargar_configuracion():
    if not os.path.exists(ARCHIVO_CONFIG):
        print(f"{Fore.RED}❌ Error: No encuentro config en: {ARCHIVO_CONFIG}")
        exit()
    with open(ARCHIVO_CONFIG, 'r') as f:
        return json.load(f)

def tarea_descarga_par(par_info):
    """
    Descarga historial y lo guarda en la carpeta correspondiente a su timeframe.
    """
    simbolo, timeframe, desde_timestamp = par_info
    
    # Instanciamos CCXT forzando FUTUROS (Datos reales de trading)
    exchange = ccxt.binance({
        'enableRateLimit': True, 
        'options': {'defaultType': 'future'} 
    })
    
    todas_velas = []
    desde = desde_timestamp
    
    print(f"{Fore.CYAN}⬇️  Iniciando {simbolo} ({timeframe})...")
    
    while True:
        try:
            # Pedimos velas (Binance da max 1000/1500 en futuros)
            velas = exchange.fetch_ohlcv(simbolo, timeframe, since=desde, limit=1000)
            
            if not velas: break
                
            # Evitar duplicados exactos al unir lotes
            if todas_velas and velas[0][0] == todas_velas[-1][0]:
                velas = velas[1:]

            todas_velas += velas
            ultimo_tiempo = velas[-1][0]
            desde = ultimo_tiempo + 1
            
            # Verificar si llegamos al presente (menos 5 minutos por seguridad)
            tiempo_actual = exchange.milliseconds()
            if ultimo_tiempo >= (tiempo_actual - 300000): break
            
            # Pausa ligera interna para no saturar la conexión del hilo
            time.sleep(0.1)
            
        except ccxt.RateLimitExceeded:
            print(f"{Fore.YELLOW}⏳ {simbolo}: Límite alcanzado. Pausando 30s...")
            time.sleep(30)
        except Exception as e:
            if "429" in str(e) or "-1003" in str(e):
                print(f"{Fore.RED}🛑 {simbolo}: Binance 429 (Ban temporal). Pausando 2 min...")
                time.sleep(120)
            else:
                print(f"{Fore.RED}❌ Error en {simbolo}: {e}")
                time.sleep(5) # Reintentar tras error de conexión
                continue
            
    # Procesar y Guardar
    if todas_velas:
        df = pd.DataFrame(todas_velas, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # --- LÓGICA DE ORGANIZACIÓN POR CARPETAS ---
        # 1. Definir carpeta destino: Data/Historico/1h/
        carpeta_destino = os.path.join(RAIZ_DATA, timeframe)
        
        # 2. Crear carpeta si no existe
        if not os.path.exists(carpeta_destino):
            os.makedirs(carpeta_destino)
            
        # 3. Guardar archivo limpio: BTCUSDT_1h.csv
        nombre_archivo = f"{simbolo.replace('/', '')}_{timeframe}.csv"
        ruta_archivo = os.path.join(carpeta_destino, nombre_archivo)
        
        df.to_csv(ruta_archivo, index=False)
        
        return f"{Fore.GREEN}✅ {simbolo}: Guardado en /{timeframe} ({len(df)} velas)"
    else:
        return f"{Fore.YELLOW}⚠️ {simbolo}: No se descargaron datos."

def main():
    print(f"{Fore.MAGENTA}🤖 RECOLECCIÓN ORGANIZADA (V5) - Hilos: {MAX_HILOS}")
    
    if not os.path.exists(RAIZ_DATA):
        os.makedirs(RAIZ_DATA)
        print(f"📂 Carpeta Raíz creada: {RAIZ_DATA}")
    
    config = cargar_configuracion()
    pares_config = config.get("pares", {})
    
    fecha_inicio = datetime.now() - timedelta(days=DIAS_HISTORIAL)
    timestamp_inicio = int(fecha_inicio.timestamp() * 1000)
    
    # Preparamos la lista de tareas MASIVA
    lista_tareas = []
    for par, detalles in pares_config.items():
        if not detalles.get("activo", True): continue
        
        # AQUÍ ESTÁ EL CAMBIO CLAVE:
        # No nos importa el timeframe del JSON, generamos tareas para los 3 timeframes
        for tf in TIMEFRAMES_A_BAJAR:
            lista_tareas.append((par, tf, timestamp_inicio))

    print(f"📅 Recolectando {len(lista_tareas)} archivos (Pares x 3 Timeframes)")
    print("-" * 50)

    # EJECUCIÓN EN PARALELO
    with ThreadPoolExecutor(max_workers=MAX_HILOS) as executor:
        futuros = []
        for tarea in lista_tareas:
            futuro = executor.submit(tarea_descarga_par, tarea)
            futuros.append(futuro)
            # Arranque escalonado para no golpear la API de golpe
            time.sleep(1) 

        for futuro in as_completed(futuros):
            try:
                print(futuro.result())
            except Exception as e:
                print(f"❌ Error crítico en hilo: {e}")

    print("-" * 50)
    print(f"{Fore.MAGENTA}🏁 PROCESO FINALIZADO. Datos listos en carpetas separadas.")

if __name__ == "__main__":
    main()