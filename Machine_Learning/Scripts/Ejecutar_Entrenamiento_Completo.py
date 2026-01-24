
import subprocess
import sys
import os
import time
from colorama import Fore, init, Style

# ==============================================================================
# ⚙️ CONFIGURACIÓN DE EJECUCIÓN (TÚ MANDAS AQUÍ)
# ==============================================================================
# True = El script NO preguntará nada y ejecutará "Sí a todo".
# False = El script pedirá confirmación en cada paso crítico (RECOMENDADO).
MODO_AUTOMATICO = True 
# ==============================================================================

init(autoreset=True)

# Rutas Relativas
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) # Scripts/
ML_DIR = os.path.dirname(BASE_DIR)                    # Machine_Learning/
CORE_DIR = os.path.join(ML_DIR, "Core")
SCRIPTS_DIR = os.path.join(ML_DIR, "Scripts")

# Scripts a Ejecutar
SCRIPT_DATA = os.path.join(CORE_DIR, "DataCollector.py")
SCRIPT_OPTIMIZER = os.path.join(CORE_DIR, "Optimizer.py")
SCRIPT_TRAINER = os.path.join(SCRIPTS_DIR, "Training", "TrainModel.py")
SCRIPT_THRESHOLDS = os.path.join(SCRIPTS_DIR, "Tests", "Optimizar_Umbrales.py")

def ejecutar_paso(nombre, ruta_script, argumentos=[]):
    print(f"\n{Fore.CYAN}" + "="*70)
    print(f"🚀 EJECUTANDO PASO: {nombre}")
    print("="*70 + f"{Style.RESET_ALL}")
    
    # Construir comando
    # Usamos sys.executable para garantizar que se usa el mismo entorno virtual python
    cmd = [sys.executable, ruta_script] + argumentos
    
    try:
        resultado = subprocess.run(cmd, check=True)
        if resultado.returncode == 0:
            print(f"\n{Fore.GREEN}✅ PASO '{nombre}' COMPLETADO CON ÉXITO.")
            return True
        else:
            print(f"\n{Fore.RED}❌ PASO '{nombre}' FINALIZÓ CON ERRORES.")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"\n{Fore.RED}❌ ERROR CRÍTICO EJECUTANDO {nombre}: {e}")
        return False
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}⚠️ PROCESO INTERRUMPIDO POR EL USUARIO.")
        return False

def confirmar_continuacion(mensaje):
    if MODO_AUTOMATICO:
        return True
        
    print(f"\n{Fore.YELLOW}❓ {mensaje}{Style.RESET_ALL}")
    resp = input("Presiona ENTER para continuar o 'n' para cancelar: ").strip().lower()
    if resp == 'n':
        return False
    return True

def main():
    print(f"{Fore.MAGENTA}🤖 INICIANDO PIPELINE DE ENTRENAMIENTO COMPLETO (V1.0)")
    print(f"Modo Automático: {'ACTIVADO' if MODO_AUTOMATICO else 'DESACTIVADO (Manual)'}")
    
    start_time = time.time()

    # ---------------------------------------------------------
    # PASO 1: RECOLECCIÓN Y PROCESAMIENTO DE DATOS
    # ---------------------------------------------------------
    if not confirmar_continuacion("¿Proceder con la Recolección/Procesamiento de Datos?"): return
    
    # DataProcessor no tiene argumentos especiales, corre siempre.
    if not ejecutar_paso("Procesamiento de Datos", SCRIPT_DATA): return

    # ---------------------------------------------------------
    # PASO 2: OPTIMIZACIÓN DE ESTRATEGIAS (GridSearch)
    # ---------------------------------------------------------
    if not confirmar_continuacion("¿Proceder con la Búsqueda de Mejores Estrategias?"): return
    
    # Si Auto = True, pasamos --auto para que Optimizer guarde config sin preguntar
    args_opt = ["--auto"] if MODO_AUTOMATICO else []
    if not ejecutar_paso("Optimización de Estrategias", SCRIPT_OPTIMIZER, args_opt): return

    # ---------------------------------------------------------
    # PASO 3: ENTRENAMIENTO DE MODELOS (Machine Learning)
    # ---------------------------------------------------------
    if not confirmar_continuacion("¿Proceder con el Entrenamiento de Modelos (.joblib)?"): return
    
    # TrainModel es automático por naturaleza
    if not ejecutar_paso("Entrenamiento de IA", SCRIPT_TRAINER): return

    # ---------------------------------------------------------
    # PASO 4: CALIBRACIÓN DE UMBRALES (Precisión)
    # ---------------------------------------------------------
    if not confirmar_continuacion("¿Proceder con la Calibración de Umbrales Finales?"): return
    
    # Si Auto = True, pasamos --auto para que Optimizar_Umbrales guarde sin preguntar
    args_th = ["--auto"] if MODO_AUTOMATICO else []
    if not ejecutar_paso("Calibración de Umbrales", SCRIPT_THRESHOLDS, args_th): return

    # ---------------------------------------------------------
    # FIN DEL FLUJO
    # ---------------------------------------------------------
    total_time = (time.time() - start_time) / 60
    print(f"\n{Fore.GREEN}" + "="*70)
    print(f"🏁 CICLO DE ENTRENAMIENTO COMPLETADO EXITOSAMENTE")
    print(f"⏱️  Tiempo Total: {total_time:.1f} minutos")
    print("="*70 + f"{Style.RESET_ALL}")
    print("Tu bot está actualizado y listo para operar con los nuevos cerebros.")

if __name__ == "__main__":
    main()
