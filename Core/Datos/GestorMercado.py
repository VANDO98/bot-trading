from binance import ThreadedWebsocketManager
from Core.Utils.Config import Config
import time

class GestorMercado:
    """
    Especialista en flujo de datos (WebSockets).
    OPTIMIZADO Y BLINDADO: 
    1. Usa Multiplexing (Futuros/Spot).
    2. Watchdog: Controla la antigüedad de los datos para detectar desconexiones silenciosas.
    """
    def __init__(self):
        self.precios = {} 
        self.ultimas_actualizaciones = {} # GUARDA LA HORA DEL ÚLTIMO DATO
        self.stream_activo = False
        
        self.twm = ThreadedWebsocketManager(
            api_key=Config.BINANCE_API_KEY, 
            api_secret=Config.BINANCE_SECRET_KEY, 
            testnet=Config.USAR_TESTNET
        )
        self.twm.start()

    def iniciar_flujo_multiples_pares(self, lista_pares):
        """Inicia el stream seleccionando la red correcta."""
        # Inicializar memorias
        for par in lista_pares:
            self.precios[par.upper()] = 0.0
            self.ultimas_actualizaciones[par.upper()] = 0 # Unix timestamp
            
        streams = [f"{par.lower()}@ticker" for par in lista_pares]
        print(f"📡 Radar iniciado para {len(streams)} pares.")

        if Config.BINANCE_API_KEY and Config.BINANCE_SECRET_KEY:
            print("🔒 MODO FUTURES (Autenticado)")
            self.twm.start_futures_multiplex_socket(
                callback=self.procesar_mensaje_multiplex, 
                streams=streams
            )
        else:
            print("🔓 MODO SPOT (Anónimo)")
            self.twm.start_multiplex_socket(
                callback=self.procesar_mensaje_multiplex, 
                streams=streams
            )
            
        self.stream_activo = True

    def procesar_mensaje_multiplex(self, msg):
        """Al recibir datos, actualizamos PRECIO y HORA."""
        if 'data' in msg:
            data = msg['data']
            if 'c' in data and 's' in data:
                symbol = data['s']
                precio = float(data['c'])
                
                self.precios[symbol] = precio
                # Marcamos el momento exacto en que recibimos vida de este par
                self.ultimas_actualizaciones[symbol] = time.time()

    def obtener_precio(self, symbol):
        """Devuelve el precio actual."""
        return self.precios.get(symbol.upper(), 0.0)

    def verificar_salud_datos(self, symbol, max_retraso_segundos=60):
        """
        NUEVA FUNCIÓN CRÍTICA:
        Verifica si los datos de un par están 'frescos'.
        Retorna True si la conexión está viva.
        Retorna False si los datos son viejos (Posible desconexión).
        """
        ultimo_check = self.ultimas_actualizaciones.get(symbol.upper(), 0)
        ahora = time.time()
        
        diferencia = ahora - ultimo_check
        
        if ultimo_check == 0:
            return False # Nunca se han recibido datos
            
        if diferencia > max_retraso_segundos:
            print(f"⚠️ ALERTA: Datos de {symbol} obsoletos ({int(diferencia)}s sin updates).")
            return False # Los datos son viejos, peligro.
            
        return True # Todo ok

    def detener_todo(self):
        self.twm.stop()
        self.precios.clear()
        self.stream_activo = False
        print("🔕 Radar detenido.")