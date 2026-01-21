import sys
import os
from datetime import datetime

class StreamLogger:
    """
    Clase que intercepta un stream (stdout/stderr) y lo guarda en un archivo,
    además de mostrarlo en la terminal original.
    """
    def __init__(self, original_stream, filename, log_all=True):
        self.terminal = original_stream
        self.filename = filename
        self.log_all = log_all
        
        # Palabras clave para detectar errores en prints normales (stdout)
        # Incluimos términos técnicos de librerías (CCXT, Requests, Websockets)
        self.errores_keywords = [
            "error", "exception", "traceback", "fallo", "critical", "fatal",
            "⚠️", "❌", "⛔", "🛑", "stop loss", "take profit",
            "connection", "timeout", "disconnected", "closed", "banned", "ddos",
            "api", "network", "warning", "retry", "reconnecting"
        ]
        
        # Asegurar que la carpeta logs existe
        if not os.path.exists('logs'):
            os.makedirs('logs')

    def write(self, message):
        # 1. Mostrar en pantalla original (SIEMPRE)
        self.terminal.write(message)
        
        # 2. Guardar en archivo (CON FILTRO)
        if message and message.strip():
            should_save = self.log_all
            
            # Si no logueamos todo (es stdout), filtro por contenido importante
            if not should_save:
                msg_lower = message.lower()
                if any(kw in msg_lower for kw in self.errores_keywords):
                    should_save = True
            
            if should_save:
                try:
                    with open(self.filename, "a", encoding='utf-8') as log:
                        # Si es el inicio de una línea con contenido, añade timestamp (opcional, por ahora raw)
                        log.write(message)
                except Exception:
                    pass

    def flush(self):
        self.terminal.flush()

def activar_logger():
    """
    Redirige stdout y stderr a un archivo diario 'logs/session_YYYY-MM-DD.log'.
    """
    fecha_hoy = datetime.now().strftime('%Y-%m-%d')
    archivo_log = f"logs/session_{fecha_hoy}.log"
    
    # Redirigimos: 
    # - stdout: Solo guarda si huele a error (log_all=False)
    # - stderr: Guarda TODO (log_all=True)
    sys.stdout = StreamLogger(sys.stdout, archivo_log, log_all=False)
    sys.stderr = StreamLogger(sys.stderr, archivo_log, log_all=True)
    
    # Este mensaje sí queremos verlo en el log para saber cuándo arrancó, forzamos un print de sistema si fuera necesario
    # pero como es stdout y tiene "ACTIVADA", tal vez no se guarde. 
    # Agregamos "⚠️" o "Inicio" si quisiéramos forzar, pero el usuario pidió "solo errores".
    # Así que el mensaje de arranque solo saldrá en consola.
    print(f"📼 Grabación de ERRORES activada -> {archivo_log}")