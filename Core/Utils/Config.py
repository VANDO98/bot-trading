import json
import os
from dotenv import load_dotenv

# Cargar variables de entorno (.env)
load_dotenv()

class Config:
    """
    Clase estática que carga la configuración UNA sola vez al inicio.
    """
    _config = {}
    
    # Rutas
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    CONFIG_FILE = os.path.join(BASE_DIR, 'config_trading.json')

    try:
        with open(CONFIG_FILE, 'r') as f:
            _config = json.load(f)
            print(f"✅ Configuración cargada desde: {CONFIG_FILE}")
    except Exception as e:
        print(f"❌ Error crítico cargando config_trading.json: {e}")
        _config = {}

    # --- Accesores Directos (Shortcuts) ---
    
    # 1. Modo de Ejecución
    MODO = _config.get('configuracion_global', {}).get('modo_ejecucion', 'dry_run')
    USAR_TESTNET = (MODO == 'testnet')
    
    # 2. Credenciales (Desde .env por seguridad)
    API_KEY = os.getenv('BINANCE_API_KEY')
    SECRET_KEY = os.getenv('BINANCE_SECRET_KEY')

    @classmethod
    def obtener_pares_activos(cls):
        """Devuelve un dict con solo los pares marcados como 'activo': true"""
        todos = cls._config.get('pares', {})
        return {k: v for k, v in todos.items() if v.get('activo', False)}

    @classmethod
    def obtener_config_estrategia(cls, par):
        return cls._config.get('pares', {}).get(par, {})