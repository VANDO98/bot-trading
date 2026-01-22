# 🧠 Guía de Entrenamiento Machine Learning (Workflow Automatizado)

El sistema cuenta con un pipeline completo de Machine Learning que automatiza la descarga, optimización y entrenamiento.

---

## � Ciclo de Vida del ML

El flujo correcto de trabajo es:
1.  **Recolectar** (`DataCollector`): Baja datos masivos.
2.  **Optimizar** (`Optimizer`): Busca la mejor estrategia y timeframe para cada par.
3.  **Entrenar** (`TrainModel`): Genera los modelos finales basados en la optimización.
4.  **Ejecutar**: El bot usa estos modelos en vivo.

---

## 🚀 Paso a Paso

### 1. Configurar Pares (Inicio)
En `config_trading.json`, simplemente asegúrate de que el par exista y esté `"activo": true`.
*   *Nota:* No importa qué estrategia/timeframe pongas inicialmente, el **Optimizador** lo corregirá después.

```json
"SOL/USDT": { "activo": true, ... }
```

### 2. Recolectar Datos (DataCollector)
Este script descarga automáticamente datos históricos para **todos** los timeframes (5m, 15m, 1h) de todos los pares activos.

```bash
python Machine_Learning/Core/DataCollector.py
```
*   **Salida:** Archivos en `Data/Historico/5m`, `Data/Historico/1h`, etc.

### 3. Optimizar Estrategias (Optimizer)
Este es el "cerebro". Prueba todas las combinaciones de estrategias (Trend, RSI/ADX, BB) y parámetros sobre los datos descargados.
*   Si encuentra una configuración con mejor rendimiento histórico que la actual, **actualiza automáticamente** tu `config_trading.json`.

```bash
python Machine_Learning/Core/Optimizer.py
```
*   **Resultado:** Tu `config_trading.json` ahora tiene la estrategia óptima para cada par.

### 4. Entrenar Modelos (TrainModel)
Finalmente, entrenamos los modelos Random Forest específicos usando la configuración ganadora.

```bash
python Machine_Learning/Scripts/TrainModel.py
```
*   Lee la configuración (ya optimizada).
*   Entrena un modelo específico por par.
*   Guarda los `.joblib` en `/Modelos/{timeframe}/`.

### 5. Reiniciar Bot
Reinicia el bot para cargar los nuevos modelos.

```bash
# Si usas tmux:
Ctrl+C (para detener)
python main.py
```

---

## � Estructura de Componentes

| Archivo | Función |
| :--- | :--- |
| `Machine_Learning/Core/DataCollector.py` | Descarga masiva multi-hilo de Binance Futures. |
| `Machine_Learning/Core/Optimizer.py` | Realiza Backtesting y Grid Search. Edita el JSON config. |
| `Machine_Learning/Scripts/TrainModel.py` | Entrena modelos RandomForest específicos por par. |
| `Core/Utils/GestorPrediccion.py` | Carga los modelos en vivo para inferencia. |

---

## ❓ Preguntas Frecuentes

**P: ¿Qué hace `DataProcessor.py`?**
R: Es un componente legado para generar "datasets únicos" globales. Para el sistema actual de modelos "Par-Específicos", no es necesario ejecutarlo manualmente, ya que `TrainModel` maneja su propio procesamiento.

**P: ¿Con qué frecuencia debo correr el Optimizer?**
R: Recomendado **mensualmente**. Los mercados cambian; una estrategia Trend que funciona hoy podría fallar el próximo mes si el mercado se vuelve lateral (RSI). El optimizador detectará esto y cambiará la estrategia del par.
