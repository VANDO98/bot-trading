# Guía de Migración a Mainnet (Dinero Real)

Sigue estos pasos estrictos para realizar una migración de forma segura.

## 📋 Lista de Verificación Previa

1.  **Cuenta de Futuros**: Tener una cuenta de Binance Futures habilitada y verificado que NO estás en modo "Single Asset" si usas pares variados (o saber que funcionará igual).
2.  **Saldo**: Tener saldo *USDT* en la billetera de **Futuros** (no Spot).
3.  **API Keys Reales**: Generar nuevas claves en Binance con permisos de **Futuros habilitados** y (opcionalmente) restricción de IP para mayor seguridad.

---

## 🚀 Pasos de Migración

### Paso 1: Respaldo de Seguridad
Antes de tocar nada, asegúrate de que tu rama actual está limpia.
```bash
git add .
git commit -m "chore: backup antes de migrar a mainnet"
```

### Paso 2: Actualizar Credenciales (.env)
El bot usa las mismas variables de entorno para ambas redes. Debes reemplazar las claves de Testnet por las Reales.

Edita el archivo `.env`:
```ini
# BORRA las claves de Testnet y pon las de MAINNET
BINANCE_API_KEY=tu_api_key_real_de_binance
BINANCE_SECRET_KEY=tu_secret_key_real_de_binance

# El resto puede quedar igual
TELEGRAM_TOKEN=...
TELEGRAM_ID=...
```
> ⚠️ **CRÍTICO**: Asegúrate de no dejar espacios extra alrededor del `=`.

### Paso 3: Configurar para Producción (config_trading.json)
Debes desactivar el modo pruebas y el modo testnet.

Edita `config_trading.json`:
- **Línea 2**: `"usar_testnet": false` (Cambiar a `false`)
- **Línea 5**: `"modo_ejecucion": "mainnet"`

### Paso 4: Ajuste de Riesgo (MUY RECOMENDADO)
Vas a entrar a un mercado real con liquidez real. Los errores cuestan dinero.
Te recomiendo **bajar la agresividad** para la primera semana:

1.  **Reducir Apalancamiento**: Bajar de 10x/15x a **3x o 5x**.
    *   Edita la sección `"pares"` en `config_trading.json` y cambia `"apalancamiento": 15` por `5`.
2.  **Reducir Tamaño de Posición**: Bajar de 10% a **5%**.
    *   Cambia `"cantidad_operacion": "10%"` por `"5%"`.
3.  **Reducir Exposición Global**:
    *   Cambia `"max_trades_abiertos": 8` por **3**.

Ejemplo de Configuración Segura para Inicio:
```json
"max_trades_abiertos": 3,
...
"BTC/USDT": {
    "cantidad_operacion": "5%",
    "apalancamiento": 5,
    ...
}
```

### Paso 5: Limpieza de Estado
Borra los archivos temporales para evitar que el bot crea que tiene posiciones antiguas.
```bash
# Script de limpieza incluido puede ayudar, o manualmente:
rm logs/*.log
rm Registros/*.csv # Opcional, si quieres historial limpio
```

### Paso 6: Lanzamiento
Ejecuta el bot.
```bash
python main.py
```

### Paso 7: Verificación Inmediata
Apenas arranque, verifica en la consola:
1.  Que diga en color **ROJO/AMARILLO**: `🔑 Gestor Ejecución: Conectado a REAL.` (o similar).
2.  Que detecte tu saldo real de USDT correctamente.
3.  Que **NO** abra operaciones inmediatamente a menos que haya señal clara.

---

## 🛡️ Recomendación de TPs Escalonados
Dado que vas a Mainnet, te sugiero activar el sistema escalonado que acabamos de implementar para asegurar ganancias:

```json
"tp_escalonados": {
  "activo": true,  <-- Actívalo
  "niveles": [ ... ],
  "auto_break_even": true
}
```
Esto protegerá tu capital moviendo el SL a Break-Even automáticamente.

---

## 🆘 En caso de Emergencia
Si el bot empieza a abrir/cerrar operaciones como loco:
1.  Presiona **CTRL + C** en la terminal inmediatamente.
2.  Entra a la App de Binance o Web y usa el botón **"Cerrar Todo" (Close All Positions)**.
3.  Revoca las API Keys si es necesario.
