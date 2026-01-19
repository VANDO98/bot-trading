import os
import joblib
import pandas as pd
from colorama import Fore

# Importamos tu ingeniería de características actualizada
from Machine_Learning.FeatureEngineering import FeatureEngineering

class GestorPrediccion:
    def __init__(self):
        self.modelo = None
        self.feature_eng = FeatureEngineering() 
        self.cargar_modelo()

    def cargar_modelo(self):
        """Carga el modelo Random Forest entrenado (.joblib)"""
        try:
            # Ruta relativa: Subimos 3 niveles desde Core/Utils/ hasta la raíz
            root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            ruta_modelo = os.path.join(root_dir, "Machine_Learning", "modelo_rf_trading.joblib")
            
            if os.path.exists(ruta_modelo):
                self.modelo = joblib.load(ruta_modelo)
                print(Fore.GREEN + f"🧠 Modelo ML cargado correctamente: {ruta_modelo}")
            else:
                print(Fore.RED + f"⚠️ No se encontró el modelo en: {ruta_modelo}")
                print(Fore.YELLOW + "   -> El bot operará SIN filtro de ML (Peligroso si dependes de él).")
        except Exception as e:
            print(Fore.RED + f"❌ Error cargando modelo ML: {e}")

    def predecir_exito(self, df_velas):
        """
        Recibe las últimas velas, calcula indicadores y pregunta al modelo.
        Retorna: True (Aprobado) / False (Rechazado)
        """
        # Si no hay modelo cargado, por seguridad APROBAMOS (Fail-open) o RECHAZAMOS?
        # Aquí asumimos que si no hay modelo, el usuario quiere operar solo con RSI.
        if self.modelo is None:
            return True 

        try:
            # 1. Generar Features (Indicadores)
            # Usamos tu FeatureEngineering que ya valida y limpia
            df_features = self.feature_eng.aplicar_features(df_velas.copy())
            
            # 2. Limpieza rápida (El modelo no acepta NaNs)
            df_features = df_features.dropna()
            
            if df_features.empty:
                print(Fore.YELLOW + "⚠️ ML: Data insuficiente tras limpieza.")
                return False

            # 3. Tomamos la ÚLTIMA vela (la situación actual del mercado)
            ultima_fila = df_features.iloc[[-1]]
            
            # 4. FILTRO DE COLUMNAS (CRÍTICO)
            # Debemos eliminar columnas que NO son features (fechas, precios crudos, target, etc.)
            # y quedarnos solo con las numéricas que usó el modelo.
            cols_excluir = ['timestamp', 'time', 'open', 'high', 'low', 'close', 'volume', 'target', 'TARGET']
            cols_modelo = [c for c in ultima_fila.columns if c.lower() not in cols_excluir]
            
            X_input = ultima_fila[cols_modelo]

            # 5. Predicción
            prediccion = self.modelo.predict(X_input)[0]          # 0 o 1
            probabilidad = self.modelo.predict_proba(X_input)[0][1] # Probabilidad de ser 1

            # Lógica de decisión
            es_aprobado = (prediccion == 1)
            
            color = Fore.GREEN if es_aprobado else Fore.RED
            print(f"{color}🧠 Análisis ML: Probabilidad éxito: {probabilidad:.2f} -> {'APROBADO' if es_aprobado else 'RECHAZADO'}")

            return es_aprobado

        except Exception as e:
            print(Fore.RED + f"⚠️ Error técnico en predicción ML: {e}")
            # En caso de error de código, dejamos pasar para no detener el bot, 
            # o retornamos False si prefieres máxima seguridad.
            return True