import os
import joblib
import pandas as pd
import pandas_ta as ta
from colorama import Fore

# Imports del sistema
from Core.Utils.Config import Config
from Core.Utils.ML_Logger import MLLogger
from Core.Utils.FeatureEngine import FeatureEngine

class GestorPrediccion:
    def __init__(self):
        # Cache para no cargar el disco mil veces
        # Clave: "BTCUSDT_1h", Valor: Modelo Cargado
        self.modelos_cache = {} 
        self.root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        # Actualización: Modelos están en la raíz "Modelos/" según reestructuración
        self.model_dir = os.path.join(self.root_dir, "Modelos")

    def _cargar_modelo_especifico(self, simbolo, timeframe):
        """Carga dinámica del modelo según par y timeframe"""
        clave_cache = f"{simbolo}_{timeframe}"
        
        if clave_cache in self.modelos_cache:
            return self.modelos_cache[clave_cache]
        
        # Construir ruta: Modelos/1h/modelo_BTCUSDT.joblib
        simbolo_limpio = simbolo.replace('/', '')
        ruta_modelo = os.path.join(self.model_dir, timeframe, f"modelo_{simbolo_limpio}.joblib")
        
        if os.path.exists(ruta_modelo):
            try:
                modelo = joblib.load(ruta_modelo)
                self.modelos_cache[clave_cache] = modelo
                # print(f"{Fore.GREEN}🧠 Modelo cargado para {simbolo} ({timeframe})")
                return modelo
            except Exception as e:
                print(Fore.RED + f"❌ Error cargando archivo modelo {simbolo}: {e}")
                return None
        else:
            # Silencioso para no spamear si es un par nuevo sin modelo
            return None

    def _generar_features_dinamicas(self, df, estrategia_nombre, params):
        """
        Delega el cálculo a FeatureEngine para mantener consistencia con el entrenamiento.
        Añade features específicas de estrategia si es necesario.
        """
        # 1. Indicadores Base (Centralizados)
        df = FeatureEngine.generar_indicadores(df)
        
        # 2. Indicadores Específicos según la estrategia (Si se mantienen lógicas custom)
        # Nota: Idealmente mover esto también a FeatureEngine o mantenerlo mínimo.
        if estrategia_nombre == "EstrategiaTrend":
            df['EMA_F'] = ta.ema(df['close'], length=params.get('ema_fast', 9))
            df['EMA_S'] = ta.ema(df['close'], length=params.get('ema_slow', 21))
            # Recalcular distancias si es necesario, OJO con sobreescribir lógica core
            # df['distancia_emas'] = ... 
            # (El código original calculaba distancia_emas aquí, lo dejamos por compatibilidad)
            df['distancia_emas'] = (df['EMA_F'] - df['EMA_S']) / df['close']
            
        elif estrategia_nombre == "EstrategiaBB":
            # Bollinger ya viene de FeatureEngine, pero si se usan params custom:
            if 'bb_length' in params:
                 bb = ta.bbands(df['close'], length=params['bb_length'], std=params.get('bb_std', 2.0))
                 if bb is not None:
                    col_u = next((c for c in bb.columns if c.startswith('BBU')), None)
                    col_l = next((c for c in bb.columns if c.startswith('BBL')), None)
                    if col_u and col_l:
                        df['dist_upper'] = df['close'] - bb[col_u]
                        df['dist_lower'] = df['close'] - bb[col_l]
        
        elif estrategia_nombre == "EstrategiaRSI_ADX":
             # Recalcular si los parámetros difieren del default (14)
             if 'rsi_periodo' in params:
                 df['RSI'] = ta.rsi(df['close'], length=params['rsi_periodo']).fillna(50)
                 df['RSI_Slope'] = df['RSI'].diff(1)
             
             if 'adx_periodo' in params:
                 adx = ta.adx(df['high'], df['low'], df['close'], length=params['adx_periodo'])
                 if adx is not None:
                     try:
                         col_adx = [c for c in adx.columns if c.startswith('ADX') and not c.startswith('ADX_') is False][0]
                         df['ADX'] = adx[col_adx].fillna(0)
                     except: pass
        
        df.fillna(0, inplace=True)
        return df

    def predecir_exito(self, simbolo, df_velas, config_par):
        """
        Método principal actualizado.
        Requiere 'config_par' para saber timeframe y parámetros.
        """
        # Extraer configuración del par
        timeframe = config_par.get('timeframe', '5m')
        estrategia_nombre = config_par.get('estrategia')
        params = config_par.get('parametros_estrategia', {})

        # 1. Cargar Modelo Específico
        modelo = self._cargar_modelo_especifico(simbolo, timeframe)
        
        if modelo is None:
            # Si no hay modelo entrenado para este par, ¿qué hacemos?
            # Opción A: Bloquear (Conservador) -> return False
            # Opción B: Dejar pasar (Arriesgado) -> return True
            # Recomendación: Dejar pasar si estamos en test, bloquear en real.
            # Por ahora retornamos True para no detener pares nuevos, pero con aviso.
            # print(Fore.YELLOW + f"⚠️ Sin modelo ML para {simbolo}. Operando sin filtro.")
            return True 

        try:
            # 2. Leer Umbral
            full_conf = Config.cargar_configuracion()
            umbral_config = full_conf.get('sistema_riesgo', {}).get('ml_threshold', 0.65)

            # 3. Generar Features (IGUAL QUE EN ENTRENAMIENTO)
            df_features = self._generar_features_dinamicas(df_velas, estrategia_nombre, params)
            ultima_fila = df_features.iloc[[-1]]

            # 4. Filtrar Columnas
            # El modelo tiene guardado qué columnas necesita
            if hasattr(modelo, "feature_names_in_"):
                cols_modelo = list(modelo.feature_names_in_)
                # Validar que las tenemos todas
                faltantes = [c for c in cols_modelo if c not in ultima_fila.columns]
                if faltantes:
                    print(Fore.RED + f"⛔ Error ML {simbolo}: Faltan columnas {faltantes}")
                    return False
                
                X_input = ultima_fila[cols_modelo]
            else:
                # Fallback legado
                return True

            # 5. Predicción
            probabilidad = modelo.predict_proba(X_input)[0][1] 
            es_aprobado = (probabilidad >= umbral_config)
            
            # 6. Logging Visual
            color = Fore.GREEN if es_aprobado else Fore.RED
            icono = "🧠"
            print(f"{color}{icono} ML {simbolo} ({timeframe}): Confianza {probabilidad:.1%} (Req: {umbral_config:.1%}) -> {'SI' if es_aprobado else 'NO'}")
            
            # Registrar
            MLLogger.registrar_prediccion(simbolo, probabilidad, umbral_config, es_aprobado, ultima_fila)

            return es_aprobado

        except Exception as e:
            print(Fore.RED + f"⚠️ Error predicción ML {simbolo}: {e}")
            return False # Ante la duda, NO operar