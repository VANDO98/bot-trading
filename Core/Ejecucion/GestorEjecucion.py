import os
import ccxt
from dotenv import load_dotenv
from Core.Utils.Config import Config
from Core.Ejecucion.GestorEjecucionBase import GestorEjecucionBase
from colorama import Fore

load_dotenv()

class GestorEjecucion(GestorEjecucionBase):
    """
    ENCARGADO DE LAS ÓRDENES (Versión CCXT + Gestión de Riesgo).
    """
    
    def __init__(self):
        key = os.getenv("BINANCE_API_KEY")
        secret = os.getenv("BINANCE_SECRET_KEY")
        
        if not key or not secret:
            print(Fore.RED + "❌ ERROR CRÍTICO: No hay API KEYS en .env")
            return

        try:
            self.exchange = ccxt.binance({
                'apiKey': key,
                'secret': secret,
                'enableRateLimit': True,
                'options': { 'defaultType': 'future' }
            })

            if Config.USAR_TESTNET:
                self.exchange.set_sandbox_mode(True)
                print(Fore.GREEN + "🔑 Gestor Ejecución: Conectado a TESTNET.")
            else:
                print(Fore.RED + "🔑 Gestor Ejecución: Conectado a REAL.")

            # Cargar mercados para saber los decimales permitidos (precisión)
            self.exchange.load_markets()

        except Exception as e:
            print(Fore.RED + f"❌ Error inicializando CCXT: {e}")

    def configurar_apalancamiento(self, simbolo, nivel):
        """
        Cambia el apalancamiento (ej: 5x, 10x) en el exchange.
        """
        try:
            self.exchange.set_leverage(nivel, simbolo)
            print(Fore.YELLOW + f"⚙️ Apalancamiento para {simbolo} configurado a {nivel}x")
        except Exception as e:
            print(Fore.RED + f"⚠️ No se pudo setear apalancamiento en {simbolo}: {e}")

    def obtener_balance_usdt(self):
        """Devuelve el saldo libre de USDT."""
        try:
            balance = self.exchange.fetch_balance()
            return float(balance['USDT']['free'])
        except Exception as e:
            print(Fore.RED + f"⚠️ Error leyendo balance: {e}")
            return 0.0

    def calcular_cantidad_por_porcentaje(self, simbolo, porcentaje_str, precio_actual, apalancamiento):
        """
        Calcula cuántas monedas comprar para que el MARGEN sea el % del balance.
        Fórmula: (Balance * %) * Apalancamiento / Precio
        """
        try:
            # 1. Obtener balance disponible
            balance = self.obtener_balance_usdt()
            if balance <= 0: return 0.0

            # 2. Convertir "10%" a 0.10
            porcentaje = float(porcentaje_str.replace('%', '')) / 100
            
            # 3. Calcular DINERO REAL A ARRIESGAR (Margen)
            margen_usdt = balance * porcentaje
            
            # (Seguridad) Binance suele pedir mínimo 5-6 USDT de margen
            if margen_usdt < 6:
                print(Fore.YELLOW + f"⚠️ El margen calculado (${margen_usdt:.2f}) es menor al mínimo ($6).")
                return 0.0

            # 4. Calcular TAMAÑO TOTAL DE LA POSICIÓN (Nocional)
            # Si pongo 100 USD x 10 leverage = Opero por valor de 1000 USD
            monto_total_posicion = margen_usdt * apalancamiento

            # 5. Calcular cantidad de monedas
            cantidad_cruda = monto_total_posicion / precio_actual
            
            # 6. AJUSTAR PRECISIÓN (Vital para que Binance no rechace la orden)
            cantidad_final = self.exchange.amount_to_precision(simbolo, cantidad_cruda)
            
            print(Fore.CYAN + f"🧮 Calculando {simbolo}: Balance ${balance:.1f} | Margen ${margen_usdt:.1f} | Posición Total ${monto_total_posicion:.1f}")

            return float(cantidad_final)

        except Exception as e:
            print(Fore.RED + f"❌ Error calculando cantidad: {e}")
            return 0.0

    def colocar_orden_mercado(self, simbolo, lado, cantidad):
        print(f"⚡ Enviando orden {lado.upper()} para {simbolo} (Cant: {cantidad})...")
        try:
            orden = self.exchange.create_order(
                symbol=simbolo,
                type='market',
                side=lado.lower(),
                amount=cantidad
            )
            precio_avg = orden.get('average', 'N/A')
            print(Fore.GREEN + f"✅ EJECUTADO: {lado.upper()} {cantidad} {simbolo} @ ${precio_avg}")
            return orden
        except Exception as e:
            print(Fore.RED + f"❌ FALLO AL EJECUTAR: {e}")
            return None
        
    def colocar_ordenes_salida(self, simbolo, lado_entrada, cantidad, precio_entrada, sl_pct, tp_pct):
        """
        Calcula y envía Stop Loss y Take Profit inmediatamente después de entrar.
        lado_entrada: 'buy' (Long) o 'sell' (Short)
        """
        try:
            # 1. Definir dirección de salida (Si entré BUY, salgo con SELL)
            lado_salida = 'sell' if lado_entrada == 'buy' else 'buy'
            
            # 2. Calcular Precios
            if lado_entrada == 'buy': # LONG
                precio_sl = precio_entrada * (1 - sl_pct)
                precio_tp = precio_entrada * (1 + tp_pct)
            else: # SHORT
                precio_sl = precio_entrada * (1 + sl_pct)
                precio_tp = precio_entrada * (1 - tp_pct)

            # Redondear precios a la precisión del mercado (Vital para Binance)
            precio_sl = self.exchange.price_to_precision(simbolo, precio_sl)
            precio_tp = self.exchange.price_to_precision(simbolo, precio_tp)

            print(Fore.YELLOW + f"🛡️ Protegiendo {simbolo}: SL en {precio_sl} | TP en {precio_tp}")

            # 3. Enviar Orden STOP LOSS
            self.exchange.create_order(
                symbol=simbolo,
                type='STOP_MARKET',
                side=lado_salida,
                amount=cantidad,
                params={'stopPrice': precio_sl, 'reduceOnly': True}
            )
            print(Fore.GREEN + f"✅ Stop Loss colocado.")

            # 4. Enviar Orden TAKE PROFIT
            self.exchange.create_order(
                symbol=simbolo,
                type='TAKE_PROFIT_MARKET',
                side=lado_salida,
                amount=cantidad,
                params={'stopPrice': precio_tp, 'reduceOnly': True}
            )
            print(Fore.GREEN + f"✅ Take Profit colocado.")
            
            return True

        except Exception as e:
            print(Fore.RED + f"❌ Error colocando protecciones (PELIGRO): {e}")
            return False
        
    def obtener_posicion_abierta(self, simbolo):
        """
        Consulta Inteligente: Detecta formatos complejos como 'BTC/USDT:USDT'.
        """
        try:
            # Traemos todas las posiciones
            posiciones = self.exchange.fetch_positions()
            
            for pos in posiciones:
                symbol_api = pos['symbol']  # Ej: 'BTC/USDT:USDT'
                
                # LÓGICA DE COINCIDENCIA:
                es_el_mismo = (symbol_api == simbolo) or (symbol_api.startswith(simbolo + ":"))
                
                if es_el_mismo:
                    cantidad = float(pos['contracts']) 
                    if abs(cantidad) > 0:
                        return True # ¡Encontrado!

            return False

        except Exception as e:
            print(Fore.RED + f"⚠️ Error consultando posición de {simbolo}: {e}")
            return False
        
    # --- MÉTODOS PARA TRAILING STOP ---

    def obtener_datos_posicion(self, simbolo):
        """
        Devuelve datos críticos para calcular el Trailing Stop.
        """
        try:
            # Normalización de símbolo para búsqueda robusta
            target = simbolo.replace('/', '').upper()
            posiciones = self.exchange.fetch_positions()
            
            for pos in posiciones:
                s_api = pos['symbol'].replace('/', '').upper()
                if s_api == target or s_api.startswith(target + ":"):
                    
                    amt = float(pos['contracts'])
                    
                    if abs(amt) > 0:
                        # --- CORRECCIÓN DE LADO (FIX) ---
                        lado_api = pos.get('side') 
                        if not lado_api:
                             raw_amt = float(pos['info']['positionAmt'])
                             lado_final = 'buy' if raw_amt > 0 else 'sell'
                        else:
                             lado_final = 'buy' if lado_api == 'long' else 'sell'
                        
                        return {
                            'entryPrice': float(pos['entryPrice']),
                            'amount': abs(amt),
                            'side': lado_final,
                            'markPrice': float(pos.get('markPrice', 0))
                        }
            return None
        except Exception as e:
            print(Fore.RED + f"⚠️ Error obteniendo datos posición {simbolo}: {e}")
            return None

    def obtener_orden_stop_loss(self, simbolo):
        """
        Busca la ID de la orden STOP_MARKET activa.
        CORREGIDO: Ahora detecta Stop Loss incluso si están en ganancia (Stop Profit).
        """
        try:
            pos = self.obtener_datos_posicion(simbolo)
            if not pos: return None
            
            ordenes = self.exchange.fetch_open_orders(simbolo)
            for o in ordenes:
                tipo = o.get('type', '').upper()
                reduce = o.get('reduceOnly', False)
                
                # Filtro ÚNICO: Tipo correcto y flag de reducción
                # Sin filtrar por precio para aceptar Stop Profit
                if (tipo == 'STOP_MARKET' or tipo == 'STOP') and reduce:
                    return o

            return None
        except Exception as e:
            print(Fore.RED + f"⚠️ Error buscando Stop Loss de {simbolo}: {e}")
            return None

    def modificar_stop_loss(self, simbolo, orden_id, nuevo_precio_stop, lado_posicion):
        """
        MODIFICACIÓN CON FILTRO DE IDENTIDAD Y ROLLBACK DE SEGURIDAD.
        """
        cantidad_original = 0.0
        precio_stop_original = 0.0
        lado_orden = 'sell' if lado_posicion == 'buy' else 'buy'

        try:
            # 1. PREPARACIÓN Y RESPALDO
            precio_flotante = float(nuevo_precio_stop)
            nuevo_precio = self.exchange.price_to_precision(simbolo, precio_flotante)
            
            # Respaldo de datos de la orden actual antes de cancelarla
            try:
                orden_vieja = self.exchange.fetch_order(orden_id, simbolo)
                cantidad_original = float(orden_vieja['amount'])
                precio_stop_original = float(orden_vieja['stopPrice'])
            except Exception as e:
                print(Fore.RED + f"❌ Error leyendo orden vieja (abortando): {e}")
                return False

            print(Fore.MAGENTA + f"🔄 Trailing: Moviendo SL de {simbolo} (${precio_stop_original} -> ${nuevo_precio})")

            # 2. CANCELACIÓN
            try:
                self.exchange.cancel_order(orden_id, simbolo)
            except Exception as e:
                print(Fore.YELLOW + f"⚠️ No se pudo cancelar orden vieja: {e}")

            # 3. CREACIÓN DE LA NUEVA ORDEN (TRAILING)
            try:
                nueva_orden = self.exchange.create_order(
                    symbol=simbolo,
                    type='STOP_MARKET',
                    side=lado_orden,
                    amount=cantidad_original,
                    params={
                        'stopPrice': nuevo_precio,
                        'reduceOnly': True
                    }
                )
                print(Fore.GREEN + f"✅ Trailing exitoso. Nuevo ID: {nueva_orden['id']}")
                return True

            except Exception as error_creacion:
                # 🚨 ROLLBACK DE EMERGENCIA 🚨
                print(Fore.RED + f"❌ FALLÓ TRAILING: {error_creacion}")
                print(Fore.YELLOW + "🛡️ RESTAURANDO SL ORIGINAL PARA PROTEGER LA CUENTA...")
                
                try:
                    self.exchange.create_order(
                        symbol=simbolo,
                        type='STOP_MARKET',
                        side=lado_orden,
                        amount=cantidad_original,
                        params={
                            'stopPrice': self.exchange.price_to_precision(simbolo, precio_stop_original),
                            'reduceOnly': True
                        }
                    )
                    print(Fore.GREEN + f"✅ ROLLBACK EXITOSO: SL restaurado en ${precio_stop_original}")
                except Exception as error_rollback:
                    print(Fore.RED + f"💀 ERROR CATASTRÓFICO: Posición desprotegida en {simbolo}. {error_rollback}")
                
                return False

        except Exception as e:
            print(Fore.RED + f"❌ Error general en modificación: {e}")
            return False
            
    # --- NUEVO MÉTODO PARA VALIDACIÓN PERIÓDICA ---
    def obtener_todos_simbolos_con_posicion(self):
        """
        Devuelve una LISTA de los símbolos que tienen posiciones abiertas (contratos > 0).
        Optimizado para hacer 1 sola petición a la API.
        """
        try:
            posiciones = self.exchange.fetch_positions()
            simbolos_activos = []
            
            for pos in posiciones:
                if float(pos['contracts']) > 0:
                    raw_symbol = pos['symbol'] # Ej: 'BTC/USDT:USDT'
                    simbolo_limpio = raw_symbol.split(':')[0] 
                    simbolos_activos.append(simbolo_limpio)
            
            return simbolos_activos
            
        except Exception as e:
            print(Fore.RED + f"⚠️ Error en validación masiva de posiciones: {e}")
            return []

    def cancelar_ordenes_pendientes(self, simbolo):
        """
        Limpieza: Borra todas las órdenes abiertas (TP, SL, Limit) de un par.
        """
        try:
            print(f"🧹 Limpiando órdenes huérfanas en {simbolo}...")
            self.exchange.cancel_all_orders(simbolo)
            return True
        except Exception as e:
            return False