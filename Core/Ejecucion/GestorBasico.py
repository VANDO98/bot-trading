from binance.enums import SIDE_BUY, SIDE_SELL, TIME_IN_FORCE_GTC, ORDER_TYPE_LIMIT
from binance.exceptions import BinanceAPIException

class GestorBasico:
    """
    Encargado de la ejecución.
    Ahora incluye GESTIÓN DE CAPITAL (Position Sizing).
    """
    def __init__(self, cliente_api):
        self.api = cliente_api.client

    def obtener_balance_usdt(self):
        """Consulta el saldo disponible en la billetera de Futuros"""
        try:
            balances = self.api.futures_account_balance()
            for asset in balances:
                if asset['asset'] == 'USDT':
                    return float(asset['balance']) # O 'availableBalance' si prefieres
            return 0.0
        except Exception as e:
            print(f"❌ Error leyendo balance: {e}")
            return 0.0

    def calcular_cantidad(self, symbol, porcentaje, precio, apalancamiento, precision=3):
        """
        Calcula cuántas monedas comprar basado en el % de la cartera.
        Fórmula: (Balance * % * Apalancamiento) / Precio
        """
        balance = self.obtener_balance_usdt()
        
        # Si tienes $1000 y quieres usar 20%, asignas $200 de margen (Cost).
        # Con apalancamiento x10, tu poder de compra es $2000.
        monto_margen = balance * (porcentaje / 100)
        poder_compra = monto_margen * apalancamiento
        
        cantidad_monedas = poder_compra / precio
        
        # Redondear según la precisión que exige Binance para ese par
        cantidad_final = round(cantidad_monedas, precision)
        
        return cantidad_final, balance

    def colocar_orden_limit(self, symbol, side, cantidad, precio):
        try:
            print(f"🚀 Enviando orden {side} para {symbol}. Cant: {cantidad} a ${precio}...")
            orden = self.api.futures_create_order(
                symbol=symbol,
                side=side,
                type=ORDER_TYPE_LIMIT,
                timeInForce=TIME_IN_FORCE_GTC,
                quantity=cantidad,
                price=str(precio)
            )
            return orden
        except BinanceAPIException as e:
            print(f"❌ Error al colocar orden: {e}")
            return None

    def configurar_apalancamiento(self, symbol, leverage):
        try:
            leverage = int(leverage)
            # print(f"⚙️  Ajustando apalancamiento de {symbol} a x{leverage}...")
            self.api.futures_change_leverage(symbol=symbol, leverage=leverage)
            return True
        except Exception as e:
            print(f"❌ Error leverage {symbol}: {e}")
            return False
            
    def cancelar_orden(self, symbol, order_id):
        try:
            self.api.futures_cancel_order(symbol=symbol, orderId=order_id)
            return True
        except:
            return False