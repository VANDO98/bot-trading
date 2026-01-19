import pandas as pd
import pandas_ta as ta
import numpy as np
import glob
import os

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
        """
        return self._calcular_indicadores(df)

    def _calcular_indicadores(self, df):
        """Calcula los 10 Jinetes del Apocalipsis (Features)"""
        # Evitar warnings de copia
        df = df.copy()

        # 1. Indicadores de Momento
        df['RSI'] = ta.rsi(df['close'], length=14)
        df['RSI'] = df['RSI'].fillna(50) 
        df['RSI_Slope'] = df['RSI'].diff(1) # Velocidad del cambio
        
        stoch = ta.stoch(df['high'], df['low'], df['close'])
        # Pandas TA devuelve k, d. Buscamos la columna K dinámicamente
        try:
            col_k = [c for c in stoch.columns if c.startswith('STOCHk')][0]
            df['Stoch_K'] = stoch[col_k]
        except:
            df['Stoch_K'] = 50 # Fallback seguro

        # 2. Tendencia
        df['EMA_200'] = ta.ema(df['close'], length=200)
        df['Dist_EMA200'] = (df['close'] - df['EMA_200']) / df['close'] 
        
        adx = ta.adx(df['high'], df['low'], df['close'], length=14)
        try:
            col_adx = [c for c in adx.columns if c.startswith('ADX') and not c.startswith('ADX_') is False][0]
            df['ADX'] = adx[col_adx]
        except:
            df['ADX'] = 0

        # 3. Volatilidad
        df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=14)
        df['ATR_Pct'] = df['ATR'] / df['close'] 
        
        # Bollinger Bands
        bb = ta.bbands(df['close'], length=20, std=2)
        if bb is not None:
            col_upper = [c for c in bb.columns if c.startswith('BBU')][0]
            col_lower = [c for c in bb.columns if c.startswith('BBL')][0]
            col_mid   = [c for c in bb.columns if c.startswith('BBM')][0]
            df['BB_Width'] = (bb[col_upper] - bb[col_lower]) / bb[col_mid]
        else:
            df['BB_Width'] = 0

        # 4. Volumen y Velas
        df['Vol_SMA_20'] = ta.sma(df['volume'], length=20)
        df['RVOL'] = df['volume'] / df['Vol_SMA_20'] 
        
        cuerpo = abs(df['close'] - df['open'])
        rango_total = df['high'] - df['low']
        df['Cuerpo_Pct'] = np.where(rango_total == 0, 0, cuerpo / rango_total)

        # Limpieza final para inferencia (Relleno de NaNs incipientes)
        df.fillna(method='ffill', inplace=True)
        df.fillna(0, inplace=True)

        return df

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
    input_dir = os.path.join(base_dir, "Data_Entrenamiento")
    output_dir = os.path.join(base_dir, "Data_Procesada")
    
    fe = FeatureEngineering()
    fe.generar_dataset_entrenamiento(input_dir, output_dir)