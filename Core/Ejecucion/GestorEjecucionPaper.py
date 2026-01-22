import pandas as pd
import os
from datetime import datetime
from colorama import Fore
from Core.Ejecucion.GestorEjecucionBase import GestorEjecucionBase

class GestorEjecucionPaper(GestorEjecucionBase):
    """
    Simula ser el GestorEjecucion pero opera con dinero ficticio.
    Guarda todo en la carpeta 'Registros' para no estorbar.
    """
    def __init__(self, gestor_datos_ref):
        print(Fore.YELLOW + "🧪 MODO PAPER TRADING: Activado (Dinero Ficticio)")
        
        # --- CAMBIO: Organización de Carpeta ---
        self.carpeta_destino = "Registros"
        self.nombre_archivo = "PaperTrading_Live.csv"
        
        # Creamos la carpeta si no existe (evita errores)
        if not os.path.exists(self.carpeta_destino):
            os.makedirs(self.carpeta_destino)
            print(Fore.CYAN + f"📂 Carpeta creada: {self.carpeta_destino}")

        # Ruta final: Registros/PaperTrading_Live.csv
        self.archivo_csv = os.path.join(self.carpeta_destino, self.nombre_archivo)
        
        self.posiciones = {} 
        self.balance_actual = 10000.0 
        self.gestor_datos = gestor_datos_ref 
        
        self._inicializar_csv()

    def _inicializar_csv(self):
        # Verifica si existe EL ARCHIVO dentro de la carpeta
        if not os.path.exists(self.archivo_csv):
            df = pd.DataFrame(columns=[
                "Fecha", "Simbolo", "Tipo", "Precio_Entrada", "Cantidad", 
                "Precio_Salida", "Resultado", "PNL_USDT", "PNL_PCT", "Balance_Acum"
            ])
            # Guardamos usando la ruta completa
            df.to_csv(self.archivo_csv, index=False)

    # --- MÉTODOS QUE IMITAN A LA CLASE REAL ---

    def configurar_apalancamiento(self, simbolo, lev):
        pass # No hace nada en papel

    def obtener_todos_simbolos_con_posicion(self):
        return list(self.posiciones.keys())
    
    def obtener_balance_usdt(self):
        return self.balance_actual

    def calcular_cantidad_por_porcentaje(self, simbolo, porcentaje_str, precio_actual, apalancamiento):
        """Simulación simplificada del cálculo de margen"""
        balance = self.obtener_balance_usdt()
        porcentaje = float(porcentaje_str.replace('%', '')) / 100
        margen = balance * porcentaje
        # En paper simple, asumimos que leverage multiplica el poder de compra
        # cantidad = (Margen * Lev) / Precio
        cantidad = (margen * apalancamiento) / precio_actual
        return cantidad

    def obtener_posicion_abierta(self, simbolo):
        return simbolo in self.posiciones

    def obtener_datos_posicion(self, simbolo):
        """Devuelve estructura similar a Binance pero calculada en vivo"""
        if simbolo not in self.posiciones: return None
        
        pos = self.posiciones[simbolo]
        precio_actual = self.gestor_datos.obtener_precio(simbolo)
        entry = pos['entryPrice']
        cantidad = pos['cantidad']
        lado = pos['side']
        
        # Calculamos PNL no realizado
        if lado == 'buy':
            roe = (precio_actual - entry) / entry
        else:
            roe = (entry - precio_actual) / entry
            
        return {
            'entryPrice': entry,
            'markPrice': precio_actual,
            'side': lado,
            'amt': cantidad,
            'roe': roe # Necesario para tu Trailing Stop
        }

    def cancelar_ordenes_pendientes(self, simbolo):
        pass 

    def colocar_orden_mercado(self, simbolo, lado, cantidad_usdt_o_tokens):
        precio_actual = self.gestor_datos.obtener_precio(simbolo)
        
        # Simulamos conversión simple de cantidad
        cantidad_tokens = cantidad_usdt_o_tokens / precio_actual if cantidad_usdt_o_tokens > 10 else cantidad_usdt_o_tokens

        self.posiciones[simbolo] = {
            'entryPrice': precio_actual,
            'cantidad': cantidad_tokens,
            'side': lado, 
            'sl_price': 0.0,
            'tp_price': 0.0
        }
        
        print(f"{Fore.MAGENTA}🧪 PAPER ORDER: {lado.upper()} {simbolo} @ {precio_actual}")
        return {'average': precio_actual, 'id': f'paper_{int(time.time())}'}

    def colocar_ordenes_salida(self, simbolo, lado_entrada, cantidad, precio_entrada, sl_pct, tp_pct):
        if simbolo in self.posiciones:
            if lado_entrada == 'buy':
                sl = precio_entrada * (1 - sl_pct)
                tp = precio_entrada * (1 + tp_pct)
            else:
                sl = precio_entrada * (1 + sl_pct)
                tp = precio_entrada * (1 - tp_pct)
            
            self.posiciones[simbolo]['sl_price'] = sl
            self.posiciones[simbolo]['tp_price'] = tp
            print(f"{Fore.CYAN}🧪 TP/SL Simulados: SL {sl:.4f} | TP {tp:.4f}")

    def modificar_stop_loss(self, simbolo, orden_id, nuevo_precio, lado):
        if simbolo in self.posiciones:
            self.posiciones[simbolo]['sl_price'] = nuevo_precio
            print(f"{Fore.CYAN}🧪 SL Actualizado a {nuevo_precio}")

    def obtener_orden_stop_loss(self, simbolo):
        if simbolo in self.posiciones:
            return {'stopPrice': self.posiciones[simbolo]['sl_price'], 'id': 'paper_sl'}
        return None

    def ejecutar_cierre_parcial(self, simbolo, cantidad_reduccion, lado_actual, tipo_orden='market'):
        if simbolo not in self.posiciones: 
            return False

        pos = self.posiciones[simbolo]
        precio_actual = self.gestor_datos.obtener_precio(simbolo)
        entry = pos['entryPrice']
        
        # Calculamos PNL proporcional a lo que vendemos
        if lado_actual == 'buy':
            pnl_usdt = (precio_actual - entry) * cantidad_reduccion
        else:
            pnl_usdt = (entry - precio_actual) * cantidad_reduccion
        
        # Actualizamos balance y reducimos posición
        self.balance_actual += pnl_usdt
        pos['cantidad'] -= cantidad_reduccion
        
        # Log en CSV
        try:
            nuevo_registro = {
                "Fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Simbolo": simbolo,
                "Tipo": f"PARTIAL_{lado_actual.upper()}",
                "Precio_Entrada": entry,
                "Cantidad": cantidad_reduccion,
                "Precio_Salida": precio_actual,
                "Resultado": "PARTIAL TAKE PROFIT",
                "PNL_USDT": round(pnl_usdt, 2),
                "PNL_PCT": round(((precio_actual - entry)/entry)*100, 2) if lado_actual == 'buy' else round(((entry - precio_actual)/entry)*100, 2),
                "Balance_Acum": round(self.balance_actual, 2)
            }
            df = pd.DataFrame([nuevo_registro])
            df.to_csv(self.archivo_csv, mode='a', header=False, index=False)
        except Exception as e:
            print(Fore.RED + f"⚠️ Error escribiendo CSV parcial: {e}")

        print(Fore.GREEN + f"💰 TP PARCIAL PAPERT: {simbolo} | PNL: ${pnl_usdt:.2f} | Restan: {pos['cantidad']:.4f}")
        return True

    # --- MOTOR DE CIERRE SIMULADO ---
    
    def chequear_cierres(self, simbolo):
        """Verifica manualmente si el precio tocó SL o TP"""
        if simbolo not in self.posiciones: return False

        pos = self.posiciones[simbolo]
        precio_actual = self.gestor_datos.obtener_precio(simbolo)
        
        sl = pos['sl_price']
        tp = pos['tp_price']
        lado = pos['side']
        cerrar_con_razon = None

        # Verificación BUY
        if lado == 'buy':
            if precio_actual <= sl: cerrar_con_razon = "STOP LOSS"
            elif precio_actual >= tp and tp > 0: cerrar_con_razon = "TAKE PROFIT"
        
        # Verificación SELL
        else:
            if precio_actual >= sl and sl > 0: cerrar_con_razon = "STOP LOSS"
            elif precio_actual <= tp and tp > 0: cerrar_con_razon = "TAKE PROFIT"

        if cerrar_con_razon:
            self._cerrar_posicion(simbolo, precio_actual, cerrar_con_razon)
            return True
        return False

    def chequear_cierres_con_vela(self, simbolo, kline):
        """
        Verificación Precisa (Wick Detection):
        Usa High y Low de la vela para ver si tocó precios aunque cerró lejos.
        """
        if simbolo not in self.posiciones: return False

        pos = self.posiciones[simbolo]
        sl = pos['sl_price']
        tp = pos['tp_price']
        lado = pos['side']
        
        # Datos de la vela
        high = float(kline['h'])
        low = float(kline['l'])
        close = float(kline['c']) # Precio cierre por defecto si hay cruce
        
        cerrar_con_razon = None
        precio_ejecucion = close

        # Lógica de prioridad: Stop Loss suele ejecutarse primero en simulaciones conservadoras
        # si ambos ocurren en la misma vela (peor caso).
        
        if lado == 'buy':
            # LONG: SL está abajo (checamos LOW), TP está arriba (checamos HIGH)
            if low <= sl: 
                cerrar_con_razon = "STOP LOSS (Wick)"
                precio_ejecucion = sl # Asumimos slippage 0 o ejecución en precio trigger
            elif high >= tp and tp > 0: 
                cerrar_con_razon = "TAKE PROFIT (Wick)"
                precio_ejecucion = tp
        
        else:
            # SHORT: SL está arriba (checamos HIGH), TP está abajo (checamos LOW)
            if high >= sl and sl > 0: 
                cerrar_con_razon = "STOP LOSS (Wick)"
                precio_ejecucion = sl
            elif low <= tp and tp > 0: 
                cerrar_con_razon = "TAKE PROFIT (Wick)"
                precio_ejecucion = tp

        if cerrar_con_razon:
            self._cerrar_posicion(simbolo, precio_ejecucion, cerrar_con_razon)
            return True
            
        return False

    def _cerrar_posicion(self, simbolo, precio_salida, razon):
        pos = self.posiciones[simbolo]
        entry = pos['entryPrice']
        cantidad = pos['cantidad']
        lado = pos['side']
        
        # Calculo PNL
        if lado == 'buy':
            pnl_usdt = (precio_salida - entry) * cantidad
            pnl_pct = (precio_salida - entry) / entry
        else:
            pnl_usdt = (entry - precio_salida) * cantidad
            pnl_pct = (entry - precio_salida) / entry

        self.balance_actual += pnl_usdt
        
        # Guardar en CSV
        nuevo_registro = {
            "Fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Simbolo": simbolo,
            "Tipo": lado.upper(),
            "Precio_Entrada": entry,
            "Cantidad": cantidad,
            "Precio_Salida": precio_salida,
            "Resultado": razon,
            "PNL_USDT": round(pnl_usdt, 2),
            "PNL_PCT": round(pnl_pct * 100, 2),
            "Balance_Acum": round(self.balance_actual, 2)
        }
        
        df = pd.DataFrame([nuevo_registro])
        df.to_csv(self.archivo_csv, mode='a', header=False, index=False)
        
        print(f"{Fore.GREEN if pnl_usdt > 0 else Fore.RED}✅ CIERRE PAPER {simbolo}: {razon} | PNL: ${pnl_usdt:.2f}")
        del self.posiciones[simbolo]