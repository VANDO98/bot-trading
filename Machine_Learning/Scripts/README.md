# 🛠️ ML Scripts

Herramientas ejecutables para gestionar el ciclo de vida del Machine Learning.
Estos scripts se deben ejecutar desde la raíz del proyecto o desde esta carpeta (tienen configuración de `sys.path` automática).

## 🚀 Principales

### `TrainModel.py`
**Entrenador**.
- Lee datos de `../Data/Processed` (o genera nuevos desde Historico).
- Entrena un `RandomForestClassifier`.
- Guarda el resultado en `../Models/modelo_rf_trading.joblib`.

### `Backtest_ML.py`
**Validador**.
- Carga el modelo actual y datos históricos.
- Simula cómo habría operado el modelo en el pasado.
- Muestra métricas de Win Rate y Calidad.

### `verify_integrity.py`
**Auditor**.
- Verifica que todas las carpetas y archivos necesarios existan.
- Prueba que las librerías se puedan importar correctamente.
- Útil después de mover carpetas o actualizar código.

### Otros
- `bajar_1h.py`: Utilidad rápida para actualizar solo datos de 1 hora.
- `Backtest_Hibrido.py`: Compara la estrategia pura vs estrategia + ML.
