import pandas as pd
import numpy as np
import joblib
import os
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
from colorama import Fore, init

init(autoreset=True)

# --- CONFIGURACIÓN ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARCHIVO_DATASET = os.path.join(BASE_DIR, "Data_Procesada", "DATASET_ENTRENAMIENTO_V1.csv")
MODELO_SALIDA = os.path.join(BASE_DIR, "modelo_rf_trading.joblib")

def entrenar_modelo_sniper():
    print(Fore.CYAN + "📂 Cargando dataset masivo (6 Millones de filas)...")
    
    if not os.path.exists(ARCHIVO_DATASET):
        print(Fore.RED + f"❌ No encuentro: {ARCHIVO_DATASET}")
        return

    # Usamos chunks o lectura optimizada si tienes poca RAM, pero con 6M debería caber en 16GB.
    # Si te da error de memoria, avísame.
    df = pd.read_csv(ARCHIVO_DATASET)
    
    # Limpieza básica
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    df.dropna(inplace=True)

    print(f"📊 Datos Totales: {len(df)}")
    
    # --- ESTRATEGIA DE BALANCEO (UNDERSAMPLING) ---
    print(Fore.YELLOW + "⚖️  Aplicando Balanceo 50/50 (Técnica Sniper)...")
    
    df_ganadoras = df[df['TARGET'] == 1.0]
    df_perdedoras = df[df['TARGET'] == 0.0]
    
    n_ganadoras = len(df_ganadoras)
    print(f"   ✅ Ganadoras disponibles: {n_ganadoras}")
    
    # Tomamos tantas perdedoras como ganadoras tengamos (Ratio 1:1)
    # Esto elimina el sesgo del 91%
    if len(df_perdedoras) > n_ganadoras:
        df_perdedoras = df_perdedoras.sample(n=n_ganadoras, random_state=42)
    
    # Unimos y mezclamos
    df_balanceado = pd.concat([df_ganadoras, df_perdedoras])
    df_balanceado = df_balanceado.sample(frac=1, random_state=42).reset_index(drop=True)
    
    print(f"   ✨ Dataset de Entrenamiento Final: {len(df_balanceado)} filas (50% Win / 50% Loss)")

    # Definir X e y
    columnas_features = [col for col in df_balanceado.columns if col != 'TARGET']
    X = df_balanceado[columnas_features]
    y = df_balanceado['TARGET']

    # Separar Train/Test
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Configuración del Random Forest
    print(Fore.MAGENTA + "🧠 Entrenando Random Forest...")
    
    rf = RandomForestClassifier(
        n_estimators=150,      # Un poco más de árboles
        max_depth=15,          # Profundidad media para captar patrones complejos
        min_samples_leaf=20,   # Evitar memorización excesiva
        n_jobs=-1,             # Usar todos los núcleos CPU
        random_state=42
    )
    
    rf.fit(X_train, y_train)

    # --- EVALUACIÓN ---
    print(Fore.CYAN + "\n📝 Resultados en Test Set (Datos no vistos):")
    y_pred = rf.predict(X_test)
    y_prob = rf.predict_proba(X_test)[:, 1]

    print(classification_report(y_test, y_pred))

    # --- ANÁLISIS DE UMBRALES (LO MÁS IMPORTANTE) ---
    print("-" * 40)
    print(Fore.YELLOW + "🎯 PRECISIÓN REAL POR NIVEL DE CONFIANZA")
    print("El modelo dirá 'Compra' muchas veces, pero ¿cuándo es fiable?")
    
    umbrales = [0.55, 0.60, 0.65, 0.70, 0.75, 0.80]
    
    mejor_umbral = 0.50
    mejor_winrate = 0.0
    
    for umbral in umbrales:
        # Filtramos predicciones donde la IA está muy segura
        indices = np.where(y_prob >= umbral)[0]
        
        if len(indices) == 0:
            print(f"Umbral > {umbral:.2f}: Sin operaciones.")
            continue
            
        # Verificamos cuántas de esas fueron realmente ganadoras (1.0)
        reales = y_test.iloc[indices]
        win_rate = reales.mean()
        total_ops = len(indices)
        
        # Proyección mensual aproximada (Asumiendo que el test es 20% de la data histórica)
        # Esto es solo un estimado visual
        
        color = Fore.GREEN if win_rate > 0.5 else Fore.RED
        print(f"Umbral > {umbral:.2f} | Ops Test: {total_ops} | {color}Win Rate: {win_rate*100:.2f}%")

        if win_rate > mejor_winrate and total_ops > 50:
            mejor_winrate = win_rate
            mejor_umbral = umbral

    # Guardar Modelo
    print("-" * 40)
    joblib.dump(rf, MODELO_SALIDA)
    print(Fore.GREEN + f"💾 Modelo guardado: {MODELO_SALIDA}")
    
    print("\n🏆 Top Indicadores:")
    importancias = pd.Series(rf.feature_importances_, index=columnas_features).sort_values(ascending=False)
    print(importancias.head(5))
    
    print(Fore.WHITE + f"\n💡 RECOMENDACIÓN: Configura tu 'ml_threshold' en el JSON cerca de {mejor_umbral:.2f}")

if __name__ == "__main__":
    entrenar_modelo_sniper()