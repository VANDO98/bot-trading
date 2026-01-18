import os
import platform
import shutil
import subprocess
from colorama import Fore, init, Style

init(autoreset=True)

def limpiar():
    sistema = platform.system()
    print(f"{Fore.CYAN}🧹 Iniciando limpieza profunda en sistema: {Fore.YELLOW}{sistema}")
    print("-" * 50)

    # 1. Borrar carpetas __pycache__
    print(f"{Fore.BLUE}📁 Eliminando __pycache__...")
    contador_pycache = 0
    for root, dirs, files in os.walk(".", topdown=False):
        for name in dirs:
            if name == "__pycache__":
                ruta = os.path.join(root, name)
                shutil.rmtree(ruta)
                contador_pycache += 1
    print(f"✅ Se eliminaron {contador_pycache} carpetas __pycache__.")

    # 2. Borrar archivos .pyc
    print(f"{Fore.BLUE}📄 Eliminando archivos compilados (.pyc)...")
    for root, dirs, files in os.walk("."):
        for file in files:
            if file.endswith(".pyc"):
                os.remove(os.path.join(root, file))

    # 3. Matar procesos de Python colgados (Zombies)
    print(f"{Fore.BLUE}💀 Finalizando procesos de Python residuales...")
    try:
        if sistema == "Windows":
            # taskkill /F /IM python.exe /T (Fuerza, Imagen, Árbol de procesos)
            subprocess.run(["taskkill", "/F", "/IM", "python.exe", "/T"], 
                           capture_output=True, text=True)
        else:
            # pkill -9 python (Ubuntu)
            subprocess.run(["pkill", "-9", "python"], 
                           capture_output=True, text=True)
        print("✅ Procesos limpiados.")
    except Exception as e:
        print(f"{Fore.RED}⚠️ No se pudieron matar procesos: {e}")

    # 4. Limpieza específica de Ubuntu (RAM Cache)
    if sistema == "Linux":
        print(f"{Fore.BLUE}🧠 Liberando caché de RAM (Ubuntu)...")
        # Intentamos liberar caché, requiere permisos de sudo
        print(f"{Fore.YELLOW}Nota: Si solicita contraseña, es para limpiar la RAM.")
        os.system("sudo sync; echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null")
        print("✅ RAM Cache liberada.")

    print("-" * 50)
    print(f"{Fore.GREEN}{Style.BRIGHT}✨ LIMPIEZA COMPLETADA CON ÉXITO")
    print(f"{Fore.WHITE}Los archivos .csv de datos históricos se han {Fore.YELLOW}CONSERVADO{Fore.WHITE}.")

if __name__ == "__main__":
    limpiar()