import time
import logging
import requests
from unicorn_binance_websocket_api.manager import BinanceWebSocketApiManager
from Core.Utils.Config import Config

logging.getLogger("unicorn_binance_websocket_api").setLevel(logging.ERROR)

class GestorWebsocket:
    """
    Gestor WebSocket v2.6 (Renamed):
    - Soluciona la contaminación de Timeframes (5m vs 1h).
    - Agrupa suscripciones WebSocket por intervalo.
    """
    def __init__(self):
        self.precios_actuales = {} 
        self.ultimas_actualizaciones = {} 
        self.stream_activo = False
        self.callback_kline = None
        self.mapa_simbolos = {}
        
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
        symbol_clean = simbolo.replace('/', '').upper()
        params = {'symbol': symbol_clean, 'interval': timeframe, 'limit': limite}
        
        try:
            resp = requests.get(self.rest_url, params=params, timeout=5)
            data = resp.json()
            
            if not isinstance(data, list):
                print(f"⚠️ Error bajando historial para {simbolo}: {data}")
                return []
                
            velas_formateadas = []
            for k in data:
                velas_formateadas.append({
                    't': k[0], 'o': k[1], 'h': k[2], 'l': k[3], 'c': k[4], 'v': k[5],
                    'x': True
                })
            return velas_formateadas

        except Exception as e:
            print(f"❌ Error conexión REST para {simbolo}: {e}")
            return []

    def obtener_velas_rango(self, simbolo, timeframe, start_ms, end_ms):
        """
        Descarga velas históricas en un rango de tiempo específico.
        start_ms, end_ms: timestamps en milisegundos.
        """
        symbol_clean = simbolo.replace('/', '').upper()
        # Binance limita a 1000 velas por request. Si el rango es grande, habría que paginar,
        # pero para el ShadowJudge (4h-24h) 1000 velas de 5m/1h suelen sobrar.
        params = {
            'symbol': symbol_clean, 
            'interval': timeframe, 
            'startTime': int(start_ms),
            'endTime': int(end_ms),
            'limit': 1000 
        }
        
        try:
            resp = requests.get(self.rest_url, params=params, timeout=10)
            data = resp.json()
            
            if not isinstance(data, list):
                print(f"⚠️ Error bajando historial rango para {simbolo}: {data}")
                return []
                
            velas_formateadas = []
            for k in data:
                velas_formateadas.append({
                    't': k[0], 'o': float(k[1]), 'h': float(k[2]), 'l': float(k[3]), 'c': float(k[4]), 'v': float(k[5]),
                    'x': True
                })
            return velas_formateadas

        except Exception as e:
            print(f"❌ Error conexión REST Rango para {simbolo}: {e}")
            return []

    def iniciar_flujo_hibrido(self, estrategias_dict, callback_kline):
        """
        FIX: Agrupa mercados por timeframe para evitar suscripciones cruzadas.
        """
        self.callback_kline = callback_kline
        
        # 1. Agrupar mercados por Timeframe
        grupos_tf = {} # {'1h': ['btc', 'eth'], '5m': ['uni']}
        
        print(f"🔌 Configurando Multiplexado Inteligente...")

        for simbolo_interno, config in estrategias_dict.items():
            s_api = simbolo_interno.replace('/', '').lower()
            
            # Guardar traducción
            self.mapa_simbolos[s_api] = simbolo_interno         
            self.mapa_simbolos[s_api.upper()] = simbolo_interno 
            
            # Inicializar precio
            self.precios_actuales[simbolo_interno] = 0.0
            
            # Agrupar
            tf = config['timeframe']
            if tf not in grupos_tf:
                grupos_tf[tf] = []
            grupos_tf[tf].append(s_api)

        try:
            # 2. Crear un stream separado por cada grupo de Timeframe
            for tf, lista_mercados in grupos_tf.items():
                print(f"   ➤ Suscribiendo {len(lista_mercados)} pares al canal kline_{tf}...")
                self.manager.create_stream(
                    channels=[f"kline_{tf}"], 
                    markets=lista_mercados, 
                    stream_label=f"Stream_{tf}",
                    output="dict"
                )
            
            self.stream_activo = True
            print(f"✅ Sockets Iniciados Correctamente.")
            
        except Exception as e:
            print(f"❌ Error al iniciar sockets: {e}")

    def procesar_msg(self, msg, **kwargs):
        if not isinstance(msg, dict): return
        payload = msg.get('data', msg)
        if not isinstance(payload, dict): return

        evento = payload.get('e')
        symbol_raw = payload.get('s')
        
        if not symbol_raw: return

        symbol_formateado = self.mapa_simbolos.get(symbol_raw, symbol_raw)

        if evento == 'kline':
            kline_data = payload['k']
            precio_cierre = float(kline_data['c'])
            self.precios_actuales[symbol_formateado] = precio_cierre
            self.ultimas_actualizaciones[symbol_formateado] = time.time()
            
            if self.callback_kline:
                self.callback_kline(symbol_formateado, kline_data)

        elif evento == '24hrTicker':
            precio = float(payload['c'])
            self.precios_actuales[symbol_formateado] = precio

    def obtener_precio(self, symbol):
        return self.precios_actuales.get(symbol, 0.0)

    def detener_todo(self):
        self.manager.stop_manager_with_all_streams()
        self.stream_activo = False