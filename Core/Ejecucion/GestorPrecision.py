from Core.API.BinanceBase import BinanceBase

class GestorPrecision(BinanceBase):
    """
    Gestor de Precisión (Adaptado a tu BinanceBase con python-binance).
    Obtiene los decimales OFICIALES directamente de la API.
    """
    def __init__(self, symbol):
        # 1. Inicializamos la base (Carga Config y conecta self.client)
        super().__init__()
        
        self.symbol = symbol
        
        # Valores por defecto (Seguridad)
        self.decimales_precio = 2
        self.decimales_cantidad = 3
        self.tick_size = 0.01
        self.step_size = 0.001
        
        self.detectado = False

    def detectar(self):
        """Descarga la configuración oficial del par desde Binance."""
        try:
            # USAMOS LA LIBRERÍA (python-binance) que ya instanció BinanceBase
            info = self.client.futures_exchange_info()
            
            for s in info['symbols']:
                if s['symbol'] == self.symbol:
                    # --- AQUI ESTÁ LA RESPUESTA A TU PREGUNTA ---
                    # Binance nos dice exactamente cuántos decimales usar
                    self.decimales_cantidad = int(s['quantityPrecision'])
                    self.decimales_precio = int(s['pricePrecision'])

                    # También guardamos los filtros por si acaso
                    for f in s['filters']:
                        if f['filterType'] == 'PRICE_FILTER':
                            self.tick_size = float(f['tickSize'])
                        elif f['filterType'] == 'LOT_SIZE':
                            self.step_size = float(f['stepSize'])
                    
                    self.detectado = True
                    print(f"✅ Precisión {self.symbol}: Precio={self.decimales_precio} dec, Cantidad={self.decimales_cantidad} dec")
                    return True
            
            print(f"⚠️ No se encontró información para el par {self.symbol}")
            return False

        except Exception as e:
            print(f"⚠️ Error obteniendo precisión: {e}")
            # Fallback de emergencia para no detener el bot
            if 'DOGE' in self.symbol: self.decimales_cantidad = 0
            return False

    def redondear_precio(self, precio):
        """Redondea el precio al número exacto de decimales permitidos."""
        if self.decimales_precio == 0:
            return int(round(precio))
        return float(f"{precio:.{self.decimales_precio}f}")

    def redondear_cantidad(self, cantidad):
        """Redondea la cantidad (monedas) al número exacto de decimales permitidos."""
        if self.decimales_cantidad == 0:
            return int(cantidad)
        return float(f"{cantidad:.{self.decimales_cantidad}f}")