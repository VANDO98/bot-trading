import sys
import os
from datetime import datetime

# Hack para importar desde la raiz
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from Core.Utils.Logger import activar_logger

print("--- INICIANDO TEST DE LOGGING ---")

# 1. Activar el logger
activar_logger()

# 2. Imprimir mensaje normal (STDOUT) - NO DEBERÍA GUARDARSE
print("ℹ️ Este mensaje es informativo y NO debería ir al log.")
print("✅ Este mensaje es de éxito normal y NO debería ir al log.")

# 3. Imprimir mensaje de error simulado (STDOUT con keyword) - SÍ DEBERÍA GUARDARSE
print("⚠️ Advertencia simulada: Esto sí debe ir al log.")
print("❌ Error simulado: Esto también.")
print("Network connection timed out (Simulated library error)") # Test keyword 'connection'/'timeout'
print("WebSocket disconnected, reconnecting... (Simulated)") # Test keyword 'disconnected'

# 3. Simular error (STDERR)
try:
    raise ValueError("❌ Este es un error simulado para probar el log.")
except Exception as e:
    sys.stderr.write(str(e) + "\n")

# 4. Verificar existencia archivo
fecha_hoy = datetime.now().strftime('%Y-%m-%d')
archivo_esperado = f"logs/session_{fecha_hoy}.log"

if os.path.exists(archivo_esperado):
    print(f"✅ Archivo encontrado: {archivo_esperado}")
    print("Contenido del archivo (Esperamos solo errores):")
    with open(archivo_esperado, 'r') as f:
        contenido = f.read()
        print(contenido)
        
    if "informativo" in contenido:
        print("❌ FALLO: Se guardó mensaje informativo.")
    else:
        print("✅ ÉXITO: Mensajes normales ignorados.")
        
    if "Advertencia" in contenido and "Error simulado" in contenido:
        print("✅ ÉXITO: Errores explícitos detectados.")
    else:
        print("❌ FALLO: No se guardaron los errores explícitos.")

    if "timed out" in contenido and "disconnected" in contenido:
        print("✅ ÉXITO: Errores de librería (keywords) detectados.")
    else:
        print("❌ FALLO: No se detectaron keywords de librería.")
else:
    print(f"❌ ERROR: No se creó el archivo {archivo_esperado}")
