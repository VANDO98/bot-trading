import sys
import os
import time

# Ajuste de rutas para importar desde la carpeta raíz
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Core.API.BinanceBase import BinanceBase
from Core.Ejecucion.GestorBasico import GestorBasico
from Core.Riesgo.GestorPosicion import GestorPosicion
from Core.Utils.Config import Config

def test_riesgo_y_seguridad():
    print("🛡️  INICIANDO TEST DE FASE 3: RIESGO Y SEGURIDAD (FIX ARQUITECTURA)")
    print("================================================================")
    
    # 1. Inicialización Correcta (Según tus archivos vando98)
    try:
        # A) Iniciamos el motor base (lee .env automáticamente)
        print("🔌 Iniciando BinanceBase...")
        api_base = BinanceBase() 
        
        if not api_base.validar_conectividad():
            print("❌ Error: No se pudo conectar con Binance.")
            return

        # B) Iniciamos GestorBasico pasándole el objeto api_base
        print("🔧 Iniciando GestorBasico...")
        gestor_basico = GestorBasico(api_base)
        
        # C) Iniciamos GestorPosicion pasándole el gestor_basico
        print("🛡️  Iniciando GestorPosicion...")
        gestor_pos = GestorPosicion(gestor_basico)
        
        print("✅ Componentes inicializados correctamente.")
        
    except Exception as e:
        print(f"❌ Error crítico al iniciar objetos: {e}")
        return

    # ---------------------------------------------------------
    # TEST: PROTOCOLO DE SEGURIDAD
    # ---------------------------------------------------------
    par_prueba = "BTCUSDT"
    print(f"\n🚑 [TEST] Simulacro de Emergencia en {par_prueba}...")
    
    try:
        # Ejecutamos el protocolo
        gestor_pos.iniciar_protocolo_seguridad(par_prueba)
        print("\n✅ Protocolo finalizado (Revisar logs arriba).")
        
    except Exception as e:
        print(f"\n❌ ERROR EN EJECUCIÓN DEL PROTOCOLO: {e}")

    print("\n" + "="*60)

if __name__ == "__main__":
    test_riesgo_y_seguridad()