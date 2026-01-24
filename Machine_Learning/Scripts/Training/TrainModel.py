import pandas as pd
import pandas_ta as ta
import json
import joblib
import os
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from colorama import Fore, init
import sys

# Permitir importar Core desde el directorio padre
# Permitir importar Core desde el directorio padre (Training -> Scripts -> ML -> Root)
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
from Core.Utils.FeatureEngine import FeatureEngine

init(autoreset=True)

# --- CONFIGURACIÓN ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) # Machine_Learning/Scripts/Training
# Estamos en ML/Scripts/Training
# .. -> Scripts
# .. -> Machine_Learning
# .. -> Root
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(BASE_DIR)))
# Unificado: Datos historicos en Machine_Learning/Data/Historico
DATA_DIR = os.path.join(ROOT_DIR, "Machine_Learning", "Data", "Historico") 
MODEL_DIR = os.path.join(ROOT_DIR, "Machine_Learning", "Models")
CONFIG_PATH = os.path.join(ROOT_DIR, "config_trading.json")

# Creamos la raíz de modelos si no existe
if not os.path.exists(MODEL_DIR):
    os.makedirs(MODEL_DIR)

def cargar_config():
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)

def calcular_indicadores_segun_estrategia(df, estrategia, params):
    """
    Usa el FeatureEngine centralizado y añade lógica específica de estrategia.
    """
    # 1. Indicadores Base (Centralizados)
    df = FeatureEngine.generar_indicadores(df)
 
    # 2. Indicadores Específicos (Delegado a FeatureEngine para adaptabilidad)
    df = FeatureEngine.agregar_indicadores_estrategia(df, estrategia, params)
    
    return df


def etiquetar_datos(df, ventana_futura=3, objetivo_minimo=0.008):
    # Retorno a futuro
    df['retorno_futuro'] = df['close'].shift(-ventana_futura) / df['close'] - 1
    # Target: 1 si supera el objetivo, 0 si no
    df['target'] = (df['retorno_futuro'] > objetivo_minimo).astype(int)
    df.dropna(subset=['retorno_futuro'], inplace=True)
    return df

def entrenar_par(par, cfg):
    # 1. Obtener Timeframe y Rutas
    timeframe = cfg.get('timeframe', '5m')
    simbolo_archivo = par.replace('/', '')
    
    # Busca CSV en: Data/Historico/1h/BTCUSDT_1h.csv
    ruta_csv = os.path.join(DATA_DIR, timeframe, f"{simbolo_archivo}_{timeframe}.csv")
    
    if not os.path.exists(ruta_csv):
        print(f"{Fore.RED}⚠️ No hay datos para {par} en {timeframe}. Saltando...")
        return

    try:
        df = pd.read_csv(ruta_csv)
        for c in ['open','high','low','close','volume']: df[c] = pd.to_numeric(df[c], errors='coerce')
        df.dropna(inplace=True)
    except Exception as e:
        print(f"Error leyendo {par}: {e}")
        return

    # 2. Calcular Features (Usando la configuración ganadora del Optimizer)
    estrategia = cfg.get('estrategia', 'EstrategiaTrend')
    params = cfg.get('parametros_estrategia', {})
    
    df = calcular_indicadores_segun_estrategia(df, estrategia, params)
    
    # 3. Etiquetar
    # Objetivo dinámico: 1.5% para 1h, 0.8% para tfs menores
    objetivo = 0.015 if timeframe == '1h' else 0.008
    df = etiquetar_datos(df, ventana_futura=3, objetivo_minimo=objetivo)
    
    # 4. Definir X e y
    cols_excluir = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'retorno_futuro', 'target']
    features = [c for c in df.columns if c not in cols_excluir]
    
    if not features: return

    X = df[features]
    y = df['target']
    
    # 5. Entrenar
    # Usamos n_estimators=100 para un buen balance entre peso y precisión
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
    
    model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
    model.fit(X_train, y_train)
    
    # 6. Guardar Modelo ORGANIZADO
    # Carpeta destino: Modelos/1h/
    carpeta_destino_modelo = os.path.join(MODEL_DIR, timeframe)
    
    if not os.path.exists(carpeta_destino_modelo):
        os.makedirs(carpeta_destino_modelo)
        
    nombre_modelo = f"modelo_{simbolo_archivo}.joblib"
    ruta_final_modelo = os.path.join(carpeta_destino_modelo, nombre_modelo)
    
    joblib.dump(model, ruta_final_modelo)
    
    # Métricas
    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    color = Fore.GREEN if acc > 0.55 else Fore.YELLOW
    
    print(f"{color}✅ {par:<10} ({timeframe}) | Guardado en /{timeframe} | Acc: {acc:.2f}")

def main():
    print(f"{Fore.MAGENTA}🧠 ENTRENAMIENTO ORGANIZADO (V2)...")
    print(f"📂 Guardando en subcarpetas dentro de: {MODEL_DIR}")
    
    config = cargar_config()
    pares = config.get('pares', {})
    
    count = 0
    for par, cfg in pares.items():
        if cfg.get('activo', False):
            entrenar_par(par, cfg)
            count += 1
            
    print("-" * 60)
    print(f"{Fore.MAGENTA}🏁 {count} modelos entrenados y organizados.")

if __name__ == "__main__":
    main()