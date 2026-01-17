import ccxt
import pandas as pd
import json
import os
import time
from datetime import datetime, timedelta

# --- CONFIGURACIÓN ---
DIAS_HISTORIAL = 730  # 2 Años
# Rutas relativas a donde está este script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CARPETA_DATA = os.path.join(BASE_DIR, "Data_Entrenamiento")
# El config está un nivel arriba ("..")
ARCHIVO_CONFIG = os.path.join(BASE_DIR, "..", "config_trading.json")

def cargar_configuracion():
    """Carga los pares desde el JSON en la carpeta raíz"""
    if not os.path.exists(ARCHIVO_CONFIG):
        print(f"❌ Error Crítico: No encuentro el archivo de configuración en:\n{ARCHIVO_CONFIG}")
        exit()
    
    with open(ARCHIVO_CONFIG, 'r') as f:
        return json.load(f)

def descargar_historial(exchange, simbolo, timeframe, desde_timestamp):
    todas_velas = []
    desde = desde_timestamp
    
    print(f"   ⬇️ Descargando {simbolo} ({timeframe})...", end="")
    
    while True:
        try:
            velas = exchange.fetch_ohlcv(simbolo, timeframe, since=desde, limit=1000)
            if not velas: break
                
            todas_velas += velas
            ultimo_tiempo = velas[-1][0]
            desde = ultimo_tiempo + 1
            
            tiempo_actual = exchange.milliseconds()
            if ultimo_tiempo >= (tiempo_actual - 60000): break
                
            print(".", end="", flush=True)
            time.sleep(0.5) 
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            break
            
    print(" ✅")
    return todas_velas

def procesar_y_guardar(velas, simbolo, timeframe):
    if not velas: return

    df = pd.DataFrame(velas, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['fecha'] = pd.to_datetime(df['timestamp'], unit='ms')
    df = df.drop_duplicates(subset=['timestamp'])
    
    nombre_archivo = f"{simbolo.replace('/', '_')}_{timeframe}.csv"
    ruta_archivo = os.path.join(CARPETA_DATA, nombre_archivo)
    
    df.to_csv(ruta_archivo, index=False)
    print(f"      💾 Guardado: {nombre_archivo} ({len(df)} velas)")

def main():
    print(f"🤖 INICIANDO RECOLECCIÓN (Guardando en: {CARPETA_DATA})")
    
    if not os.path.exists(CARPETA_DATA):
        os.makedirs(CARPETA_DATA)
    
    config = cargar_configuracion()
    pares_config = config.get("pares", {})
    
    exchange = ccxt.binance({'enableRateLimit': True})
    
    fecha_inicio = datetime.now() - timedelta(days=DIAS_HISTORIAL)
    timestamp_inicio = int(fecha_inicio.timestamp() * 1000)
    
    print(f"📅 Desde: {fecha_inicio.strftime('%Y-%m-%d')} (Hace {DIAS_HISTORIAL} días)")
    print("-" * 50)

    for par, detalles in pares_config.items():
        if not detalles.get("activo", True): continue
        
        # Forzamos timeframe de 5m si no está definido, o usamos el del JSON
        timeframe = detalles.get("timeframe", "5m")
        
        print(f"🔄 Procesando {par}...")
        data = descargar_historial(exchange, par, timeframe, timestamp_inicio)
        procesar_y_guardar(data, par, timeframe)
        
    print("-" * 50)
    print("🚀 PROCESO COMPLETADO.")

if __name__ == "__main__":
    main()