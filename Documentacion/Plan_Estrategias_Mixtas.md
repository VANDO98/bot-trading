# Plan de Implementación: Estrategias Mixtas (Long/Short Bidireccional)

Este plan detalla la arquitectura para integrar estrategias que operan en **Ambiciones Direcciones (Compra y Venta)** en el mercado de Futuros.

---

## 🏗️ 1. Nuevas Estrategias en Detalle

### A. `EstrategiaTrend_Candle` (Tendencia + Price Action)
Combina la fuerza de la tendencia (EMAs) con la confirmación de la acción del precio (Velas).
*   **LONG (Compra):**
    1.  **Tendencia:** EMA Rápida > EMA Lenta.
    2.  **Fuerza:** ADX > Mínimo configurado.
    3.  **Confirmación:** Cierre de vela con patrón alcista (*Bullish Engulfing* o *Hammer*).
*   **SHORT (Venta):**
    1.  **Tendencia:** EMA Rápida < EMA Lenta.
    2.  **Fuerza:** ADX > Mínimo configurado.
    3.  **Confirmación:** Cierre de vela con patrón bajista (*Bearish Engulfing* o *Shooting Star*).

### B. `EstrategiaSqueeze_Momentum_Pro` (Volatilidad Explosiva Avanzada)
Basada en el indicador "TTM Squeeze" profesional (John Carter), no una versión simplificada.
*   **Condición Base (Squeeze):** Bandas de Bollinger (2.0 std) DENTRO de Canales Keltner (1.5 ATR). Indica "energía acumulada".
*   **Momentum (El Gatillo):**
    *   Calculado usando **Regresión Lineal** sobre la diferencia `(Close - (Highest + Lowest + SMA)/3)`. Esto suaviza el ruido y detecta la dirección real de la fuerza.
*   **Filtros de Entrada (Robustez):**
    *   **Volumen:** Requiere `RVOL > 1.2` (Volumen 20% superior al promedio) en la vela de ruptura.
    *   **ADX:** `ADX > 20` (Opcional, configurable) para evitar falsas rupturas en rangos muertos.
*   **Lógica de Disparo:**
    *   **LONG:** Squeeze liberado + Momentum > 0 (Histograma Verde/Cyan) + RVOL Confirmado.
    *   **SHORT:** Squeeze liberado + Momentum < 0 (Histograma Rojo) + RVOL Confirmado.

---

## 🛠️ 2. Modificaciones Técnicas (Paso a Paso)

### Paso 1: Potenciar el Cerebro (`FeatureEngine.py`)
Añadiremos los cálculos matemáticos necesarios para que `BotController` y `Optimizer` entiendan estos conceptos.
*   [ ] **Patrones de Velas:** Usar `ta.cdl_pattern` para detectar 'engulfing', 'hammer', 'shootingstar'.
*   [ ] **Canales Keltner (KC):** `KC_Upper = EMA(20) + (2 * ATR(20))`, `KC_Lower = EMA(20) - (2 * ATR(20))`.
*   [ ] **Momentum:** `Close` actual menos `Close` de hace 12 periodos (o Linear Regression Slope).

### Paso 2: Crear las Clases (`Estrategias/Concretas/`)
Aquí reside la lógica de decisión Long/Short.

**Archivo: `EstrategiaTrend_Candle.py`**
```python
def generar_senal(self, df):
    # Logica Short
    if ema_fast < ema_slow and adx > min and df['CDL_BEARISH_ENGULFING'].iloc[-1] != 0:
        return "VENTA"
    # Logica Long
    elif ema_fast > ema_slow and adx > min and df['CDL_BULLISH_ENGULFING'].iloc[-1] != 0:
        return "COMPRA"
    return "NEUTRO"
```

**Archivo: `EstrategiaSqueeze_Momentum.py`**
```python
def generar_senal(self, df):
    # Logica Short
    if squeeze_on and momentum < 0 and price < bb_lower:
        return "VENTA"
    # Logica Long
    elif squeeze_on and momentum > 0 and price > bb_upper:
        return "COMPRA"
    return "NEUTRO"
```

### Paso 3: Entrenar al Optimizador (`Optimizer.py`)
Incorporar estas estrategias al "Torneo" de optimización.
*   El optimizador simulará millones de velas pasadas.
*   Verificará si entrar en Short con un *Shooting Star* fue rentable históricamente para ese par en particular.
*   Verificará si entrar en Long con Squeeze fue rentable.
*   **Resultado:** Elegirá automáticamente cuál usar.

---

## ✅ Resultado Esperado
Un sistema híbrido y flexible que:
1.  Sigue operando tendencias fuertes (`Trend`).
2.  Pero sabe esperar la confirmación exacta (`Trend_Candle`).
3.  Y aprovecha los momentos explosivos (`Squeeze`).
Todo ello operando tanto al alza (Long) como a la baja (Short).
