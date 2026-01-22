# Nota Técnica: Lógica de Temporizador del Trailing Stop

**Fecha:** 22/01/2026
**Tema:** Desincronización del Trailing Stop con el reloj (:00, :15, :30).

## Comportamiento Observado
Los logs del Trailing Stop aparecen en minutos "extraños" (ej: `00:19`, `00:34`, `00:49`) en lugar de los cuartos de hora naturales.

## Causa Confirmada
La lógica implementada en `BotController.py` utiliza un intervalo **Relativo**, no Absoluto.

```python
# Lógica Actual
toca_por_tiempo = (now - last_check) > 900 # 15 minutos en segundos
```

Esto significa que el intervalo de 15 minutos comienza a contar **desde el momento en que se ejecutó por última vez** (o desde que arrancó el bot).
- Si el bot arranca/reinicia a las `00:04`, el chequeo será a las `00:19`, luego `00:34`, etc.

## Estado
- **Funcionalidad:** Correcta (la seguridad se mantiene porque el intervalo es fijo).
- **Estética:** Desalineada con el reloj de pared.

## Posible Mejora Futura (Opción B)
Si se desea alinear con el reloj (:00, :15, :30), se debe cambiar la condición para usar módulo de tiempo:

```python
# Propuesta (No implementada)
minuto_actual = datetime.now().minute
es_cuarto_de_hora = minuto_actual % 15 == 0
```
