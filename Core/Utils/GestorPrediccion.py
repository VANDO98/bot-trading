import os
import joblib
import pandas as pd
from colorama import Fore

# Imports del sistema
from Core.Utils.Config import Config
from Core.Utils.ML_Logger import MLLogger
from Machine_Learning.FeatureEngineering import FeatureEngineering

class GestorPrediccion:
    def __init__(self):
        self.modelo = None
        self.feature_eng = FeatureEngineering() 
        self.features_esperadas = [] # Lista para guardar el ADN del modelo
        self.cargar_modelo()

    def cargar_modelo(self):
        try:
            root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            ruta_modelo = os.path.join(root_dir, "Machine_Learning", "modelo_rf_trading.joblib")
            
            if os.path.exists(ruta_modelo):
                self.modelo = joblib.load(ruta_modelo)
                
                # 🔥 AUTO-DETECCIÓN DE COLUMNAS (La clave del éxito)
                if hasattr(self.modelo, "feature_names_in_"):
                    self.features_esperadas = list(self.modelo.feature_names_in_)
                    print(Fore.GREEN + f"🧠 Modelo ML cargado. Espera {len(self.features_esperadas)} variables.")
                else:
                    print(Fore.YELLOW + "⚠️ El modelo no tiene metadatos de columnas. Se usará modo manual.")
            else:
                print(Fore.RED + f"⚠️ No se encontró el modelo en: {ruta_modelo}")
        except Exception as e:
            print(Fore.RED + f"❌ Error cargando modelo ML: {e}")

    def predecir_exito(self, simbolo, df_velas):
        if self.modelo is None: return True 

        # 1. Leer Umbral Configurado
        try:
            full_conf = Config.cargar_configuracion()
            umbral_config = full_conf.get('sistema_riesgo', {}).get('ml_threshold', 0.65)
        except:
            umbral_config = 0.65

        try:
            # 2. Generar Features (Calcula TODO: Features + Intermedios)
            df_features = self.feature_eng.aplicar_features(df_velas.copy())
            
            # Limpieza básica de N/A
            df_features = df_features.dropna()
            if df_features.empty: return False

            # 3. FILTRADO QUIRÚRGICO DE COLUMNAS
            # Aquí es donde arreglamos el error. Seleccionamos SOLO lo que el modelo pide.
            ultima_fila = df_features.iloc[[-1]]
            
            if self.features_esperadas:
                # Verificamos que todas las columnas existan
                faltantes = [col for col in self.features_esperadas if col not in ultima_fila.columns]
                if faltantes:
                    print(Fore.RED + f"⛔ Error Data: Faltan columnas requeridas por el modelo: {faltantes}")
                    return False
                
                # Seleccionamos SOLO las 9 columnas del entrenamiento (ignorando ATR, EMA_200, etc.)
                X_input = ultima_fila[self.features_esperadas]
            else:
                # Fallback por si el modelo es muy viejo (no debería pasar con tu test actual)
                cols_excluir = ['timestamp', 'time', 'open', 'high', 'low', 'close', 'volume', 'target', 'TARGET']
                cols_modelo = [c for c in ultima_fila.columns if c.lower() not in cols_excluir]
                X_input = ultima_fila[cols_modelo]

            # 4. Predicción
            probabilidad = self.modelo.predict_proba(X_input)[0][1] 

            # 5. Decisión
            es_aprobado = (probabilidad >= umbral_config)
            
            # 6. Logging
            color = Fore.GREEN if es_aprobado else Fore.RED
            icono = "🎯" if es_aprobado else "🛑"
            
            print(f"{color}{icono} ML {simbolo}: Prob {probabilidad:.1%} vs Req {umbral_config:.1%} -> {'APROBADO' if es_aprobado else 'DENEGADO'}")
            
            # Guardamos Log Completo
            MLLogger.registrar_prediccion(simbolo, probabilidad, umbral_config, es_aprobado, ultima_fila)

            return es_aprobado

        except Exception as e:
            print(Fore.RED + f"⚠️ Error predicción ML: {e}")
            # Fail-Safe: Si falla, NO operamos
            print(Fore.RED + "⛔ BLOQUEO DE SEGURIDAD: Error técnico en ML.")
            return False