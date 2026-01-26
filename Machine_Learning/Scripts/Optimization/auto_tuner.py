import os
import sys
import json
import sqlite3
import shutil
from datetime import datetime
from colorama import Fore, init

init(autoreset=True)

# Path Setup
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.append(ROOT_DIR)

from Core.Utils.ShadowLogger import ShadowLogger

# ==========================================
# ⚙️ CONFIGURACIÓN DEL AUTO-TUNER
# ==========================================
ENABLE_AUTOTUNER = False  # MASTER SWITCH: Si es False, solo reporta.

WINDOW_SIZE = 20         # Últimos N trades por par para analizar
MIN_TRADES_REQUIRED = 5  # Mínimo de trades para tomar decisión

# Reglas de FNR (False Negative Rate)
# FNR = (Ganadoras Rechazadas) / (Total Rechazadas)
FNR_HIGH_THRESHOLD = 0.60  # Si > 60% eran buenas -> Bajar umbral (ser menos miedoso)
FNR_LOW_THRESHOLD = 0.10   # Si < 10% eran buenas -> Subir umbral (ser más selectivo)

STEP_ADJUST = 0.05         # Cuánto mover el umbral
MIN_ML_THRESHOLD = 0.45    # Límite inferior de seguridad
MAX_ML_THRESHOLD = 0.95    # Límite superior

CONFIG_PATH = os.path.join(ROOT_DIR, 'config_trading.json')

class AutoTuner:
    def __init__(self):
        self.db_path = ShadowLogger.DB_PATH
        
    def _conectar(self):
        return sqlite3.connect(self.db_path)

    def run_tuning_cycle(self):
        print(f"\n{Fore.CYAN}🔧 Iniciando Auto-Tuner V1.0")
        print(f"   Master Switch: {'🟢 ON' if ENABLE_AUTOTUNER else '🔴 OFF (Dry Run)'}")
        
        if not os.path.exists(self.db_path):
            print("❌ Base de datos no encontrada.")
            return

        # 1. Obtener lista de símbolos que tenemos en DB
        conn = self._conectar()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT DISTINCT symbol FROM shadow_trades")
        rows = cursor.fetchall()
        simbolos = [r['symbol'] for r in rows]
        
        print(f"   Pares detectados en historia: {simbolos}")
        
        cambios_propuestos = {} # { 'BTC/USDT': 0.70 }
        
        for par in simbolos:
            self._analizar_par(conn, par, cambios_propuestos)
            
        conn.close()
        
        # 4. Aplicar Cambios si enabled
        if cambios_propuestos:
            self._aplicar_cambios(cambios_propuestos)
        else:
            print(f"\n✅ Análisis completado. No se requieren cambios.")

    def _analizar_par(self, conn, sub_simbolo, cambios_dict):
        """Analiza estadísticas de un par específico."""
        cursor = conn.cursor()
        
        # Traer últimos N procesados
        query = '''
            SELECT judge_verdict 
            FROM shadow_trades 
            WHERE symbol = ? AND status = 'PROCESSED' 
            ORDER BY id DESC LIMIT ?
        '''
        cursor.execute(query, (sub_simbolo, WINDOW_SIZE))
        rows = cursor.fetchall()
        
        total_analizados = len(rows)
        if total_analizados < MIN_TRADES_REQUIRED:
            print(f"   ℹ️ {sub_simbolo}: Pocos datos ({total_analizados}/{MIN_TRADES_REQUIRED}). Skip.")
            return

        # Calcular métricas
        false_negatives = sum(1 for r in rows if r['judge_verdict'] == 'FALSE_NEGATIVE')
        # true_negatives = sum(1 for r in rows if r['judge_verdict'] == 'TRUE_NEGATIVE')
        
        fnr = false_negatives / total_analizados
        print(f"   📊 {sub_simbolo}: FNR = {fnr:.2f} ({false_negatives}/{total_analizados} oportunidades perdidas)")
        
        # Leer config actual para ese par
        current_config = self._leer_config_actual(sub_simbolo)
        if not current_config: 
            return
            
        current_threshold = current_config.get('ml_threshold', 0.80) # Default si no existe
        
        # Lógica de Decisión
        nuevo_threshold = current_threshold
        accion = "MANTENER"
        
        if fnr > FNR_HIGH_THRESHOLD:
            # El bot está rechazando demasiadas buenas -> BAJAR umbral
            nuevo_threshold = max(MIN_ML_THRESHOLD, current_threshold - STEP_ADJUST)
            if nuevo_threshold != current_threshold:
                accion = "BAJAR (Menos estricto)"
                
        elif fnr < FNR_LOW_THRESHOLD:
            # El bot casi nunca se equivoca al rechazar, quizás está aceptando basura -> SUBIR umbral
            # (Esta lógica asume que queremos optimizar shadow, pero cuidado con matar el winrate real)
            # Por seguridad, solo subimos si está muy bajo.
            nuevo_threshold = min(MAX_ML_THRESHOLD, current_threshold + STEP_ADJUST)
            if nuevo_threshold != current_threshold:
                accion = "SUBIR (Más estricto)"
        
        if nuevo_threshold != current_threshold:
            print(f"      💡 SUGERENCIA: {accion} umbral de {current_threshold:.2f} -> {nuevo_threshold:.2f}")
            cambios_dict[sub_simbolo] = nuevo_threshold
        else:
            print(f"      OK. Umbral {current_threshold:.2f} parece óptimo.")

    def _leer_config_actual(self, simbolo):
        """Lee el JSON y extrae la config del par."""
        try:
            with open(CONFIG_PATH, 'r') as f:
                data = json.load(f)
            return data.get('pares', {}).get(simbolo, {})
        except Exception:
            return None

    def _aplicar_cambios(self, cambios):
        """Escribe en el JSON de configuración de forma segura."""
        print(f"\n📝 Preparando actualización de {len(cambios)} pares...")
        
        if not ENABLE_AUTOTUNER:
            print(f"{Fore.YELLOW}⚠️ MODO DRY-RUN: No se modificarán archivos. Activa ENABLE_AUTOTUNER=True para aplicar.")
            return

        # 1. Backup
        backup_path = CONFIG_PATH + ".bak"
        try:
            shutil.copyfile(CONFIG_PATH, backup_path)
            print(f"   💾 Backup creado: {backup_path}")
        except Exception as e:
            print(f"   ❌ Falló el backup. Abortando por seguridad: {e}")
            return

        # 2. Modificación Atómica (Load -> Modify -> Save)
        try:
            with open(CONFIG_PATH, 'r') as f:
                full_config = json.load(f)
            
            for simbolo, nuevo_valor in cambios.items():
                if simbolo in full_config['pares']:
                    old = full_config['pares'][simbolo].get('ml_threshold', 'N/A')
                    full_config['pares'][simbolo]['ml_threshold'] = round(nuevo_valor, 2)
                    print(f"   ✅ {simbolo}: {old} -> {nuevo_valor:.2f}")
            
            with open(CONFIG_PATH, 'w') as f:
                json.dump(full_config, f, indent=4)
                
            print(f"{Fore.GREEN}🎉 Configuración actualizada exitosamente.")
            
        except Exception as e:
            print(f"{Fore.RED}❌ Error grave escribiendo config: {e}")
            print(f"   Restaurando backup...")
            shutil.copyfile(backup_path, CONFIG_PATH)


if __name__ == "__main__":
    tuner = AutoTuner()
    tuner.run_tuning_cycle()
