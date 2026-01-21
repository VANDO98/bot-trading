import sys
import os
import ccxt
import json
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
from colorama import init, Fore, Style
from pathlib import Path

# Ajuste de rutas para importar Core
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from Core.Utils.Config import Config

init(autoreset=True)

class RecolectorForense:
    def __init__(self):
        print(Fore.YELLOW + "🕵️ INICIANDO RECOLECCIÓN FORENSE (MODO TIEMPO)...")
        
        # 1. Cargar Configuración
        self.config_completa = Config.cargar_configuracion()
        self.pares_config = self.config_completa.get('pares', {})
        self.usar_testnet = self.config_completa.get('usar_testnet', True)

        # 2. Conectar Exchange
        env_path = Path(__file__).parent.parent / '.env'
        load_dotenv(dotenv_path=env_path)
        
        key = os.getenv("BINANCE_API_KEY")
        secret = os.getenv("BINANCE_SECRET_KEY")
        
        if not key or not secret:
            print(Fore.RED + "❌ Error: No se encontraron API Keys en .env")
            sys.exit()

        try:
            self.exchange = ccxt.binance({
                'apiKey': key,
                'secret': secret,
                'options': {'defaultType': 'future'}
            })
            if self.usar_testnet:
                self.exchange.set_sandbox_mode(True)
                print(Fore.MAGENTA + "🧪 MODO TESTNET DETECTADO")
            else:
                print(Fore.CYAN + "💳 MODO REAL DETECTADO")
                
            self.exchange.load_markets()
        except Exception as e:
            print(Fore.RED + f"❌ Error de conexión: {e}")
            sys.exit()

    def serializar(self, obj):
        """Convierte objetos de CCXT a formato JSON compatible"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        return str(obj)

    def recolectar_por_tiempo(self, horas_atras=24):
        # Calcular Timestamp de inicio (milisegundos)
        ahora = time.time()
        inicio_segundos = ahora - (horas_atras * 3600)
        since_ms = int(inicio_segundos * 1000)
        
        fecha_legible = datetime.fromtimestamp(inicio_segundos).strftime('%Y-%m-%d %H:%M:%S')

        reporte = {
            "timestamp_generacion": datetime.now().isoformat(),
            "periodo_analisis": {
                "horas_atras": horas_atras,
                "desde": fecha_legible
            },
            "modo": "TESTNET" if self.usar_testnet else "REAL",
            "pares_analizados": [],
            "datos": {}
        }

        # --- CAMBIO: LEER TODOS LOS PARES DEL JSON (IGNORANDO 'ACTIVO') ---
        todos_los_pares = list(self.pares_config.keys())
        todos_los_pares.sort()
        
        print(Fore.CYAN + f"📥 Analizando historial de {len(todos_los_pares)} pares desde: {fecha_legible}")
        print(Fore.WHITE + "-" * 60)

        for par in todos_los_pares:
            # Filtro visual para no ensuciar si no hay datos
            print(f"   🔎 Escaneando {par}...", end=" ")
            
            datos_par = {
                "trades": [],
                "income_pnl": []
            }

            try:
                # 1. Fetch de TRADES (Con filtro de TIEMPO 'since')
                trades = self.exchange.fetch_my_trades(par, since=since_ms)
                datos_par["trades"] = trades
                
                # 2. Fetch de INCOME (Con filtro de TIEMPO 'since')
                # Income trae: REALIZED_PNL, FUNDING_FEE, COMMISSION, etc.
                try:
                    income = self.exchange.fetch_income(par, since=since_ms)
                    datos_par["income_pnl"] = income
                except Exception as e_inc:
                    # Algunos pares nuevos pueden dar error en income si no hay historial
                    pass

                # Guardamos solo si encontramos algo relevante para no llenar el JSON de basura vacía
                hay_datos = len(trades) > 0 or len(datos_par["income_pnl"]) > 0
                
                if hay_datos:
                    reporte["datos"][par] = datos_par
                    reporte["pares_analizados"].append(par)
                    
                    # Info visual rápida
                    pnl_acumulado = sum(float(x['income']) for x in datos_par["income_pnl"] if x['incomeType'] == 'REALIZED_PNL')
                    color_pnl = Fore.GREEN if pnl_acumulado >= 0 else Fore.RED
                    print(f"{Fore.GREEN}✅ DATOS ENCONTRADOS | Trades: {len(trades)} | PnL: {color_pnl}${pnl_acumulado:.2f}")
                else:
                    print(f"{Fore.LIGHTBLACK_EX}⚪ Sin actividad reciente")
                
                # Pausa anti-ban
                time.sleep(0.15)

            except Exception as e:
                print(Fore.RED + f"❌ Error: {e}")
                # A veces el par ya no existe o cambió de nombre, lo registramos igual
                reporte["datos"][par] = {"error": str(e)}

        # Guardar Archivo
        archivo_salida = "auditoria_trades_24h.json"
        try:
            with open(archivo_salida, 'w', encoding='utf-8') as f:
                json.dump(reporte, f, indent=2, default=self.serializar)
            
            print(Fore.WHITE + "-" * 60)
            print(Fore.GREEN + f"✨ ANÁLISIS COMPLETO.") 
            print(Fore.YELLOW + f"📂 Archivo generado: {os.path.abspath(archivo_salida)}")
            print(Fore.WHITE + "👉 Por favor, sube este archivo al chat para analizar tu flujo de dinero.")
            print(Fore.WHITE + "-" * 60)
        except Exception as e:
            print(Fore.RED + f"❌ Error guardando archivo: {e}")

if __name__ == "__main__":
    recolector = RecolectorForense()
    # Puedes cambiar 24 por el número de horas que quieras revisar
    recolector.recolectar_por_tiempo(horas_atras=24)