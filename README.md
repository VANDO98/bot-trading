# 🤖 Bot de Trading Algorítmico - Shadow Evolution (v3.5)

> Sistema de trading autónomo para Binance Futures con Machine Learning, arquitectura híbrida, gestión de riesgo avanzada y **Sistema de Auto-Aprendizaje (Shadow Trading)**.

![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)
![Binance API](https://img.shields.io/badge/Binance-Futures-yellow.svg)
![Status](https://img.shields.io/badge/Estado-Producción-green.svg)
![ML](https://img.shields.io/badge/ML-Self_Learning-purple.svg)
![DB](https://img.shields.io/badge/SQLite-Shadow_DB-lightgrey.svg)

---

## 🎯 Filosofía del Sistema

El bot ha evolucionado de un simple ejecutor de reglas a un sistema que **aprende de sus propios errores**:

- **Filtro ML**: Random Forest valida cada señal técnica antes de ejecutar.
- **Shadow Mode**: Si el ML rechaza una operación, el sistema la "opera en la sombra" (sin dinero).
- **Shadow Judge**: Un juez imparcial analiza después si el rechazo fue correcto o un error (Oportunidad Perdida).
- **Auto-Tuner**: El bot ajusta su propia sensibilidad (umbral de miedo) basándose en el veredicto del juez.

---

## ✨ Características Principales

### 🧠 Shadow Trading (Nuevo en v3.5)
El ciclo de mejora continua está 100% automatizado:
1.  **Data Collection**: `ShadowLogger` guarda rechazos en una base de datos SQLite segura.
2.  **Analysis**: `ShadowJudge` viaja al futuro (simulación) para ver qué pasó con esas operaciones rechazadas. Evalúa éxito según ROE y Apalancamiento.
3.  **Optimization**: `AutoTuner` calcula la tasa de error (FNR).
    - Si rechaza demasiadas buenas -> **Baja el umbral**.
    - Si acepta demasiada basura -> **Sube el umbral**.

### 🪜 Toma de Ganancias Escalonada (Ladder TP)
Dos modos disponibles:
- **Modo Simple**: Venta única al 20% ROE (50% posición).
- **Modo Escalera**: Ventas parciales progresivas (20% -> 30%, 40% -> 35%, 80% -> 67%). Deja correr ganancias en tendencias fuertes.

### 🛡️ Protección Avanzada
- **Auto Break-Even**: Se activa automáticamente para proteger la entrada (+0.5%).
- **Trailing Stop Híbrido**: Gatilla por cierre de vela O por tiempo (15 min), ajustado por ATR y Volatilidad.
- **Ejecución Blindada**: Mecanismos de `Rollback`, `Ghost Buster` (limpieza de órdenes fantasma) y Sincronización automática.

---

## 📁 Arquitectura del Proyecto

```
bot-trading/
├── Core/
│   ├── API/                  # WebSocket Manager
│   ├── Ejecucion/            # Motores (Real y Paper)
│   ├── Utils/
│   │   ├── ShadowLogger.py   # [NUEVO] Logging SQLite
│   │   ├── ML_Logger.py      # Auditoría CSV
│   │   └── GestorPrediccion.py
│   └── BotController.py      # Cerebro Principal
├── Machine_Learning/
│   ├── Data/
│   │   └── shadow_data.db    # [NUEVO] Base de datos de aprendizaje
│   ├── Scripts/
│   │   ├── Analysis/
│   │   │   └── shadow_judge.py  # [NUEVO] El Juez Imparcial
│   │   ├── Optimization/
│   │   │   └── auto_tuner.py    # [NUEVO] El Optimizador Autónomo
│   └── Logs/
├── Estrategias/              # Lógica de señales (RSI, SuperTrend, etc.)
└── config_trading.json       # Configuración central
```

---

## 🚀 Uso del Auto-Tuner

El sistema de optimización es modular. Puedes ejecutarlo manualmente o programarlo (CRON).

### 1. Ejecución Manual
```bash
python Machine_Learning/Scripts/Optimization/auto_tuner.py
```

### 2. Configuración
En el script `auto_tuner.py`:
- `ENABLE_AUTOTUNER = False`: Modo **Dry Run** (Solo sugiere, envía alerta a Telegram).
- `ENABLE_AUTOTUNER = True`: Modo **Live** (Modifica `config_trading.json` automáticamente).

---

## 🔧 Configuración Rápida

### Variables de Entorno (.env)
```env
BINANCE_API_KEY=tu_api_key
BINANCE_SECRET_KEY=tu_secret_key
TELEGRAM_TOKEN=tu_bot_token
TELEGRAM_ID=tu_chat_id
```

### Configuración de Riesgo (config_trading.json)
```json
"sistema_riesgo": {
  "stop_loss_pct": 0.02,
  "take_profit_pct": 0.28,
  "ml_threshold": 0.75  // Este valor es ajustado SOLO por el AutoTuner
}
```

---

## 📈 Roadmap & Estado

- [x] Conexión Binance Futures (Estable)
- [x] Machine Learning (Random Forest)
- [x] Paper Trading (Simulación)
- [x] **Shadow Trading System (Fase 1: Recolección)**
- [x] **Shadow Judge (Fase 2: Análisis)**
- [x] **Auto-Tuner (Fase 3: Auto-Optimización)**
- [x] Notificaciones Telegram Inteligentes
- [x] Migración a SQLite
- [ ] Dashboard Web Completo (React/Next.js)

---

## ⚠️ Disclaimer

**Este software opera con dinero real.** El trading de futuros conlleva riesgos significativos. La funcionalidad de Auto-Tuning modifica parámetros de riesgo automáticamente; úsala con precaución y monitoreo constante inicial.

---

## 📝 Licencia

Este proyecto es de uso privado. No redistribuir sin autorización.