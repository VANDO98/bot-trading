# Plan de Implementación: Estrategias Mixtas Avanzadas

**Objetivo:** Implementar nuevas estrategias concretas que combinen lógica de tendencia con Price Action (Velas) y Volatilidad (Squeeze), integrándolas en el sistema actual para que el `Optimizer` pueda seleccionarlas.

---

## 🏗️ Nuevas Estrategias

### 1. `EstrategiaTrend_Candle` (Tendencia + Confirmación de Velas)
*   **Concepto:** Misma base que `EstrategiaTrend` (Cruce EMAs + ADX), pero la señal de entrada **requiere** un patrón de velas a favor.
*   **Lógica de Entrada / Salida:**
    *   **LONG:** EMA Rápida > Lenta + ADX > Min + (Patrón Bullish: Engulfing, Hammer o Morning Star).
    *   **SHORT:** EMA Rápida < Lenta + ADX > Min + (Patrón Bearish: Engulfing, Shooting Star o Evening Star).
*   **Ventaja:** Evita entrar en cruces de EMA "sucios" donde el precio muestra rechazo immediato (mechas).

### 2. `EstrategiaSqueeze_Momentum` (Volatilidad Explosiva)
*   **Concepto:** Detecta momentos de consolidación (Bandas Bollinger dentro de Canales Keltner) seguidos de una expansión.
*   **Lógica:**
    *   **Squeeze ON:** Bandas Bollinger (BB) < Canales Keltner (KC).
    *   **Disparo (Fire):** BB rompen KC hacia afuera + Momentum positivo.
    *   **LONG:** Rompe Banda Superior + Momentum > 0.
    *   **SHORT:** Rompe Banda Inferior + Momentum < 0.

---

## 🛠️ Cambios Requeridos

### A. Core / FeatureEngine.py
Necesitamos calcular los nuevos indicadores base.
1.  **Patrones de Velas:** Añadir `ta.cdl_pattern(name=["engulfing", "hammer", "shootingstar"])`.
2.  **Canales Keltner:** Añadir cálculo de KC (EMA +/- ATR * Multiplicador).
3.  **Momentum:** Añadir cálculo de momentum linear (`close - close.shift(n)`).

### B. Estrategias / Concretas (Nuevos Archivos)
Crear las clases Python que heredan de `EstrategiaBase`.
- `Estrategias/Concretas/EstrategiaTrend_Candle.py`
- `Estrategias/Concretas/EstrategiaSqueeze_Momentum.py`

### C. Machine_Learning / Core / Optimizer.py
Registrar las estrategias en el "Torneo".
- Añadir a `GRID_PARAMETROS`:
    ```python
    "EstrategiaTrend_Candle": {
        "ema_fast": [20, 50],
        "require_pattern": [True] # Booleano para activar el filtro
    },
    "EstrategiaSqueeze_Momentum": {
        "mult_kc": [1.5, 2.0], # Multiplicador KC
        "std_bb": [2.0]        # Desv Std BB
    }
    ```
- Implementar la lógica de simulación (`simular_estrategia`) para estas 2 nuevas opciones.

### D. Entrenamiento y Predicción
- Actualizar `TrainModel.py` y `GestorPrediccion.py` para que sepan calcular los features específicos de estas estrategias (similar a lo que hicimos con RSI_ADX).

---

## 📅 Roadmap de Ejecución
1.  **FeatureEngine:** Agregar indicadores necesarios.
2.  **Clases Estrategia:** Crear los archivos `.py` en `Estrategias/Concretas`.
3.  **Integración ML:** Actualizar `Optimizer` y `TrainModel`.
4.  **Validación:** Ejecutar un `Optimizer` rápido para ver si las nuevas estrategias ganan a las viejas en algún par.
