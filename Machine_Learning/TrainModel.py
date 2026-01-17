import pandas as pd
import numpy as np
import joblib
import os
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, precision_score
from colorama import Fore, init

init(autoreset=True)

# --- CONFIGURACIÓN ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARCHIVO_DATASET = os.path.join(BASE_DIR, "Data_Procesada", "DATASET_ENTRENAMIENTO_V1.csv")
MODELO_SALIDA = os.path.join(BASE_DIR, "modelo_rf_trading.joblib")

def entrenar_modelo():
    print(Fore.CYAN + "📂 Cargando dataset masivo (esto puede tardar unos segundos)...")
    
    if not os.path.exists(ARCHIVO_DATASET):
        print(Fore.RED + f"❌ No encuentro el archivo: {ARCHIVO_DATASET}")
        return

    # Cargar datos
    df = pd.read_csv(ARCHIVO_DATASET)
    
    # Limpieza final de seguridad (infinitos o nulos)
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    df.dropna(inplace=True)

    print(f"📊 Filas totales para entrenamiento: {len(df)}")

    # Definir X (Features) e y (Target)
    columnas_features = [col for col in df.columns if col != 'TARGET']
    X = df[columnas_features]
    y = df['TARGET']

    # Separar Train (80%) y Test (20%)
    # IMPORTANTE: shuffle=False para respetar el orden temporal (No hacer trampa mirando el futuro)
    # Aunque al mezclar pares el tiempo es relativo, shuffle=False es buena práctica en series temporales.
    # Para este experimento mezclaremos (shuffle=True) para generalizar patrones abstractos.
    print(Fore.YELLOW + "✂️  Dividiendo datos (Train/Test)...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, shuffle=True)

    # Configurar el Random Forest
    # n_estimators=100: 100 árboles de decisión
    # max_depth=10: Limitamos la profundidad para evitar que memorice (overfitting)
    # class_weight='balanced': Porque hay más perdedoras (0) que ganadoras (1), esto equilibra.
    print(Fore.MAGENTA + "🧠 Entrenando Random Forest (puede tardar 1-2 mins)...")
    
    rf = RandomForestClassifier(
        n_estimators=100, 
        max_depth=12, 
        min_samples_leaf=50, # Exige que al menos 50 velas confirmen una regla
        random_state=42, 
        n_jobs=-1, # Usar todos los núcleos de tu i7
        class_weight="balanced"
    )
    
    rf.fit(X_train, y_train)

    # --- EVALUACIÓN ---
    print(Fore.CYAN + "\n📝 Evaluando resultados en datos NO VISTOS (Test set)...")
    y_pred = rf.predict(X_test)
    y_prob = rf.predict_proba(X_test)[:, 1] # Probabilidad de ser clase 1

    # Métricas Base
    print(classification_report(y_test, y_pred))

    # --- ANÁLISIS DE PRECISIÓN REAL ---
    # Lo que nos importa: Cuando el bot dice "COMPRA" con > 60% de seguridad... ¿Acierta?
    
    print("-" * 40)
    print(Fore.YELLOW + "🎯 ANÁLISIS DE CONFIANZA (¿Qué tan bueno es el filtro?)")
    
    umbrales = [0.50, 0.55, 0.60, 0.65, 0.70]
    
    for umbral in umbrales:
        # Filtramos solo las predicciones donde el modelo está muy seguro
        indices_alta_confianza = np.where(y_prob >= umbral)[0]
        
        if len(indices_alta_confianza) == 0:
            print(f"Umbral {umbral}: Sin operaciones.")
            continue
            
        aciertos_reales = y_test.iloc[indices_alta_confianza]
        win_rate = aciertos_reales.mean()
        total_ops = len(indices_alta_confianza)
        
        color = Fore.GREEN if win_rate > 0.40 else Fore.RED
        print(f"Umbral > {umbral:.2f} | Ops: {total_ops} | {color}Win Rate: {win_rate*100:.2f}%")

    # Guardar
    print("-" * 40)
    joblib.dump(rf, MODELO_SALIDA)
    print(Fore.GREEN + f"💾 Modelo guardado exitosamente en: {MODELO_SALIDA}")
    
    # Feature Importance (Curiosidad: ¿Qué indicador sirvió más?)
    importancias = pd.Series(rf.feature_importances_, index=columnas_features).sort_values(ascending=False)
    print("\n🏆 Top 3 Indicadores más importantes:")
    print(importancias.head(3))

if __name__ == "__main__":
    entrenar_modelo()