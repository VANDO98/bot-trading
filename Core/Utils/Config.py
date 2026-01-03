import os
from dotenv import load_dotenv

class Config:
    """
    Proveedor global de constantes y variables de entorno.
    Centraliza la configuración para evitar 'magic numbers' dispersos.
    """
    
    # 1. Cargar variables de entorno al iniciar la clase
    load_dotenv()

    # --- Credenciales de API (Se leen del archivo .env) ---
    BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
    BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY")

    # --- Configuración de Red y API ---
    USAR_TESTNET = True 
    URL_FUTURES_MAIN = "https://fapi.binance.com"
    URL_FUTURES_TESTNET = "https://testnet.binancefuture.com"

    # --- Configuración del Bot ---
    NOMBRE_BOT = "BinanceBot-ARM-t4g"
    TIMEFRAME_DEFECTO = "5m"  # Scalping 5m
    
    # --- Gestión de Riesgo Global ---
    MAX_POSICIONES = 4        
    TIMEOUT_ORDEN_LIMIT = 15  

    @staticmethod
    def validar_config():
        """Verifica que las claves críticas existan antes de arrancar."""
        if not Config.BINANCE_API_KEY or not Config.BINANCE_SECRET_KEY:
            raise EnvironmentError("❌ ERROR CRÍTICO: No se encontraron las claves API en el archivo .env")
        print(f"✅ Configuración cargada correctamente. Modo Testnet: {Config.USAR_TESTNET}")

if __name__ == "__main__":
    try:
        Config.validar_config()
    except Exception as e:
        print(e)