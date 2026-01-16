import time
from colorama import Fore, Style

# Módulos del sistema
from Core.Utils.Config import Config
from Core.API.GestorHibrido import GestorHibrido
from Core.Ejecucion.GestorEjecucion import GestorEjecucion 

# Estrategias
from Estrategias.Concretas.EstrategiaRSI import EstrategiaRSI

class BotController:
    """
    ORQUESTADOR FINAL: Datos -> Estrategia -> EJECUCIÓN (+ Sincronización)
    """
    
    def __init__(self):
        print(Fore.YELLOW + "🤖 Inicializando BotController v2.3 (FULL AUTO)...")
        
        self.catalogo_estrategias = { "EstrategiaRSI": EstrategiaRSI }
        self.gestor_datos = GestorHibrido()
        self.gestor_ejecucion = GestorEjecucion()
        
        self.estrategias_activas = {} 
        self.config_pares = {} 
        
        self.cargar_estrategias_desde_config()

    def cargar_estrategias_desde_config(self):
        self.config_pares = Config.obtener_pares_activos()
        print(f"⚙️ Configurando {len(self.config_pares)} pares activos...")
        
        for par, cfg in self.config_pares.items():
            nombre_clase = cfg.get('estrategia')
            params = cfg.get('parametros_estrategia', {})
            
            ClaseEstrategia = self.catalogo_estrategias.get(nombre_clase)
            
            if ClaseEstrategia:
                instancia = ClaseEstrategia(nombre=par, parametros_json=params)
                self.estrategias_activas[par] = instancia
                print(f"   ✅ {par} -> Lista ({nombre_clase})")

    def iniciar(self):
        """
        Arranca el sistema verificando estado en Binance.
        """
        if not self.estrategias_activas:
            print(Fore.RED + "❌ No hay estrategias. Abortando.")
            return

        print(Fore.CYAN + "\n🔥 Iniciando Sincronización y Pre-Carga...")

        for par, estrategia in self.estrategias_activas.items():
            # 1. Configurar Apalancamiento
            lev = self.config_pares[par].get('apalancamiento', 1)
            self.gestor_ejecucion.configurar_apalancamiento(par, lev)

            # 2. SINCRONIZACIÓN DE ESTADO (AQUÍ ESTÁ LO NUEVO) 👁️
            # Preguntamos a Binance: "¿Estamos dentro?"
            esta_dentro = self.gestor_ejecucion.obtener_posicion_abierta(par)
            estrategia.posicion_abierta = esta_dentro
            
            estado_str = f"{Fore.RED}OCUPADO{Fore.CYAN}" if esta_dentro else f"{Fore.GREEN}LIBRE{Fore.CYAN}"
            print(f"   👁️ Estado inicial de {par}: {estado_str}")

            # 3. Descargar Historial
            tf = self.config_pares[par]['timeframe']
            print(f"   📥 Descargando historial para {par} ({tf})...", end="\r")
            
            historial = self.gestor_datos.obtener_velas_historicas(par, tf, limite=1000)
            for kline in historial:
                estrategia.recibir_vela(par, kline)
            
            print(f"   ✅ {par}: {len(historial)} velas cargadas.")

        print(Fore.GREEN + "✨ Todo sincronizado.\n")

        # 4. Iniciar WebSockets
        self.gestor_datos.iniciar_flujo_hibrido(
            estrategias_dict=self.config_pares,
            callback_kline=self.procesar_vela
        )
        print(Fore.GREEN + "🚀 Bot Operativo y Sincronizado.")

    def procesar_vela(self, simbolo, kline_data):
        """
        Lógica Principal con 'Watchdog' de estado.
        """
        estrategia = self.estrategias_activas.get(simbolo)
        if not estrategia: return

        # --- MONITOR DE SALIDA (AQUÍ ESTÁ LO NUEVO) ---
        # Si el bot cree que tiene posición, verifica si el mercado la cerró (TP/SL)
        if estrategia.posicion_abierta:
            if kline_data['x']: # Solo verificamos al cierre de vela para no saturar la API
                sigue_abierta = self.gestor_ejecucion.obtener_posicion_abierta(simbolo)
                
                if not sigue_abierta:
                    print(f"{Fore.YELLOW}🔓 Posición en {simbolo} ya no existe (SL/TP ejecutado). Bot liberado.")
                    estrategia.posicion_abierta = False
        # ---------------------------------------------

        # 1. Pensar
        senal = estrategia.recibir_vela(simbolo, kline_data)
        
        # 2. Actuar
        if senal in ["COMPRA", "VENTA"]:
            self.gestionar_ejecucion(simbolo, senal, estrategia)

    def gestionar_ejecucion(self, simbolo, senal, estrategia):
        if estrategia.posicion_abierta:
            return 

        lado = "buy" if senal == "COMPRA" else "sell"
        
        # Cargar configuración
        config_cantidad = self.config_pares[simbolo].get('cantidad_operacion', 0)
        precio_actual = self.gestor_datos.obtener_precio(simbolo)
        
        # Calcular Cantidad
        if isinstance(config_cantidad, str) and '%' in config_cantidad:
            cantidad_final = self.gestor_ejecucion.calcular_cantidad_por_porcentaje(
                simbolo, config_cantidad, precio_actual
            )
        else:
            cantidad_final = float(config_cantidad)

        if cantidad_final <= 0: return

        print(f"{Fore.MAGENTA}⚡ ALERTA: {lado.upper()} {simbolo} (Cant: {cantidad_final})...{Style.RESET_ALL}")
        
        # Ejecutar Entrada
        orden = self.gestor_ejecucion.colocar_orden_mercado(simbolo, lado, cantidad_final)
        
        if orden:
            estrategia.posicion_abierta = True
            
            precio_fill = float(orden.get('average', 0.0))
            if precio_fill == 0.0: precio_fill = precio_actual

            print(f"{Fore.GREEN}✅ ENTRADA CONFIRMADA: {simbolo} | Precio: {precio_fill}{Style.RESET_ALL}")
            
            # Colocar SL / TP
            config_global = Config.cargar_configuracion()
            riesgo = config_global.get('sistema_riesgo', {})
            sl_pct = riesgo.get('stop_loss_pct', 0.02)
            tp_pct = riesgo.get('take_profit_pct', 0.04)

            print(f"🛡️ Colocando SL ({sl_pct*100}%) y TP ({tp_pct*100}%)")

            self.gestor_ejecucion.colocar_ordenes_salida(
                simbolo=simbolo,
                lado_entrada=lado,
                cantidad=cantidad_final,
                precio_entrada=precio_fill,
                sl_pct=sl_pct,
                tp_pct=tp_pct
            )
        else:
            print(Fore.RED + "❌ ERROR AL ENTRAR.")

    def detener(self):
        print(Fore.YELLOW + "\n🛑 Deteniendo sistema...")
        self.gestor_datos.detener_todo()