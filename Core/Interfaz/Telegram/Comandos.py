import os
import json
from Core.Utils.Auditoria import GestorAuditoria

class GestorComandos:
    def __init__(self, bot_controller):
        self.bot = bot_controller
        # Inicializamos el Auditor conectado a Binance
        self.auditor = GestorAuditoria(bot_controller)

    def ejecutar(self, comando, args, chat_id, enviar_texto_func, enviar_foto_func, enviar_documento_func=None):
        """Procesa el comando recibido."""
        cmd = comando.lower().strip()

        # 1. STATUS
        if cmd == "/status":
            msg = "🤖 **ESTADO DEL SISTEMA**\n"
            msg += "━━━━━━━━━━━━━━━━\n"
            contador = 0
            for par, estrategia in self.bot.estrategias_activas.items():
                estado = "🟢 DENTRO" if estrategia.posicion_abierta else "⚪ ESPERANDO"
                msg += f"**{par}**: {estado}\n"
                if estrategia.posicion_abierta: contador += 1
            
            # Agregamos info del ML actual al status
            ml_actual = self.bot.config_global.get('sistema_riesgo', {}).get('ml_threshold', 0.65)
            msg += f"\n🧠 Nivel ML: **{ml_actual}**"
            msg += f"\n📊 Activos: {contador}/{self.bot.config_global.get('max_trades_abiertos', 5)}"
            enviar_texto_func(chat_id, msg)

        # 2. BALANCE
        elif cmd == "/balance":
            try:
                bal = self.bot.gestor_ejecucion.exchange.fetch_balance()
                usdt = bal['USDT']
                msg = f"💰 **BALANCE FUTUROS**\n"
                msg += f"💵 Total: ${float(usdt['total']):.2f}\n"
                msg += f"🔓 Libre: ${float(usdt['free']):.2f}\n"
                msg += f"🔒 Usado: ${float(usdt['used']):.2f}"
                enviar_texto_func(chat_id, msg)
            except Exception as e:
                enviar_texto_func(chat_id, f"❌ Error balance: {e}")

        # 3. GRAFICA (Dashboard Completo)
        elif cmd == "/grafica":
            try:
                horas = int(args[0]) if args and args[0].isdigit() else 24
                enviar_texto_func(chat_id, f"📡 Generando dashboard ({horas}h)...")
                
                # Importar el analizador
                from Core.Utils.AnalizadorTrades import AnalizadorTrades
                
                # Crear analizador
                analizador = AnalizadorTrades(exchange_instance=self.bot.gestor_ejecucion.exchange)
                
                # Generar reporte completo (reutilizamos la lógica ya que genera el dashboard)
                resultado = analizador.generar_reporte(horas)
                
                if resultado and os.path.exists(resultado['dashboard']):
                    enviar_foto_func(chat_id, resultado['dashboard'])
                    enviar_texto_func(chat_id, "📊 Aquí tienes el dashboard de rendimiento actualizado.")
                else:
                    enviar_texto_func(chat_id, "📉 No hay trades o datos suficientes para generar la gráfica.")
            
            except Exception as e:
                enviar_texto_func(chat_id, f"❌ Error generando gráfica: {e}")

        # 4. REPORTE (Análisis Completo con Dashboard + Excel)
        elif cmd == "/reporte":
            try:
                horas = int(args[0]) if args and args[0].isdigit() else 24
                enviar_texto_func(chat_id, f"🧮 Generando análisis completo ({horas}h)...")
                
                # Importar el analizador
                from Core.Utils.AnalizadorTrades import AnalizadorTrades
                
                # Crear analizador reutilizando el exchange del bot
                analizador = AnalizadorTrades(exchange_instance=self.bot.gestor_ejecucion.exchange)
                
                # Generar reporte
                resultado = analizador.generar_reporte(horas)
                
                if resultado:
                    # Enviar resumen de texto
                    resumen = resultado['resumen']
                    msg = f"📊 **Análisis Completo ({horas}h)**\\n\\n"
                    msg += f"💰 PnL Total: **${resumen['pnl_total']:.2f}** USDT\\n"
                    msg += f"🎯 Win Rate Promedio: **{resumen['win_rate_promedio']:.1f}%**\\n"
                    msg += f"📈 Pares Analizados: **{resumen['num_pares']}**\\n"
                    msg += f"🔢 Total Trades: **{resumen['num_trades']}**"
                    enviar_texto_func(chat_id, msg)
                    
                    # Enviar dashboard
                    if os.path.exists(resultado['dashboard']):
                        enviar_foto_func(chat_id, resultado['dashboard'])
                    
                    # Enviar Excel
                    if os.path.exists(resultado['excel']):
                        if enviar_documento_func:
                            enviar_documento_func(chat_id, resultado['excel'])
                        else:
                            enviar_texto_func(chat_id, f"📁 Excel generado en: {resultado['excel']}")
                else:
                    enviar_texto_func(chat_id, "📉 No hay trades en el periodo especificado")
                    
            except Exception as e:
                enviar_texto_func(chat_id, f"❌ Error reporte: {e}")

        # 5. DASHBOARD (TOGGLE)
        elif cmd == "/dash":
            # Invertimos el estado actual
            estado_actual = self.bot.mostrar_dashboard
            nuevo_estado = not estado_actual
            self.bot.mostrar_dashboard = nuevo_estado
            
            if nuevo_estado:
                enviar_texto_func(chat_id, "📺 **Dashboard ACTIVADO** en consola.")
            else:
                enviar_texto_func(chat_id, "🔇 **Dashboard APAGADO** (Modo Silencioso).")

        # 6. HELP
        elif cmd == "/help":
            msg = (
                "📜 **COMANDOS**\n"
                "/status - Ver posiciones y ML\n"
                "/posiciones - Detalle PNL/SL/TP\n"
                "/balance - Ver dinero\n"
                "/grafica [h] - Top 5 Volatilidad\n"
                "/reporte [h] - Descargar CSV\n"
                "/ml [0.0-0.9] - Ajustar filtro IA\n"
                "/dash - Activar/Desactivar Dashboard\n"
                "/reiniciar - Reiniciar Bot (Watchdog)\n"
                "/config - Ver configuración actual\n"
            )
            enviar_texto_func(chat_id, msg)

        # =========================================================
        # 7. CONFIGURACION ML (NUEVO BLOQUE)
        # =========================================================
        elif cmd == "/ml":
            try:
                if not args:
                    enviar_texto_func(chat_id, "⚠️ Uso: `/ml 0.60` (Cambiar umbral)")
                    return

                nuevo_valor = float(args[0])

                if not (0.01 <= nuevo_valor <= 0.99):
                    enviar_texto_func(chat_id, "⛔ El valor debe estar entre 0.01 y 0.99")
                    return
                
                # Llamamos al método que creamos en BotController
                exito, info = self.bot.actualizar_umbral_ml(nuevo_valor)

                if exito:
                    enviar_texto_func(chat_id, f"✅ **Umbral ML Actualizado**\n\nAnterior: {info}\nNuevo: **{nuevo_valor}**\n\n_El bot aplicará este filtro inmediatamente._")
                else:
                    enviar_texto_func(chat_id, f"❌ Error guardando config: {info}")

            except ValueError:
                enviar_texto_func(chat_id, "❌ Error: Debes enviar un número (Ej: 0.55)")
            except Exception as e:
                enviar_texto_func(chat_id, f"❌ Error crítico ML: {e}")

        # =========================================================
        # 8. VER CONFIGURACION JSON (NUEVO)
        # =========================================================
        elif cmd == "/config":
            try:
                # Leemos directo del archivo para asegurar datos frescos
                with open("config_trading.json", "r") as f:
                    data = json.load(f)

                # Extraemos secciones
                gl = data.get("configuracion_global", {})
                rs = data.get("sistema_riesgo", {})
                testnet = data.get("usar_testnet", False)

                # Construimos el mensaje con emojis
                msg = "⚙️ **CONFIGURACIÓN ACTUAL**\n"
                msg += "━━━━━━━━━━━━━━━━\n\n"

                # Sección General
                modo_emoji = "🧪 Testnet" if testnet else "🔥 REAL (Mainnet)"
                msg += f"🖥 **Sistema Base**\n"
                msg += f"• Modo: {modo_emoji}\n"
                msg += f"• Moneda: **{gl.get('moneda_base', 'USDT')}** 💵\n"
                msg += f"• Max Trades: **{gl.get('max_trades_abiertos', 5)}** 📊\n\n"

                # Sección Riesgo
                sl_pct = rs.get('stop_loss_pct', 0.0) * 100
                tp_pct = rs.get('take_profit_pct', 0.0) * 100
                ml_th = rs.get('ml_threshold', 0.0)
                be_roe = rs.get('activacion_break_even_roe', 0.0) * 100
                ts_roe = rs.get('trailing_stop_roe', 0.0) * 100

                msg += f"🛡 **Gestión de Riesgo**\n"
                msg += f"• 🧠 Filtro IA (ML): **{ml_th}**\n"
                msg += f"• 🛑 Stop Loss: **{sl_pct:.1f}%**\n"
                msg += f"• 💰 Take Profit: **{tp_pct:.1f}%**\n"
                msg += f"• 🛡 Break Even: al **{be_roe:.1f}%** ROE\n"
                msg += f"• 🏃 Trailing Stop: al **{ts_roe:.1f}%** ROE\n"

                enviar_texto_func(chat_id, msg)

            except Exception as e:
                enviar_texto_func(chat_id, f"❌ Error leyendo config: {e}")
        
        # =========================================================
        # 9. MIS POSICIONES (NUEVO)
        # =========================================================
        elif cmd in ["/posiciones", "/pnl"]:
            try:
                simbolos_activos = self.bot.gestor_ejecucion.obtener_todos_simbolos_con_posicion()
                
                if not simbolos_activos:
                    enviar_texto_func(chat_id, "🚫 **No hay posiciones abiertas actualmente.**")
                    return

                msg = "📊 **POSICIONES ACTIVAS**\n"
                msg += "━━━━━━━━━━━━━━━━\n"

                for simbolo in simbolos_activos:
                    # 1. Obtener Datos Básicos
                    datos = self.bot.gestor_ejecucion.obtener_datos_posicion(simbolo)
                    if not datos: continue

                    # Normalización de claves (Paper vs Real)
                    entry_price = datos['entryPrice']
                    mark_price = datos.get('markPrice', 0.0)
                    if mark_price == 0: 
                        mark_price = self.bot.gestor_datos.obtener_precio(simbolo)

                    side = datos['side'] # 'buy' o 'sell'
                    
                    # 'amount' en Real, 'amt' en Paper
                    amount = datos.get('amount', datos.get('amt', 0.0))

                    # 2. Calcular PNL y ROE
                    if side == 'buy':
                        pnl_puntos = mark_price - entry_price
                        roe = (pnl_puntos / entry_price) * 100
                    else:
                        pnl_puntos = entry_price - mark_price
                        roe = (pnl_puntos / entry_price) * 100
                    
                    pnl_usdt = pnl_puntos * amount
                    
                    # 3. Obtener SL y TP
                    sl_precio = 0.0
                    tp_precio = 0.0

                    # Detectar si es Paper o Real para buscar órdenes
                    es_paper = hasattr(self.bot.gestor_ejecucion, 'posiciones')
                    
                    if es_paper:
                        # Modo Paper: Acceso directo al dict de memoria
                        pos_memoria = self.bot.gestor_ejecucion.posiciones.get(simbolo, {})
                        sl_precio = pos_memoria.get('sl_price', 0.0)
                        tp_precio = pos_memoria.get('tp_price', 0.0)
                    else:
                        # Modo Real: Consultar API de Open Orders
                        try:
                            ordenes = self.bot.gestor_ejecucion.exchange.fetch_open_orders(simbolo)
                            for o in ordenes:
                                tipo = o.get('type', '').upper()
                                reduce = o.get('reduceOnly', False)
                                precio_ord = float(o.get('stopPrice', o.get('price', 0.0)))
                                
                                # SL suele ser STOP_MARKET
                                if (tipo in ['STOP_MARKET', 'STOP']) and reduce:
                                    sl_precio = precio_ord
                                # TP suele ser TAKE_PROFIT_MARKET o LIMIT
                                elif (tipo in ['TAKE_PROFIT_MARKET', 'TAKE_PROFIT', 'LIMIT']) and reduce:
                                    # Distinguir TP de otras cosas (simple heurística)
                                    if side == 'buy' and precio_ord > entry_price:
                                        tp_precio = precio_ord
                                    elif side == 'sell' and precio_ord < entry_price:
                                        tp_precio = precio_ord
                        except:
                            pass

                    # 4. Formatear Bloque
                    icono_lado = "🟢 LONG" if side == 'buy' else "🔴 SHORT"
                    roi_icono = "🚀" if roe > 0 else "🔻"
                    
                    msg += f"\n{icono_lado} | **{simbolo}**\n"
                    msg += f"🚪 Entrada: **${entry_price:,.2f}**\n"
                    msg += f"📊 Mark: `${mark_price:,.2f}`\n"
                    msg += f"💰 PNL: **${pnl_usdt:,.2f}** ({roi_icono} {roe:.2f}%)\n"
                    
                    if sl_precio > 0:
                        msg += f"🛑 SL: `${sl_precio:,.2f}`\n"
                    else:
                        msg += f"🛑 SL: ⚠️ NO ACTIVO\n"

                    if tp_precio > 0:
                        msg += f"🎯 TP: `${tp_precio:,.2f}`\n"
                    else:
                        msg += f"🎯 TP: --\n"
                    
                    msg += "〰️〰️〰️〰️〰️〰️〰️\n"

                enviar_texto_func(chat_id, msg)

            except Exception as e:
                enviar_texto_func(chat_id, f"❌ Error recuperando posiciones: {e}")

        # =========================================================
        # 10. REINICIAR (NUEVO)
        # =========================================================
        elif cmd == "/reiniciar":
            enviar_texto_func(chat_id, "🔄 **Reiniciando Sistema...**\n\nEl bot volverá a estar online en unos segundos.")
            
            # Forzamos cierre. El Watchdog lo detectará y volverá a lanzar main.py
            # Usamos os._exit(0) para matar hilos rebeldes si los hubiera
            import sys
            sys.stdout.flush()
            os._exit(0)


        else:
            enviar_texto_func(chat_id, "❓ Comando desconocido. Prueba /help")