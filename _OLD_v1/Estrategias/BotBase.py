import time
import sys
import json
import os
from Core.Utils.Config import Config
from Core.API.BinanceBase import BinanceBase
from Core.Datos.GestorMercado import GestorMercado
from Core.Datos.GestorAnalisis import GestorAnalisis
from Core.Datos.GestorVelas import GestorVelas
from Core.Ejecucion.GestorBasico import GestorBasico

# --- NUEVOS COMPONENTES DE SEGURIDAD ---
from Core.Riesgo.GestorPosicion import GestorPosicion
from Core.Riesgo.GestorCapital import GestorCapital
# ---------------------------------------

class BotBase:
    """
    Clase Base (Infraestructura).
    Ubicación: Estrategias/BotBase.py
    ACTUALIZADO: Integra Seguridad (Posición y Capital).
    """
    def __init__(self):
        print("🏗️  Inicializando BotBase v4 (Con Seguridad Integrada)...")
        
        # 1. Cargar Configuración
        try:
            Config.validar_config()
        except Exception as e:
            print(f"❌ Error de Configuración (.env): {e}")
            sys.exit()
        
        # 2. Cargar Estrategias
        self.estrategias = self.cargar_json_estrategias()
        
        # 3. Conexiones API REST
        self.api = BinanceBase()
        if not self.api.validar_conectividad():
            print("❌ Error crítico: No hay conexión con Binance.")
            sys.exit()
            
        # 4. Inicializar Componentes Especialistas
        self.mercado = GestorMercado()      # Ojos (WebSockets)
        self.analista = GestorAnalisis()    # Cerebro (Indicadores)
        self.velas = GestorVelas(self.api)  # Memoria (Historial)
        
        # --- NUEVA ESTRUCTURA DE EJECUCIÓN Y RIESGO ---
        # A. Ejecutor (Manos)
        self.ejecutor = GestorBasico(self.api) 
        
        # B. Guardián de Cupos (Evita abrir más de 4 posiciones o duplicar)
        self.capital = GestorCapital(self.api)
        
        # C. Guardián de Posición (Coloca SL, limpia órdenes zombies)
        # Nota: GestorPosicion necesita al ejecutor para operar
        self.posicion = GestorPosicion(self.ejecutor)
        # ----------------------------------------------
        
        # 5. Configurar cuenta (Apalancamiento)
        self.pares_activos = []
        self.configurar_cuenta()
        
    def cargar_json_estrategias(self):
        """Carga el archivo estrategias.json de la carpeta actual."""
        carpeta_actual = os.path.dirname(os.path.abspath(__file__))
        ruta = os.path.join(carpeta_actual, 'estrategias.json')
        try:
            with open(ruta, 'r') as f:
                data = json.load(f)
                print(f"📄 Estrategias cargadas: {len(data)} pares.")
                return data
        except Exception as e:
            print(f"❌ Error leyendo estrategias.json: {e}")
            sys.exit()

    def configurar_cuenta(self):
        """Configura apalancamiento inicial."""
        print("🔧 Ajustando apalancamiento en Binance...")
        for par, config in self.estrategias.items():
            if config.get("activo", False):
                self.pares_activos.append(par)
                if Config.BINANCE_API_KEY:
                    leverage = config.get("apalancamiento", 1)
                    self.ejecutor.configurar_apalancamiento(par, leverage)
        print(f"✅ BotBase listo. Pares activos: {len(self.pares_activos)}")

    def iniciar_servicios(self):
        """Secuencia de Arranque: Snapshot + WebSockets + Auditoría Inicial"""
        if not self.pares_activos:
            print("⚠️ No hay pares activos.")
            return

        # FASE 1: Snapshot Histórico
        print("\n📚 FASE 1: Cargando historial (Memoria)...")
        for par in self.pares_activos:
            tf = self.estrategias[par]["timeframe"]
            self.velas.inicializar_par(par, tf)
            time.sleep(0.5)

        # FASE 2: WebSockets
        print("\n📡 FASE 2: Iniciando WebSockets...")
        self.mercado.iniciar_flujo_hibrido(
            self.estrategias, 
            callback_kline=self.velas.actualizar_vela_en_tiempo_real
        )
        
        print("⏳ Sincronizando flujos (5s)...")
        time.sleep(5)
        
        # FASE 3: Auditoría de Seguridad (NUEVO)
        # Al arrancar, revisamos si ya teníamos posiciones abiertas para protegerlas
        print("\n🛡️  FASE 3: Auditoría de Posiciones Abiertas...")
        for par in self.pares_activos:
            # Esto colocará el SL si el bot se reinició con una posición abierta
            self.posicion.iniciar_protocolo_seguridad(par)
            
        print("🚀 SISTEMA OPERATIVO.\n")

    def detener_servicios(self):
        self.mercado.detener_todo()
        print("🛑 Servicios detenidos.")