import sys
import os

# Ajuste de rutas para encontrar 'Core'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Core.Ejecucion.GestorPrecision import GestorPrecision
from Core.Utils.Config import Config

def test_precision_real():
    print("🔬 INICIANDO TEST DE PRECISIÓN (API REAL)")
    print("=========================================")
    
    # Aseguramos que la configuración esté cargada (importante para que BinanceBase sepa si es Testnet)
    try:
        Config.validar_config()
    except:
        pass # Si ya estaba cargada, seguimos
    
    # Probamos con DOGEUSDT (Caso especial de 0 decimales en cantidad)
    par = "DOGEUSDT" 
    print(f"📡 Conectando a Binance Futures ({'TESTNET' if Config.USAR_TESTNET else 'MAINNET'}) para {par}...")
    
    try:
        # CORRECCIÓN: Instanciamos sin 'testnet=True', la clase ya lo sabe por Config
        gestor = GestorPrecision(par)
        
        if gestor.detectar():
            print(f"✅ Detección Exitosa para {par}")
            print(f"   • Decimales Precio (pricePrecision): {gestor.decimales_precio}")
            print(f"   • Decimales Cantidad (quantityPrecision): {gestor.decimales_cantidad}")
            print(f"   • Tick Size: {gestor.tick_size}")
            print(f"   • Step Size: {gestor.step_size}")
            
            # Pruebas de Redondeo
            precio_sucio = 0.123456789
            cantidad_sucia = 50.999999
            
            p_clean = gestor.redondear_precio(precio_sucio)
            q_clean = gestor.redondear_cantidad(cantidad_sucia)
            
            print("\n🧮 PRUEBA MATEMÁTICA:")
            print(f"   • Precio Original: {precio_sucio} -> Redondeado: {p_clean}")
            print(f"   • Cantidad Original: {cantidad_sucia} -> Redondeado: {q_clean}")
            
            # Validación visual
            if gestor.decimales_cantidad == 0 and isinstance(q_clean, int):
                 print("   🌟 CORRECTO: La cantidad es un entero (int).")
            elif gestor.decimales_cantidad == 0 and q_clean.is_integer():
                 print("   🌟 CORRECTO: La cantidad respeta el formato entero.")
                 
        else:
            print("❌ Falló la detección de filtros (Revisa tu conexión o el par).")
            
    except Exception as e:
        print(f"❌ Error durante el test: {e}")

if __name__ == "__main__":
    test_precision_real()