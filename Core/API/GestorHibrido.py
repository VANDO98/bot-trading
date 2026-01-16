import time
import logging
from unicorn_binance_websocket_api.manager import BinanceWebSocketApiManager
from Core.Utils.Config import Config

# Desactivamos logs ruidosos de la librería, solo errores críticos
logging.getLogger("unicorn_binance_websocket_api").setLevel(logging.ERROR)

class GestorHibrido:
    """
    Gestor de Conexión WebSocket Híbrido (Ticker + Klines).
    Versión Estable v2.3 para Unicorn v1.46.2
    """
    def __init__(self):
        self.precios_actuales = {} 
        self.ultimas_actualizaciones = {} 
        self.stream_activo = False
        self.callback_kline = None
        
        # Selección de entorno
        if Config.USAR_TESTNET:
            self.exchange_target = "binance.com-futures-testnet"
        else:
            self.exchange_target = "binance.com-futures"
            
        print(f"🔌 Conectando a Binance ({'TESTNET' if Config.USAR_TESTNET else 'LIVE'})...")

        # Inicializamos el Manager con el callback global
        self.manager = BinanceWebSocketApiManager(
            exchange=self.exchange_target,
            process_stream_data=self.procesar_msg 
        )

    def iniciar_flujo_hibrido(self, estrategias_dict, callback_kline):
        """
        Inicia suscripciones separadas para Ticker y Kline.
        """
        self.callback_kline = callback_kline
        print("📡 Iniciando suscripción a flujos de mercado...")
        
        streams_iniciados = 0
        
        for par, config in estrategias_dict.items():
            if not config.get("activo", False): 
                continue
            
            symbol = par.replace('/', '').lower()
            tf = config['timeframe']
            
            # Inicializamos memoria
            self.precios_actuales[par] = 0.0
            self.ultimas_actualizaciones[par] = time.time()
            
            # 1. Stream Ticker
            self.manager.create_stream(
                channels=['ticker'], 
                markets=[symbol], 
                output="dict"
            )

            # 2. Stream Kline
            self.manager.create_stream(
                channels=[f'kline_{tf}'], 
                markets=[symbol], 
                output="dict"
            )
            streams_iniciados += 2
            
        self.stream_activo = True
        print(f"✅ Conexión establecida: {streams_iniciados} streams activos.")

    def procesar_msg(self, msg, **kwargs):
        """
        Router de mensajes silencioso y eficiente.
        """
        if not isinstance(msg, dict): return
        
        # Extraer payload
        payload = msg.get('data', msg)
        if not isinstance(payload, dict): return

        # Validar evento y símbolo
        evento = payload.get('e')
        symbol_raw = payload.get('s') # Viene como BTCUSDT

        if not symbol_raw or not evento: return

        # Formatear símbolo a BTC/USDT
        if symbol_raw.endswith('USDT'):
            symbol_formateado = f"{symbol_raw[:-4]}/{symbol_raw[-4:]}"
        else:
            symbol_formateado = symbol_raw

        # Enrutamiento de datos
        if evento == '24hrTicker':
            # Actualizar precio en caché (memoria rápida)
            self.precios_actuales[symbol_formateado] = float(payload['c'])
            self.ultimas_actualizaciones[symbol_formateado] = time.time()

        elif evento == 'kline':
            # Disparar análisis de estrategia
            kline_data = payload['k']
            if self.callback_kline:
                self.callback_kline(symbol_formateado, kline_data)

    def obtener_precio(self, symbol):
        """Devuelve el último precio conocido del activo."""
        return self.precios_actuales.get(symbol, 0.0)

    def verificar_salud_datos(self, symbol, max_retraso=60):
        """Watchdog: Devuelve False si el flujo de datos se ha congelado."""
        last_update = self.ultimas_actualizaciones.get(symbol, 0)
        if last_update == 0: return False
        if time.time() - last_update > max_retraso: return False
        return True

    def detener_todo(self):
        self.manager.stop_manager_with_all_streams()
        self.stream_activo = False
        print("🔕 WebSockets detenidos.")