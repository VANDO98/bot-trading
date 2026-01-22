import csv
import os
from datetime import datetime

class MLLogger:
    # 1. Calculamos la ruta absoluta a la carpeta Machine_Learning
    # (Estamos en Core/Utils/, así que subimos 3 niveles para llegar a la raíz)
    ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ARCHIVO_LOG = os.path.join(ROOT_DIR, "Machine_Learning", "Logs", "historial_ml.csv")

    @staticmethod
    def registrar_prediccion(par, probabilidad, umbral, resultado, input_features=None):
        """
        Guarda cada consulta al modelo en un CSV dentro de Machine_Learning/.
        """
        # Verificamos si el archivo existe en la nueva ruta
        existe = os.path.isfile(MLLogger.ARCHIVO_LOG)
        
        try:
            with open(MLLogger.ARCHIVO_LOG, mode='a', newline='') as file:
                writer = csv.writer(file)
                
                # Encabezados si es archivo nuevo
                if not existe:
                    writer.writerow(["Fecha", "Par", "Probabilidad", "Umbral_Config", "Resultado", "Detalles_Extra"])
                
                # Datos a guardar
                fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                estado = "APROBADO" if resultado else "RECHAZADO"
                
                # Opcional: Guardar algún indicador clave para contexto
                detalles = ""
                if input_features is not None and not input_features.empty:
                    try:
                        # Guardamos RSI y ADX si existen para depuración rápida
                        rsi = input_features.iloc[-1].get('RSI', 0)
                        adx = input_features.iloc[-1].get('ADX', 0)
                        detalles = f"RSI={rsi:.1f} | ADX={adx:.1f}"
                    except:
                        pass

                writer.writerow([fecha, par, f"{probabilidad:.4f}", umbral, estado, detalles])
                
        except Exception as e:
            print(f"⚠️ Error escribiendo log ML: {e}")