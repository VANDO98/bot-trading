import sqlite3
import os
from datetime import datetime
from colorama import Fore

class ShadowLogger:
    """
    Registra operaciones rechazadas ('Shadow Trades') en SQLite.
    Centraliza logs y resultados de análisis en una sola tabla.
    """
    
    # Rutas
    ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    DB_PATH = os.path.join(ROOT_DIR, "Machine_Learning", "Data", "shadow_data.db")

    @staticmethod
    def _conectar():
        """Crea la conexión y valida que la tabla exista."""
        conn = sqlite3.connect(ShadowLogger.DB_PATH)
        cursor = conn.cursor()
        
        # Schema con status 'PENDING' por defecto
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS shadow_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                symbol TEXT,
                signal TEXT,
                price REAL,
                ml_prob REAL,
                ml_threshold REAL,
                rejection_reason TEXT,
                strategy_name TEXT,
                atr REAL,
                sl_theoretical REAL,
                tp_theoretical REAL,
                leverage REAL,
                status TEXT DEFAULT 'PENDING',
                judge_verdict TEXT,
                max_roe REAL,
                analysis_timestamp TEXT
            )
        ''')
        conn.commit()
        return conn

    @staticmethod
    def registrar_rechazo(
        simbolo, 
        senal, 
        precio_entrada, 
        probabilidad, 
        umbral, 
        motivo, 
        estrategia_nombre,
        atr=0.0,
        sl_teorico=0.0,
        tp_teorico=0.0,
        apalancamiento=1.0
    ):
        """
        Inserta un nuevo registro en la BD con estado PENDING.
        """
        try:
            # Asegurar directorio (redundante pero seguro)
            os.makedirs(os.path.dirname(ShadowLogger.DB_PATH), exist_ok=True)
            
            conn = ShadowLogger._conectar()
            cursor = conn.cursor()
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            cursor.execute('''
                INSERT INTO shadow_trades (
                    timestamp, symbol, signal, price, ml_prob, ml_threshold, 
                    rejection_reason, strategy_name, atr, sl_theoretical, 
                    tp_theoretical, leverage
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                timestamp, simbolo, senal, precio_entrada, probabilidad, umbral,
                motivo, estrategia_nombre, atr, sl_teorico, tp_teorico, apalancamiento
            ))
            
            conn.commit()
            conn.close()
            
            print(f"{Fore.LIGHTBLACK_EX}🌑 Shadow Trade registrado en DB para {simbolo}")
                
        except Exception as e:
            print(f"{Fore.RED}⚠️ Error escribiendo Shadow Log en DB: {e}")
