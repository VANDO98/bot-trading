from abc import ABC, abstractmethod

class GestorEjecucionBase(ABC):
    """
    Interfaz abstracta para los gestores de ejecución.
    Garantiza que tanto el paper trading como la ejecución real implementen
    los mismos métodos requeridos por el bot.
    """
    
    @abstractmethod
    def configurar_apalancamiento(self, simbolo, nivel):
        pass

    @abstractmethod
    def obtener_balance_usdt(self):
        # Nota: Paper trading tiene su propio "balance virtual"
        pass

    @abstractmethod
    def calcular_cantidad_por_porcentaje(self, simbolo, porcentaje_str, precio_actual, apalancamiento):
        # Devuelve cantidad de assets (monedas)
        pass

    @abstractmethod
    def colocar_orden_mercado(self, simbolo, lado, cantidad):
        # Debe devolver un dict con info de la orden o None
        pass

    @abstractmethod
    def colocar_ordenes_salida(self, simbolo, lado_entrada, cantidad, precio_entrada, sl_pct, tp_pct):
        # Devuelve True/False
        pass

    @abstractmethod
    def obtener_posicion_abierta(self, simbolo):
        # Devuelve True si hay posición, False si no
        pass

    @abstractmethod
    def obtener_datos_posicion(self, simbolo):
        # Devuelve dict: {'entryPrice', 'amount', 'side', 'markPrice'} o None
        pass
    
    @abstractmethod
    def obtener_orden_stop_loss(self, simbolo):
        # Devuelve objeto orden o None
        pass

    @abstractmethod
    def modificar_stop_loss(self, simbolo, orden_id, nuevo_precio_stop, lado_posicion):
        # Devuelve True/False
        pass

    @abstractmethod
    def obtener_todos_simbolos_con_posicion(self):
        # Devuelve lista [BTCUSDT, ETHUSDT...]
        pass

    @abstractmethod
    def cancelar_ordenes_pendientes(self, simbolo):
        # Devuelve True/False
        pass

    @abstractmethod
    def ejecutar_cierre_parcial(self, simbolo, cantidad_reduccion, lado_actual, tipo_orden='market'):
        """
        [NUEVO] Cierra parcialmente una posición y reajusta Stop Loss.
        """
        pass

    def chequear_cierres_con_vela(self, simbolo, kline):
        """
        [Opcional] Para Paper Trading avanzado.
        Permite validar si un mechazo tocó el SL/TP dentro de la vela.
        Por defecto no hace nada en ejecución real (el Exchange se encarga).
        """
        pass
