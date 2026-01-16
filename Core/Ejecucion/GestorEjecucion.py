import os
import ccxt
from dotenv import load_dotenv
from Core.Utils.Config import Config
from colorama import Fore

load_dotenv()

class GestorEjecucion:
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

    # ... dentro de GestorEjecucion ...

    def configurar_apalancamiento(self, simbolo, nivel):
        """
        Cambia el apalancamiento (ej: 5x, 10x) en el exchange.
        """
        try:
            # Binance Futures necesita el simbolo sin barra (BTCUSDT) para este endpoint a veces,
            # pero ccxt suele manejarlo. Probamos el estándar.
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

    def calcular_cantidad_por_porcentaje(self, simbolo, porcentaje_str, precio_actual):
        """
        Calcula cuántas monedas comprar basado en un % del balance.
        Ej: "10%" de 1000 USDT con BTC a 50k -> Devuelve 0.002 BTC (ajustado).
        """
        try:
            # 1. Obtener balance disponible
            balance = self.obtener_balance_usdt()
            if balance <= 0: return 0.0

            # 2. Convertir "10%" a 0.10
            porcentaje = float(porcentaje_str.replace('%', '')) / 100
            
            # 3. Calcular cuánto USDT vamos a gastar
            monto_usdt = balance * porcentaje
            
            # (Seguridad) Binance suele pedir mínimo 5-10 USDT
            if monto_usdt < 6:
                print(Fore.YELLOW + f"⚠️ El {porcentaje_str} de tu cuenta (${monto_usdt:.2f}) es menor al mínimo ($6).")
                return 0.0

            # 4. Calcular cantidad de monedas (Ej: 100 USDT / 50000 = 0.002 BTC)
            cantidad_cruda = monto_usdt / precio_actual
            
            # 5. AJUSTAR PRECISIÓN (Vital para que Binance no rechace la orden)
            # ccxt tiene una función mágica para esto: amount_to_precision
            cantidad_final = self.exchange.amount_to_precision(simbolo, cantidad_cruda)
            
            return float(cantidad_final)

        except Exception as e:
            print(Fore.RED + f"❌ Error calculando porcentaje: {e}")
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
            # Usamos price_to_precision de CCXT
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
                # 1. Exacta: 'BTC/USDT' == 'BTC/USDT'
                # 2. Con sufijo: 'BTC/USDT:USDT' empieza con 'BTC/USDT'
                es_el_mismo = (symbol_api == simbolo) or (symbol_api.startswith(simbolo + ":"))
                
                if es_el_mismo:
                    cantidad = float(pos['contracts']) 
                    if abs(cantidad) > 0:
                        return True # ¡Encontrado!

            return False

        except Exception as e:
            print(Fore.RED + f"⚠️ Error consultando posición de {simbolo}: {e}")
            return False