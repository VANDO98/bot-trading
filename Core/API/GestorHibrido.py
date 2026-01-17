import time
import logging
import requests  # Mantenemos tu dependencia original
from unicorn_binance_websocket_api.manager import BinanceWebSocketApiManager
from Core.Utils.Config import Config

# Desactivamos logs ruidosos
logging.getLogger("unicorn_binance_websocket_api").setLevel(logging.ERROR)

class GestorHibrido:
    """
    Gestor Híbrido v2.5:
    1. REST API -> Descarga historial inicial (Pre-carga) usando requests.
    2. WebSocket -> Mantiene datos en vivo (Multiplexado 1 socket para N pares).
    """
    def __init__(self):
        self.precios_actuales = {} 
        self.ultimas_actualizaciones = {} 
        self.stream_activo = False
        self.callback_kline = None
        
        # Mapa para traducir nombres (Corrección del precio 0.0000)
        # Ej: 'btcusdt' -> 'BTC/USDT'
        self.mapa_simbolos = {}
        
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

    def obtener_velas_historicas(self, simbolo, timeframe, limite=1000):
        """
        Descarga las últimas 'limite' velas vía HTTP.
        (MANTENIDO ORIGINAL SEGÚN SOLICITUD)
        """
        # Formato Binance REST: BTCUSDT (sin barra)
        symbol_clean = simbolo.replace('/', '').upper()
        
        params = {
            'symbol': symbol_clean,
            'interval': timeframe,
            'limit': limite
        }
        
        try:
            # Petición síncrona
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
        Versión Optimizada: Usa MULTIPLEXADO y MAPEO.
        """
        self.callback_kline = callback_kline
        
        # 1. Preparar listas y Mapa de Traducción
        canales = set()
        mercados = []
        
        print(f"🔌 Configurando Multiplexado para {len(estrategias_dict)} pares...")

        for simbolo_interno, config in estrategias_dict.items():
            # Generamos nombres API: 'BTC/USDT' -> 'btcusdt'
            s_api = simbolo_interno.replace('/', '').lower()
            
            # GUARDAMOS LA TRADUCCIÓN (CRÍTICO PARA ARREGLAR PRECIOS EN 0)
            self.mapa_simbolos[s_api] = simbolo_interno         # 'btcusdt' -> 'BTC/USDT'
            self.mapa_simbolos[s_api.upper()] = simbolo_interno # 'BTCUSDT' -> 'BTC/USDT'
            
            mercados.append(s_api)
            tf = config['timeframe']
            canales.add(f"kline_{tf}")
            
            # Inicializamos precio en el dict para que exista la clave
            self.precios_actuales[simbolo_interno] = 0.0

        try:
            # 2. CREAR UN SOLO SOCKET (MULTIPLEXADO)
            # Pasamos lista de canales y lista de mercados. La librería los combina.
            self.manager.create_stream(
                channels=list(canales), 
                markets=mercados, 
                stream_label="FlujoMaestro",
                output="dict"
            )
            self.stream_activo = True
            print(f"✅ Socket Maestro Iniciado: Escuchando {len(mercados)} mercados.")
            
        except Exception as e:
            print(f"❌ Error al iniciar socket maestro: {e}")

    def procesar_msg(self, msg, **kwargs):
        """
        Router de mensajes WS.
        Maneja la estructura multiplexada y traduce símbolos.
        """
        # Estructura típica multiplexada: {'stream': '...', 'data': {...}}
        if not isinstance(msg, dict): return
        
        # Extraemos la carga útil
        payload = msg.get('data', msg)
        if not isinstance(payload, dict): return

        # Obtenemos evento y símbolo CRUDO de la API (ej: 'BTCUSDT')
        evento = payload.get('e')
        symbol_raw = payload.get('s')
        
        # Validaciones básicas
        if not symbol_raw: return

        # --- TRADUCCIÓN DE NOMBRE (ARREGLO DEL 0.0000) ---
        # Buscamos 'BTCUSDT' en el mapa -> devuelve 'BTC/USDT'
        # Si no existe, usamos el raw por seguridad.
        symbol_formateado = self.mapa_simbolos.get(symbol_raw, symbol_raw)

        # Proceasamiento Kline (Velas)
        if evento == 'kline':
            kline_data = payload['k']
            
            # Actualizar precio actual para el Dashboard
            precio_cierre = float(kline_data['c'])
            self.precios_actuales[symbol_formateado] = precio_cierre
            self.ultimas_actualizaciones[symbol_formateado] = time.time()
            
            # Enviar a la estrategia
            if self.callback_kline:
                self.callback_kline(symbol_formateado, kline_data)

        # Procesamiento Ticker (si estuvieras suscrito a tickers, opcional)
        elif evento == '24hrTicker':
            precio = float(payload['c'])
            self.precios_actuales[symbol_formateado] = precio

    def obtener_precio(self, symbol):
        # Devuelve el precio usando la clave correcta (ej: BTC/USDT)
        return self.precios_actuales.get(symbol, 0.0)

    def detener_todo(self):
        self.manager.stop_manager_with_all_streams()
        self.stream_activo = False