# 🚀 Roadmap Técnico v4.0 (Mejoras de Sistema)

Este documento recopila las oportunidades de mejora detectadas tras la implementación del sistema "Shadow Trading" (v3.5).

---

## 1. 🧪 Testing Automatizado (Robustez)
**Estado Actual:** Pruebas manuales o scripts de un solo uso (`Test/`).
**Propuesta:** Implementar una suite de pruebas unitarias robusta usando `pytest`.
- **Objetivo:** Simular escenarios de mercado complejos para validar al "Juez" sin esperar días.
- **Detalle:**
    - Crear `Test/Unit/test_shadow_judge.py`.
    - Mockear datos de velas (crear velas falsas donde el precio sube/baja) y verificar que `ShadowJudge` retorne `TRUE/FALSE NEGATIVE` correctamente.
    - CI/CD básico: Que los tests corran antes de cada commit.

## 2. 📊 Dashboard Web (Visibilidad)
**Estado Actual:** Logs de consola, CSVs y notificaciones de Telegram.
**Propuesta:** Desarrollar un Frontend ligero (Next.js/React + FastAPI).
- **Objetivo:** Visualizar en tiempo real qué está haciendo el "Shadow Trading" vs el "Real Trading".
- **Funcionalidades:**
    - Gráfico de velas (TradingView Widget) mostrando dónde entró el bot y dónde rechazó (puntos rojos/verdes).
    - Métricas en vivo del Auto-Tuner (FNR actual por moneda).
    - Botón de pánico web para detener el bot.

## 3. ⏪ Backtesting Engine (Validación Histórica)
**Estado Actual:** `ShadowJudge` es un "Forward Tester" (prueba en datos futuros a medida que llegan).
**Propuesta:** Crear un motor de Backtesting dedicado.
- **Objetivo:** Probar configuraciones en datos del 2023/2024.
- **Diferencia con Shadow:**
    - Shadow espera a que pase el tiempo real.
    - Backtesting descarga 1 año de datos y simula 12 meses en minutos.
- **Uso:** Antes de activar una estrategia nueva, pasarla por el Backtester para ver si hubiera sobrevivido al mercado bajista.

---

## 4. 🧠 Neural Shadow Mode (A/B Testing en Vivo)
**Estado Actual:** Solo corre un modelo (Random Forest/XGBoost).
**Propuesta:** Validar Redes Neuronales sin arriesgar capital ni colapsar la RAM del servidor.
- **Problemática:** Correr 2 bots completos (uno real y uno paper) consume >2GB RAM. Servidor actual: 1.8GB.
- **Solución: "Zero-Copy Inference"**
    - **Arquitectura:** El `BotController` actual actúa como "Maestro de Datos".
    - **Schema Change:** Agregar columna `ml_model` a la tabla `shadow_trades` (ej. 'RandomForest', 'NeuralNetwork_LSTM').
    - **Flujo:**
        1. Bot recibe vela de Binance.
        2. Bot calcula indicadores (ya en RAM).
        3. **Paso Extra:** Pasa esos mismos indicadores a una Red Neuronal (LSTM Universal) en milisegundos.
        4. Si la LSTM dice "COMPRAR", el bot **NO opera**, pero guarda el registro en `shadow_trades` manteniendo la estrategia original (ej. 'Estrategia_B') pero marcando `ml_model='NeuralNetwork_LSTM'`.
    - **Ventaja:** Consumo de RAM marginal (solo pesa el modelo cargado, ~100MB) vs duplicar todo el bot (~400MB+).
    - **Evaluación:** El `ShadowJudge` comparará el rendimiento agrupando por `ml_model` para determinar cuál cerebro es superior.
    - **Infraestructura de Entrenamiento (Tip):**
        - No se requiere GPU local costosa.
        - **Recomendación:** Usar **Google Colab (Free Tier)** para entrenar los modelos pesados (.h5) en la nube usando sus GPUs NVIDIA Tesla T4 gratuitas, y luego solo subir el archivo entrenado al servidor.
    - **📚 Guía Detallada:** Ver [Guia_Entrenamiento_Neuronal.md](./Guia_Entrenamiento_Neuronal.md) para instrucciones paso a paso sobre datos, arquitectura LSTM y prevención de Lookahead Bias.

---

*Documento generado automáticamente por Antigravity tras finalizar la Fase 3.*
