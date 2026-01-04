import time
from Estrategias.BotBase import BotBase 
from binance.enums import SIDE_BUY, SIDE_SELL

class BotTrading(BotBase):
    """
    Clase Principal: CEREBRO DE TRADING
    Hereda la conexión y herramientas de BotBase.
    Aquí reside la lógica de decisión (Cuándo comprar/vender).
    """
    def iniciar(self):
        try:
            # 1. Arrancar motores (Descarga de velas + WebSockets)
            self.iniciar_servicios()
            
            print("\n🔥 SISTEMA OPERATIVO. ESCANEANDO OPORTUNIDADES...")
            print("---------------------------------------------------------")
            
            # 2. Bucle Infinito
            while True:
                self.ejecutar_estrategia()
                time.sleep(5) # "Pensar" cada 5 segundos

        except KeyboardInterrupt:
            print("\n🛑 Deteniendo bot por orden del usuario...")
            self.detener_servicios()

    def ejecutar_estrategia(self):
        for par in self.pares_activos:
            # 1. Seguridad
            if not self.mercado.verificar_salud_datos(par):
                continue
            
            # 2. Datos y Estado
            precio = self.mercado.obtener_precio(par)
            config = self.estrategias[par]
            
            # --- NUEVA SEGURIDAD ---
            posicion_actual = self.ejecutor.obtener_posicion(par)
            tengo_posicion = abs(posicion_actual) > 0
            
            # Consultamos si ya hay una orden puesta esperando llenarse
            tengo_ordenes_pendientes = self.ejecutor.verificar_ordenes_pendientes(par)
            
            # 3. Análisis Técnico
            precios_cierre = self.velas.obtener_closes(par)
            if len(precios_cierre) < 50: continue

            rsi_periodo = config["indicadores"].get("rsi_periodo", 14)
            rsi_actual = self.analista.calcular_rsi(precios_cierre, rsi_periodo)
            if rsi_actual is None: continue

            # 4. LÓGICA DE DECISIÓN
            rsi_compra = config["indicadores"]["rsi_sobreventa"] 
            rsi_venta = config["indicadores"]["rsi_sobrecompra"]
            
            porcentaje = config.get("porcentaje_balance", 1)
            leverage = config.get("apalancamiento", 1)
            decimales = config.get("decimales", 3)

            # --- ESCENARIO A: BUSCAR ENTRADA ---
            # Solo entramos si NO tenemos posición Y TAMPOCO órdenes esperando
            if not tengo_posicion and not tengo_ordenes_pendientes:
                
                if rsi_actual < rsi_compra:
                    print(f"✅ {par}: RSI {rsi_actual:.2f} < {rsi_compra} -> ¡ABRIENDO LONG 🚀!")
                    cant, _ = self.ejecutor.calcular_cantidad(par, porcentaje, precio, leverage, decimales)
                    if cant > 0: 
                        self.ejecutor.colocar_orden_limit(par, SIDE_BUY, cant, precio)
                    
                elif rsi_actual > rsi_venta:
                    print(f"✅ {par}: RSI {rsi_actual:.2f} > {rsi_venta} -> ¡ABRIENDO SHORT 📉!")
                    cant, _ = self.ejecutor.calcular_cantidad(par, porcentaje, precio, leverage, decimales)
                    if cant > 0: 
                        self.ejecutor.colocar_orden_limit(par, SIDE_SELL, cant, precio)
                
                else:
                    print(f"🤖 {par:<8} | ${precio:<10,.2f} | RSI: {rsi_actual:.2f} | 💤 Esperando...")

            # --- ESCENARIO B: BUSCAR SALIDA ---
            elif tengo_posicion:
                tipo = "LONG 🟢" if posicion_actual > 0 else "SHORT 🔴"
                print(f"🛡️ {par:<8} | EN {tipo} ({posicion_actual}) | RSI: {rsi_actual:.2f} | Gestionando salida...")

                if posicion_actual > 0 and rsi_actual > rsi_venta:
                    print(f"💰 CERRANDO LONG...")
                    self.ejecutor.cerrar_posicion_mercado(par, posicion_actual)

                elif posicion_actual < 0 and rsi_actual < rsi_compra:
                    print(f"💰 CERRANDO SHORT...")
                    self.ejecutor.cerrar_posicion_mercado(par, posicion_actual)
            
            # --- ESCENARIO C: ÓRDENES PENDIENTES ---
            elif tengo_ordenes_pendientes:
                print(f"⏳ {par}: Tiene una orden abierta esperando llenarse... (No hacemos nada)")
                
# -------------------------------------------------------------
# PUNTO DE ENTRADA (ESTO ES LO QUE TE FALTABA)
# -------------------------------------------------------------
if __name__ == "__main__":
    bot = BotTrading()
    bot.iniciar()