# 🤖 Evolución ML - Bot de Trading Algorítmico (Beta v2.8)

> Sistema de trading autónomo para Binance Futures con arquitectura híbrida, protecciones de ejecución avanzadas (Cancel & Replace) y visualización en tiempo real.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Binance API](https://img.shields.io/badge/Binance-Futures-yellow.svg)
![Status](https://img.shields.io/badge/Estado-Producción_Estable-green.svg)

## 🧠 Filosofía del Sistema: "Moon Mode" (Trend Following)
El bot está diseñado para **dejar correr las ganancias**.
- **Entrada:** Confirmación algorítmica (RSI + ADX + Acción de Precio).
- **Salida:**
  1. **Take Profit Extendido (30%):** Configurado globalmente en JSON para actuar como "Techo de Seguridad" ante pumps violentos.
  2. **Trailing Stop Dinámico:** El verdadero motor de salida. Persigue el precio protegiendo ganancias (Breakeven al 5%, Trailing al 10%) sin cortar la tendencia prematuramente.

---

## 🚀 Innovaciones Técnicas (v2.8)

### 1. Ejecución Blindada ("A Prueba de Balas")
* **Estrategia Cancel & Replace:** Supera las limitaciones de la API de Binance para editar órdenes `STOP_MARKET`, asegurando que el Stop Loss siempre se mueva.
* **Rollback de Emergencia:** Sistema de seguridad transaccional. Si falla la colocación de un nuevo Stop Loss (por lag o rechazo), el sistema **restaura automáticamente** la orden anterior en milisegundos para nunca dejar la posición desprotegida.
* **Anti-Desync:** Validación periódica (cada 5 min) que sincroniza la memoria del bot con la blockchain real.

### 2. Gestión de Riesgo
* **Configuración Centralizada:** Control total de SL/TP y Apalancamiento desde `config_trading.json`.
* **Lógica Anti-Retroceso:** Algoritmo matemático que garantiza que el Stop Loss solo se mueva a favor de la ganancia.

### 3. Arquitectura del Proyecto
  
   bot-trading/
   ├── Core/
   │   ├── API/            # Conexión Híbrida (REST + WebSockets)
   │   ├── Ejecucion/      # Drivers de Órdenes (Lógica Rollback)
   │   ├── Utils/          # Dashboard.py (Visualización), Logger
   │   └── BotController.py # Cerebro Orquestador
   ├── Estrategias/        # Lógica de decisión modular
   ├── Test/               # Scripts de validación (Sandbox)
   ├── main.py             # Punto de entrada
   └── config_trading.json # Configuración de pares y riesgo

### 🛠️ Instalación y Uso

   1. Requisitos:
      pip install -r requirements.txt

   2. Configuración:
      *  Archivo .env: Claves BINANCE_API_KEY y BINANCE_SECRET_KEY.
      *  Archivo config_trading.json: Define tus pares, apalancamiento y el TP objetivo (ej. 0.30).

   3. Ejecución:
      python main.py

## 📋 Roadmap & Estado
   [x] Conexión Binance Futures (Estable)

   [x] Protección Rollback (Implementada)

   [x] Trailing Stop (Cancel/Replace Validado)

   [x] Dashboard Visual (Separado y Modular)

   [ ] Módulo Machine Learning (En fase de entrenamiento)

   [ ] Notificaciones Telegram (Pendiente)

⚠️ Disclaimer: Este software opera con dinero real. El trading de futuros conlleva riesgos significativos. Utilizar bajo propia responsabilidad.