# 🤖 Bot de Trading Algorítmico - Evolución ML (v3.0)

> Sistema de trading autónomo para Binance Futures con Machine Learning, arquitectura híbrida, gestión de riesgo avanzada y toma de ganancias escalonada.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Binance API](https://img.shields.io/badge/Binance-Futures-yellow.svg)
![Status](https://img.shields.io/badge/Estado-Producción-green.svg)
![ML](https://img.shields.io/badge/ML-Random_Forest-orange.svg)

---

## 🎯 Filosofía del Sistema

El bot está diseñado para **maximizar ganancias en tendencias fuertes** mientras protege el capital:

- **Entrada Inteligente**: Doble filtro (Análisis Técnico + Machine Learning)
- **Salida Progresiva**: Sistema de TPs escalonados para capturar movimientos explosivos
- **Protección Dinámica**: Trailing Stop + Auto Break-Even
- **Adaptabilidad**: Cambia entre modos según volatilidad del mercado

---

## ✨ Características Principales

### 🧠 Machine Learning (Random Forest)
- **Filtro de Entrada**: El modelo ML valida cada señal técnica antes de ejecutar
- **Entrenamiento Continuo**: Aprende de operaciones pasadas
- **Umbral Configurable**: Control de sensibilidad (default: 80% confianza)

### 🪜 Toma de Ganancias Escalonada (Ladder TP)
Dos modos disponibles:

#### **Modo Simple** (por defecto)
- Venta única al alcanzar 20% ROE
- 50% de la posición cerrada
- Resto protegido por Trailing Stop

#### **Modo Escalera** (`tp_escalonados.activo: true`)
- **Nivel 1**: ROE 20% → Vende 30%
- **Nivel 2**: ROE 40% → Vende 35%
- **Nivel 3**: ROE 80% → Vende 67%
- **Resultado**: Deja 15% corriendo indefinidamente
- **Ventaja**: 4x más ganancia en tendencias fuertes vs. modo simple

### 🛡️ Protección Avanzada

#### Auto Break-Even
- Se activa automáticamente después del primer TP escalonado
- Solo mueve el SL si mejora la protección actual
- Elimina riesgo de pérdida garantizando entrada + 0.5%

#### Trailing Stop Híbrido
- **Gatillo Doble**: Al cierre de vela O cada 15 minutos
- **Break-Even**: Activa al 7% ROE (Risk Shield a -0.5%)
- **Trailing Dinámico**: Activa al 10% ROE usando ATR (2x)
- **Validación Periódica**: Ghost Buster cada 5 minutos

#### Ejecución Blindada
- **Cancel & Replace**: Supera limitaciones de Binance API
- **Rollback de Emergencia**: Restaura SL anterior si falla actualización
- **Sincronización Automática**: Repara órdenes huérfanas

---

## 📁 Arquitectura del Proyecto

```
bot-trading/
├── Core/
│   ├── API/                  # RESTful + WebSocket híbrido
│   ├── Ejecucion/
│   │   ├── GestorEjecucion.py       # Motor real (Binance)
│   │   └── GestorEjecucionPaper.py  # Simulador (Paper Trading)
│   ├── Interfaz/Telegram/    # Bot de notificaciones
│   ├── Utils/
│   │   ├── GestorPrediccion.py      # ML Engine
│   │   ├── Dashboard.py             # Visualización
│   │   └── TradeLogger.py           # Auditoría
│   └── BotController.py      # Orquestador principal
├── Estrategias/
│   ├── EstrategiaBase.py     # Clase abstracta
│   ├── Concretas/            # RSI+ADX, Trend Following, etc.
│   └── Selector.py           # Factory pattern
├── Machine_Learning/
│   ├── Core/                 # Procesamiento de datos
│   ├── Models/               # Modelos entrenados
│   └── Scripts/              # Entrenamiento y optimización
├── Test/                     # Suite de tests
├── main.py                   # Punto de entrada
└── config_trading.json       # Configuración central
```

---

## � Instalación

### Requisitos
```bash
pip install -r requirements.txt
```

### Configuración

#### 1. Variables de Entorno (`.env`)
```env
BINANCE_API_KEY=tu_api_key
BINANCE_SECRET_KEY=tu_secret_key
```

#### 2. Configuración de Riesgo (`config_trading.json`)
```json
"sistema_riesgo": {
  "stop_loss_pct": 0.02,
  "take_profit_pct": 0.28,
  "tp_parcial_roe": 0.20,
  "porcentaje_venta_parcial": 0.50,
  "tp_escalonados": {
    "activo": false,
    "niveles": [
      { "roe": 0.20, "porcentaje_venta": 0.30 },
      { "roe": 0.40, "porcentaje_venta": 0.35 },
      { "roe": 0.80, "porcentaje_venta": 0.67 }
    ],
    "auto_break_even": true
  },
  "ml_threshold": 0.80
}
```

#### 3. Configuración de Pares
```json
"pares": {
  "BTC/USDT": {
    "activo": true,
    "estrategia": "EstrategiaTrend",
    "cantidad_operacion": "10%",
    "timeframe": "1h",
    "apalancamiento": 15
  }
}
```

### Ejecución

#### Modo Testnet (Recomendado para testing)
```bash
# En config_trading.json: "usar_testnet": true
python main.py
```

#### Modo Paper Trading (Simulación)
```bash
# En config_trading.json: "modo_ejecucion": "paper"
python main.py
```

#### Modo Producción (Mainnet - Dinero Real)
```bash
# En config_trading.json: "usar_testnet": false, "modo_ejecucion": "mainnet"
python main.py
```

> ⚠️ **ADVERTENCIA**: Este modo opera con dinero real en la red principal de Binance.

---

## � Roadmap & Estado

- [x] Conexión Binance Futures (Estable)
- [x] Protección Rollback (Implementada)
- [x] Trailing Stop Dinámico (Cancel/Replace Validado)
- [x] Machine Learning (Random Forest - Operativo)
- [x] Toma de Ganancias Parcial (Simple)
- [x] Toma de Ganancias Escalonada (Ladder)
- [x] Auto Break-Even (Condicional)
- [x] Dashboard Visual (Modular)
- [x] Paper Trading (Simulación Completa)
- [ ] Notificaciones Telegram Avanzadas (En desarrollo)
- [ ] Optimización ML (GridSearch automático)
- [ ] Backtesting Engine

---

## 🧪 Testing

El bot incluye tests exhaustivos:

```bash
# Test de TP Escalonado
python Test/test_ladder_tp.py

# Test de ROE
python Test/verificar_roe_real.py

# Test de Trailing Masivo
python Test/test_trailing_masivo.py
```

---

## 📈 Resultados (Paper Trading)

| Sistema | ROE Final | Ganancia | Posición Restante |
|---------|-----------|----------|-------------------|
| Simple  | 20%       | $10,000  | 50%               |
| Escalera| 80%       | $40,188  | 15%               |

*Escenario: 1 BTC @ $100k → $180k en tendencia alcista*

---

## ⚠️ Disclaimer

**Este software opera con dinero real.** El trading de futuros conlleva riesgos significativos de pérdida de capital. 

- Comienza siempre en **Modo Testnet** o **Paper Trading**
- Comprende completamente la configuración antes de usar capital real
- Nunca arriesgues más de lo que puedes permitirte perder
- El rendimiento pasado no garantiza resultados futuros

**Uso bajo tu propia responsabilidad.**

---

## 📝 Licencia

Este proyecto es de uso privado. No redistribuir sin autorización.