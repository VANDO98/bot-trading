import os
import sys
import json
import sqlite3
import shutil
from datetime import datetime
from colorama import Fore, init
import requests
from dotenv import load_dotenv

load_dotenv() # Cargar variables de entorno (.env)

init(autoreset=True)

# Path Setup
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.append(ROOT_DIR)

from Core.Utils.ShadowLogger import ShadowLogger
from Machine_Learning.Scripts.Analysis.shadow_judge import ShadowJudge

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
MIN_ML_THRESHOLD = 0.37    # Límite inferior de seguridad
MAX_ML_THRESHOLD = 0.95    # Límite superior

CONFIG_PATH = os.path.join(ROOT_DIR, 'config_trading.json')

class AutoTuner:
    def __init__(self):
        self.db_path = ShadowLogger.DB_PATH
        self.telegram_token = os.getenv("TELEGRAM_TOKEN")
        self.telegram_id = os.getenv("TELEGRAM_ID")
        
    def _conectar(self):
        return sqlite3.connect(self.db_path)

    def _notificar_telegram(self, mensaje):
        """Envía alerta a Telegram si está configurado."""
        if not self.telegram_token or not self.telegram_id:
            return
            
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload = {
            "chat_id": self.telegram_id,
            "text": mensaje,
            "parse_mode": "Markdown"
        }
        try:
            requests.post(url, data=payload, timeout=5)
        except Exception as e:
            print(f"{Fore.RED}⚠️ Error enviando Telegram: {e}")

    def run_tuning_cycle(self):
        print(f"\n{Fore.CYAN}🔧 Iniciando Auto-Tuner V1.0")
        print(f"   Master Switch: {'🟢 ON' if ENABLE_AUTOTUNER else '🔴 OFF (Dry Run)'}")
        
        # 0. EJECUTAR JUEZ (Asegurar que los datos estén frescos)
        print(f"\n{Fore.YELLOW}⚖️ Invocando al Juez (ShadowJudge) antes de optimizar...")
        try:
            judge = ShadowJudge()
            judge.run_analysis()
        except Exception as e:
            print(f"{Fore.RED}❌ Error ejecutando Juez: {e}")
            # Continuamos, quizás hay datos viejos útiles
        
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
            # Intención: Bajar umbral para capturar más oportunidades
            proposed = current_threshold - STEP_ADJUST
            nuevo_threshold = max(MIN_ML_THRESHOLD, proposed)
            
            if nuevo_threshold < current_threshold:
                accion = "BAJAR (Menos estricto)"
            elif nuevo_threshold > current_threshold:
                accion = "SUBIR (Corrección a Mínimo Seguro)"
                
        elif fnr < FNR_LOW_THRESHOLD:
            # Intención: Subir umbral para filtrar mejor
            proposed = current_threshold + STEP_ADJUST
            nuevo_threshold = min(MAX_ML_THRESHOLD, proposed)
            
            if nuevo_threshold > current_threshold:
                accion = "SUBIR (Más estricto)"
            elif nuevo_threshold < current_threshold:
                accion = "BAJAR (Corrección a Máximo Seguro)"
        
        if nuevo_threshold != current_threshold:
            print(f"      💡 SUGERENCIA: {accion} umbral de {current_threshold:.2f} -> {nuevo_threshold:.2f}")
            cambios_dict[sub_simbolo] = nuevo_threshold
            
            # Notificación de Sugerencia (Solo si NO está habilitado el auto-tuner, para avisar humano)
            if not ENABLE_AUTOTUNER:
                msg = f"🔧 *Auto-Tuner Suggestion*\n\nPair: `{sub_simbolo}`\nFalse Negative Rate: `{fnr:.2f}`\nAction: *{accion}*\nChange: `{current_threshold}` -> `{nuevo_threshold}`\n\n_System is in Dry-Run mode._"
                self._notificar_telegram(msg)
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
                    
                    # Notificación de Cambio Aplicado
                    msg = f"🔧 *Auto-Tuner APPLIED*\n\nPair: `{simbolo}`\nOld Threshold: `{old}`\nNew Threshold: `{nuevo_valor:.2f}`\n\n_Configuration updated._"
                    self._notificar_telegram(msg)
            
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
