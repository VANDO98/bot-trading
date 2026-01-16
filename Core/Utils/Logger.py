import sys
import os
from datetime import datetime

class DetectorErrores:
    """
    Clase que intercepta la salida de errores (stderr) y la guarda en un archivo,
    además de mostrarla en consola.
    """
    def __init__(self):
        # Asegurar que la carpeta logs existe
        if not os.path.exists('logs'):
            os.makedirs('logs')
            
        self.terminal = sys.stderr
        self.log_file = open("logs/errores.log", "a", encoding='utf-8')

    def write(self, message):
        # 1. Mostrar en pantalla (para que sigas viéndolo fugazmente)
        self.terminal.write(message)
        
        # 2. Guardar en archivo (si tiene contenido real)
        if message.strip():
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            # Evitamos poner timestamp en saltos de linea puros
            self.log_file.write(f"[{timestamp}] {message}\n")
            self.log_file.flush() # Guardar inmediatamente

    def flush(self):
        self.terminal.flush()
        self.log_file.flush()

def activar_logger():
    """Redirige los errores al archivo logs/errores.log"""
    sys.stderr = DetectorErrores()
    print("📼 Sistema de grabación de errores ACTIVADO.")