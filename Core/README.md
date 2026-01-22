# 🧠 Core del Bot

El núcleo del sistema. Aquí se orquesta la ejecución, la conexión con el Exchange y la gestión de riesgo.

## 📂 Estructura Interna

### 🔸 [BotController.py](./BotController.py)
**El Cerebro**.
- Inicializa todos los gestores.
- Mantiene el bucle principal (`main_loop`).
- Decide cuándo buscar oportunidades y cuándo auditar posiciones.

### 🔸 [API/](./API/)
**Conectividad**.
- `GestorWebsocket.py`: Mantiene la conexión en tiempo real con Binance para recibir precios y actualizaciones de órdenes sin latencia.

### 🔸 [Datos/](./Datos/)
**Información de Mercado**.
- `GestorPares.py`: Filtra y selecciona qué pares operar según volumen y volatilidad.
- `BaseDatos.py`: Persistencia temporal de datos.

### 🔸 [Ejecucion/](./Ejecucion/)
**Operaciones de Mercado**.
- `GestorEjecucionBase.py`: Clase padre que define cómo se ejecuta una orden.
- `GestorEjecucion.py`: Ejecución **REAL** en Binance (Mainnet).
- `GestorEjecucionPaper.py`: Simulación **PAPER TRADING**. Ejecuta órdenes ficticias para pruebas sin riesgo.

### 🔸 [Interfaz/](./Interfaz/)
**Comunicación**.
- `Telegram/`: Manejadores para el bot de Telegram (comandos, notificaciones).

### 🔸 [Riesgo/](./Riesgo/)
**Protección de Capital**.
- `GestorStopLoss.py`: Lógica para modificar Stop Loss dinámicamente (Trailing Stop, Break Even).

### 🔸 [Utils/](./Utils/)
**Utilidades Transversales**.
- `Config.py`: Carga la configuración desde `config_trading.json`.
- `AnalizadorTrades.py`: Genera reportes de Excel.
- `GestorPrediccion.py`: Conecta el Core con la carpeta `Machine_Learning`.
