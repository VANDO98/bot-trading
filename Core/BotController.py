import time
import pandas as pd
from colorama import Fore, Style
import json

# Módulos del sistema
from Core.Utils.Config import Config
from Core.API.GestorHibrido import GestorHibrido
from Core.Ejecucion.GestorEjecucion import GestorEjecucion 
from Core.Utils.TradeLogger import TradeLogger 
from Core.Utils.GestorPrediccion import GestorPrediccion

# Modo Paper Trading (opcional)
from Core.Ejecucion.GestorEjecucionPaper import GestorEjecucionPaper

# Estrategias
#from Estrategias.Concretas.EstrategiaRSI import EstrategiaRSI
#from Estrategias.Concretas.EstrategiaRSI_ADX import EstrategiaRSI_ADX
from Estrategias.Selector import Selector 


class BotController:
    """
    ORQUESTADOR FINAL V2.9.3 (ESTABLE)
    - Integración ML con Traductor de Datos.
    - Limpieza de Órdenes Fantasma (Ghost Buster).
    - Fail-Safe activado.
    """
    
    def __init__(self):
        print(Fore.YELLOW + "🤖 Inicializando BotController v2.9.3 (FINAL)...")
        
        self.mostrar_dashboard = True #False para iniciar sin dashboard

        # Catálogo de Estrategias desde el Selector (Factory Pattern)
        
        # =======================================================
        # 1. CARGA DE CONFIGURACIÓN (PRIMERO QUE TODO)
        # =======================================================
        # [CRÍTICO] Esto actualiza Config.USAR_TESTNET antes de conectar nada
        full_config = Config.cargar_configuracion()
        self.config_global = full_config.get('configuracion_global', {})
        self.config_pares = {} 

        # =======================================================
        # 2. CONEXIÓN DE DATOS (GESTOR HÍBRIDO)
        # =======================================================
        # Ahora GestorHibrido leerá el valor correcto (False/Mainnet)
        self.gestor_datos = GestorHibrido()
        
        # =======================================================
        # 3. SELECCIÓN DE MOTOR DE EJECUCIÓN (REAL vs PAPER)
        # =======================================================
        modo = self.config_global.get('modo_ejecucion', 'testnet')
        
        if modo == 'paper':
            print(Fore.MAGENTA + "📝 Modo PAPER TRADING detectado. Usando motor simulado.")
            self.gestor_ejecucion = GestorEjecucionPaper(self.gestor_datos)
        else:
            print(Fore.CYAN + "💳 Modo EXCHANGE detectado. Usando motor de ejecución real.")
            self.gestor_ejecucion = GestorEjecucion()
        # --------------------------------------------------------

        self.gestor_prediccion = GestorPrediccion()
        
        self.estrategias_activas = {} 
        # self.config_pares se llenará en el método cargar_estrategias
        
        self.ultima_validacion = time.time()
        self.intervalo_validacion = 300 

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
            
            # --- CAMBIO CLAVE: USAR EL SELECTOR ---
            instancia = Selector.obtener_estrategia(nombre_clase, par, params)
            
            if instancia:
                self.estrategias_activas[par] = instancia
                print(f"   ✅ {par} -> Lista ({nombre_clase})")
            else:
                print(f"   ⚠️ {par} -> Estrategia no encontrada, omitiendo.")

    def iniciar(self):
        if not self.estrategias_activas:
            print(Fore.RED + "❌ No hay estrategias. Abortando.")
            return

        print(Fore.CYAN + "\n🔥 Iniciando Sincronización y Pre-Carga...")

        try:
            activos_reales = self.gestor_ejecucion.obtener_todos_simbolos_con_posicion()
        except:
            activos_reales = []

        for par, estrategia in self.estrategias_activas.items():
            lev = self.config_pares[par].get('apalancamiento', 1)
            self.gestor_ejecucion.configurar_apalancamiento(par, lev)

            esta_dentro = par in activos_reales
            estrategia.posicion_abierta = esta_dentro
            
            estado_str = f"{Fore.RED}OCUPADO{Fore.CYAN}" if esta_dentro else f"{Fore.GREEN}LIBRE{Fore.CYAN}"
            print(f"   👁️ {par}: {estado_str}")

            # Limpieza inicial preventiva
            if not esta_dentro:
                self.gestor_ejecucion.cancelar_ordenes_pendientes(par)

            tf = self.config_pares[par]['timeframe']
            print(f"   📥 Historial {par} ({tf})...", end="\r")
            
            historial = self.gestor_datos.obtener_velas_historicas(par, tf, limite=1000)
            for kline in historial:
                estrategia.recibir_vela(par, kline, ejecutar_analisis=True)
            
            print(f"   ✅ {par}: {len(historial)} velas.")

        print(Fore.GREEN + "✨ Todo sincronizado.\n")

        self.gestor_datos.iniciar_flujo_hibrido(
            estrategias_dict=self.config_pares,
            callback_kline=self.procesar_vela
        )
        print(Fore.GREEN + "🚀 Bot Operativo y Vigilando.")

    def validar_sincronizacion_periodica(self):
        if time.time() - self.ultima_validacion > self.intervalo_validacion:
            print(Fore.YELLOW + "🕵️ Ejecutando validación periódica (Ghost Buster)...")
            try:
                simbolos_en_exchange = self.gestor_ejecucion.obtener_todos_simbolos_con_posicion()
                cambios = 0
                for par, estrategia in self.estrategias_activas.items():
                    estado_memoria = estrategia.posicion_abierta
                    estado_real = par in simbolos_en_exchange
                    
                    if estado_memoria != estado_real:
                        print(f"{Fore.MAGENTA}⚠️ CORRECCIÓN {par}: Memoria({estado_memoria}) -> Real({estado_real})")
                        estrategia.posicion_abierta = estado_real
                        cambios += 1
                    
                    # Limpieza incondicional si no hay posición
                    if not estado_real:
                        self.gestor_ejecucion.cancelar_ordenes_pendientes(par)
                
                if cambios == 0:
                    print(Fore.GREEN + "✅ Sincronización OK. Área limpia.")
                    
            except Exception as e:
                print(Fore.RED + f"❌ Error en validación periódica: {e}")
            
            self.ultima_validacion = time.time()

    def procesar_vela(self, simbolo, kline_data):
        self.validar_sincronizacion_periodica()

        # ============================================================
        # 🧪 BLOQUE PAPER TRADING (SIMULACIÓN EN VIVO)
        # ============================================================
        # Como no hay órdenes reales en Binance, nosotros debemos 
        # verificar manualmente si el precio tocó el SL o TP.
        if isinstance(self.gestor_ejecucion, GestorEjecucionPaper):
             self.gestor_ejecucion.chequear_cierres(simbolo)
        # ============================================================

        estrategia = self.estrategias_activas.get(simbolo)
        if not estrategia: return

        total_abiertas = sum(1 for e in self.estrategias_activas.values() if e.posicion_abierta)
        limite_trades = self.config_global.get('max_trades_abiertos', 5)
        # Hibernamos si estamos llenos y esta estrategia no tiene posición
        en_hibernacion = (not estrategia.posicion_abierta) and (total_abiertas >= limite_trades)

        if estrategia.posicion_abierta:
            if kline_data['x']: 
                sigue_abierta = self.gestor_ejecucion.obtener_posicion_abierta(simbolo)
                if not sigue_abierta:
                    print(f"{Fore.YELLOW}🔓 Posición cerrada externamente en {simbolo}.")
                    estrategia.posicion_abierta = False
                    self.gestor_ejecucion.cancelar_ordenes_pendientes(simbolo)
                    return 

                datos_pos = self.gestor_ejecucion.obtener_datos_posicion(simbolo)
                if datos_pos:
                    self.aplicar_trailing_stop(simbolo, estrategia, datos_pos)
        
        # Enviamos la vela a la estrategia (técnica)
        senal = estrategia.recibir_vela(simbolo, kline_data, ejecutar_analisis=not en_hibernacion)

        if en_hibernacion: return 

        if not estrategia.posicion_abierta:
            if senal in ["COMPRA", "VENTA"]:
                if total_abiertas < limite_trades:
                    self.gestionar_ejecucion(simbolo, senal, estrategia)
                else:
                    print(f"{Fore.LIGHTBLACK_EX}⛔ Señal ignorada en {simbolo}: Límite alcanzado ({total_abiertas}/{limite_trades})")

    def aplicar_trailing_stop(self, simbolo, estrategia, datos_pos):
        entry_price = datos_pos['entryPrice']
        mark_price = datos_pos['markPrice']
        lado = datos_pos['side']
        lev = self.config_pares[simbolo].get('apalancamiento', 1)

        if lado == 'buy':
            delta_precio = (mark_price - entry_price) / entry_price
        else:
            delta_precio = (entry_price - mark_price) / entry_price

        roe_real = delta_precio * lev 
        orden_sl = self.gestor_ejecucion.obtener_orden_stop_loss(simbolo)
        if not orden_sl: return
        sl_actual = float(orden_sl['stopPrice'])
        
        nuevo_sl = None
        motivo = ""

        if roe_real >= 0.10: 
            atr = estrategia.calcular_atr(periodo=14) 
            if atr > 0:
                distancia_atr = 2 * atr 
                margen_fee = entry_price * 0.0015 
                if lado == 'buy':
                    target_atr = mark_price - distancia_atr
                    target_be = entry_price + margen_fee
                    target_final = max(target_atr, target_be)
                    if target_final > sl_actual:
                        nuevo_sl = target_final
                        motivo = f"Trailing Dinámico (ROE {roe_real*100:.1f}%)"
                else: 
                    target_atr = mark_price + distancia_atr
                    target_be = entry_price - margen_fee
                    target_final = min(target_atr, target_be)
                    if target_final < sl_actual:
                        nuevo_sl = target_final
                        motivo = f"Trailing Dinámico (ROE {roe_real*100:.1f}%)"
        
        elif roe_real >= 0.05:
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
            distancia_seguridad = mark_price * 0.002 
            es_seguro = False
            if lado == 'buy':
                if nuevo_sl < (mark_price - distancia_seguridad): es_seguro = True
            else:
                if nuevo_sl > (mark_price + distancia_seguridad): es_seguro = True
            
            if es_seguro:
                print(f"{Fore.CYAN}🚀 {motivo}: Moviendo SL de {sl_actual} a {nuevo_sl}")
                self.gestor_ejecucion.modificar_stop_loss(simbolo, orden_sl['id'], nuevo_sl, lado)
                TradeLogger.registrar(simbolo, "TRAILING_UPDATE", nuevo_sl, f"{motivo}")

    def gestionar_ejecucion(self, simbolo, senal, estrategia):
        """
        Maneja la ejecución de órdenes con filtro de Machine Learning.
        """
        if estrategia.posicion_abierta: return 

        lado = "buy" if senal == "COMPRA" else "sell"
        
        # Datos del Config
        cfg_par = self.config_pares[simbolo] # <--- Obtenemos la config completa
        config_cantidad = cfg_par.get('cantidad_operacion', 0)
        apalancamiento = cfg_par.get('apalancamiento', 1) 
        
        # ============================================================
        # 🧠 FILTRO 2: MACHINE LEARNING (EVOLUTIVO V3)
        # ============================================================
        print(f"🤖 Estrategia Técnica sugiere: {senal}. Consultando al ML...")
        
        try:
            if estrategia.velas is None or estrategia.velas.empty:
                print(Fore.RED + "⛔ Error Data: La estrategia no tiene velas en memoria.")
                return 

            # Validación de cantidad mínima de datos (para EMA 200, etc.)
            if len(estrategia.velas) < 200:
                print(Fore.YELLOW + f"⚠️ Data insuficiente en memoria ({len(estrategia.velas)} velas).")
                return 

            # --- CAMBIO CRÍTICO AQUÍ ---
            # Pasamos 'cfg_par' que contiene timeframe, estrategia y parámetros
            ml_aprueba = self.gestor_prediccion.predecir_exito(
                simbolo, 
                estrategia.velas.copy(),
                cfg_par 
            )
            
            if not ml_aprueba:
                print(Fore.LIGHTRED_EX + f"⛔ ML FILTRO: Operación cancelada por riesgo alto en {simbolo}.")
                return 

        except Exception as e:
            print(Fore.RED + f"❌ Excepción crítica en ML: {e}")
            return 

        # ============================================================
        # 🚀 EJECUCIÓN (Si ML aprueba)
        # ============================================================
        precio_actual = self.gestor_datos.obtener_precio(simbolo)
        
        if isinstance(config_cantidad, str) and '%' in config_cantidad:
            cantidad_final = self.gestor_ejecucion.calcular_cantidad_por_porcentaje(
                simbolo, config_cantidad, precio_actual, apalancamiento
            )
        else:
            cantidad_final = float(config_cantidad)

        if cantidad_final <= 0: return

        print(f"{Fore.MAGENTA}⚡ ALERTA: {lado.upper()} {simbolo} (Cant: {cantidad_final})...")
        
        orden = self.gestor_ejecucion.colocar_orden_mercado(simbolo, lado, cantidad_final)
        
        if orden:
            estrategia.posicion_abierta = True
            precio_fill = float(orden.get('average', 0.0))
            if precio_fill == 0.0: precio_fill = precio_actual
            
            print(f"{Fore.GREEN}✅ ENTRADA CONFIRMADA: {simbolo} | Precio: {precio_fill}")
            TradeLogger.registrar(simbolo, f"ENTRADA_{lado.upper()}", precio_fill, f"Cant: {cantidad_final} | Lev: {apalancamiento}x")

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

            precio_sl_inicial = precio_fill * (1 - sl_pct) if lado == 'buy' else precio_fill * (1 + sl_pct)
            TradeLogger.registrar(simbolo, "SL_INICIAL", precio_sl_inicial, f"Distancia: {sl_pct*100}%")

        else:
            print(Fore.RED + "❌ ERROR AL ENTRAR.")

    def detener(self):
        print(Fore.YELLOW + "\n🛑 Deteniendo sistema...")
        self.gestor_datos.detener_todo()

    # --- AGREGAR ESTE MÉTODO AL FINAL DE LA CLASE ---
    def actualizar_umbral_ml(self, nuevo_valor):
        """
        Actualiza el ml_threshold en memoria y en el archivo JSON
        para que persista y sea leído por GestorPrediccion.
        """
        try:
            # 1. Definir ruta del archivo
            ruta_config = "config_trading.json"
            
            # 2. Cargar config actual
            with open(ruta_config, 'r') as f:
                data = json.load(f)
            
            # 3. Modificar valor
            if 'sistema_riesgo' not in data:
                data['sistema_riesgo'] = {}
            
            valor_anterior = data['sistema_riesgo'].get('ml_threshold', 0.0)
            data['sistema_riesgo']['ml_threshold'] = float(nuevo_valor)
            
            # 4. Guardar cambios en disco
            with open(ruta_config, 'w') as f:
                json.dump(data, f, indent=2)
                
            print(f"✅ Configuración actualizada: ML Threshold {valor_anterior} -> {nuevo_valor}")
            return True, valor_anterior
            
        except Exception as e:
            print(f"❌ Error guardando config: {e}")
            return False, str(e)