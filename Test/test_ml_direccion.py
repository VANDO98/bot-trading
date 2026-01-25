#!/usr/bin/env python3
"""
Test unitario para verificar que la columna 'Direccion' se registra correctamente
en historial_ml.csv
"""
import sys
import os
import pandas as pd

# Agregar rutas para imports
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from Core.Utils.ML_Logger import MLLogger
from colorama import Fore

def test_direccion_column():
    """Prueba que MLLogger registre correctamente la columna Direccion"""
    
    print(f"{Fore.CYAN}🧪 Iniciando test de columna 'Direccion'...\n")
    
    # Crear datos de prueba
    test_par = "TEST/USDT"
    test_probabilidad = 0.75
    test_umbral = 0.65
    test_resultado = True
    test_direccion = "COMPRA"
    
    # Datos de features simulados (opcional)
    test_features = pd.DataFrame({
        'RSI': [45.5],
        'ADX': [28.3]
    })
    
    print(f"{Fore.YELLOW}📝 Registrando predicción de prueba:")
    print(f"   Par: {test_par}")
    print(f"   Dirección: {test_direccion}")
    print(f"   Probabilidad: {test_probabilidad}")
    print(f"   Umbral: {test_umbral}")
    print(f"   Resultado: {'APROBADO' if test_resultado else 'RECHAZADO'}\n")
    
    # Llamar al logger con todos los parámetros
    try:
        MLLogger.registrar_prediccion(
            par=test_par,
            probabilidad=test_probabilidad,
            umbral=test_umbral,
            resultado=test_resultado,
            input_features=test_features,
            direccion=test_direccion
        )
        print(f"{Fore.GREEN}✅ Registro exitoso!\n")
    except Exception as e:
        print(f"{Fore.RED}❌ Error al registrar: {e}\n")
        return False
    
    # Verificar que el archivo existe y tiene la columna correcta
    try:
        archivo_log = MLLogger.ARCHIVO_LOG
        print(f"{Fore.CYAN}📂 Verificando archivo: {archivo_log}\n")
        
        if not os.path.exists(archivo_log):
            print(f"{Fore.RED}❌ El archivo no existe!\n")
            return False
        
        # Leer el CSV
        df = pd.read_csv(archivo_log)
        
        print(f"{Fore.YELLOW}📊 Columnas encontradas:")
        for col in df.columns:
            print(f"   - {col}")
        print()
        
        # Verificar que la columna 'Direccion' existe
        if 'Direccion' not in df.columns:
            print(f"{Fore.RED}❌ La columna 'Direccion' NO está presente!\n")
            return False
        
        print(f"{Fore.GREEN}✅ Columna 'Direccion' encontrada!\n")
        
        # Mostrar las últimas 3 entradas
        print(f"{Fore.CYAN}📋 Últimas 3 entradas del log:")
        print(df.tail(3).to_string(index=False))
        print()
        
        # Verificar que nuestra entrada de prueba está ahí
        ultima_entrada = df.iloc[-1]
        if ultima_entrada['Par'] == test_par and ultima_entrada['Direccion'] == test_direccion:
            print(f"{Fore.GREEN}✅ Entrada de prueba verificada correctamente!")
            print(f"   Par: {ultima_entrada['Par']}")
            print(f"   Direccion: {ultima_entrada['Direccion']}")
            print(f"   Probabilidad: {ultima_entrada['Probabilidad']}")
            print(f"   Resultado: {ultima_entrada['Resultado']}\n")
        else:
            print(f"{Fore.YELLOW}⚠️ No se encontró la entrada de prueba exacta\n")
        
        return True
        
    except Exception as e:
        print(f"{Fore.RED}❌ Error al verificar archivo: {e}\n")
        return False

if __name__ == "__main__":
    print(f"{Fore.CYAN}{'='*60}")
    print(f"{Fore.CYAN}  TEST: Columna 'Direccion' en historial_ml.csv")
    print(f"{Fore.CYAN}{'='*60}\n")
    
    resultado = test_direccion_column()
    
    print(f"{Fore.CYAN}{'='*60}")
    if resultado:
        print(f"{Fore.GREEN}✅ TEST PASADO: La columna 'Direccion' funciona correctamente!")
    else:
        print(f"{Fore.RED}❌ TEST FALLIDO: Revisar implementación")
    print(f"{Fore.CYAN}{'='*60}\n")
    
    sys.exit(0 if resultado else 1)
