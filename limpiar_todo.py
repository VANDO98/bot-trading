import os
import platform
import shutil
import subprocess
import time
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
                try:
                    shutil.rmtree(ruta)
                    contador_pycache += 1
                except Exception as e:
                    print(f"{Fore.RED}   Error borrando {ruta}: {e}")
    print(f"✅ Se eliminaron {contador_pycache} carpetas __pycache__.")

    # 2. Borrar archivos .pyc
    print(f"{Fore.BLUE}📄 Eliminando archivos compilados (.pyc)...")
    for root, dirs, files in os.walk("."):
        for file in files:
            if file.endswith(".pyc"):
                try:
                    os.remove(os.path.join(root, file))
                except Exception:
                    pass

    # 3. Matar procesos de Python colgados (Zombies)
    print(f"{Fore.BLUE}💀 Finalizando procesos de Python residuales (Zombies)...")
    
    try:
        if sistema == "Windows":
            print(f"{Fore.YELLOW}   Detectado Windows: Usando taskkill...")
            # taskkill /F /IM python.exe /T (Fuerza, Imagen, Árbol de procesos)
            subprocess.run(["taskkill", "/F", "/IM", "python.exe", "/T"], 
                           capture_output=True, text=True)
            
        else:
            print(f"{Fore.YELLOW}   Detectado Linux/Mac: Usando pkill agresivo (-f)...")
            # pkill -9 -f python (Busca 'python', 'python3', 'venv/bin/python')
            subprocess.run(["pkill", "-9", "-f", "python"], capture_output=True)
            
            # Doble seguridad: Matar cualquier cosa que se llame 'main.py'
            subprocess.run(["pkill", "-9", "-f", "main.py"], capture_output=True)
            
        print("✅ Procesos limpiados.")
        
    except Exception as e:
        print(f"{Fore.RED}⚠️ No se pudieron matar procesos automáticamente: {e}")
        print(f"{Fore.WHITE}   Intenta cerrar la terminal manualmente.")

    # 4. Limpieza específica de Ubuntu (RAM Cache)
    if sistema == "Linux":
        print(f"{Fore.BLUE}🧠 Liberando caché de RAM (Ubuntu)...")
        try:
            # Intentamos liberar caché sin pedir password si es posible, o ignoramos si falla
            os.system("sync")
            # El siguiente comando requiere sudo, si falla no pasa nada, es opcional
            res = os.system("echo 3 > /proc/sys/vm/drop_caches 2>/dev/null")
            if res != 0:
                print(f"{Fore.LIGHTBLACK_EX}   (Nota: Se requiere sudo para liberar RAM profunda, omitido).")
        except:
            pass
        print("✅ Memoria sincronizada.")

    print("-" * 50)
    print(f"{Fore.GREEN}{Style.BRIGHT}✨ LIMPIEZA COMPLETADA CON ÉXITO")
    print(f"{Fore.WHITE}Ahora puedes iniciar el bot con: {Fore.CYAN}python3 main.py")

if __name__ == "__main__":
    limpiar()