# 📈 Estrategias de Trading

Módulo encargado de la lógica de entrada (Señales).

## 🧩 Componentes

- **`EstrategiaBase.py`**: Interfaz que define los métodos obligatorios (`analizar_par`, `confirmar_tendencia`).
- **`Selector.py`**: Utilidad para cargar una estrategia por su nombre (string) desde la configuración.

## 📂 [Concretas/](./Concretas/)
Aquí residen las implementaciones específicas:

- `EstrategiaTrend.py`: Seguimiento de tendencia con EMAs y ADX.
- `EstrategiaRSI_ADX.py`: Combinación de oscilador (RSI) y fuerza (ADX).
- `EstrategiaBB.py`: Rebotes en Bandas de Bollinger.
- `EstrategiaRSI.py`: RSI simple (probablemente base o prueba).
