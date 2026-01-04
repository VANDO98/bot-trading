from binance.enums import SIDE_BUY, SIDE_SELL, TIME_IN_FORCE_GTC, ORDER_TYPE_LIMIT
from binance.exceptions import BinanceAPIException
from Core.Ejecucion.GestorPrecision import GestorPrecision  # <--- IMPORTAMOS TU NUEVA ARMA

class GestorBasico:
    """
    Encargado de la ejecución.
    Ahora incluye GESTIÓN DE CAPITAL (Position Sizing).
    """
    def __init__(self, cliente_api):
        self.api = cliente_api.client
        # Cache de gestores de precisión para no instanciar uno en cada orden
        self.precisiones = {}

    def _obtener_precision(self, symbol):
        """Busca o crea el gestor de precisión para el par."""
        if symbol not in self.precisiones:
            gp = GestorPrecision(symbol)
            gp.detectar() # Auto-detectar decimales al primer uso
            self.precisiones[symbol] = gp
        return self.precisiones[symbol]

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
        
        cantidad_cruda = poder_compra / precio
        
        # --- MAGIA AQUÍ ---
        gp = self._obtener_precision(symbol)
        cantidad_final = gp.redondear_cantidad(cantidad_cruda)
        # ------------------
        
        return cantidad_final, balance

    def colocar_orden_limit(self, symbol, side, cantidad, precio):
        try:

            # --- VALIDACIÓN DE PRECISIÓN ---
            gp = self._obtener_precision(symbol)
            precio_final = gp.redondear_precio(precio)
            cantidad_final = gp.redondear_cantidad(cantidad)
            # -------------------------------

            print(f"🚀 Enviando orden {side} para {symbol}. Cant: {cantidad_final} a ${precio_final}...")
            
            orden = self.api.futures_create_order(
                symbol=symbol,
                side=side,
                type=ORDER_TYPE_LIMIT,
                timeInForce=TIME_IN_FORCE_GTC,
                quantity=cantidad_final,
                price=str(precio_final)
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
        
    # ... (Mantén los métodos anteriores igual) ...

    def obtener_posicion(self, symbol):
        """
        Consulta en Binance si tenemos una posición abierta para este par.
        Retorna la cantidad (amt).
        - Si amt > 0: Estamos en LONG.
        - Si amt < 0: Estamos en SHORT.
        - Si amt == 0: No tenemos posición.
        """
        try:
            # Info de posiciones (riesgo)
            positions = self.api.futures_position_information(symbol=symbol)
            # La API a veces devuelve una lista, buscamos el item correcto
            for p in positions:
                if p['symbol'] == symbol:
                    return float(p['positionAmt'])
            return 0.0
        except Exception as e:
            print(f"❌ Error consultando posición de {symbol}: {e}")
            return 0.0
            
    def cerrar_posicion_mercado(self, symbol, cantidad_actual):
        """
        Cierra una posición lanzando una orden contraria a Mercado.
        """
        try:
            side = SIDE_SELL if cantidad_actual > 0 else SIDE_BUY
            print(f"🚨 CERRANDO POSICIÓN de {symbol} (Market)...")
            
            # Para cerrar, enviamos una orden con la misma cantidad pero lado contrario
            # Usamos abs() porque la cantidad puede venir negativa si es Short
            orden = self.api.futures_create_order(
                symbol=symbol,
                side=side,
                type="MARKET",
                quantity=abs(cantidad_actual)
            )
            return orden
        except Exception as e:
            print(f"❌ Error cerrando posición: {e}")
            return None
        
    def verificar_ordenes_pendientes(self, symbol):
        """
        Devuelve True si hay órdenes abiertas (Limit) esperando llenarse.
        """
        try:
            ordenes = self.api.futures_get_open_orders(symbol=symbol)
            return len(ordenes) > 0
        except Exception as e:
            print(f"⚠️ Error verificando órdenes pendientes: {e}")
            return False