import time
from Estrategias.BotBase import BotBase 

class BotTrading(BotBase):
    def iniciar(self):
        try:
            self.iniciar_servicios()
            
            print("\n📊 MONITOREO DE INDICADORES EN TIEMPO REAL")
            print("---------------------------------------------------------")
            
            while True:
                self.ejecutar_estrategia()
                time.sleep(5) 

        except KeyboardInterrupt:
            self.detener_servicios()

    def ejecutar_estrategia(self):
        for par in self.pares_activos:
            # 1. Seguridad
            if not self.mercado.verificar_salud_datos(par):
                continue
            
            # 2. Datos
            precio = self.mercado.obtener_precio(par)
            config = self.estrategias[par]
            
            # --- NUEVO: CÁLCULO DE POSICIÓN ---
            porcentaje = config.get("porcentaje_balance", 1) # Por defecto 1% si falta
            leverage = config.get("apalancamiento", 1)
            decimales = config.get("decimales", 3)
            
            # Calculamos cuánto compraríamos SI se diera la señal
            cantidad_a_comprar, balance_total = self.ejecutor.calcular_cantidad(
                symbol=par, 
                porcentaje=porcentaje, 
                precio=precio, 
                apalancamiento=leverage,
                precision=decimales
            )
            
            # 3. Análisis Técnico
            precios_cierre = self.velas.obtener_closes(par)
            if len(precios_cierre) < 50:
                continue

            rsi_periodo = config["indicadores"].get("rsi_periodo", 14)
            rsi_actual = self.analista.calcular_rsi(precios_cierre, rsi_periodo)
            
            if rsi_actual is None: continue

            # 4. Visualización
            rsi_compra = config["indicadores"]["rsi_sobreventa"]
            
            print(f"🤖 {par} | ${precio:,.2f} | RSI: {rsi_actual:.2f} | Posición Potencial: {cantidad_a_comprar} monedas ({porcentaje}% de ${balance_total:.0f})")
            
if __name__ == "__main__":
    bot = BotTrading()
    bot.iniciar()