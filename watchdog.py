import subprocess
import time
import sys
import os
from colorama import Fore, init

init()

def detectar_venv():
    """
    Busca el directorio del entorno virtual y devuelve la ruta al ejecutable python.
    Prioriza .venv_v2, luego venv, luego None.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Buscar .venv_v2 primero (parece ser el activo según los directorios)
    candidates = ['.venv_v2', 'venv', '.venv']
    
    for venv_dir in candidates:
        venv_path = os.path.join(base_dir, venv_dir)
        python_path = os.path.join(venv_path, 'bin', 'python')
        
        if os.path.exists(python_path):
            print(f"{Fore.GREEN}🐍 Venv detectado: {venv_dir}")
            return python_path, venv_path
    
    print(f"{Fore.YELLOW}⚠️ No se encontró venv. Usando Python del sistema: {sys.executable}")
    return sys.executable, None

def verificar_requirements(python_executable, venv_path):
    """
    Verifica que las dependencias de requirements.txt estén instaladas.
    Si faltan, intenta instalarlas automáticamente.
    """
    requirements_file = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    
    if not os.path.exists(requirements_file):
        print(f"{Fore.YELLOW}⚠️ No se encontró requirements.txt. Saltando verificación.")
        return True
    
    try:
        # Verificar si pip-check está disponible o simplemente intentar instalar
        print(f"{Fore.CYAN}📦 Verificando dependencias...")
        
        # Ejecutar pip install para asegurar que todo esté actualizado
        # Usamos --quiet para no saturar la consola
        result = subprocess.run(
            [python_executable, '-m', 'pip', 'install', '-q', '-r', requirements_file],
            capture_output=True,
            text=True,
            timeout=120  # 2 minutos máximo
        )
        
        if result.returncode == 0:
            print(f"{Fore.GREEN}✅ Dependencias verificadas y actualizadas.")
            return True
        else:
            print(f"{Fore.RED}❌ Error instalando dependencias:")
            print(result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print(f"{Fore.YELLOW}⚠️ La instalación de dependencias tardó demasiado. Continuando...")
        return True
    except Exception as e:
        print(f"{Fore.YELLOW}⚠️ Error verificando requirements: {e}")
        print(f"{Fore.YELLOW}Continuando de todas formas...")
        return True

def run_bot():
    """
    Ejecuta el bot principal en un subproceso y monitorea su estado.
    Si el subproceso muere, lo reinicia.
    """
    script_path = os.path.join(os.path.dirname(__file__), "main.py")
    python_executable, venv_path = detectar_venv()
    
    # Verificar dependencias UNA VEZ al inicio (no en cada reinicio)
    print(f"{Fore.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    if not verificar_requirements(python_executable, venv_path):
        print(f"{Fore.RED}❌ No se pudieron instalar las dependencias. Abortando.")
        sys.exit(1)
    print(f"{Fore.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    while True:
        print(f"{Fore.CYAN}👀 Watchdog: Iniciando Bot ({script_path})...")
        print(f"{Fore.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        try:
            # Ejecutamos main.py con el Python del venv detectado
            process = subprocess.Popen([python_executable, script_path])
            
            try:
                # Esperamos a que el proceso termine
                process.wait()
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}🛑 Watchdog: Deteniendo bot por usuario...")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                sys.exit(0)
            
            # Si el proceso terminó...
            code = process.returncode
            print(f"{Fore.MAGENTA}⚠️ Watchdog: El bot se detuvo (Código {code}).")
            
            if code == 0:
                print(f"{Fore.GREEN}🔄 Reinicio solicitado (Clean Exit). Reiniciando en 2s...")
            else:
                print(f"{Fore.RED}💥 El bot crasheó. Reiniciando en 5s...")
                time.sleep(3) # Espera un poco más si fue error
                
            time.sleep(2)

        except Exception as e:
            print(f"{Fore.RED}❌ Error crítico en Watchdog: {e}")
            time.sleep(5)

if __name__ == "__main__":
    print(f"{Fore.GREEN}🐶 Watchdog iniciado.")
    run_bot()
