import pandas as pd
import time

class GestorVelas:
    """
    Gestor de Memoria de Mercado (Sliding Window).
    Mantiene siempre un Dataframe de exactamente 1000 velas.
    Optimizado para no re-procesar todo el historial, solo actualiza la punta.
    """
    def __init__(self, cliente_api):
        self.api = cliente_api.client
        self.historial = {} # Diccionario: {'BTCUSDT': DataFrame, ...}
        self.max_velas = 1000 # TU REQUISITO: Estandarizar a 1000 velas

    def inicializar_par(self, symbol, timeframe):
        """
        Descarga la foto inicial (Snapshot) de 1000 velas.
        """
        try:
            print(f"📥 Descargando {self.max_velas} velas iniciales para {symbol} ({timeframe})...")
            
            # Mapeo de intervalos
            interval_map = {
                "1m": self.api.KLINE_INTERVAL_1MINUTE,
                "5m": self.api.KLINE_INTERVAL_5MINUTE,
                "15m": self.api.KLINE_INTERVAL_15MINUTE,
                "1h": self.api.KLINE_INTERVAL_1HOUR,
                "4h": self.api.KLINE_INTERVAL_4HOUR,
            }
            
            # 1. Petición API (Pesada, solo se hace una vez al inicio)
            klines = self.api.futures_klines(
                symbol=symbol, 
                interval=interval_map.get(timeframe, "5m"), 
                limit=self.max_velas
            )
            
            # 2. Convertir a DataFrame ligero
            datos = []
            for k in klines:
                datos.append({
                    "timestamp": int(k[0]),
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                    "cerrada": True # Las históricas ya cerraron
                })
            
            df = pd.DataFrame(datos)
            
            # Optimizamos tipos de datos para gastar menos RAM
            df = df.astype({"open": "float64", "high": "float64", "low": "float64", "close": "float64", "volume": "float64"})
            
            self.historial[symbol] = df
            print(f"✅ {symbol}: Memoria inicializada con {len(df)} velas.")
            return True

        except Exception as e:
            print(f"❌ Error descargando velas de {symbol}: {e}")
            return False

    def actualizar_vela_en_tiempo_real(self, symbol, kline):
        """
        Método Quirúrgico: Recibe el dato del socket y opera sobre la última fila.
        NO descarga nada. NO recalcula todo el DataFrame.
        """
        if symbol not in self.historial:
            return

        df = self.historial[symbol]
        
        # Datos que llegan del WebSocket
        nuevo_timestamp = int(kline['t'])
        nueva_data = {
            "timestamp": nuevo_timestamp,
            "open": float(kline['o']),
            "high": float(kline['h']),
            "low": float(kline['l']),
            "close": float(kline['c']),
            "volume": float(kline['v']),
            "cerrada": kline['x'] # Bool: ¿Se cerró la vela ya?
        }

        # Lógica de "Costura" (Stitching)
        ultimo_timestamp = df.iloc[-1]['timestamp']

        if nuevo_timestamp == ultimo_timestamp:
            # ESCENARIO A: La vela sigue abierta (Estamos en el mismo minuto/periodo)
            # Solo actualizamos los valores de la última fila (Sobrescribir)
            # Usamos .iloc[-1] que es muy rápido
            for col, val in nueva_data.items():
                df.at[df.index[-1], col] = val
                
        elif nuevo_timestamp > ultimo_timestamp:
            # ESCENARIO B: Vela nueva (Cambio de turno)
            # 1. Agregamos la nueva fila al final
            df_nueva_fila = pd.DataFrame([nueva_data])
            # Usamos concat que es el estándar nuevo de pandas (append murió)
            df = pd.concat([df, df_nueva_fila], ignore_index=True)
            
            # 2. MANTENIMIENTO: Si nos pasamos de 1000, cortamos la cabeza (la más vieja)
            if len(df) > self.max_velas:
                df = df.iloc[1:].reset_index(drop=True)
                
            # Guardamos la referencia actualizada
            self.historial[symbol] = df
            
    def obtener_dataframe(self, symbol):
        return self.historial.get(symbol, None)

    def obtener_closes(self, symbol):
        """Helper rápido para indicadores"""
        if symbol in self.historial:
            return self.historial[symbol]['close'].values
        return []