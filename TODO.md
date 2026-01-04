# 🚀 Plan de Trabajo - Próxima Sesión (2026-01-04)

## 🚨 Correcciones Críticas (Bugs Detectados)
- [ ] **Sincronización de SL en Llenado Parcial:** Investigar por qué el Stop Loss no se coloca inmediatamente cuando la orden `LIMIT` no se completa al 100% de forma instantánea.
- [ ] **Control de Cupos:** Validar `GestorCapital`. Asegurar que el bot respete el límite de 4 posiciones máximas, incluso con 8 pares activos en el JSON.
- [ ] **Fix Error -2021:** Modificar `GestorPosicion.py` para ejecutar `cerrar_mercado` si el precio actual ya superó el nivel del 1% (evitar rechazo de orden de Binance).

## 📊 Interfaz y Rendimiento (Dashboard v2)
- [ ] **Dashboard Estático:** Implementar una interfaz de terminal fija (usando `curses` o secuencias de escape ANSI) que actualice solo valores cambiantes para evitar el scroll infinito en la terminal.
- [ ] **Módulo Externo:** Separar la lógica del Dashboard a un archivo independiente para que `main.py` solo lo invoque.
- [ ] **Monitor de CPU:** Añadir una métrica de consumo de CPU y memoria del proceso para optimizar el rendimiento con 8+ pares.

## 🎯 Hitos del Plan Maestro
- [ ] **Trailing Stop Perfecto:** Desarrollar la lógica de seguimiento de precio una vez la posición esté en ganancias.
- [ ] **Gestor Telegram (50%):** Implementar comandos básicos de consulta de estado y balance vía Telegram.
- [ ] **Auditoría Plan Maestro:** Revisar hitos restantes de las fases de Cimientos y Ejecución.

## ✅ Completado con éxito (2026-01-03)
- [x] Solucionado Error -4130 (Limpieza manual REST de Algo Orders).
- [x] Implementado `GestorPrecision` con detección automática de Binance (`quantityPrecision`).
- [x] Redondeo automático integrado en `GestorBasico`.
- [x] Configuración de 8 pares en `estrategias.json`.
- [x] Método de Entrada con Timeout Paciente (180s).