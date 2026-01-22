# ⚙️ ML Core

Esta carpeta contiene la **lógica pura** del sistema de Machine Learning. Estos módulos son utilizados tanto por los scripts de entrenamiento como por el bot en vivo.

## 📜 Módulos Principales

### `FeatureEngineering.py`
El cerebro matemático.
- **Responsabilidad**: Recibir velas crudas (OHLCV) y devolver un DataFrame con indicadores técnicos (RSI, ADX, EMAs, etc.).
- **Uso**: Garantiza que el bot en vivo calcule *exactamente* lo mismo que se usó durante el entrenamiento.

### `DataProcessor.py`
El encargado de la limpieza.
- **Responsabilidad**: Normalizar datos, llenar valores nulos, y etiquetar datos (Labeling) para entrenamiento supervisado.
- **Uso**: Convierte datos históricos en un dataset listo para `scikit-learn`.

### `DataCollector.py`
El recolector.
- **Responsabilidad**: Conectarse a la API de Binance y descargar años de historia de precios.
- **Output**: Guarda archivos en `../Data/Historico/`.

### `Optimizer.py`
El optimizador.
- **Responsabilidad**: Probar miles de combinaciones de parámetros (Grid Search) para encontrar la mejor configuración de indicadores antes de entrenar la IA.
