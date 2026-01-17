import csv
import os
from datetime import datetime

class TradeLogger:
    """
    Registra eventos de trading en un archivo CSV persistente.
    """
    # Se guardará en la carpeta raíz del proyecto
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ARCHIVO = os.path.join(BASE_DIR, 'historial_trading.csv')

    @staticmethod
    def registrar(simbolo, accion, precio, extra=""):
        """
        Escribe una línea en el CSV.
        - accion: "ENTRADA", "SL_INICIAL", "TRAILING_UPDATE", "CIERRE"
        """
        existe = os.path.isfile(TradeLogger.ARCHIVO)
        
        try:
            with open(TradeLogger.ARCHIVO, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Si es archivo nuevo, ponemos encabezados
                if not existe:
                    writer.writerow(['FECHA_HORA', 'PAR', 'ACCION', 'PRECIO', 'DETALLES'])
                
                # Escribimos el evento
                ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                writer.writerow([ahora, simbolo, accion, precio, extra])
                
        except Exception as e:
            print(f"⚠️ Error escribiendo log CSV: {e}")