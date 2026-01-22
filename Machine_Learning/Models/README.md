# 🧠 ML Models

Aquí residen los "cerebros" del bot.

## 📄 Archivos

### `modelo_rf_trading.joblib`
**El Modelo Activo**.
- Este es el archivo que el `GestorPrediccion.py` del bot principal carga al iniciarse.
- Si este archivo no existe, el bot no usará filtro de Machine Learning.

### Subcarpetas por Timeframe (Opcional)
- A veces, el entrenamiento genera modelos específicos por temporalidad (ej. `1h/modelo_btc.joblib`).
- El script de entrenamiento decide si guardar un modelo monolítico o uno fragmentado.

## ⚠️ Mantenimiento
- Para actualizar el modelo del bot:
    1. Ejecutar `python3 Machine_Learning/Scripts/TrainModel.py`.
    2. Verificar que se cree un nuevo `.joblib` aquí.
    3. Reiniciar el bot (o esperar a su recarga automática si está configurada).
