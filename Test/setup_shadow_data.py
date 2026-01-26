import sys
import os
import csv
from datetime import datetime, timedelta

# Ruta al log
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVO_LOG = os.path.join(ROOT_DIR, "Machine_Learning", "Logs", "shadow_trades.csv")

def inject_test_data():
    print("💉 Inyectando datos de prueba antiguos en shadow_trades.csv...")
    
    # 2 días atrás
    past_date = datetime.now() - timedelta(days=2)
    timestamp_str = past_date.strftime("%Y-%m-%d %H:%M:%S")
    
    # Mejor estrategia: Usar el propio Gestor para buscar el precio real de ese momento.
    # Esto valida también la modificación que hicimos en GestorWebsocket.
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from Core.API.GestorWebsocket import GestorWebsocket
    gestor = GestorWebsocket()
    
    # Buscamos 1 vela de ese momento
    ts_ms = int(past_date.timestamp() * 1000)
    velas = gestor.obtener_velas_rango("BTC/USDT", "5m", ts_ms, ts_ms + 60000*10) # 10 mins ventana
    
    if velas:
        precio_real = float(velas[0]['o']) # Precio de apertura real
        print(f"🎯 Precio REAL de BTC hace 2 días ({timestamp_str}): ${precio_real}")
        
        # Simulamos una configuración típica
        sl_pct = 0.02 # 2%
        tp_pct = 0.04 # 4%
        
        sl_val = precio_real * (1 - sl_pct)
        tp_val = precio_real * (1 + tp_pct)
        
        # Inyectamos COMPRA con Leverage 50x (para exagerar ROE)
        # Usamos ShadowLogger directamente para probar la inserción en DB
        from Core.Utils.ShadowLogger import ShadowLogger
        
        ShadowLogger.registrar_rechazo(
            simbolo="BTC/USDT",
            senal="COMPRA",
            precio_entrada=precio_real,
            probabilidad=0.50,
            umbral=0.60,
            motivo="Test SQLite Flow",
            estrategia_nombre="TestStrat",
            atr=100.0,
            sl_teorico=sl_val,
            tp_teorico=tp_val,
            apalancamiento=50.0
        )
            
        print(f"✅ Dato inyectado en DB: {timestamp_str} | BTC/USDT | Entry: {precio_real}")
    else:
        print("⚠️ No se pudo obtener precio real para el test. Abortando inyección.")
        
    gestor.detener_todo()

if __name__ == "__main__":
    inject_test_data()
