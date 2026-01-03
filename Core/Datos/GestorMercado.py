from binance import ThreadedWebsocketManager
from Core.Utils.Config import Config
import time

class GestorMercado:
    """
    Especialista en flujo de datos (WebSockets).
    OPTIMIZADO: 
    1. Usa Multiplexing para eficiencia (1 conexión para N pares).
    2. Detecta automáticamente si debe usar la red de FUTUROS o SPOT.
    Fuente: Plan Maestro - Fase 2 [GestorMercado]
    """
    def __init__(self):
        self.precios = {} 
        self.stream_activo = False
        
        # Inicializamos el Manager. 
        # Si hay claves en Config, las usa. Si no, entra en modo anónimo.
        self.twm = ThreadedWebsocketManager(
            api_key=Config.BINANCE_API_KEY, 
            api_secret=Config.BINANCE_SECRET_KEY, 
            testnet=Config.USAR_TESTNET
        )
        self.twm.start()

    def iniciar_flujo_multiples_pares(self, lista_pares):
        """
        Abre el flujo de datos para una lista de pares.
        Selecciona la red (Futures vs Spot) basándose en las credenciales.
        """
        # 1. Limpiar/Inicializar precios en 0
        for par in lista_pares:
            self.precios[par.upper()] = 0.0
            
        # 2. Preparar los nombres de los streams (minúsculas + @ticker)
        streams = [f"{par.lower()}@ticker" for par in lista_pares]
        
        print(f"📡 Configurando radares para {len(streams)} pares...")

        # --- AQUÍ ESTÁ EL CAMBIO CRÍTICO ---
        # Verificamos si existen las claves para decidir a qué red conectar.
        
        if Config.BINANCE_API_KEY and Config.BINANCE_SECRET_KEY:
            # CASO A: Tenemos llaves -> Usamos la red de FUTUROS
            # Es vital usar 'start_futures_multiplex_socket' para obtener precios de contratos,
            # funding rates implícitos y volumen real de derivados.
            print("🔒 MODO OPERATIVO: Conectando a BINANCE FUTURES (Datos Reales de Contratos)")
            self.twm.start_futures_multiplex_socket(
                callback=self.procesar_mensaje_multiplex, 
                streams=streams
            )
        else:
            # CASO B: No hay llaves -> Usamos SPOT (Solo para pruebas de conectividad)
            # Esto permite correr los tests de estrés sin arriesgar la cuenta.
            print("🔓 MODO OBSERVADOR: Conectando a BINANCE SPOT (Solo referencia, NO OPERAR)")
            self.twm.start_multiplex_socket(
                callback=self.procesar_mensaje_multiplex, 
                streams=streams
            )
            
        self.stream_activo = True

    def procesar_mensaje_multiplex(self, msg):
        """
        Callback que procesa los mensajes entrantes.
        Estructura típica msg: {'stream': 'btcusdt@ticker', 'data': {'s': 'BTCUSDT', 'c': '50000', ...}}
        """
        if 'data' in msg:
            data = msg['data']
            if 'c' in data and 's' in data:
                symbol = data['s']
                precio = float(data['c'])
                self.precios[symbol] = precio

    def obtener_precio(self, symbol):
        """Devuelve el precio actual del par."""
        return self.precios.get(symbol.upper(), 0.0)

    def detener_todo(self):
        """Detiene la conexión de forma segura."""
        self.twm.stop()
        self.precios.clear()
        self.stream_activo = False
        print("🔕 Radar Multiplex detenido.")