import pandas as pd
import pandas_ta as ta
import numpy as np
import glob
import os
import sys

# Importar Core
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from Core.Utils.FeatureEngine import FeatureEngine as CoreEngine

class FeatureEngineering:
    """
    Clase centralizada para el cálculo de indicadores.
    Sirve tanto para crear datasets de entrenamiento como para inferencia en vivo.
    """
    
    def __init__(self):
        # Configuración Target (Solo para entrenamiento)
        self.HORIZONTE_VELAS = 24
        self.MULTIPLO_TP = 2.0
        self.MULTIPLO_SL = 1.0

    def aplicar_features(self, df):
        """
        MÉTODO PÚBLICO PARA EL BOT EN VIVO.
        Recibe velas crudas -> Devuelve velas con indicadores.
        DELEGADO A CORE.
        """
        return CoreEngine.generar_indicadores(df)

    def _calcular_indicadores(self, df):
        """
        Wrapper interno para mantener compatibilidad si algo lo llama.
        """
        return CoreEngine.generar_indicadores(df)


    def generar_dataset_entrenamiento(self, carpeta_input, carpeta_output):
        """Genera el CSV masivo para entrenar el modelo (Solo uso offline)."""
        if not os.path.exists(carpeta_output): os.makedirs(carpeta_output)
            
        archivos = glob.glob(os.path.join(carpeta_input, "*.csv"))
        print(f"📂 Encontrados {len(archivos)} pares en {carpeta_input}")
        
        dfs = []
        for archivo in archivos:
            print(f"⚡ Procesando {os.path.basename(archivo)}...")
            df = pd.read_csv(archivo)
            
            df = self._calcular_indicadores(df)
            df.dropna(inplace=True)
            df.reset_index(drop=True, inplace=True)
            
            df = self._etiquetar_triple_barrera(df)
            
            features = ['RSI', 'RSI_Slope', 'Stoch_K', 'Dist_EMA200', 'ADX', 
                        'ATR_Pct', 'BB_Width', 'RVOL', 'Cuerpo_Pct', 'TARGET']
            
            # Asegurar que existan todas las columnas
            for col in features:
                if col not in df.columns:
                    df[col] = 0

            dfs.append(df[features].copy())
            
        if dfs:
            master = pd.concat(dfs, ignore_index=True)
            ruta = os.path.join(carpeta_output, "DATASET_ENTRENAMIENTO_V1.csv")
            master.to_csv(ruta, index=False)
            print(f"✅ DATASET FINAL CREADO: {ruta}")
            print(f"📊 Filas: {len(master)} | Win Rate: {master['TARGET'].mean()*100:.2f}%")
        else:
            print("⚠️ No se encontraron datos para procesar.")

    def _etiquetar_triple_barrera(self, df):
        """Lógica de etiquetado para entrenamiento (No se usa en vivo)."""
        df['TARGET'] = 0
        tp_dist = df['ATR'] * self.MULTIPLO_TP
        sl_dist = df['ATR'] * self.MULTIPLO_SL
        
        closes = df['close'].values
        highs = df['high'].values
        lows = df['low'].values
        targets = np.zeros(len(df))
        
        for i in range(len(df) - self.HORIZONTE_VELAS):
            entrada = closes[i]
            tp = entrada + tp_dist.values[i]
            sl = entrada - sl_dist.values[i]
            
            vent_h = highs[i+1 : i+1+self.HORIZONTE_VELAS]
            vent_l = lows[i+1 : i+1+self.HORIZONTE_VELAS]
            
            idx_tp = np.argmax(vent_h >= tp) if np.any(vent_h >= tp) else -1
            idx_sl = np.argmax(vent_l <= sl) if np.any(vent_l <= sl) else -1
                
            if idx_tp != -1:
                if idx_sl == -1 or idx_tp < idx_sl:
                    targets[i] = 1 
                else:
                    targets[i] = 0 
            else:
                targets[i] = 0 
                
        df['TARGET'] = targets
        return df

# Bloque para ejecutar como script independiente si se desea
if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # Corrigiendo rutas para la nueva estructura
    # FeatureEngineering esta en Core. Data en ../Data
    ml_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    input_dir = os.path.join(ml_dir, "Data", "Raw")
    output_dir = os.path.join(ml_dir, "Data", "Processed")
    
    fe = FeatureEngineering()
    fe.generar_dataset_entrenamiento(input_dir, output_dir)