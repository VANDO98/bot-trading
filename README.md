# 🤖 Binance Futures Scalping Bot v5.0
> Sistema automatizado de trading para futuros basado en indicadores técnicos y gestión de riesgo avanzada.

## 📌 Plan Maestro - Estado del Proyecto

### Fase 1: Cimientos [COMPLETADO ✅]
- [x] Conexión robusta con Binance API (REST/WebSocket).
- [x] Gestor de Configuración dinámico (`.env` y `JSON`).
- [x] Sistema de Logs Forense.
- [x] **Gestor de Precisión:** Ajuste automático de decimales (Tick/Step Size).

### Fase 2: Ejecución [EN PROCESO 🛠️]
- [x] **Estrategia Multiactivo:** Soporte para 8+ pares simultáneos.
- [x] **Entradas Limit:** Implementación de "Timeout Paciente" (180s) para ahorro de fees.
- [ ] **Dashboard Estático:** Interfaz de terminal profesional (Próxima sesión).
- [ ] **Control de Posiciones:** Límite estricto de 4 posiciones simultáneas.

### Fase 3: Riesgo y Seguridad [EN PROCESO 🛠️]
- [x] **Limpieza de Zombies:** Eliminación automática de órdenes huérfanas.
- [ ] **Trailing Stop:** Lógica de seguimiento de ganancias (Próxima sesión).
- [ ] **Fix SL Parcial:** Corrección de Stop Loss en llenados no instantáneos.
- [ ] **Telegram Manager (50%):** Comandos básicos de monitoreo.

---

## 🚀 Instalación y Uso

1. **Requisitos:** Python 3.9+, `python-binance`, `pandas`, `python-dotenv`.
2. **Configuración:** - Renombrar `.env.example` a `.env` y colocar tus API Keys.
   - Ajustar pares y temporalidades en `estrategias.json`.
3. **Ejecución:**
   ```bash
   python main.py