import sys
import os
import unittest
from colorama import Fore

# Importación hacky
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from Core.Ejecucion.GestorEjecucionPaper import GestorEjecucionPaper

class MockGestorDatos:
    def obtener_precio(self, simbolo):
        return 100.0

class TestPaperWicks(unittest.TestCase):
    def setUp(self):
        self.gestor = GestorEjecucionPaper(MockGestorDatos())
        # Simulamos una posición LONG
        # Entrada: 100
        # SL: 95
        # TP: 105
        self.simbolo = "BTCUSDT"
        self.gestor.posiciones[self.simbolo] = {
            'entryPrice': 100.0,
            'cantidad': 1,
            'side': 'buy',
            'sl_price': 95.0,
            'tp_price': 105.0
        }

    def test_wick_tp(self):
        """Vela abre en 100, toca 106 (TP), cierra en 102. Debería cerrar por TP."""
        kline = {'o': 100, 'h': 106, 'l': 99, 'c': 102}
        
        cerrado = self.gestor.chequear_cierres_con_vela(self.simbolo, kline)
        self.assertTrue(cerrado, "El TP debió activarse por el High (106)")
        self.assertNotIn(self.simbolo, self.gestor.posiciones, "La posición debió borrarse")
        
    def test_wick_sl(self):
        """Vela abre en 100, toca 90 (SL), cierra en 98. Debería cerrar por SL."""
        # Reiniciar posición
        self.setUp()
        kline = {'o': 100, 'h': 101, 'l': 90, 'c': 98}
        
        cerrado = self.gestor.chequear_cierres_con_vela(self.simbolo, kline)
        self.assertTrue(cerrado, "El SL debió activarse por el Low (90)")

    def test_no_activacion(self):
        """Vela se mueve dentro del rango (96-104), cierra en 100. No debe cerrar."""
        self.setUp()
        kline = {'o': 100, 'h': 104, 'l': 96, 'c': 100}
        
        cerrado = self.gestor.chequear_cierres_con_vela(self.simbolo, kline)
        self.assertFalse(cerrado, "No debió cerrar")
        self.assertIn(self.simbolo, self.gestor.posiciones, "La posición debe seguir viva")

if __name__ == '__main__':
    print(Fore.CYAN + "🧪 TEST DE WICKS EN PAPER TRADING...")
    unittest.main()
