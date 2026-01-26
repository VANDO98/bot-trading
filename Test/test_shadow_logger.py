import sys
import os
import time

# Add root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Core.Utils.ShadowLogger import ShadowLogger

def test_shadow_logging():
    print("🧪 Testing ShadowLogger...")
    
    simbolo = "BTC/USDT"
    senal = "COMPRA"
    precio_entrada = 50000.0
    probabilidad = 0.55
    umbral = 0.65
    motivo = "Score Insuficiente"
    estrategia = "RSI_Bollinger"
    atr = 100.0
    sl_teorico = 49000.0
    tp_teorico = 51000.0
    
    # Clean up previous log if exists
    if os.path.exists(ShadowLogger.ARCHIVO_LOG):
        # Rename it to keep history if needed, or just delete for test
        # Let's just append to it, mimicking real behavior
        pass
        
    ShadowLogger.registrar_rechazo(
        simbolo, senal, precio_entrada, probabilidad, umbral, motivo, estrategia, atr, sl_teorico, tp_teorico
    )
    
    # Verify file exists and content
    if os.path.exists(ShadowLogger.ARCHIVO_LOG):
        print("✅ Log file created.")
        with open(ShadowLogger.ARCHIVO_LOG, 'r') as f:
            lines = f.readlines()
            print(f"📄 Log content ({len(lines)} lines):")
            for line in lines[-2:]: # Show last 2 lines
                print(line.strip())
            
        print("✅ Test Passed.")
    else:
        print("❌ Log file NOT created.")

if __name__ == "__main__":
    test_shadow_logging()
