import time
import logging
from colorama import Fore, Style

# Módulos del sistema
from Core.Utils.Config import Config
from Core.API.GestorHibrido import GestorHibrido

# Importar tus estrategias aquí
from Estrategias.Concretas.EstrategiaRSI import EstrategiaRSI

class BotController:
    """
    ORQUESTADOR PRINCIPAL (Capa de Control)
    - Conecta el GestorHibrido (Datos) con las Estrategias (Lógica).
    - Recibe señales y (futuro) ejecuta órdenes.
    """
    
    def __init__(self):
        # --- ESTA PARTE SE MANTIENE IGUAL ---
        print(Fore.YELLOW + "🤖 Inicializando BotController v2.3...")
        
        # 1. Mapa de Estrategias Disponibles
        self.catalogo_estrategias = {
            "EstrategiaRSI": EstrategiaRSI
        }
        
        # 2. Inicializar componentes
        self.gestor_datos = GestorHibrido()
        self.estrategias_activas = {} # Diccionario: {'BTC/USDT': instancia_estrategia}
        
        # 3. Cargar configuración
        self.cargar_estrategias_desde_config()

    def cargar_estrategias_desde_config(self):
        """
        Lee el JSON y crea las instancias de las estrategias para cada par activo.
        """
        config_pares = Config.obtener_pares_activos()
        
        print(f"⚙️ Configurando {len(config_pares)} pares activos...")
        
        for par, cfg in config_pares.items():
            nombre_clase = cfg.get('estrategia')
            params = cfg.get('parametros_estrategia', {})
            
            # Buscar la clase en el catálogo
            ClaseEstrategia = self.catalogo_estrategias.get(nombre_clase)
            
            if ClaseEstrategia:
                # Instanciar la estrategia
                instancia = ClaseEstrategia(nombre=par, parametros_json=params)
                self.estrategias_activas[par] = instancia
                print(f"   ✅ {par} -> Cargada con {nombre_clase}")
            else:
                print(f"   ❌ Error: Estrategia '{nombre_clase}' no encontrada para {par}")

    def iniciar(self):
        """
        1. Descarga historial (Pre-carga).
        2. Inicia WebSockets.
        """
        if not self.estrategias_activas:
            print(Fore.RED + "❌ No hay estrategias. Abortando.")
            return

        config_pares = Config.obtener_pares_activos()

        # --- FASE 1: PRE-CALENTAMIENTO (REST API) ---
        print(Fore.CYAN + "\n🔥 Iniciando Pre-Carga de Historial (1000 velas)...")
        
        for par, estrategia in self.estrategias_activas.items():
            tf = config_pares[par]['timeframe']
            print(f"   📥 Descargando para {par} ({tf})...", end="\r")
            
            # Descargamos las últimas 100 velas vía HTTP
            historial = self.gestor_datos.obtener_velas_historicas(par, tf, limite=1000)
            
            # Las inyectamos en la estrategia una por una como si acabaran de llegar
            for kline in historial:
                estrategia.recibir_vela(par, kline)
            
            print(f"   ✅ {par}: {len(historial)} velas cargadas. RSI listo.")

        print(Fore.GREEN + "✨ Pre-carga completada. Indicadores sincronizados.\n")

        # --- FASE 2: TIEMPO REAL (WEBSOCKETS) ---
        self.gestor_datos.iniciar_flujo_hibrido(
            estrategias_dict=config_pares,
            callback_kline=self.procesar_vela
        )
        print(Fore.GREEN + "🚀 Bot Operativo y pensando desde el segundo 0.")

    def procesar_vela(self, simbolo, kline_data):
        """
        Router: Recibe datos del GestorHibrido y los manda a la estrategia.
        """
        estrategia = self.estrategias_activas.get(simbolo)
        
        if not estrategia: return

        # Inyectar datos al cerebro
        senal = estrategia.recibir_vela(simbolo, kline_data)
        
        # Si hay señal, imprimimos (Futuro: Ejecutar Orden)
        if senal != "NEUTRO":
            self.ejecutar_senal(simbolo, senal, kline_data['c'])

    def ejecutar_senal(self, simbolo, senal, precio):
        """
        Placeholder para la ejecución de órdenes.
        """
        color = Fore.GREEN if senal == "COMPRA" else Fore.RED
        # Este print saldrá en medio del dashboard, pero sirve de log
        # print(f"{color}🚨 SEÑAL: {senal} en {simbolo} a ${precio} {Style.RESET_ALL}")
        pass 

    def detener(self):
        print(Fore.YELLOW + "\n🛑 Deteniendo sistema...")
        self.gestor_datos.detener_todo()
        print("✅ Sistema apagado.")