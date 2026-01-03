from binance import ThreadedWebsocketManager
from Core.Utils.Config import Config
import time

class GestorMercado:
    """
    Especialista en WebSockets.
    ARQUITECTURA HÍBRIDA:
    1. Escucha @ticker para visualización en tiempo real y Watchdog.
    2. Escucha @kline para alimentar el historial matemático.
    Todo en una sola conexión multiplexada.
    """
    def __init__(self):
        self.precios_actuales = {} 
        self.ultimas_actualizaciones = {} 
        self.stream_activo = False
        self.callback_kline = None # Canal de comunicación con GestorVelas
        
        self.twm = ThreadedWebsocketManager(
            api_key=Config.BINANCE_API_KEY, 
            api_secret=Config.BINANCE_SECRET_KEY, 
            testnet=Config.USAR_TESTNET
        )
        self.twm.start()

    def iniciar_flujo_hibrido(self, estrategias_dict, callback_kline):
        """
        Genera DOS suscripciones por cada par:
        1. par@ticker (Para precio rápido)
        2. par@kline_T (Para indicadores)
        """
        self.callback_kline = callback_kline
        streams = []
        
        print("📡 Configurando WebSockets Híbridos (Precio + Velas)...")
        
        for par, config in estrategias_dict.items():
            if not config.get("activo", False):
                continue
            
            # Inicializamos variables
            self.precios_actuales[par] = 0.0
            self.ultimas_actualizaciones[par] = 0
            
            par_lower = par.lower()
            tf = config['timeframe']
            
            # 1. Stream de Precio (Rápido, independiente)
            streams.append(f"{par_lower}@ticker")
            
            # 2. Stream de Velas (Para cálculos)
            streams.append(f"{par_lower}@kline_{tf}")
            
        print(f"🔗 Suscribiendo a {len(streams)} canales simultáneos...")

        # Iniciamos el Multiplex Socket (Futures o Spot)
        if Config.BINANCE_API_KEY:
            self.twm.start_futures_multiplex_socket(callback=self.procesar_msg, streams=streams)
        else:
            print("⚠️ Sin claves: Usando Spot para simulación")
            self.twm.start_multiplex_socket(callback=self.procesar_msg, streams=streams)
            
        self.stream_activo = True

    def procesar_msg(self, msg):
        """
        ROUTER DE MENSAJES:
        Separa lo que es precio (Ticker) de lo que es estructura (Kline).
        """
        if 'data' not in msg:
            return

        payload = msg['data']
        evento = payload.get('e') # Tipo de evento
        symbol = payload.get('s') # Símbolo (Ej: BTCUSDT)

        # CASO A: Actualización de Precio (Ticker)
        # El evento suele llamarse '24hrTicker' en Spot o Futures
        if evento == '24hrTicker':
            # Actualizamos SOLO el precio visual y el Watchdog
            self.precios_actuales[symbol] = float(payload['c'])
            self.ultimas_actualizaciones[symbol] = time.time()

        # CASO B: Actualización de Vela (Kline)
        elif evento == 'kline':
            kline_data = payload['k']
            # Enviamos la data cruda al GestorVelas para que él haga su magia
            if self.callback_kline:
                self.callback_kline(symbol, kline_data)

    def obtener_precio(self, symbol):
        return self.precios_actuales.get(symbol, 0.0)

    def verificar_salud_datos(self, symbol, max_retraso=60):
        """Revisa la antigüedad del dato del TICKER (no de la vela)"""
        last_update = self.ultimas_actualizaciones.get(symbol, 0)
        if last_update == 0: 
            return False
        
        if time.time() - last_update > max_retraso:
            return False
        return True

    def detener_todo(self):
        self.twm.stop()
        self.stream_activo = False
        print("🔕 WebSockets detenidos.")