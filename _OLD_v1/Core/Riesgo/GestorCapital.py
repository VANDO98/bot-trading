from Core.Utils.Config import Config

class GestorCapital:
    """
    Administrador de Fondos y Cupos.
    Responsabilidad: Asegurar que no se viole el límite de posiciones simultáneas.
    """
    def __init__(self, cliente_api):
        self.api = cliente_api.client
        self.max_posiciones = Config.MAX_POSICIONES # Generalmente 4

    def hay_cupo_disponible(self):
        """
        Consulta a la API cuántas posiciones tienen dinero invertido.
        Retorna True si hay espacio para operar.
        """
        try:
            posiciones_activas = 0
            info = self.api.futures_position_information()
            
            for p in info:
                # Si positionAmt es diferente de 0, es una posición abierta
                if float(p['positionAmt']) != 0:
                    posiciones_activas += 1
            
            if posiciones_activas >= self.max_posiciones:
                # Opcional: imprimir solo si hay intento de operación para no spammear logs
                return False
            
            return True

        except Exception as e:
            print(f"⚠️ Error verificando cupo de capital: {e}")
            # Ante la duda (error de red), por seguridad decimos que NO hay cupo
            return False

    def obtener_apalancamiento_actual(self, symbol):
        """Auxiliar para verificar configuración"""
        try:
            info = self.api.futures_position_information(symbol=symbol)
            if info and len(info) > 0:
                return int(info[0]['leverage'])
            return 1
        except:
            return 1