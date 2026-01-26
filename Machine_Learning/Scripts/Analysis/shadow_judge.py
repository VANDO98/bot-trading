import sys
import os
import sqlite3
import time
from datetime import datetime, timedelta
from colorama import Fore, init

# Init colorama
init(autoreset=True)

# Add root path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.append(ROOT_DIR)

from Core.API.GestorWebsocket import GestorWebsocket
from Core.Utils.ShadowLogger import ShadowLogger

class ShadowJudge:
    def __init__(self):
        self.db_path = ShadowLogger.DB_PATH
        self.gestor = GestorWebsocket()
        
    def _conectar(self):
        return sqlite3.connect(self.db_path)

    def run_analysis(self, hours_forward=24, min_roe=10.0):
        """
        Analiza operaciones PENDING en la base de datos.
        min_roe: Porcentaje de ROE mínimo para considerar 'Oportunidad Perdida' (False Negative).
        """
        print(f"{Fore.CYAN}⚖️ Iniciando Shadow Judge (Análisis SQLite)...")
        print(f"   ⏱️ Ventana: {hours_forward}h | 🎯 Meta ROE: {min_roe}%")
        
        if not os.path.exists(self.db_path):
            print(f"{Fore.RED}❌ No se encontró la base de datos: {self.db_path}")
            return

        conn = self._conectar()
        conn.row_factory = sqlite3.Row # Para acceder por nombre de columna
        cursor = conn.cursor()
        
        # 1. Obtener Pendientes
        cursor.execute("SELECT * FROM shadow_trades WHERE status = 'PENDING'")
        rows = cursor.fetchall()
        
        print(f"📄 Pendientes de análisis: {len(rows)}")
        
        pnl_total_potencial = 0.0
        
        for row in rows:
            trade_id = row['id']
            simbolo = row['symbol']
            senal = row['signal']
            timestamp_str = row['timestamp']
            
            try:
                # Parsear fecha
                dt_obj = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                
                # Check de Madurez
                tiempo_madurez = dt_obj + timedelta(hours=hours_forward)
                if datetime.now() < tiempo_madurez:
                    # Aún no maduro, saltar silenciosamente o con log debug
                    continue
                
                # Descargar velas
                start_ms = int(dt_obj.timestamp() * 1000)
                end_ms = int((dt_obj + timedelta(hours=hours_forward)).timestamp() * 1000)
                
                print(f"   🔍 Analizando ID {trade_id} | {simbolo} ({timestamp_str})...")
                velas = self.gestor.obtener_velas_rango(simbolo, '5m', start_ms, end_ms)
                
                if not velas:
                    print(f"      ⚠️ Sin datos históricos.")
                    continue
                    
                # Extraer datos
                sl_teorico = row['sl_theoretical']
                tp_teorico = row['tp_theoretical']
                apalancamiento = row['leverage'] if row['leverage'] else 1.0
                precio_entrada = row['price']
                
                outcome = "NEUTRAL"
                max_roe_reached = -999.0
                
                # Simulación
                for v in velas:
                    low = float(v['l'])
                    high = float(v['h'])
                    
                    if senal == "COMPRA":
                        if low <= sl_teorico:
                            roe_loss = ((sl_teorico - precio_entrada) / precio_entrada) * apalancamiento * 100
                            max_roe_reached = roe_loss 
                            outcome = "TRUE_NEGATIVE"
                            break
                        
                        roe_high = ((high - precio_entrada) / precio_entrada) * apalancamiento * 100
                        if roe_high > max_roe_reached: max_roe_reached = roe_high
                            
                        if high >= tp_teorico or roe_high >= min_roe:
                            outcome = "FALSE_NEGATIVE"
                            break
                            
                    elif senal == "VENTA":
                        if high >= sl_teorico:
                            roe_loss = ((precio_entrada - sl_teorico) / precio_entrada) * apalancamiento * 100
                            max_roe_reached = roe_loss
                            outcome = "TRUE_NEGATIVE"
                            break
                        
                        roe_low = ((precio_entrada - low) / precio_entrada) * apalancamiento * 100
                        if roe_low > max_roe_reached: max_roe_reached = roe_low
                            
                        if low <= tp_teorico or roe_low >= min_roe:
                            outcome = "FALSE_NEGATIVE"
                            break
                
                # Log Visual
                color = Fore.GREEN if outcome == 'TRUE_NEGATIVE' else Fore.RED if outcome == 'FALSE_NEGATIVE' else Fore.YELLOW
                print(f"      👉 Veredicto: {color}{outcome} (Max ROE: {max_roe_reached:.2f}%)")
                
                # Actualizar DB (Atomic Update)
                cursor.execute('''
                    UPDATE shadow_trades 
                    SET judge_verdict = ?, max_roe = ?, status = 'PROCESSED', analysis_timestamp = ?
                    WHERE id = ?
                ''', (
                    outcome, 
                    round(max_roe_reached, 2), 
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                    trade_id
                ))
                conn.commit()
                
                # Rate limit
                time.sleep(0.1)

            except Exception as e:
                print(f"{Fore.RED}      ❌ Error analizando ID {trade_id}: {e}")
        
        conn.close()
        print(f"\n{Fore.GREEN}✅ Ciclo de análisis completado.")

if __name__ == "__main__":
    judge = ShadowJudge()
    judge.run_analysis()
