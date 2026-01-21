
import pandas as pd
import sys
import os

# Find the file, we know the directory structure from previous commands
# It was "Registros/Analisis_20260121_110804/analisis_completo.xlsx" in the prompt, 
# but let's be dynamic or use the specific path if provided.
# The previous `find` command will confirm the path, but since I cannot access its output immediately in this turn,
# I will use the path from the user prompt or try to find it.

file_path = "Registros/Analisis_20260121_110804/analisis_completo.xlsx"

if not os.path.exists(file_path):
    # Try to find it in the latest analysis folder
    registros_dir = "Registros"
    if os.path.exists(registros_dir):
        subdirs = [os.path.join(registros_dir, d) for d in os.listdir(registros_dir) if os.path.isdir(os.path.join(registros_dir, d)) and d.startswith("Analisis_")]
        subdirs.sort(reverse=True)
        if subdirs:
            file_path = os.path.join(subdirs[0], "analisis_completo.xlsx")

print(f"Reading file: {file_path}")

try:
    df_resumen = pd.read_excel(file_path, sheet_name='Resumen')
    print("\n=== RESUMEN DE RENDIMIENTO ===")
    print(df_resumen.to_string())

    # Calculate some aggregated stats for context
    total_pnl = df_resumen['PnL_Neto'].sum()
    avg_win_rate = df_resumen['Win_Rate'].mean()
    print(f"\nTotal PnL: {total_pnl}")
    print(f"Average Win Rate: {avg_win_rate}")

except Exception as e:
    print(f"Error reading excel: {e}")
