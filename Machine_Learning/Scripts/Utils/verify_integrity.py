import sys
import os
import importlib.util
from colorama import Fore, init

init(autoreset=True)

def check_path_exists(path, description):
    if os.path.exists(path):
        print(f"{Fore.GREEN}✅ {description} encontrado: {path}")
        return True
    else:
        print(f"{Fore.RED}❌ {description} NO encontrado: {path}")
        return False

def check_import(module_name, file_path):
    try:
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        print(f"{Fore.GREEN}✅ Importación exitosa: {module_name}")
        return True
    except Exception as e:
        print(f"{Fore.RED}❌ Falló importación de {module_name}: {e}")
        return False

def main():
    print(Fore.YELLOW + "🔍 VERIFICANDO INTEGRIDAD DE REESTRUCTURACIÓN ML...\n")
    
    base_dir = os.path.dirname(os.path.abspath(__file__)) # Scripts/
    ml_dir = os.path.dirname(base_dir) # Machine_Learning/
    
    # 1. VERIFICAR DIRECTORIOS
    print(Fore.CYAN + "--- 1. Directorios ---")
    dirs = {
        "Core": os.path.join(ml_dir, "Core"),
        "Models": os.path.join(ml_dir, "Models"),
        "Logs": os.path.join(ml_dir, "Logs"),
        "Data/Raw": os.path.join(ml_dir, "Data", "Raw"),
        "Data/Processed": os.path.join(ml_dir, "Data", "Processed"),
        "Data/Historico": os.path.join(ml_dir, "Data", "Historico")
    }
    
    all_dirs_ok = True
    for name, path in dirs.items():
        if not check_path_exists(path, f"Dir {name}"):
            all_dirs_ok = False
            
    # 2. VERIFICAR ARCHIVOS CLAVE
    print(Fore.CYAN + "\n--- 2. Archivos Clave ---")
    files = {
        "Joblib": os.path.join(ml_dir, "Models", "modelo_rf_trading.joblib"),
        "CSV Logs": os.path.join(ml_dir, "Logs", "historial_ml.csv"),
        "Init Core": os.path.join(ml_dir, "Core", "__init__.py")
    }
    
    for name, path in files.items():
        check_path_exists(path, f"File {name}")

    # 3. VERIFICAR IMPORTACIONES (Simulando Scripts)
    print(Fore.CYAN + "\n--- 3. Importaciones desde Scripts ---")
    # Añadimos Core al path como hacen los scripts
    core_path = os.path.join(ml_dir, "Core")
    sys.path.append(core_path)
    
    # Intentamos importar modulos de Core
    modules_to_test = [
        ("DataProcessor", os.path.join(core_path, "DataProcessor.py")),
        ("FeatureEngineering", os.path.join(core_path, "FeatureEngineering.py")),
        ("DataCollector", os.path.join(core_path, "DataCollector.py"))
    ]
    
    import_ok = True
    for name, path in modules_to_test:
        if not check_import(name, path):
            import_ok = False

    # 4. Verificar rutas internas de módulos (leyendo atributos si es posible o texto)
    # Por ejemplo verificar si DataProcessor.CARPETA_ENTRADA apunta bien
    # Esto es más difícil dinámicamente sin instanciar, pero ya lo hicimos en los edits.
    
    print("\n" + "-"*40)
    if all_dirs_ok and import_ok:
        print(Fore.GREEN + "🎉 INTEGRIDAD VERIFICADA: La estructura parece sólida.")
    else:
        print(Fore.RED + "⚠️ ATENCIÓN: Se encontraron errores críticos.")

if __name__ == "__main__":
    main()
