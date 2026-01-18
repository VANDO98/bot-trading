import os
# CORRECCIÓN: Importamos el Auditor
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

        # 3. GRAFICA (Top 5 Binance)
        elif cmd == "/grafica":
            horas = 24
            if args and args[0].isdigit():
                horas = int(args[0])
            
            enviar_texto_func(chat_id, f"📡 Consultando Binance y generando Top 5 ({horas}h)...")
            
            # CORRECCIÓN: Usamos el auditor para la gráfica Top 5
            ruta, texto = self.auditor.generar_grafica_top5(horas)
            
            if ruta and os.path.exists(ruta):
                enviar_foto_func(chat_id, ruta)
                enviar_texto_func(chat_id, texto)
            else:
                enviar_texto_func(chat_id, texto)

        # 4. REPORTE (CSV Auditoría)
        elif cmd == "/reporte":
            try:
                horas = int(args[0]) if args and args[0].isdigit() else 24
                enviar_texto_func(chat_id, f"🧮 Calculando métricas y generando CSV ({horas}h)...")
                
                ruta_csv, mensaje_status = self.auditor.generar_csv_resumen(horas)
                
                if ruta_csv and os.path.exists(ruta_csv):
                    if enviar_documento_func:
                        enviar_documento_func(chat_id, ruta_csv)
                    else:
                        enviar_texto_func(chat_id, "❌ Error: Función de documento no disponible.")
                else:
                    enviar_texto_func(chat_id, mensaje_status)
            except Exception as e:
                enviar_texto_func(chat_id, f"❌ Error reporte: {e}")

        # 5. COMANDO DASHBOARD (ON/OFF)
        elif cmd == "/dash":
            modo = args[0].lower() if args else ""
            
            if modo == "on":
                self.bot.mostrar_dashboard = True
                enviar_texto_func(chat_id, "📺 **Dashboard ACTIVADO** en consola.")
            
            elif modo == "off":
                self.bot.mostrar_dashboard = False
                enviar_texto_func(chat_id, "c **Dashboard APAGADO** (Modo Silencioso).")
            
            else:
                enviar_texto_func(chat_id, "⚠️ Uso: `/dash on` o `/dash off`")

        # 6. HELP (Actualizamos la lista)
        elif cmd == "/help":
            msg = (
                "📜 **COMANDOS**\n"
                "/status - Ver posiciones\n"
                "/balance - Ver dinero\n"
                "/grafica [horas] - Ver rendimiento\n"
                "/reporte [horas] - Descargar CSV\n"
                "/dash [on/off] - Controlar consola" # <--- Nuevo
            )
            enviar_texto_func(chat_id, msg)
        
        else:
            enviar_texto_func(chat_id, "❓ Comando desconocido. Prueba /help")