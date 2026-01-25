import pandas as pd
import numpy as np

# Simular estructura de velas
columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'cerrada']
velas = pd.DataFrame(columns=columns)

# Crear DataFrame con índice duplicado para simular el fallo
# Simulemos que por alguna razón (concatenación errónea) tenemos el índice 0 dos veces
row1 = pd.DataFrame([{
    'timestamp': pd.Timestamp('2023-01-01 12:00:00'),
    'open': 100, 'high': 105, 'low': 95, 'close': 102, 'volume': 1000, 'cerrada': True
}])

row2 = pd.DataFrame([{
    'timestamp': pd.Timestamp('2023-01-01 13:00:00'),
    'open': 102, 'high': 108, 'low': 100, 'close': 105, 'volume': 1500, 'cerrada': False
}])

# Concatenar de forma que reset_index no se ha llamado o hay indices sucios
velas = pd.concat([row1, row2], ignore_index=True)
# Forzar duplicado de índice para probar la teoría
velas.index = [0, 0] 

print("Indice actual (con duplicados):", velas.index.tolist())

try:
    # Simular la actualización intrabarra (Caso B de EstrategiaBase)
    # idx = self.velas.index[-1]
    # self.velas.loc[idx, ...] = ...
    
    idx = velas.index[-1] # Esto devolverá un Int64Index([0, 0]) o similar si hay duplicados, o el valor escalar
    print(f"Index to update: {idx}")
    
    nueva_vela = [103, 110, 101, 108, 2000]
    
    # Esta línea debería fallar con "Reindexing only valid with uniquely valued Index objects"
    # si idx es ambiguo o el índice tiene duplicados.
    velas.loc[idx, ['open', 'high', 'low', 'close', 'volume']] = nueva_vela
    
    print("✅ Actualización exitosa (No se reprodujo el error)")
    print(velas)

except Exception as e:
    print(f"❌ Error reproducido: {e}")
