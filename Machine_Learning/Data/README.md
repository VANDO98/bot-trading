# 🗄️ ML Data

Almacenamiento centralizado de datos. Esta estructura separa los datos por su etapa de procesamiento.

## 📂 Subcarpetas

### 🟢 [Historico/](./Historico/)
**Datos Fuente (OHLCV)**.
- Archivos `.csv` con velas puras descargadas de Binance.
- Formato: `BTCUSDT_5m.csv`, `ETHUSDT_1h.csv`.
- Generado por: `Core/DataCollector.py` o scripts de descarga.
- **Nota**: Estos datos son la materia prima.

### 🟡 [Raw/](./Raw/)
**Datos de Entrada**.
- Carpeta de tránsito para datasets específicos o subconjuntos que se van a usar para un experimento puntual.
- A menudo contiene copias de `Historico` seleccionadas para un backtest específico.

### 🔴 [Processed/](./Processed/)
**Datasets de Entrenamiento**.
- Archivos `.csv` que ya han pasado por `FeatureEngineering`.
- Contienen columnas de indicadores (`RSI`, `ADX`) y la columna objetivo (`TARGET`).
- **Listo para IA**: Estos archivos son los que lee `TrainModel.py`.
