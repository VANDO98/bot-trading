import json
import os

class Config:
    """
    Gestor de Configuración Centralizado.
    Lee el archivo config_trading.json para proveer datos a todo el bot.
    """
    
    # 1. Rutas Dinámicas (Funciona en Windows, Mac y Linux)
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    RUTA_CONFIG = os.path.join(BASE_DIR, 'config_trading.json')
    
    # Variable estática para acceso rápido
    USAR_TESTNET = True

    @staticmethod
    def _cargar_json():
        """Método interno seguro para leer el archivo"""
        try:
            with open(Config.RUTA_CONFIG, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data
        except FileNotFoundError:
            print(f"❌ Error Config: No encuentro el archivo en {Config.RUTA_CONFIG}")
            return {}
        except Exception as e:
            print(f"❌ Error Config: El JSON está mal formado ({e})")
            return {}

    @staticmethod
    def cargar_configuracion():
        """
        [NUEVO] Devuelve TODO el diccionario y ACTUALIZA flags globales.
        """
        data = Config._cargar_json()
        
        # --- CORRECCIÓN CRÍTICA ---
        # Actualizamos la variable estática INMEDIATAMENTE al leer el archivo.
        # Así, cualquier módulo que consulte Config.USAR_TESTNET después verá el valor real.
        if data:
            Config.USAR_TESTNET = data.get("usar_testnet", True)
            
        return data

    @staticmethod
    def obtener_pares_activos():
        """
        Devuelve un diccionario filtrado solo con los pares activos.
        """
        data = Config._cargar_json()
        
        # Actualizamos la variable global (para que GestorHibrido sepa a dónde conectar)
        # Nota: Ahora busca 'usar_testnet' en la raíz del JSON
        Config.USAR_TESTNET = data.get("usar_testnet", True)
        
        pares_raw = data.get("pares", {})
        pares_activos = {}
        
        for par, detalles in pares_raw.items():
            if detalles.get("activo", False):
                pares_activos[par] = detalles
                
        return pares_activos