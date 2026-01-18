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
    ORQUESTADOR FINAL V2.7
    - ROE Corregido (Apalancamiento)
    - Semáforo de Límite de Posiciones
    - Validación Periódica con Binance (Anti-Desync)
    """
    
    def __init__(self):
        print(Fore.YELLOW + "🤖 Inicializando BotController v2.7 (FULL SAFE)...")
        
        self.catalogo_estrategias = { 
            "EstrategiaRSI": EstrategiaRSI,
            "EstrategiaRSI_ADX": EstrategiaRSI_ADX
        }
        
        self.gestor_datos = GestorHibrido()
        self.gestor_ejecucion = GestorEjecucion()
        
        self.estrategias_activas = {} 
        self.config_pares = {} 
        self.config_global = {} 
        
        # --- NUEVO: Variables para validación periódica ---
        self.ultima_validacion = time.time()
        self.intervalo_validacion = 300  # 5 minutos (300 segundos)

        self.cargar_estrategias_desde_config()

    def cargar_estrategias_desde_config(self):
        full_config = Config.cargar_configuracion()
        self.config_global = full_config.get('configuracion_global', {})
        self.config_pares = full_config.get('pares', {})
        
        print(f"⚙️ Configurando {len(self.config_pares)} pares activos...")
        
        for par, cfg in self.config_pares.items():
            if not cfg.get('activo', False): continue

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

        # 1. Sincronización Inicial Estricta
        try:
            activos_reales = self.gestor_ejecucion.obtener_todos_simbolos_con_posicion()
        except:
            activos_reales = []

        for par, estrategia in self.estrategias_activas.items():
            # A. Configurar Apalancamiento
            lev = self.config_pares[par].get('apalancamiento', 1)
            self.gestor_ejecucion.configurar_apalancamiento(par, lev)

            # B. Sincronización de Estado (Usando la lista masiva)
            esta_dentro = par in activos_reales
            estrategia.posicion_abierta = esta_dentro
            
            estado_str = f"{Fore.RED}OCUPADO{Fore.CYAN}" if esta_dentro else f"{Fore.GREEN}LIBRE{Fore.CYAN}"
            print(f"   👁️ {par}: {estado_str}")

            # C. Descargar Historial
            tf = self.config_pares[par]['timeframe']
            print(f"   📥 Historial {par} ({tf})...", end="\r")
            
            historial = self.gestor_datos.obtener_velas_historicas(par, tf, limite=1000)
            for kline in historial:
                # En carga inicial calculamos todo para tener los indicadores listos
                estrategia.recibir_vela(par, kline, ejecutar_analisis=True)
            
            print(f"   ✅ {par}: {len(historial)} velas.")

        print(Fore.GREEN + "✨ Todo sincronizado.\n")

        self.gestor_datos.iniciar_flujo_hibrido(
            estrategias_dict=self.config_pares,
            callback_kline=self.procesar_vela
        )
        print(Fore.GREEN + "🚀 Bot Operativo y Vigilando.")

    def validar_sincronizacion_periodica(self):
        """
        Mecanismo de seguridad: Cada 5 min consulta a Binance la verdad absoluta.
        """
        if time.time() - self.ultima_validacion > self.intervalo_validacion:
            print(Fore.YELLOW + "🕵️ Ejecutando validación periódica de posiciones...")
            
            try:
                # Obtenemos la verdad de Binance
                simbolos_en_exchange = self.gestor_ejecucion.obtener_todos_simbolos_con_posicion()
                
                cambios = 0
                for par, estrategia in self.estrategias_activas.items():
                    estado_memoria = estrategia.posicion_abierta
                    estado_real = par in simbolos_en_exchange
                    
                    if estado_memoria != estado_real:
                        print(f"{Fore.MAGENTA}⚠️ CORRECCIÓN {par}: Memoria({estado_memoria}) -> Real({estado_real})")
                        estrategia.posicion_abierta = estado_real
                        cambios += 1
                
                if cambios == 0:
                    print(Fore.GREEN + "✅ Sincronización correcta. Todo en orden.")
                
            except Exception as e:
                print(Fore.RED + f"❌ Error en validación periódica: {e}")
            
            self.ultima_validacion = time.time()

    def procesar_vela(self, simbolo, kline_data):
        """
        Ciclo Principal: Validación -> Semáforo -> Estrategia -> Ejecución
        """
        # 1. Ejecutar validación de seguridad si toca
        self.validar_sincronizacion_periodica()

        estrategia = self.estrategias_activas.get(simbolo)
        if not estrategia: return

        # 2. SEMÁFORO DE POSICIONES
        total_abiertas = sum(1 for e in self.estrategias_activas.values() if e.posicion_abierta)
        limite_trades = self.config_global.get('max_trades_abiertos', 5)
        
        # Si NO estoy dentro Y ya no hay cupo -> Hibernar
        en_hibernacion = (not estrategia.posicion_abierta) and (total_abiertas >= limite_trades)

        # 3. GESTIÓN DE SALIDA (Trailing Stop)
        # Prioridad absoluta: Si estoy dentro, gestiono la salida independientemente del límite
        if estrategia.posicion_abierta:
            if kline_data['x']: # Cierre de vela
                # Chequeo rápido de seguridad
                sigue_abierta = self.gestor_ejecucion.obtener_posicion_abierta(simbolo)
                if not sigue_abierta:
                    # Si Binance dice que cerró (SL o TP hit), liberamos memoria
                    print(f"{Fore.YELLOW}🔓 Posición cerrada externamente en {simbolo}.")
                    estrategia.posicion_abierta = False
                    return

                datos_pos = self.gestor_ejecucion.obtener_datos_posicion(simbolo)
                if datos_pos:
                    self.aplicar_trailing_stop(simbolo, estrategia, datos_pos)
        
        # 4. PROCESAR ESTRATEGIA
        # Si estamos hibernando, 'ejecutar_analisis=False' ahorra CPU
        senal = estrategia.recibir_vela(simbolo, kline_data, ejecutar_analisis=not en_hibernacion)

        if en_hibernacion:
            return # No hacemos nada más si no hay cupo

        # 5. GESTIÓN DE ENTRADA
        if not estrategia.posicion_abierta:
            if senal in ["COMPRA", "VENTA"]:
                # Doble check del semáforo antes de disparar dinero real
                if total_abiertas < limite_trades:
                    self.gestionar_ejecucion(simbolo, senal, estrategia)
                else:
                    print(f"{Fore.LIGHTBLACK_EX}⛔ Señal ignorada en {simbolo}: Límite alcanzado ({total_abiertas}/{limite_trades})")


    def aplicar_trailing_stop(self, simbolo, estrategia, datos_pos):
        """
        Trailing Stop con ROE REAL (Corregido).
        """
        entry_price = datos_pos['entryPrice']
        mark_price = datos_pos['markPrice']
        lado = datos_pos['side']
        lev = self.config_pares[simbolo].get('apalancamiento', 1)

        # 1. Calcular Delta Porcentual del Precio
        if lado == 'buy':
            delta_precio = (mark_price - entry_price) / entry_price
        else:
            delta_precio = (entry_price - mark_price) / entry_price

        # 2. CALCULAR ROE REAL (Delta * Leverage)
        roe_real = delta_precio * lev 

        orden_sl = self.gestor_ejecucion.obtener_orden_stop_loss(simbolo)
        if not orden_sl: return
        sl_actual = float(orden_sl['stopPrice'])
        
        nuevo_sl = None
        motivo = ""

        # --- FASE A: MAXIMIZACIÓN (ROE > 10%) -> Trailing con ATR ---
        if roe_real >= 0.10: 
            atr = estrategia.calcular_atr(periodo=14) 
            if atr > 0:
                distancia = 2 * atr 
                if lado == 'buy':
                    target = mark_price - distancia
                    if target > sl_actual:
                        nuevo_sl = target
                        motivo = f"Trailing ATR (ROE {roe_real*100:.1f}%)"
                else:
                    target = mark_price + distancia
                    if target < sl_actual:
                        nuevo_sl = target
                        motivo = f"Trailing ATR (ROE {roe_real*100:.1f}%)"
        
        # --- FASE B: BREAKEVEN (ROE > 5%) ---
        elif roe_real >= 0.05:
            # Cubrir fees (aprox 0.15% del precio base suele ser seguro)
            margen_fee = entry_price * 0.0015 
            
            if lado == 'buy':
                target = entry_price + margen_fee
                if target > sl_actual: 
                    nuevo_sl = target
                    motivo = f"Breakeven (ROE {roe_real*100:.1f}%)"
            else:
                target = entry_price - margen_fee
                if target < sl_actual: 
                    nuevo_sl = target
                    motivo = f"Breakeven (ROE {roe_real*100:.1f}%)"

        if nuevo_sl:
            print(f"{Fore.CYAN}🚀 {motivo}: Moviendo SL de {sl_actual} a {nuevo_sl}")
            self.gestor_ejecucion.modificar_stop_loss(simbolo, orden_sl['id'], nuevo_sl)
            TradeLogger.registrar(simbolo, "TRAILING_UPDATE", nuevo_sl, f"{motivo}")


    def gestionar_ejecucion(self, simbolo, senal, estrategia):
        if estrategia.posicion_abierta: return 

        lado = "buy" if senal == "COMPRA" else "sell"
        config_cantidad = self.config_pares[simbolo].get('cantidad_operacion', 0)
        
        # Obtener Apalancamiento Configurado
        apalancamiento = self.config_pares[simbolo].get('apalancamiento', 1) 
        
        precio_actual = self.gestor_datos.obtener_precio(simbolo)
        
        # Calcular Cantidad
        if isinstance(config_cantidad, str) and '%' in config_cantidad:
            cantidad_final = self.gestor_ejecucion.calcular_cantidad_por_porcentaje(
                simbolo, config_cantidad, precio_actual, apalancamiento
            )
        else:
            cantidad_final = float(config_cantidad)

        if cantidad_final <= 0: return

        print(f"{Fore.MAGENTA}⚡ ALERTA: {lado.upper()} {simbolo} (Cant: {cantidad_final})...")
        
        # Ejecutar Entrada
        orden = self.gestor_ejecucion.colocar_orden_mercado(simbolo, lado, cantidad_final)
        
        if orden:
            estrategia.posicion_abierta = True
            precio_fill = float(orden.get('average', 0.0))
            if precio_fill == 0.0: precio_fill = precio_actual
            
            print(f"{Fore.GREEN}✅ ENTRADA CONFIRMADA: {simbolo} | Precio: {precio_fill}")
            
            # [LOG CSV] Registrar Entrada
            TradeLogger.registrar(simbolo, f"ENTRADA_{lado.upper()}", precio_fill, f"Cant: {cantidad_final} | Lev: {apalancamiento}x")

            # --- PROTECCIONES INICIALES ---
            # Recargamos config por seguridad para tener el riesgo fresco
            full_conf = Config.cargar_configuracion()
            riesgo = full_conf.get('sistema_riesgo', {})
            sl_pct = riesgo.get('stop_loss_pct', 0.02)
            tp_pct = riesgo.get('take_profit_pct', 0.50)

            print(f"🛡️ Colocando SL Inicial ({sl_pct*100}%) y TP...")

            self.gestor_ejecucion.colocar_ordenes_salida(
                simbolo=simbolo,
                lado_entrada=lado,
                cantidad=cantidad_final,
                precio_entrada=precio_fill,
                sl_pct=sl_pct,
                tp_pct=tp_pct 
            )

            # [LOG CSV] Registrar SL Inicial (AQUÍ ESTÁ LA LÍNEA QUE FALTABA)
            precio_sl_inicial = precio_fill * (1 - sl_pct) if lado == 'buy' else precio_fill * (1 + sl_pct)
            TradeLogger.registrar(simbolo, "SL_INICIAL", precio_sl_inicial, f"Distancia: {sl_pct*100}%")

        else:
            print(Fore.RED + "❌ ERROR AL ENTRAR.")
            
    def detener(self):
        print(Fore.YELLOW + "\n🛑 Deteniendo sistema...")
        self.gestor_datos.detener_todo()