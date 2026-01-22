# 🧠 Machine Learning Module

Este directorio contiene todo el ecosistema de Machine Learning del bot de trading. Su objetivo es recolectar datos, entrenar modelos y proveer predicciones al Core del bot.

## 📂 Estructura de Carpetas

### 🔹 [Core/](./Core/)
**Lógica Interna**. Contiene las clases y módulos que procesan los datos y ejecutan la lógica matemática.
- `FeatureEngineering.py`: Cálculo de indicadores técnicos.
- `DataProcessor.py`: Limpieza y normalización.
- `Optimizer.py`: Algoritmos de optimización de estrategias.

### 🔹 [Data/](./Data/)
**Almacén de Datos**. Centraliza todos los archivos CSV.
- `Historico/`: Datos OHLCV descargados de Binance (para re-entrenar).
- `Raw/`: Datos crudos para backtest o experimentos.
- `Processed/`: Datasets limpios listos para entrenamiento (con features calculadas).

### 🔹 [Models/](./Models/)
**Modelos Entrenados**. Aquí se guardan los archivos `.joblib` que el bot carga en vivo.
- El bot principal (`Core/BotController`) busca aquí el archivo `modelo_rf_trading.joblib`.

### 🔹 [Scripts/](./Scripts/)
**Ejecutables**. Scripts para operar manual o automáticamente el ciclo de vida ML.
- `TrainModel.py`: Entrena un nuevo modelo con los datos actuales.
- `Backtest_*.py`: Pruebas de rendimiento del modelo.
- `verify_integrity.py`: Chequeo de salud de la estructura de carpetas.

### 🔹 [Logs/](./Logs/)
**Registros**.
- `historial_ml.csv`: Registro histórico de cada predicción hecha en vivo (útil para auditoría).
