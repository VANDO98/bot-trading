import os
import time
import pandas as pd
from colorama import init, Fore, Style, Back

class Dashboard:
    def __init__(self, bot_controller):
        """
        Clase encargada exclusivamente de la visualización en consola.
        Recibe la instancia del bot para leer sus datos en tiempo real.
        """
        init(autoreset=True)
        self.bot = bot_controller
        self.ancho = 160 
        self.inicio = time.time()  # Hora de inicio del dashboard
        self.last_action_cache = "" # Cache para la última acción

    def _limpiar_pantalla(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def _formatear_precio(self, precio):
        if precio < 1.0: return f"{precio:.5f}"
        if precio < 100: return f"{precio:.3f}"
        return f"{precio:.2f}"

    def _obtener_color_rsi(self, rsi_val, sobreventa, sobrecompra):
        if rsi_val <= sobreventa: return Fore.GREEN + Style.BRIGHT
        elif rsi_val >= sobrecompra: return Fore.RED + Style.BRIGHT
        else: return Fore.WHITE

    def _obtener_color_adx(self, adx_val, minimo):
        if adx_val >= minimo: return Fore.GREEN + Style.BRIGHT
        return Fore.LIGHTBLACK_EX 

    def _leer_ultima_accion(self):
        """Lee la última línea del CSV de historial para el footer."""
        try:
            ruta_csv = os.path.join(os.getcwd(), 'historial_trading.csv')
            if os.path.exists(ruta_csv):
                with open(ruta_csv, 'rb') as f:
                    f.seek(-1024, os.SEEK_END) # Ir al final (aprox)
                    last = f.readlines()[-1].decode('utf-8').strip()
                    # Parsear para mostrar bonito: FECHA, PAR, ACCION
                    parts = last.split(',')
                    if len(parts) >= 3:
                        return f"[{parts[0]}] {parts[1]} -> {parts[2]} ({parts[3]})"
                    return last
            return "Sin actividad reciente."
        except:
            return "Sin datos."
            
    def _calcular_countdown(self):
        """Calcula tiempo restante para cierre de vela (estimado)."""
        # Tomamos el timeframe del primer par activo como referencia
        if not self.bot.config_pares: return "N/A"
        
        # Asumimos que todos van sincronizados o tomamos el primero
        par_ref = list(self.bot.config_pares.keys())[0]
        tf_str = self.bot.config_pares[par_ref].get('timeframe', '1h')
        
        # Convertir tf a segundos
        tf_map = {'1m': 60, '3m': 180, '5m': 300, '15m': 900, '1h': 3600, '4h': 14400}
        secs = tf_map.get(tf_str, 3600)
        
        # Calculo remanente actual
        now_ts = time.time()
        remanente = secs - (now_ts % secs)
        mins = int(remanente // 60)
        segs = int(remanente % 60)
        
        # Color rojo si queda poco
        color = Fore.RED if remanente < 60 else Fore.CYAN
        return f"{color}{mins:02d}m {segs:02d}s"

    def mostrar(self):
        """Renderiza la tabla completa."""
        self._limpiar_pantalla()
        
        # --- METRICAS HEADER ---
        uptime_sec = time.time() - self.inicio
        h = int(uptime_sec // 3600)
        m = int((uptime_sec % 3600) // 60)
        uptime_str = f"{h}h {m}m"
        
        # Balance (Cacheado o Directo si es rápido)
        bal = self.bot.gestor_ejecucion.obtener_balance_usdt()
        
        # Ping Estimado (Simulado o real si tuvieramos timestamp de ws)
        # Usamos time.time() rapidito
        t0 = time.time()
        # Ping falso/rápido para no bloquear (o podriamos usar latency del WS si GestorDatos lo expone)
        # Por ahora mostramos latencia interna de renderizado
        ping = int((time.time() - t0) * 1000) 
        
        countdown = self._calcular_countdown()
        
        # Header Mejorado
        header_txt = f" 🤖 BOT V3.4 | ⏱️ Up: {uptime_str} | 💰 Bal: ${bal:.2f} | 🕒 Vela: {countdown} "
        print(Back.BLUE + Fore.WHITE + header_txt.center(self.ancho))
        print(Back.BLACK + "-" * self.ancho)
        # SE AÑADE COLUMNA 'LADO'
        print(f"{'PAR':<12} | {'LADO':<6} | {'PRECIO':<10} | {'RSI':<5} | {'ADX':<5} | {'ROE %':<9} | {'PNL $':<9} | {'SL ACT':<10} | {'SL ATR':<10} | {'ESTADO':<18} | {'SEÑAL'}")
        print("-" * self.ancho)

        # Ordenar pares alfabéticamente
        pares_ordenados = sorted(self.bot.estrategias_activas.keys())
        
        for par in pares_ordenados:
            estrategia = self.bot.estrategias_activas[par]
            precio_real = self.bot.gestor_datos.obtener_precio(par)
            
            # Variables visuales por defecto
            lado_str = " -- "
            color_lado = Fore.LIGHTBLACK_EX
            
            rsi_str, adx_str = "Calc..", "N/A"
            roe_str, pnl_usd_str = f"{Fore.LIGHTBLACK_EX}   --   ", f"{Fore.LIGHTBLACK_EX}   --   "
            sl_act_str, sl_atr_str = f"{Fore.LIGHTBLACK_EX}   --   ", f"{Fore.LIGHTBLACK_EX}   --   "
            color_rsi, color_adx = Fore.CYAN, Fore.WHITE
            estado_txt, senal_txt = "Esperando...", ""

            # 1. INDICADORES (RSI / ADX)
            if not estrategia.velas.empty:
                if 'RSI' in estrategia.velas.columns:
                    val_rsi = estrategia.velas.iloc[-1]['RSI']
                    if pd.notna(val_rsi):
                        s_venta = estrategia.parametros.get('rsi_sobreventa', 30)
                        s_compra = estrategia.parametros.get('rsi_sobrecompra', 70)
                        color_rsi = self._obtener_color_rsi(val_rsi, s_venta, s_compra)
                        rsi_str = f"{val_rsi:.1f}"
                        if val_rsi <= s_venta: estado_txt = f"{Fore.GREEN}SOBREVENTA"
                        elif val_rsi >= s_compra: estado_txt = f"{Fore.RED}SOBRECOMPRA"
                        else: estado_txt = f"{Fore.WHITE}NEUTRO"

                if 'ADX' in estrategia.velas.columns:
                    val_adx = estrategia.velas.iloc[-1]['ADX']
                    if pd.notna(val_adx):
                        min_adx = estrategia.parametros.get('adx_minimo', 25)
                        color_adx = self._obtener_color_adx(val_adx, min_adx)
                        adx_str = f"{val_adx:.1f}"

            # 2. GESTIÓN DE POSICIÓN
            if estrategia.posicion_abierta:
                estado_txt = f"{Back.MAGENTA}{Fore.WHITE} EN MERCADO "
                datos_pos = self.bot.gestor_ejecucion.obtener_datos_posicion(par)
                
                if datos_pos:
                    entry = datos_pos['entryPrice']
                    side = datos_pos['side']
                    amount = datos_pos['amount']
                    mark = datos_pos.get('markPrice', precio_real) 
                    lev = self.bot.config_pares[par].get('apalancamiento', 1)

                    # --- DETECCIÓN DE LADO (LONG/SHORT) ---
                    if side == 'buy':
                        lado_str = "LONG"
                        color_lado = Fore.GREEN + Style.BRIGHT
                    else:
                        lado_str = "SHORT"
                        color_lado = Fore.RED + Style.BRIGHT

                    # Cálculo PNL
                    if side == 'buy':
                        delta_pct = (mark - entry) / entry
                        diff_precio = mark - entry
                    else:
                        delta_pct = (entry - mark) / entry
                        diff_precio = entry - mark
                    
                    roe_val = delta_pct * lev * 100
                    pnl_usd_val = diff_precio * amount

                    # Colores PNL
                    if roe_val > 0: color_pnl = Fore.GREEN + Style.BRIGHT
                    elif roe_val < 0: color_pnl = Fore.RED + Style.BRIGHT
                    else: color_pnl = Fore.WHITE
                    
                    roe_str = f"{color_pnl}{roe_val:+.2f}%"
                    pnl_usd_str = f"{color_pnl}${pnl_usd_val:+.2f}"

                    # --- SL ACTUAL ---
                    orden_sl = self.bot.gestor_ejecucion.obtener_orden_stop_loss(par)
                    if orden_sl:
                        sl_val = float(orden_sl['stopPrice'])
                        sl_act_str = f"{Fore.YELLOW}{self._formatear_precio(sl_val)}"
                    else:
                        sl_act_str = f"{Fore.RED}NO SL"

                    # --- SL ATR (Optimizado) ---
                    if roe_val >= 10.0: 
                        atr = estrategia.atr_actual
                        # Fallback si el bot aún no lo calculó
                        if atr == 0: atr = estrategia.calcular_atr(14) 

                        if atr > 0:
                            dist_atr = 2 * atr
                            margen_fee = entry * 0.0015
                            
                            if side == 'buy':
                                target_final = max(mark - dist_atr, entry + margen_fee)
                                color_atr = Fore.GREEN if orden_sl and target_final > float(orden_sl['stopPrice']) else Fore.LIGHTBLACK_EX
                            else:
                                target_final = min(mark + dist_atr, entry - margen_fee)
                                color_atr = Fore.GREEN if orden_sl and target_final < float(orden_sl['stopPrice']) else Fore.LIGHTBLACK_EX
                            
                            sl_atr_str = f"{color_atr}{self._formatear_precio(target_final)}"
                    else:
                        sl_atr_str = f"{Fore.BLACK}Wait 10%" 

            # 3. SEÑALES (Solo si no hay posición)
            elif 'RSI' in estrategia.velas.columns and 'ADX' in estrategia.velas.columns:
                v_rsi = estrategia.velas.iloc[-1]['RSI']
                v_adx = estrategia.velas.iloc[-1]['ADX']
                if pd.notna(v_rsi) and pd.notna(v_adx):
                    s_venta = estrategia.parametros.get('rsi_sobreventa', 30)
                    s_compra = estrategia.parametros.get('rsi_sobrecompra', 70)
                    min_adx = estrategia.parametros.get('adx_minimo', 25)
                    
                    if v_adx > min_adx: 
                        if v_rsi < s_venta: senal_txt = f"{Back.GREEN}{Fore.WHITE} COMPRA "
                        elif v_rsi > s_compra: senal_txt = f"{Back.RED}{Fore.WHITE} VENTA "

            # Renderizar Fila
            p_str = self._formatear_precio(precio_real)
            print(f"{Fore.CYAN}{par:<12} {Style.RESET_ALL}| "
                  f"{color_lado}{lado_str:<6} {Style.RESET_ALL}| " # NUEVA COLUMNA
                  f"{p_str:<10} | "
                  f"{color_rsi}{rsi_str:<5} {Style.RESET_ALL}| "
                  f"{color_adx}{adx_str:<5} {Style.RESET_ALL}| "
                  f"{roe_str:<9} {Style.RESET_ALL}| " 
                  f"{pnl_usd_str:<9} {Style.RESET_ALL}| " 
                  f"{sl_act_str:<10} {Style.RESET_ALL}| "
                  f"{sl_atr_str:<10} {Style.RESET_ALL}| " 
                  f"{estado_txt:<18} | " 
                  f"{senal_txt}")

        print("-" * self.ancho)
        
        # Footer con Última Acción
        last_action = self._leer_ultima_accion()
        print(f" 📢 Última Acción: {Fore.YELLOW}{last_action}")
        print(f"{Fore.LIGHTBLACK_EX} Monitor activo (Refresco 5s). Ctrl+C para menú.")