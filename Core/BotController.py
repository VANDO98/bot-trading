import time
from colorama import Fore, Style

# Módulos del sistema
from Core.Utils.Config import Config
from Core.API.GestorHibrido import GestorHibrido
from Core.Ejecucion.GestorEjecucion import GestorEjecucion 

from Core.Utils.TradeLogger import TradeLogger 

# Estrategias
from Estrategias.Concretas.EstrategiaRSI import EstrategiaRSI
from Estrategias.Concretas.EstrategiaRSI_ADX import EstrategiaRSI_ADX

class BotController:
    """
    ORQUESTADOR FINAL: Datos -> Estrategia -> EJECUCIÓN
    Fase 6: Incluye Trailing Stop Dinámico (ATR) y Corrección de Tamaño de Posición.
    """
    
    def __init__(self):
        print(Fore.YELLOW + "🤖 Inicializando BotController v2.5 (CORREGIDO)...")
        
        self.catalogo_estrategias = { 
            "EstrategiaRSI": EstrategiaRSI,
            "EstrategiaRSI_ADX": EstrategiaRSI_ADX
        }
        
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
        if not self.estrategias_activas:
            print(Fore.RED + "❌ No hay estrategias. Abortando.")
            return

        print(Fore.CYAN + "\n🔥 Iniciando Sincronización y Pre-Carga...")

        for par, estrategia in self.estrategias_activas.items():
            # 1. Configurar Apalancamiento
            lev = self.config_pares[par].get('apalancamiento', 1)
            self.gestor_ejecucion.configurar_apalancamiento(par, lev)

            # 2. Sincronización de Estado
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

        self.gestor_datos.iniciar_flujo_hibrido(
            estrategias_dict=self.config_pares,
            callback_kline=self.procesar_vela
        )
        print(Fore.GREEN + "🚀 Bot Operativo y Vigilando.")

    def procesar_vela(self, simbolo, kline_data):
        """
        Lógica Principal: Señales + Trailing Stop
        """
        estrategia = self.estrategias_activas.get(simbolo)
        if not estrategia: return

        # --- GESTIÓN DE POSICIÓN (TRAILING STOP & SYNC) ---
        if estrategia.posicion_abierta:
            # Solo actuamos al cierre de vela para estabilidad
            if kline_data['x']:
                
                # 1. Verificar si seguimos dentro
                sigue_abierta = self.gestor_ejecucion.obtener_posicion_abierta(simbolo)
                if not sigue_abierta:
                    print(f"{Fore.YELLOW}🔓 Posición cerrada en {simbolo}. Bot libre.")
                    estrategia.posicion_abierta = False
                    return

                # 2. Obtener datos para el Trailing
                datos_pos = self.gestor_ejecucion.obtener_datos_posicion(simbolo)
                if datos_pos:
                    self.aplicar_trailing_stop(simbolo, estrategia, datos_pos)
        
        # --------------------------------------------------

        # Lógica de Entrada (Solo si estamos LIBRES)
        if not estrategia.posicion_abierta:
            senal = estrategia.recibir_vela(simbolo, kline_data)
            if senal in ["COMPRA", "VENTA"]:
                self.gestionar_ejecucion(simbolo, senal, estrategia)

    def aplicar_trailing_stop(self, simbolo, estrategia, datos_pos):
        """
        Lógica de Trailing Stop Universal (Basada en ATR).
        """
        entry_price = datos_pos['entryPrice']
        mark_price = datos_pos['markPrice']
        lado = datos_pos['side']
        
        # Calcular ROE (Retorno aproximado sobre precio)
        if lado == 'buy':
            delta_pct = (mark_price - entry_price) / entry_price
        else:
            delta_pct = (entry_price - mark_price) / entry_price

        # Obtener SL actual
        orden_sl = self.gestor_ejecucion.obtener_orden_stop_loss(simbolo)
        if not orden_sl: return
        sl_actual = float(orden_sl['stopPrice'])
        
        nuevo_sl = None
        motivo = ""

        # --- FASE 3: MAXIMIZACIÓN (ROE > 10%) -> Trailing con ATR ---
        if delta_pct >= 0.10: 
            atr = estrategia.calcular_atr(periodo=14) 
            
            if atr > 0:
                distancia = 2 * atr # Distancia de 2 ATRs
                
                if lado == 'buy':
                    target = mark_price - distancia
                    if target > sl_actual: # Solo subir
                        nuevo_sl = target
                        motivo = f"Trailing ATR (ROE {delta_pct*100:.1f}%)"
                else: # Short
                    target = mark_price + distancia
                    if target < sl_actual: # Solo bajar
                        nuevo_sl = target
                        motivo = f"Trailing ATR (ROE {delta_pct*100:.1f}%)"
        
        # --- FASE 2: ASEGURAMIENTO (ROE > 7%) -> Breakeven ---
        elif delta_pct >= 0.07:
            margen = entry_price * 0.001 # +0.1% para cubrir comisiones
            
            if lado == 'buy':
                target = entry_price + margen
                if target > sl_actual: 
                    nuevo_sl = target
                    motivo = "Breakeven"
            else:
                target = entry_price - margen
                if target < sl_actual: 
                    nuevo_sl = target
                    motivo = "Breakeven"

        # Ejecutar modificación
        if nuevo_sl:
            print(f"{Fore.CYAN}🚀 {motivo}: Moviendo SL de {sl_actual} a {nuevo_sl}")
            self.gestor_ejecucion.modificar_stop_loss(simbolo, orden_sl['id'], nuevo_sl)

            # [LOG CSV] Registrar el Movimiento
            TradeLogger.registrar(simbolo, "TRAILING_UPDATE", nuevo_sl, f"{motivo} (Antes: {sl_actual})")


    def gestionar_ejecucion(self, simbolo, senal, estrategia):
        if estrategia.posicion_abierta: return 

        lado = "buy" if senal == "COMPRA" else "sell"
        config_cantidad = self.config_pares[simbolo].get('cantidad_operacion', 0)
        
        # --- NUEVO: Obtener Apalancamiento Configurado ---
        apalancamiento = self.config_pares[simbolo].get('apalancamiento', 1) 
        
        precio_actual = self.gestor_datos.obtener_precio(simbolo)
        
        # Calcular Cantidad
        if isinstance(config_cantidad, str) and '%' in config_cantidad:
            # --- MODIFICADO: Pasamos el apalancamiento ---
            cantidad_final = self.gestor_ejecucion.calcular_cantidad_por_porcentaje(
                simbolo, config_cantidad, precio_actual, apalancamiento
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
            
            # [LOG CSV] Registrar Entrada
            TradeLogger.registrar(simbolo, f"ENTRADA_{lado.upper()}", precio_fill, f"Cant: {cantidad_final} | Lev: {apalancamiento}x")

            # --- PROTECCIONES INICIALES ---
            config_global = Config.cargar_configuracion()
            riesgo = config_global.get('sistema_riesgo', {})
            sl_pct = riesgo.get('stop_loss_pct', 0.02)
            
            print(f"🛡️ Colocando SL Inicial ({sl_pct*100}%) y TP Extendido (50%)")

            self.gestor_ejecucion.colocar_ordenes_salida(
                simbolo=simbolo,
                lado_entrada=lado,
                cantidad=cantidad_final,
                precio_entrada=precio_fill,
                sl_pct=sl_pct,
                tp_pct=0.50 
            )

            # [LOG CSV] Registrar SL Inicial
            precio_sl_inicial = precio_fill * (1 - sl_pct) if lado == 'buy' else precio_fill * (1 + sl_pct)
            TradeLogger.registrar(simbolo, "SL_INICIAL", precio_sl_inicial, f"Distancia: {sl_pct*100}%")

        else:
            print(Fore.RED + "❌ ERROR AL ENTRAR.")

    def detener(self):
        print(Fore.YELLOW + "\n🛑 Deteniendo sistema...")
        self.gestor_datos.detener_todo()