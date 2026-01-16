from binance.client import Client
from binance.exceptions import BinanceAPIException
from Core.Utils.Config import Config
import time

class BinanceBase:
    """
    Motor de comunicación REST. Maneja la autenticación y configuración inicial.
    Fuente: Plan Maestro - Fase 1 [Cimientos]
    """
    def __init__(self):
        # 1. Validar claves antes de intentar nada
        Config.validar_config()
        
        # 2. Inicializar cliente (Detectar si es Testnet o Real)
        self.client = Client(Config.BINANCE_API_KEY, Config.BINANCE_SECRET_KEY, testnet=Config.USAR_TESTNET)
        
        print(f"🔌 Motor Iniciado. Testnet: {Config.USAR_TESTNET}")

    def validar_conectividad(self):
        """Prueba simple de ping al servidor."""
        try:
            self.client.ping()
            return True
        except Exception as e:
            print(f"❌ Error de Ping: {e}")
            return False

    def obtener_saldo_usdt(self):
        """Obtiene el saldo disponible en Futures para operar."""
        try:
            account = self.client.futures_account_balance()
            for asset in account:
                if asset['asset'] == 'USDT':
                    # CORRECCIÓN: Usamos 'availableBalance' en lugar de 'withdrawAvailable'
                    return float(asset['balance']), float(asset['availableBalance'])
            return 0.0, 0.0
        except BinanceAPIException as e:
            print(f"❌ Error al obtener saldo: {e}")
            return None

    def configurar_cuenta(self, symbol):
        """
        Fuerza el Margen Cruzado y el Apalancamiento por defecto.
        Requisito del Plan Maestro: setear_modo_cuenta() 
        """
        try:
            # 1. Cambiar a Margin Type: CROSSED (Cruzado)
            try:
                self.client.futures_change_margin_type(symbol=symbol, marginType='CROSSED')
                print(f"✅ {symbol}: Modo Cruzado activado.")
            except BinanceAPIException as e:
                # Si ya está en Cruzado, Binance devuelve error código -4046 "No need to change margin type"
                if e.code == -4046:
                    print(f"ℹ️ {symbol}: Ya estaba en modo Cruzado.")
                else:
                    raise e

            # 2. Cambiar apalancamiento (Ej: 5x por seguridad inicial)
            self.client.futures_change_leverage(symbol=symbol, leverage=5)
            print(f"✅ {symbol}: Apalancamiento ajustado a 5x.")
            
        except Exception as e:
            print(f"⚠️ Alerta Configuración Cuenta: {e}")