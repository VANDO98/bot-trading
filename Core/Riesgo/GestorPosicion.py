import time
import hmac
import hashlib
import requests
from urllib.parse import urlencode
from binance.enums import ORDER_TYPE_MARKET
from Core.Utils.Config import Config

class GestorPosicion:
    """
    Dueño de la 'Verdad Financiera'.
    Versión: Compatible con arquitectura vando98.
    """
    def __init__(self, gestor_basico):
        self.basico = gestor_basico
        self.client = gestor_basico.api # Acceso directo al cliente de python-binance

    def iniciar_protocolo_seguridad(self, symbol):
        """
        Se ejecuta AL INICIO del bot para cada par.
        """
        print(f"🛡️  [SEGURIDAD] Auditando estado real de {symbol}...")
        
        # 1. Obtener la verdad desnuda de Binance
        posicion = self._obtener_posicion_real(symbol)
        
        if not posicion:
            print(f"   ✅ {symbol}: Sin posiciones abiertas. Todo limpio.")
            return

        # 2. Si hay posición, entramos en MODO EMERGENCIA
        print(f"   ⚠️ {symbol}: POSICIÓN DETECTADA. Iniciando protocolo de saneamiento.")
        
        cantidad = float(posicion['positionAmt'])
        precio_entrada = float(posicion['entryPrice'])
        precio_actual = float(posicion['markPrice'])
        lado = "LONG" if cantidad > 0 else "SHORT"
        
        # 3. Limpieza de Órdenes Antiguas (Doble Barrido)
        self._limpiar_ordenes_zombie(symbol)

        # 4. Cálculo del Límite de Dolor (-1%)
        porcentaje_max_loss = 0.01 
        
        precio_limite = 0.0
        side_cierre = ""
        esta_fuera_de_limite = False

        if lado == "LONG":
            precio_limite = precio_entrada * (1 - porcentaje_max_loss)
            esta_fuera_de_limite = precio_actual < precio_limite
            side_cierre = "SELL"
        else: # SHORT
            precio_limite = precio_entrada * (1 + porcentaje_max_loss)
            esta_fuera_de_limite = precio_actual > precio_limite
            side_cierre = "BUY"

        # 5. Ejecución de la Regla de Seguridad
        if esta_fuera_de_limite:
            print(f"   🚨 {symbol}: La pérdida actual excede el 1%. CERRANDO POSICIÓN AHORA.")
            self._cerrar_posicion_mercado(symbol, side_cierre, abs(cantidad))
        else:
            print(f"   🛡️ {symbol}: Posición recuperable. Colocando STOP LOSS de emergencia al -1%.")
            print(f"      • Entrada: {precio_entrada} | Stop: {precio_limite:.2f}")
            self._colocar_stop_emergencia(symbol, side_cierre, precio_limite)

    def _obtener_posicion_real(self, symbol):
        try:
            info = self.client.futures_position_information(symbol=symbol)
            for p in info:
                if float(p['positionAmt']) != 0:
                    return {
                        'positionAmt': p['positionAmt'],
                        'entryPrice': p['entryPrice'],
                        'markPrice': p['markPrice']
                    }
            return None
        except Exception as e:
            print(f"❌ Error leyendo API: {e}")
            return None

    def _limpiar_ordenes_zombie(self, symbol):
        """
        Elimina TANTO órdenes estándar como 'Algo Orders' (Conditional).
        Usa requests directo para máxima fiabilidad con el endpoint nuevo.
        """
        print(f"   🧹 Iniciando limpieza profunda de órdenes en {symbol}...")
        try:
            # A) Limpieza Estándar (Librería)
            self.client.futures_cancel_all_open_orders(symbol=symbol)
            
            # B) Limpieza de Algo Orders (Manual REST para evitar bugs de librería)
            self._borrar_algo_orders_manual(symbol)

            time.sleep(2)
            print(f"   ✅ Mesa limpia.")

        except Exception as e:
            print(f"   ❌ Error en limpieza general: {e}")

    def _borrar_algo_orders_manual(self, symbol):
        """
        Petición manual DELETE /fapi/v1/algoOpenOrders
        """
        try:
            base_url = Config.URL_FUTURES_TESTNET if Config.USAR_TESTNET else Config.URL_FUTURES_MAIN
            endpoint = "/fapi/v1/algoOpenOrders"
            
            params = {
                'symbol': symbol,
                'timestamp': int(time.time() * 1000),
                'recvWindow': 5000
            }
            
            # Firma Manual
            query_string = urlencode(params)
            signature = hmac.new(
                Config.BINANCE_SECRET_KEY.encode('utf-8'),
                query_string.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            url = f"{base_url}{endpoint}?{query_string}&signature={signature}"
            headers = {'X-MBX-APIKEY': Config.BINANCE_API_KEY}
            
            res = requests.delete(url, headers=headers)
            
            if res.status_code == 200:
                print("      • Algo Orders: Eliminadas (REST Manual).")
            elif res.status_code == 400 and -2011 in res.json().values():
                 print("      • Algo Orders: Ninguna pendiente.")
            else:
                 print(f"      • Aviso Algo: {res.json()}")

        except Exception as e:
            print(f"      • Error Algo Manual: {e}")

    def _cerrar_posicion_mercado(self, symbol, side, cantidad):
        try:
            self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type=ORDER_TYPE_MARKET,
                quantity=cantidad,
                reduceOnly=True
            )
            print(f"   ✅ {symbol}: Posición cerrada exitosamente.")
        except Exception as e:
            print(f"   ❌ FALLO AL CERRAR {symbol}: {e}")

    def _colocar_stop_emergencia(self, symbol, side, precio_stop):
        try:
            precio_str = "{:.2f}".format(precio_stop)
            
            self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type="STOP_MARKET",
                stopPrice=precio_str,
                closePosition=True
            )
            print(f"   ✅ {symbol}: Stop Loss de Emergencia colocado en {precio_str}.")
        except Exception as e:
            print(f"   ❌ FALLO AL COLOCAR STOP {symbol}: {e}")