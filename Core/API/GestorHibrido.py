import time
import logging
import requests  # <--- NUEVA DEPENDENCIA
from unicorn_binance_websocket_api.manager import BinanceWebSocketApiManager
from Core.Utils.Config import Config

# Desactivamos logs ruidosos
logging.getLogger("unicorn_binance_websocket_api").setLevel(logging.ERROR)

class GestorHibrido:
    """
    Gestor Híbrido:
    1. REST API -> Descarga historial inicial (Pre-carga).
    2. WebSocket -> Mantiene datos en vivo.
    """
    def __init__(self):
        self.precios_actuales = {} 
        self.ultimas_actualizaciones = {} 
        self.stream_activo = False
        self.callback_kline = None
        
        # Selección de URLs
        if Config.USAR_TESTNET:
            self.exchange_target = "binance.com-futures-testnet"
            self.rest_url = "https://testnet.binancefuture.com/fapi/v1/klines"
        else:
            self.exchange_target = "binance.com-futures"
            self.rest_url = "https://fapi.binance.com/fapi/v1/klines"
            
        print(f"🔌 Conectando a Binance ({'TESTNET' if Config.USAR_TESTNET else 'LIVE'})...")

        self.manager = BinanceWebSocketApiManager(
            exchange=self.exchange_target,
            process_stream_data=self.procesar_msg 
        )

    def obtener_velas_historicas(self, simbolo, timeframe, limite=100):
        """
        Descarga las últimas 'limite' velas vía HTTP para calentar indicadores.
        """
        # Formato Binance REST: BTCUSDT (sin barra)
        symbol_clean = simbolo.replace('/', '').upper()
        
        params = {
            'symbol': symbol_clean,
            'interval': timeframe,
            'limit': limite
        }
        
        try:
            # Petición síncrona (bloquea hasta recibir datos)
            resp = requests.get(self.rest_url, params=params, timeout=5)
            data = resp.json()
            
            if not isinstance(data, list):
                print(f"⚠️ Error bajando historial para {simbolo}: {data}")
                return []
                
            # Convertimos al formato que espera tu estrategia
            velas_formateadas = []
            for k in data:
                # k = [time, open, high, low, close, volume, ...]
                velas_formateadas.append({
                    't': k[0],
                    'o': k[1],
                    'h': k[2],
                    'l': k[3],
                    'c': k[4],
                    'v': k[5],
                    'x': True # Asumimos cerradas porque son historia
                })
            
            return velas_formateadas

        except Exception as e:
            print(f"❌ Error conexión REST para {simbolo}: {e}")
            return []

    def iniciar_flujo_hibrido(self, estrategias_dict, callback_kline):
        """
        Inicia suscripciones WS.
        """
        self.callback_kline = callback_kline
        print("📡 Iniciando WebSockets...")
        
        for par, config in estrategias_dict.items():
            if not config.get("activo", False): 
                continue
            
            symbol = par.replace('/', '').lower()
            tf = config['timeframe']
            
            # Inicializamos memoria
            self.precios_actuales[par] = 0.0
            
            # 1. Stream Ticker
            self.manager.create_stream(channels=['ticker'], markets=[symbol], output="dict")

            # 2. Stream Kline
            self.manager.create_stream(channels=[f'kline_{tf}'], markets=[symbol], output="dict")
            
        self.stream_activo = True
        print(f"✅ WebSockets conectados.")

    def procesar_msg(self, msg, **kwargs):
        """Router de mensajes WS"""
        if not isinstance(msg, dict): return
        payload = msg.get('data', msg)
        if not isinstance(payload, dict): return

        evento = payload.get('e')
        symbol_raw = payload.get('s')

        if not symbol_raw or not evento: return

        if symbol_raw.endswith('USDT'):
            symbol_formateado = f"{symbol_raw[:-4]}/{symbol_raw[-4:]}"
        else:
            symbol_formateado = symbol_raw

        if evento == '24hrTicker':
            self.precios_actuales[symbol_formateado] = float(payload['c'])
            self.ultimas_actualizaciones[symbol_formateado] = time.time()

        elif evento == 'kline':
            kline_data = payload['k']
            if self.callback_kline:
                self.callback_kline(symbol_formateado, kline_data)

    def obtener_precio(self, symbol):
        return self.precios_actuales.get(symbol, 0.0)

    def detener_todo(self):
        self.manager.stop_manager_with_all_streams()
        self.stream_activo = False