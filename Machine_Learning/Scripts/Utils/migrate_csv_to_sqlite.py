import sqlite3
import pandas as pd
import os
import sys

# Ruta raíz
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.append(ROOT_DIR)

from Core.Utils.ShadowLogger import ShadowLogger

def migrate():
    print("📦 Iniciando migración CSV -> SQLite...")
    
    csv_path = os.path.join(ROOT_DIR, "Machine_Learning", "Logs", "shadow_trades.csv")
    results_path = os.path.join(ROOT_DIR, "Machine_Learning", "Logs", "shadow_results.csv")
    
    if not os.path.exists(csv_path):
        print("⚠️ No hay shadow_trades.csv para migrar.")
        return

    # 1. Cargar Logs originales (Manejo MANUAL robusto)
    # Pandas es quisquilloso con filas de diferente longitud (11 vs 12 columnas).
    # Lo haremos a la antigua: leer líneas, split y pad.
    
    data_rows = []
    with open(csv_path, 'r') as f:
        lines = f.readlines()
    
    # Saltamos encabezado (linea 0)
    for line in lines[1:]:
        parts = line.strip().split(',')
        if len(parts) < 11: continue # Linea vacia o rota
        
        # Si tiene 11 columnas, le falta apalancamiento -> agregar "1.0"
        if len(parts) == 11:
            parts.append("1.0")
            
        # Si tiene 12, está ok. Si tiene más, cortamos o dejamos (asumimos 12 max)
        # Limpiamos comillas si hubiera
        parts = [p.replace('"', '').strip() for p in parts]
        
        # Mapear a dict para facilitar DataFrame
        row_dict = {
            "timestamp": parts[0],
            "simbolo": parts[1],
            "senal": parts[2],
            "precio_entrada": float(parts[3]),
            "ml_prob": float(parts[4]),
            "ml_threshold": float(parts[5]),
            "motivo_rechazo": parts[6],
            "estrategia": parts[7],
            "atr": float(parts[8]) if parts[8] else 0.0,
            "sl_teorico": float(parts[9]) if parts[9] else 0.0,
            "tp_teorico": float(parts[10]) if parts[10] else 0.0,
            "apalancamiento": float(parts[11]) if parts[11] else 1.0
        }
        data_rows.append(row_dict)

    df_logs = pd.DataFrame(data_rows)
    print(f"📄 Procesados manualmente {len(df_logs)} registros.")
    
    # 2. Cargar Resultados existentes (si hay)
    # Si existe results log, intentamos cruzar datos.
    # El archivo de resultados tenía las mismas columnas + veredicto.
    # Así que lo mejor es usar el de resultados como fuente primaria si existe, 
    # ya que contiene TODO lo del log + el resultado.
    
    df_final = df_logs.copy()
    
    if os.path.exists(results_path):
        print(f"📄 Encontrado shadow_results.csv, usándolo para enriquecer datos...")
        df_results = pd.read_csv(results_path)
        
        # Como no tenemos ID, cruzamos por timestamp + simbolo (asumiendo unicidad suficiente)
        # O más simple: Si está en resultados, usamos resultados.
        # Vamos a asumir que results contiene un subconjunto de logs que YA fueron procesados.
        # Pero results.csv se generaba CONCATENANDO en los tests anteriores.
        
        # Estrategia:
        # Iterar sobre df_logs (todos los eventos).
        # Buscar match en df_results.
        # Si match -> status='PROCESSED', copiar veredicto.
        # Si no -> status='PENDING'.
        
        # Convertir a datetime para merge preciso
        df_logs['timestamp'] = pd.to_datetime(df_logs['timestamp'])
        df_results['timestamp'] = pd.to_datetime(df_results['timestamp'])
        
        # Verificar columnas disponibles
        available_cols = ['timestamp', 'simbolo', 'resultado_juez', 'analisis_timestamp']
        if 'max_roe' in df_results.columns:
            available_cols.append('max_roe')
        else:
            print("⚠️ 'max_roe' no encontrado en results. Se llenará con NaN.")
            
        # Hacemos un merge left
        df_merged = pd.merge(df_logs, df_results[available_cols], 
                             on=['timestamp', 'simbolo'], how='left')
        
        df_final = df_merged
    else:
        # Si no hay resultados, todo es PENDING
        df_final['resultado_juez'] = None
        df_final['max_roe'] = None
        df_final['analisis_timestamp'] = None

    # 3. Insertar en SQLite
    conn = ShadowLogger._conectar() # Esto crea la tabla si no existe
    cursor = conn.cursor()
    
    count = 0
    for _, row in df_final.iterrows():
        # Determinar status
        status = 'PROCESSED' if pd.notna(row['resultado_juez']) else 'PENDING'
        
        # Manejo de columnas que podrían faltar en CSVs viejos (apalancamiento)
        lev = row.get('apalancamiento', 1.0)
        if pd.isna(lev): lev = 1.0
        
        # Limpieza de valores NaN en general
        if pd.isna(row['atr']): row['atr'] = 0.0
        if pd.isna(row['sl_teorico']): row['sl_teorico'] = 0.0
        if pd.isna(row['tp_teorico']): row['tp_teorico'] = 0.0
        
        max_roe = row.get('max_roe')
        if pd.isna(max_roe): max_roe = None
        
        verdict = row.get('resultado_juez')
        if pd.isna(verdict): verdict = None
        
        ana_ts = row.get('analisis_timestamp')
        if pd.isna(ana_ts): ana_ts = None
        
        timestamp_str = row['timestamp'].strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute('''
            INSERT INTO shadow_trades (
                timestamp, symbol, signal, price, ml_prob, ml_threshold, 
                rejection_reason, strategy_name, atr, sl_theoretical, 
                tp_theoretical, leverage, status, judge_verdict, max_roe, analysis_timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            timestamp_str, row['simbolo'], row['senal'], row['precio_entrada'], 
            row['ml_prob'], row['ml_threshold'], row['motivo_rechazo'], 
            row['estrategia'], row['atr'], row['sl_teorico'], row['tp_teorico'], 
            lev, status, verdict, max_roe, ana_ts
        ))
        count += 1
        
    conn.commit()
    conn.close()
    
    print(f"✅ Migración completada. {count} registros insertados en DB.")
    
    # Renombrar CSV para evitar confusión (backup)
    os.rename(csv_path, csv_path + ".bak")
    if os.path.exists(results_path):
        os.rename(results_path, results_path + ".bak")
    print("🔒 Archivos CSV renombrados a .bak")

if __name__ == "__main__":
    migrate()
