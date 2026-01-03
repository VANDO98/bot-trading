import sys
import os
import time
import pandas as pd
from datetime import datetime

# Ajuste de rutas para importar desde la carpeta raíz
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Estrategias.BotBase import BotBase

def imprimir_titulo(texto):
    print("\n" + "="*60)
    print(f"🔬 DIAGNÓSTICO: {texto}")
    print("="*60)

def diagnostico_profundo():
    print("🚀 INICIANDO TEST DE INTEGRIDAD DEL SISTEMA...")
    
    # 1. Instanciamos el BotBase (Carga configuración, API y conecta todo)
    try:
        bot = BotBase()
        # Forzamos la descarga de datos sin iniciar el bucle infinito del main
        print("📥 Descargando datos para análisis estático...")
        for par in bot.pares_activos:
            tf = bot.estrategias[par]["timeframe"]
            bot.velas.inicializar_par(par, tf)
            time.sleep(1)
    except Exception as e:
        print(f"❌ ERROR CRÍTICO AL INICIAR: {e}")
        return

    # --- FASE 1: AUDITORÍA DE MEMORIA (RAM) ---
    imprimir_titulo("INTEGRIDAD DE DATOS (VELAS)")
    
    for par in bot.pares_activos:
        df = bot.velas.obtener_dataframe(par)
        
        if df is None or df.empty:
            print(f"❌ {par}: DataFrame vacío o inexistente.")
            continue
            
        cantidad = len(df)
        ultimo_time =  datetime.fromtimestamp(df.iloc[-1]['timestamp'] / 1000)
        primer_time = datetime.fromtimestamp(df.iloc[0]['timestamp'] / 1000)
        
        # Verificamos si hay saltos de tiempo (Gaps)
        # Calculamos la diferencia entre velas consecutivas
        diffs = df['timestamp'].diff().dropna()
        # El salto esperado en ms (ej: 5m = 300,000ms)
        salto_esperado = diffs.median()
        saltos_raros = diffs[diffs != salto_esperado]
        
        print(f"🔎 {par}:")
        print(f"   • Cantidad de velas: {cantidad} (Esperado: ~1000)")
        print(f"   • Rango: {primer_time}  ->  {ultimo_time}")
        
        if cantidad < 999:
             print("   ⚠️ ADVERTENCIA: Menos de 1000 velas.")
        elif not saltos_raros.empty:
             print(f"   ⚠️ ADVERTENCIA: Se detectaron {len(saltos_raros)} huecos en el tiempo (Data corrupta).")
        else:
             print("   ✅ Integridad Temporal: PERFECTA (Sin huecos).")

    # --- FASE 2: PRECISIÓN MATEMÁTICA (RSI) ---
    imprimir_titulo("CÁLCULO DE INDICADORES (RSI)")
    print("ℹ️  Compara estos valores con tu App de Binance o TradingView:")
    
    for par in bot.pares_activos:
        closes = bot.velas.obtener_closes(par)
        config = bot.estrategias[par]
        periodo = config["indicadores"].get("rsi_periodo", 14)
        
        rsi = bot.analista.calcular_rsi(closes, periodo)
        precio_actual = closes[-1]
        
        print(f"📊 {par} ({bot.estrategias[par]['timeframe']}):")
        print(f"   • Precio Cierre Vela: ${precio_actual:,.2f}")
        print(f"   • RSI ({periodo}): {rsi:.2f}")
        print("   -----------------------")

    # --- FASE 3: LÓGICA FINANCIERA (CARTERA) ---
    imprimir_titulo("SIMULACIÓN DE GESTIÓN DE RIESGO")
    
    balance = bot.ejecutor.obtener_balance_usdt()
    print(f"💰 Balance Real en Futuros: ${balance:.2f} USDT")
    
    if balance < 10:
        print("⚠️ Saldo bajo o Modo Test (Simularemos con $1,000 ficticios)")
        balance_simulado = 1000.0
    else:
        balance_simulado = balance

    for par in bot.pares_activos:
        config = bot.estrategias[par]
        porcentaje = config.get("porcentaje_balance", 1)
        leverage = config.get("apalancamiento", 1)
        decimales = config.get("decimales", 3)
        precio = bot.mercado.obtener_precio(par) 
        if precio == 0: precio = bot.velas.obtener_closes(par)[-1] # Fallback si no hay stream

        # Cálculo manual para verificar al bot
        margen_teorico = balance_simulado * (porcentaje / 100)
        poder_compra = margen_teorico * leverage
        cantidad_esperada = round(poder_compra / precio, decimales)
        
        # Cálculo del Bot
        # Hackeamos temporalmente el obtener_balance para testear con la simulación si es necesario
        original_get_balance = bot.ejecutor.obtener_balance_usdt
        if balance < 10:
            bot.ejecutor.obtener_balance_usdt = lambda: 1000.0
            
        cantidad_bot, _ = bot.ejecutor.calcular_cantidad(par, porcentaje, precio, leverage, decimales)
        
        # Restauramos
        bot.ejecutor.obtener_balance_usdt = original_get_balance

        print(f"Risk {par}:")
        print(f"   • Estrategia: {porcentaje}% de la cuenta x{leverage} apalancamiento")
        print(f"   • Inversión (Margen): ${margen_teorico:.2f}")
        print(f"   • Poder de Compra Total: ${poder_compra:.2f}")
        print(f"   • Cantidad Calculada por Bot: {cantidad_bot}")
        print(f"   • Cantidad Verificación Manual: {cantidad_esperada}")
        
        if abs(cantidad_bot - cantidad_esperada) < 0.00001:
            print("   ✅ CÁLCULO EXACTO.")
        else:
            print("   ❌ DISCREPANCIA EN EL CÁLCULO.")

    # Limpieza
    bot.detener_servicios()
    print("\n🏁 DIAGNÓSTICO FINALIZADO.")

if __name__ == "__main__":
    diagnostico_profundo()