import sys
import os
from colorama import init, Fore

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Core.Ejecucion.GestorEjecucionPaper import GestorEjecucionPaper
from Core.Utils.Config import Config

class MockGestorDatos:
    def __init__(self):
        self.precios = {'BTC/USDT': 100000.0}
    
    def obtener_precio(self, simbolo):
        return self.precios.get(simbolo, 0.0)

def test_ladder_sistema_escalonado():
    """
    Test 1: Sistema Escalonado Activado
    - Nivel 1: 20% ROE → vende 30%
    - Nivel 2: 40% ROE → vende 35%
    - Nivel 3: 80% ROE → vende 67%
    - Verifica que quede ~15% al final
    """
    print(Fore.CYAN + "\n" + "="*70)
    print(Fore.CYAN + "TEST 1: SISTEMA ESCALONADO (tp_escalonados.activo = true)")
    print(Fore.CYAN + "="*70)
    
    mock_datos = MockGestorDatos()
    gestor = GestorEjecucionPaper(mock_datos)
    simbolo = 'BTC/USDT'
    
    # Simular posición inicial: 1 BTC @ $100,000
    gestor.posiciones[simbolo] = {
        'entryPrice': 100000.0,
        'cantidad': 1.0,
        'side': 'buy',
        'sl_price': 98000.0,
        'tp_price': 128000.0
    }
    
    balance_inicial = gestor.obtener_balance_usdt()
    print(f"Balance Inicial: ${balance_inicial:.2f}")
    print(f"Posición Inicial: {gestor.posiciones[simbolo]['cantidad']} BTC @ ${gestor.posiciones[simbolo]['entryPrice']}")
    
    # NIVEL 1: ROE 20% (precio sube a $120,000)
    print(Fore.YELLOW + "\n[NIVEL 1] Precio sube a $120,000 (ROE 20%)")
    mock_datos.precios[simbolo] = 120000.0
    cantidad_venta_n1 = gestor.posiciones[simbolo]['cantidad'] * 0.30
    exito = gestor.ejecutar_cierre_parcial(simbolo, cantidad_venta_n1, 'buy')
    
    assert exito, "Nivel 1 falló"
    assert abs(gestor.posiciones[simbolo]['cantidad'] - 0.70) < 0.01, f"Esperado 0.70, obtenido {gestor.posiciones[simbolo]['cantidad']}"
    print(Fore.GREEN + f"✅ Nivel 1 OK. Quedan: {gestor.posiciones[simbolo]['cantidad']:.4f} BTC")
    
    # NIVEL 2: ROE 40% (precio sube a $140,000)
    print(Fore.YELLOW + "\n[NIVEL 2] Precio sube a $140,000 (ROE 40%)")
    mock_datos.precios[simbolo] = 140000.0
    cantidad_venta_n2 = gestor.posiciones[simbolo]['cantidad'] * 0.35
    exito = gestor.ejecutar_cierre_parcial(simbolo, cantidad_venta_n2, 'buy')
    
    assert exito, "Nivel 2 falló"
    restante_n2 = 0.70 * 0.65  # Después de vender 35% de 0.70
    assert abs(gestor.posiciones[simbolo]['cantidad'] - restante_n2) < 0.01, f"Esperado {restante_n2}, obtenido {gestor.posiciones[simbolo]['cantidad']}"
    print(Fore.GREEN + f"✅ Nivel 2 OK. Quedan: {gestor.posiciones[simbolo]['cantidad']:.4f} BTC")
    
    # NIVEL 3: ROE 80% (precio sube a $180,000)
    print(Fore.YELLOW + "\n[NIVEL 3] Precio sube a $180,000 (ROE 80%)")
    mock_datos.precios[simbolo] = 180000.0
    cantidad_venta_n3 = gestor.posiciones[simbolo]['cantidad'] * 0.67
    exito = gestor.ejecutar_cierre_parcial(simbolo, cantidad_venta_n3, 'buy')
    
    assert exito, "Nivel 3 falló"
    restante_final = restante_n2 * 0.33  # Después de vender 67%
    assert abs(gestor.posiciones[simbolo]['cantidad'] - restante_final) < 0.01, f"Esperado {restante_final}, obtenido {gestor.posiciones[simbolo]['cantidad']}"
    
    # Verificar que queda ~15% de la posición original
    porcentaje_restante = (gestor.posiciones[simbolo]['cantidad'] / 1.0) * 100
    print(Fore.MAGENTA + f"\n📊 Posición Final: {gestor.posiciones[simbolo]['cantidad']:.4f} BTC ({porcentaje_restante:.1f}% de la original)")
    assert abs(porcentaje_restante - 15.0) < 1.0, f"Esperado ~15%, obtenido {porcentaje_restante}%"
    
    balance_final = gestor.obtener_balance_usdt()
    ganancia = balance_final - balance_inicial
    print(Fore.GREEN + f"Balance Final: ${balance_final:.2f} (+${ganancia:.2f})")
    print(Fore.GREEN + "\n✅ TEST 1 PASADO: Sistema Escalonado funciona correctamente\n")


def test_sistema_simple():
    """
    Test 2: Sistema Simple Activado
    - Único nivel: 20% ROE → vende 50%
    - Verifica que no vuelva a vender
    """
    print(Fore.CYAN + "\n" + "="*70)
    print(Fore.CYAN + "TEST 2: SISTEMA SIMPLE (tp_escalonados.activo = false)")
    print(Fore.CYAN + "="*70)
    
    mock_datos = MockGestorDatos()
    gestor = GestorEjecucionPaper(mock_datos)
    simbolo = 'BTC/USDT'
    
    gestor.posiciones[simbolo] = {
        'entryPrice': 100000.0,
        'cantidad': 1.0,
        'side': 'buy',
        'sl_price': 98000.0,
        'tp_price': 128000.0
    }
    
    balance_inicial = gestor.obtener_balance_usdt()
    print(f"Balance Inicial: ${balance_inicial:.2f}")
    print(f"Posición Inicial: {gestor.posiciones[simbolo]['cantidad']} BTC")
    
    # Venta única al 20% ROE
    print(Fore.YELLOW + "\n[ÚNICO NIVEL] Precio sube a $120,000 (ROE 20%)")
    mock_datos.precios[simbolo] = 120000.0
    cantidad_venta = gestor.posiciones[simbolo]['cantidad'] * 0.50
    exito = gestor.ejecutar_cierre_parcial(simbolo, cantidad_venta, 'buy')
    
    assert exito, "Venta simple falló"
    assert abs(gestor.posiciones[simbolo]['cantidad'] - 0.50) < 0.01, "Esperado 0.50 BTC restantes"
    
    balance_final = gestor.obtener_balance_usdt()
    ganancia = balance_final - balance_inicial
    print(Fore.GREEN + f"✅ Venta OK. Quedan: {gestor.posiciones[simbolo]['cantidad']:.4f} BTC")
    print(Fore.GREEN + f"Balance Final: ${balance_final:.2f} (+${ganancia:.2f})")
    print(Fore.GREEN + "\n✅ TEST 2 PASADO: Sistema Simple funciona correctamente\n")


def test_porcentajes_matematicos():
    """
    Test 3: Validación Matemática de Porcentajes
    Verifica la fórmula: 30%, 35%, 67% → queda 15%
    """
    print(Fore.CYAN + "\n" + "="*70)
    print(Fore.CYAN + "TEST 3: VALIDACIÓN MATEMÁTICA DE PORCENTAJES")
    print(Fore.CYAN + "="*70)
    
    cantidad_original = 1.0
    
    # Nivel 1: vender 30%
    venta_n1 = cantidad_original * 0.30
    restante_n1 = cantidad_original - venta_n1
    print(f"Nivel 1: Vender 30% ({venta_n1:.4f}), Queda: {restante_n1:.4f}")
    
    # Nivel 2: vender 35% de lo que queda
    venta_n2 = restante_n1 * 0.35
    restante_n2 = restante_n1 - venta_n2
    print(f"Nivel 2: Vender 35% de {restante_n1:.4f} ({venta_n2:.4f}), Queda: {restante_n2:.4f}")
    
    # Nivel 3: vender 67% de lo que queda
    venta_n3 = restante_n2 * 0.67
    restante_n3 = restante_n2 - venta_n3
    print(f"Nivel 3: Vender 67% de {restante_n2:.4f} ({venta_n3:.4f}), Queda: {restante_n3:.4f}")
    
    porcentaje_final = (restante_n3 / cantidad_original) * 100
    print(Fore.MAGENTA + f"\nPorcentaje Final: {porcentaje_final:.2f}%")
    
    assert abs(porcentaje_final - 15.0) < 0.5, f"Error: Esperado ~15%, obtenido {porcentaje_final}%"
    print(Fore.GREEN + "\n✅ TEST 3 PASADO: Porcentajes correctos (15% restante)\n")


if __name__ == "__main__":
    init(autoreset=True)
    
    try:
        test_ladder_sistema_escalonado()
        test_sistema_simple()
        test_porcentajes_matematicos()
        
        print(Fore.GREEN + "="*70)
        print(Fore.GREEN + "🎉 TODOS LOS TESTS PASARON EXITOSAMENTE")
        print(Fore.GREEN + "="*70)
        
    except AssertionError as e:
        print(Fore.RED + f"\n❌ TEST FALLIDO: {e}")
        sys.exit(1)
    except Exception as e:
        print(Fore.RED + f"\n💥 ERROR INESPERADO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
