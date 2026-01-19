import time
import pandas as pd
from colorama import Fore, Style

# Módulos del sistema
from Core.Utils.Config import Config
from Core.API.GestorHibrido import GestorHibrido
from Core.Ejecucion.GestorEjecucion import GestorEjecucion 
from Core.Utils.TradeLogger import TradeLogger 
from Core.Utils.GestorPrediccion import GestorPrediccion

# Estrategias
from Estrategias.Concretas.EstrategiaRSI import EstrategiaRSI
from Estrategias.Concretas.EstrategiaRSI_ADX import EstrategiaRSI_ADX

class BotController:
    """
    ORQUESTADOR FINAL V2.9.3 (ESTABLE)
    - Integración ML con Traductor de Datos.
    - Limpieza de Órdenes Fantasma (Ghost Buster).
    - Fail-Safe activado.
    """
    
    def __init__(self):
        print(Fore.YELLOW + "🤖 Inicializando BotController v2.9.3 (FINAL)...")
        
        self.mostrar_dashboard = False 

        self.catalogo_estrategias = { 
            "EstrategiaRSI": EstrategiaRSI,
            "EstrategiaRSI_ADX": EstrategiaRSI_ADX
        }
        
        self.gestor_datos = GestorHibrido()
        self.gestor_ejecucion = GestorEjecucion()
        self.gestor_prediccion = GestorPrediccion()
        
        self.estrategias_activas = {} 
        self.config_pares = {} 
        self.config_global = {} 
        
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

        estrategia = self.estrategias_activas.get(simbolo)
        if not estrategia: return

        total_abiertas = sum(1 for e in self.estrategias_activas.values() if e.posicion_abierta)
        limite_trades = self.config_global.get('max_trades_abiertos', 5)
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
        if estrategia.posicion_abierta: return 

        lado = "buy" if senal == "COMPRA" else "sell"
        config_cantidad = self.config_pares[simbolo].get('cantidad_operacion', 0)
        apalancamiento = self.config_pares[simbolo].get('apalancamiento', 1) 
        
        # ============================================================
        # 🧠 FILTRO 2: MACHINE LEARNING (CON TRADUCTOR DE DATOS)
        # ============================================================
        print(f"🤖 Estrategia Técnica sugiere: {senal}. Consultando al ML...")
        
        raw_velas = self.gestor_datos.obtener_velas_historicas(simbolo, self.config_pares[simbolo]['timeframe'], limite=200)
        df_velas_recientes = None
        
        try:
            if isinstance(raw_velas, list):
                if not raw_velas: 
                    print(Fore.YELLOW + "⚠️ Data insuficiente para ML (Lista vacía).")
                    return # Bloqueo

                # CASO A: Lista de Listas (Standard CCXT)
                if isinstance(raw_velas[0], list):
                    df_velas_recientes = pd.DataFrame(
                        raw_velas, 
                        columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
                    )
                
                # CASO B: Lista de Dicts (Binance Raw)
                elif isinstance(raw_velas[0], dict):
                    df_velas_recientes = pd.DataFrame(raw_velas)
                    # Normalizamos columnas
                    df_velas_recientes.columns = [x.lower() for x in df_velas_recientes.columns]
                    # TRADUCTOR AUTOMÁTICO
                    mapeo = {
                        't': 'timestamp', 'o': 'open', 'h': 'high', 
                        'l': 'low', 'c': 'close', 'v': 'volume',
                    }
                    df_velas_recientes.rename(columns=mapeo, inplace=True)
            
            elif isinstance(raw_velas, pd.DataFrame):
                df_velas_recientes = raw_velas.copy()
                df_velas_recientes.columns = [x.lower() for x in df_velas_recientes.columns]
                # Traductor preventivo
                mapeo = {'t': 'timestamp', 'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close', 'v': 'volume'}
                df_velas_recientes.rename(columns=mapeo, inplace=True)

            # CONVERSIÓN A NUMÉRICO (Vital para evitar errores de tipo 'str')
            if df_velas_recientes is not None:
                cols_num = ['open', 'high', 'low', 'close', 'volume']
                for c in cols_num:
                    if c in df_velas_recientes.columns:
                        df_velas_recientes[c] = pd.to_numeric(df_velas_recientes[c], errors='coerce')

            # VALIDACIÓN Y PREDICCIÓN
            if df_velas_recientes is not None and not df_velas_recientes.empty:
                cols_req = ['close', 'high', 'low', 'volume']
                if not all(col in df_velas_recientes.columns for col in cols_req):
                    print(Fore.RED + f"⛔ Error Data: Faltan columnas tras traducción. Vistas: {list(df_velas_recientes.columns)}")
                    return # Bloqueo

                ml_aprueba = self.gestor_prediccion.predecir_exito(simbolo, df_velas_recientes)
                
                if not ml_aprueba:
                    print(Fore.LIGHTRED_EX + f"⛔ ML FILTRO: Operación cancelada por baja probabilidad en {simbolo}.")
                    return # Bloqueo Estratégico
            else:
                print(Fore.RED + "⛔ Error: No se pudo generar DataFrame válido para ML.")
                return # Bloqueo Técnico

        except Exception as e:
            print(Fore.RED + f"❌ Excepción crítica en preparación de datos ML: {e}")
            return # Bloqueo Total

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