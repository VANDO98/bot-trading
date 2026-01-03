import time
import sys
import json
import os
from Core.Utils.Config import Config
from Core.API.BinanceBase import BinanceBase
from Core.Datos.GestorMercado import GestorMercado
from Core.Datos.GestorAnalisis import GestorAnalisis
from Core.Ejecucion.GestorBasico import GestorBasico
from Core.Datos.GestorVelas import GestorVelas # <--- Componente de Memoria

class BotBase:
    """
    Clase Base (Infraestructura).
    Ubicación: Estrategias/BotBase.py
    
    Responsabilidades:
    1. Cargar configuración (JSON + .env).
    2. Inicializar conexión con Binance.
    3. Preparar componentes (Mercado, Velas, Análisis, Ejecución).
    4. Descargar historial inicial (Snapshot).
    5. Iniciar WebSockets Híbridos.
    """
    def __init__(self):
        print("🏗️  Inicializando BotBase v3 (Con Memoria de Mercado)...")
        
        # 1. Cargar Configuración General (.env)
        try:
            Config.validar_config()
        except Exception as e:
            print(f"❌ Error de Configuración (.env): {e}")
            sys.exit()
        
        # 2. Cargar Estrategias (JSON)
        self.estrategias = self.cargar_json_estrategias()
        
        # 3. Conexiones API REST
        self.api = BinanceBase()
        if not self.api.validar_conectividad():
            print("❌ Error crítico: No hay conexión con Binance.")
            sys.exit()
            
        # 4. Inicializar Componentes Especialistas
        self.mercado = GestorMercado()      # Ojos (WebSockets)
        self.analista = GestorAnalisis()    # Cerebro (Indicadores)
        self.ejecutor = GestorBasico(self.api) # Manos (Órdenes)
        self.velas = GestorVelas(self.api)  # Memoria (Historial Klines)
        
        # 5. Configurar cuenta (Apalancamiento)
        self.pares_activos = []
        self.configurar_cuenta()
        
    def cargar_json_estrategias(self):
        """
        Carga el archivo estrategias.json de la carpeta actual.
        """
        carpeta_actual = os.path.dirname(os.path.abspath(__file__))
        ruta = os.path.join(carpeta_actual, 'estrategias.json')
        
        try:
            with open(ruta, 'r') as f:
                data = json.load(f)
                print(f"📄 Estrategias cargadas desde: {ruta}")
                return data
        except Exception as e:
            print(f"❌ Error crítico leyendo estrategias.json: {e}")
            sys.exit()

    def configurar_cuenta(self):
        """Lee el JSON y configura apalancamiento en Binance Futures"""
        print("🔧 Ajustando configuraciones de cuenta...")
        for par, config in self.estrategias.items():
            if config.get("activo", False):
                self.pares_activos.append(par)
                
                # Solo configuramos si hay claves API reales
                if Config.BINANCE_API_KEY:
                    leverage = config.get("apalancamiento", 1)
                    self.ejecutor.configurar_apalancamiento(par, leverage)
        
        print(f"✅ BotBase listo. Pares activos: {len(self.pares_activos)}")

    def iniciar_servicios(self):
        """
        Secuencia de Arranque:
        1. Descarga histórica (Snapshot de 1000 velas).
        2. Conexión WebSocket Híbrida (Ticker + Klines).
        """
        if not self.pares_activos:
            print("⚠️ No hay pares activos en el JSON. El bot no hará nada.")
            return

        # PASO 1: Llenar la memoria (Snapshot)
        print("\n📚 FASE 1: Cargando historial de mercado (1000 velas por par)...")
        for par in self.pares_activos:
            tf = self.estrategias[par]["timeframe"]
            # Descargamos las velas iniciales
            exito = self.velas.inicializar_par(par, tf)
            if not exito:
                print(f"⚠️ Advertencia: No se pudo descargar historial de {par}")
            
            time.sleep(0.5) # Pequeña pausa para no saturar API en el arranque

        # PASO 2: Iniciar WebSockets Híbridos
        # Pasamos la función de 'velas' como callback para que el Mercado le envíe los datos
        print("\n📡 FASE 2: Iniciando conexión en tiempo real...")
        
        self.mercado.iniciar_flujo_hibrido(
            self.estrategias, 
            callback_kline=self.velas.actualizar_vela_en_tiempo_real
        )
        
        print("⏳ Sincronizando flujos (Esperando 5s)...")
        time.sleep(5)
        print("🚀 SERVICIOS INICIADOS CORRECTAMENTE. Listo para operar.\n")

    def detener_servicios(self):
        self.mercado.detener_todo()
        print("🛑 Servicios detenidos.")