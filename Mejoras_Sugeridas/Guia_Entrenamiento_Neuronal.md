# 🧠 Guía Técnica: Entrenamiento de Redes Neuronales sin Lookahead Bias

Esta guía detalla el protocolo estricto para entrenar modelos de Deep Learning (LSTM) para el sistema "Shadow Trading", asegurando que los resultados sean realistas y no sufran de "espejismo del futuro" (Lookahead Bias).

## 1. La Filosofía de los Datos

A diferencia de los bosques aleatorios (que ven una foto estática), las redes LSTM ven una **película** (secuencia de velas).

### 🛠️ Ingeniería de Características (Features)
No alimentes a la red com precios brutos (BTC a $100k vs $20k confunde a la red). Usa **cambios relativos** e indicadores normalizados:
1.  **Log Returns:** `np.log(close / close.shift(1))` (Cambio porcentual).
2.  **RSI Normalizado:** `RSI / 100.0` (Para que esté entre 0 y 1).
3.  **Distancia a EMAs:** `(Close - EMA_200) / Close` (Porcentaje de distancia).
4.  **Volumen Relativo:** `Volumen / EMA_Volumen_20`.

### 🎯 Definición del Objetivo (Target)
¿Qué queremos predecir? No predigas el precio exacto. Predice la **probabilidad de éxito**.
*   **Target = 1 (Buy):** Si en las próximas `N` velas el precio sube `TP%` antes de bajar `SL%`.
*   **Target = 0 (Wait):** Cualquier otro caso.

---

## 2. 🛡️ Protocolo Anti-Lookahead Bias (CRÍTICO)

El error #1 en IA de trading es filtrar información del futuro hacia el pasado. Sigue estas reglas sagradas:

### Regla A: División Temporal Estricta
Jamás mezcles los datos aleatoriamente (`shuffle=True` en train_test_split está PROHIBIDO).
*   **Correcto:**
    *   Train: Enero 2023 - Octubre 2023
    *   Test: Noviembre 2023 - Diciembre 2023
*   **Incorrecto:** Tomar días al azar de todo el año.

### Regla B: Escalado Honesto (Data Leakage)
Al usar `StandardScaler` o `MinMaxScaler`:
1.  Calcula el scaler (`fit`) USANDO SOLO LOS DATOS DE TRAIN.
2.  Aplica el scaler (`transform`) a Test.
*   **Por qué:** Si calculas el máximo precio de *todo* el año para escalar, el modelo de Enero "sabrá" implícitamente cuál será el máximo de Diciembre. Eso es trampa.

```python
# Ejemplo de Código Correcto
split = int(len(df) * 0.8)
train_df = df.iloc[:split]
test_df = df.iloc[split:]

scaler = StandardScaler()
# El scaler solo conoce el pasado
train_scaled = scaler.fit_transform(train_df) 
# Al futuro le aplicamos las reglas del pasado
test_scaled = scaler.transform(test_df) 
```

---

## 3. Arquitectura Recomendada (LSTM)

Para empezar, mantén la red simple para evitar sobreajuste (overfitting).

**Entrada:** Ventana de tiempo (ej. últimas 10 velas de 5m). `Shape: (Batch, 10, N_Features)`

1.  **Capa LSTM (Input):**
    *   `units=64`
    *   `return_sequences=False` (Solo nos importa la decisión final tras ver las 10 velas).
2.  **Capa Dropout:**
    *   `rate=0.2` (Apaga el 20% de neuronas al azar para obligar a la red a no memorizar).
3.  **Capa Densa (Output):**
    *   `units=1`
    *   `activation='sigmoid'` (Nos da una probabilidad entre 0% y 100%).

---

## 4. Estrategia de Google Colab (Paso a Paso)

Para no quemar tu laptop, usa la nube:

1.  **Exportar Datos:** Crea un script local que genere `training_data.csv` con tus indicadores ya calculados.
2.  **Subir a Drive:** Sube el CSV a tu Google Drive.
3.  **Colab Notebook:**
    *   Montar Drive: `from google.colab import drive; drive.mount('/content/drive')`
    *   Cargar CSV con Pandas.
    *   Aplicar Protocolo Anti-Lookahead (Split + Scaling).
    *   Crear Modelo Keras/TensorFlow.
    *   Entrenar: `model.fit(X_train, y_train, epochs=20, batch_size=32, validation_data=(X_test, y_test))`
4.  **Descargar:**
    *   Baja dos archivos vitales: `mi_modelo.h5` (Cerebro) y `scaler.pkl` (Traductor).
5.  **Implementar:** Ponlos en la carpeta `Machine_Learning/Models/` de tu bot.

---

## 5. Validación con "Shadow Judge"

Una vez tengas el modelo `.h5`:
1.  Activa el **Neural Shadow Mode** (ver Roadmap).
2.  Deja que opere en "sombra" durante 1 semana.
3.  Si el `ShadowJudge` dice que el modelo neuronal gana dinero real (no solo en simulación), entonces (y solo entonces) promociónalo a producción.
