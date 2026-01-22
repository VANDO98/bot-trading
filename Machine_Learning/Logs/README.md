# 📝 ML Logs

Registros de actividad del sistema de Machine Learning.

## 📄 Archivos

### `historial_ml.csv`
**Bitácora de Predicciones**.
Cada vez que el bot en vivo consulta al modelo, se añade una fila aquí.

**Columnas**:
- `timestamp`: Fecha/Hora.
- `simbolo`: Par operado (ej. BTCUSDT).
- `input_features`: JSON con los valores exactos de los indicadores que vio el bot (RSI, ADX, etc.).
- `probabilidad`: Qué tan seguro estaba el modelo (0.0 a 1.0).
- `umbral`: El umbral que se requería para aprobar.
- `prediccion`: 1 (Aprobado) o 0 (Rechazado).
- `resultado_real`: (Opcional) Se puede rellenar a futuro para medir si la IA acertó.

**Uso**:
Este archivo es vital para diagnosticar por qué el bot tomó o rechazó una operación.
