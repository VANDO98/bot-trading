#!/usr/bin/env python3
"""
Script de Análisis de Trading
Descarga trades del exchange y genera reportes completos (Excel + Gráficos)
"""

import os
import sys
import ccxt
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Añadir el directorio raíz al path para importar módulos del bot
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Core.Utils.Config import Config

# Configurar estilo de gráficos
sns.set_style("darkgrid")
plt.rcParams['figure.figsize'] = (16, 10)
plt.rcParams['font.size'] = 10

load_dotenv()


class AnalizadorTrades:
    """Clase principal para descargar y analizar trades"""
    
    def __init__(self):
        """Inicializa la conexión con el exchange"""
        self.exchange = None
        self.trades_df = None
        self.config = None
        self._conectar_exchange()
    
    def _conectar_exchange(self):
        """Establece conexión con Binance Futures"""
        key = os.getenv("BINANCE_API_KEY")
        secret = os.getenv("BINANCE_SECRET_KEY")
        
        if not key or not secret:
            print("❌ ERROR: No hay API keys en .env")
            sys.exit(1)
        
        try:
            self.exchange = ccxt.binance({
                'apiKey': key,
                'secret': secret,
                'enableRateLimit': True,
                'options': {'defaultType': 'future'}
            })
            
            # Cargar configuración
            self.config = Config.cargar_configuracion()
            
            # Configurar testnet/mainnet
            if Config.USAR_TESTNET:
                self.exchange.set_sandbox_mode(True)
                print("🔑 Conectado a BINANCE TESTNET")
            else:
                print("🔑 Conectado a BINANCE MAINNET")
            
            self.exchange.load_markets()
            print("✅ Conexión establecida correctamente\n")
            
        except Exception as e:
            print(f"❌ Error conectando al exchange: {e}")
            sys.exit(1)
    
    def descargar_trades(self, horas_atras):
        """
        Descarga todos los trades del periodo especificado
        
        Args:
            horas_atras (int): Número de horas hacia atrás
        """
        print(f"📥 Descargando trades de las últimas {horas_atras} horas...\n")
        
        # Calcular timestamp de inicio
        ahora = datetime.now()
        inicio = ahora - timedelta(hours=horas_atras)
        since = int(inicio.timestamp() * 1000)  # Convertir a milisegundos
        
        # Obtener pares activos de la configuración
        pares = self.config.get('pares', {})
        simbolos_activos = [par for par, cfg in pares.items() if cfg.get('activo', False)]
        
        print(f"Pares a consultar: {len(simbolos_activos)}")
        
        todos_los_trades = []
        
        for simbolo in simbolos_activos:
            try:
                print(f"  ➤ Descargando {simbolo}...", end=" ")
                
                # Descargar trades
                trades = self.exchange.fetch_my_trades(
                    symbol=simbolo,
                    since=since,
                    limit=1000
                )
                
                if trades:
                    todos_los_trades.extend(trades)
                    print(f"✅ {len(trades)} trades")
                else:
                    print("⚪ Sin trades")
                    
            except Exception as e:
                print(f"❌ Error: {e}")
        
        if not todos_los_trades:
            print("\n⚠️ No se encontraron trades en el periodo especificado")
            return False
        
        # Convertir a DataFrame
        self.trades_df = pd.DataFrame(todos_los_trades)
        print(f"\n✅ Total descargado: {len(self.trades_df)} trades")
        
        return True
    
    def procesar_datos(self):
        """Procesa y calcula métricas de los trades"""
        print("\n🔄 Procesando datos...")
        
        if self.trades_df is None or self.trades_df.empty:
            print("❌ No hay datos para procesar")
            return
        
        # Normalizar timestamps
        self.trades_df['fecha_hora'] = pd.to_datetime(
            self.trades_df['timestamp'], 
            unit='ms'
        )
        
        # Calcular comisiones en USDT
        self.trades_df['fee_usdt'] = self.trades_df.apply(
            lambda row: row['fee']['cost'] if row['fee']['currency'] == 'USDT' else 0,
            axis=1
        )
        
        # Calcular valor de cada trade
        self.trades_df['valor_trade'] = (
            self.trades_df['price'] * self.trades_df['amount']
        )
        
        # Separar compras y ventas
        self.trades_df['tipo'] = self.trades_df['side'].map({
            'buy': 'COMPRA',
            'sell': 'VENTA'
        })
        
        print("✅ Datos procesados correctamente")
    
    def calcular_metricas_por_par(self):
        """
        Calcula métricas clave agrupadas por par:
        - PnL Neto
        - Win Rate
        - Max Drawdown
        - Profit Factor
        """
        print("📊 Calculando métricas por par...")
        
        # Agrupar por símbolo y calcular PnL
        metricas_por_par = []
        
        for simbolo in self.trades_df['symbol'].unique():
            trades_par = self.trades_df[self.trades_df['symbol'] == simbolo].copy()
            trades_par = trades_par.sort_values('timestamp')
            
            # Calcular PnL simulando entradas/salidas
            pnl_total = 0
            posicion_actual = 0
            precio_entrada = 0
            trades_cerrados = []
            
            for _, trade in trades_par.iterrows():
                if trade['side'] == 'buy':
                    if posicion_actual <= 0:  # Abriendo long o cerrando short
                        if posicion_actual < 0:  # Cerrando short
                            pnl = (precio_entrada - trade['price']) * abs(posicion_actual)
                            trades_cerrados.append(pnl - trade['fee_usdt'])
                            posicion_actual = 0
                        # Abriendo long
                        precio_entrada = trade['price']
                        posicion_actual = trade['amount']
                    else:  # Aumentando long
                        precio_entrada = (precio_entrada * posicion_actual + trade['price'] * trade['amount']) / (posicion_actual + trade['amount'])
                        posicion_actual += trade['amount']
                        
                else:  # sell
                    if posicion_actual >= 0:  # Cerrando long o abriendo short
                        if posicion_actual > 0:  # Cerrando long
                            pnl = (trade['price'] - precio_entrada) * posicion_actual
                            trades_cerrados.append(pnl - trade['fee_usdt'])
                            posicion_actual = 0
                        # Abriendo short
                        precio_entrada = trade['price']
                        posicion_actual = -trade['amount']
                    else:  # Aumentando short
                        precio_entrada = (precio_entrada * abs(posicion_actual) + trade['price'] * trade['amount']) / (abs(posicion_actual) + trade['amount'])
                        posicion_actual -= trade['amount']
            
            # Calcular métricas
            if trades_cerrados:
                pnl_neto = sum(trades_cerrados)
                trades_ganadores = [t for t in trades_cerrados if t > 0]
                trades_perdedores = [t for t in trades_cerrados if t < 0]
                
                win_rate = (len(trades_ganadores) / len(trades_cerrados)) * 100 if trades_cerrados else 0
                
                # Calcular Max Drawdown
                pnl_acumulado = []
                acum = 0
                for t in trades_cerrados:
                    acum += t
                    pnl_acumulado.append(acum)
                
                if pnl_acumulado:
                    peak = pnl_acumulado[0]
                    max_dd = 0
                    for valor in pnl_acumulado:
                        if valor > peak:
                            peak = valor
                        dd = peak - valor
                        if dd > max_dd:
                            max_dd = dd
                else:
                    max_dd = 0
                
                # Profit Factor
                suma_ganancias = sum(trades_ganadores) if trades_ganadores else 0
                suma_perdidas = abs(sum(trades_perdedores)) if trades_perdedores else 0
                profit_factor = suma_ganancias / suma_perdidas if suma_perdidas > 0 else 99.9
                
                metricas_por_par.append({
                    'Par': simbolo,
                    'PnL_Neto': pnl_neto,
                    'Win_Rate': win_rate,
                    'Max_Drawdown': max_dd,
                    'Profit_Factor': profit_factor,
                    'Num_Trades': len(trades_cerrados)
                })
        
        return pd.DataFrame(metricas_por_par)
    
    def generar_dashboard(self, df_metricas, carpeta_salida):
        """
        Genera el dashboard de 4 cuadrantes con métricas por par
        
        Args:
            df_metricas (DataFrame): Métricas calculadas por par
            carpeta_salida (str): Ruta donde guardar el gráfico
        """
        print("📈 Generando dashboard de rendimiento...")
        
        if df_metricas.empty:
            print("⚠️ No hay datos para generar dashboard")
            return
        
        # Ordenar por PnL para mejor visualización
        df_metricas = df_metricas.sort_values('PnL_Neto', ascending=False)
        
        # Crear figura con 4 subplots (2x2)
        fig, axes = plt.subplots(2, 2, figsize=(16, 10))
        fig.suptitle('Dashboard de Rendimiento por Par', fontsize=20, fontweight='bold', y=0.995)
        
        # Definir colores
        color_positivo = '#4CAF50'
        color_negativo = '#F44336'
        color_neutral = '#2196F3'
        
        # 1. PnL Neto (Top-Left)
        ax1 = axes[0, 0]
        colores_pnl = [color_positivo if x > 0 else color_negativo for x in df_metricas['PnL_Neto']]
        ax1.barh(df_metricas['Par'], df_metricas['PnL_Neto'], color=colores_pnl)
        ax1.set_xlabel('PnL (USDT)', fontweight='bold')
        ax1.set_title('PnL Neto (USDT)', fontsize=14, fontweight='bold', pad=10)
        ax1.axvline(x=0, color='black', linestyle='-', linewidth=0.8)
        ax1.grid(axis='x', alpha=0.3)
        
        # Añadir valores en las barras
        for i, v in enumerate(df_metricas['PnL_Neto']):
            ax1.text(v, i, f' ${v:.2f}', va='center', fontsize=9)
        
        # 2. Win Rate (Top-Right)
        ax2 = axes[0, 1]
        colores_wr = [color_positivo if x >= 50 else color_negativo for x in df_metricas['Win_Rate']]
        ax2.barh(df_metricas['Par'], df_metricas['Win_Rate'], color=colores_wr)
        ax2.set_xlabel('Win Rate (%)', fontweight='bold')
        ax2.set_title('Win Rate (%)', fontsize=14, fontweight='bold', pad=10)
        ax2.set_xlim(0, 100)
        ax2.axvline(x=50, color='orange', linestyle='--', linewidth=1.5, label='Break Even (50%)')
        ax2.grid(axis='x', alpha=0.3)
        ax2.legend(loc='lower right')
        
        # Añadir valores
        for i, v in enumerate(df_metricas['Win_Rate']):
            ax2.text(v, i, f' {v:.1f}%', va='center', fontsize=9)
        
        # 3. Max Drawdown (Bottom-Left)
        ax3 = axes[1, 0]
        ax3.barh(df_metricas['Par'], df_metricas['Max_Drawdown'], color=color_negativo)
        ax3.set_xlabel('Max Drawdown (USDT)', fontweight='bold')
        ax3.set_title('Max Drawdown (USDT)', fontsize=14, fontweight='bold', pad=10)
        ax3.grid(axis='x', alpha=0.3)
        
        # Añadir valores
        for i, v in enumerate(df_metricas['Max_Drawdown']):
            ax3.text(v, i, f' ${v:.2f}', va='center', fontsize=9)
        
        # 4. Profit Factor (Bottom-Right)
        ax4 = axes[1, 1]
        colores_pf = [color_positivo if x > 1 else color_negativo for x in df_metricas['Profit_Factor']]
        df_metricas_pf = df_metricas.copy()
        df_metricas_pf['Profit_Factor'] = df_metricas_pf['Profit_Factor'].clip(upper=10)  # Limitar a 10 para visualización
        ax4.barh(df_metricas_pf['Par'], df_metricas_pf['Profit_Factor'], color=colores_pf)
        ax4.set_xlabel('Profit Factor', fontweight='bold')
        ax4.set_title('Profit Factor', fontsize=14, fontweight='bold', pad=10)
        ax4.axvline(x=1, color='orange', linestyle='--', linewidth=1.5, label='Break Even (1.0)')
        ax4.grid(axis='x', alpha=0.3)
        ax4.legend(loc='lower right')
        
        # Añadir valores
        for i, v in enumerate(df_metricas['Profit_Factor']):
            display_val = min(v, 10)
            label = f' {v:.2f}+' if v > 10 else f' {v:.2f}'
            ax4.text(display_val, i, label, va='center', fontsize=9)
        
        plt.tight_layout()
        
        # Guardar
        ruta_dashboard = os.path.join(carpeta_salida, 'dashboard_rendimiento.png')
        plt.savefig(ruta_dashboard, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"✅ Dashboard guardado: {ruta_dashboard}")
    
    def generar_pnl_acumulado(self, carpeta_salida):
        """Genera gráfico de PnL acumulado en el tiempo"""
        print("📈 Generando gráfico de PnL acumulado...")
        
        # Ordenar por timestamp
        df_ordenado = self.trades_df.sort_values('timestamp').copy()
        
        # Calcular PnL acumulado (simplificado)
        df_ordenado['pnl_estimado'] = df_ordenado.apply(
            lambda row: row['valor_trade'] if row['side'] == 'sell' else -row['valor_trade'],
            axis=1
        )
        df_ordenado['pnl_acumulado'] = df_ordenado['pnl_estimado'].cumsum()
        
        # Crear gráfico
        plt.figure(figsize=(14, 6))
        plt.plot(df_ordenado['fecha_hora'], df_ordenado['pnl_acumulado'], 
                linewidth=2, color='#2196F3')
        plt.fill_between(df_ordenado['fecha_hora'], df_ordenado['pnl_acumulado'], 
                         alpha=0.3, color='#2196F3')
        plt.axhline(y=0, color='red', linestyle='--', linewidth=1, alpha=0.7)
        plt.title('PnL Acumulado en el Tiempo', fontsize=16, fontweight='bold', pad=15)
        plt.xlabel('Fecha/Hora', fontweight='bold')
        plt.ylabel('PnL Acumulado (USDT)', fontweight='bold')
        plt.grid(alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # Guardar
        ruta_pnl = os.path.join(carpeta_salida, 'pnl_acumulado.png')
        plt.savefig(ruta_pnl, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"✅ Gráfico PnL guardado: {ruta_pnl}")
    
    def exportar_excel(self, df_metricas, carpeta_salida):
        """
        Exporta los resultados a un archivo Excel
        
        Args:
            df_metricas (DataFrame): Métricas por par
            carpeta_salida (str): Ruta donde guardar el archivo
        """
        print("📄 Generando archivo Excel...")
        
        ruta_excel = os.path.join(carpeta_salida, 'analisis_completo.xlsx')
        
        with pd.ExcelWriter(ruta_excel, engine='openpyxl') as writer:
            # Hoja 1: Resumen
            df_metricas.to_excel(writer, sheet_name='Resumen', index=False)
            
            # Hoja 2: Trades completos
            columnas_importantes = [
                'fecha_hora', 'symbol', 'side', 'price', 'amount', 
                'valor_trade', 'fee_usdt', 'tipo'
            ]
            df_trades = self.trades_df[columnas_importantes].copy()
            df_trades.to_excel(writer, sheet_name='Trades', index=False)
        
        print(f"✅ Excel guardado: {ruta_excel}")
    
    def ejecutar_analisis_completo(self, horas):
        """
        Ejecuta el flujo completo de análisis
        
        Args:
            horas (int): Horas hacia atrás
        """
        # 1. Descargar trades
        if not self.descargar_trades(horas):
            return
        
        # 2. Procesar datos
        self.procesar_datos()
        
        # 3. Calcular métricas
        df_metricas = self.calcular_metricas_por_par()
        
        if df_metricas.empty:
            print("⚠️ No hay trades cerrados para analizar")
            return
        
        # 4. Crear carpeta de salida
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        carpeta_salida = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            f"Analisis_{timestamp}"
        )
        os.makedirs(carpeta_salida, exist_ok=True)
        print(f"\n📁 Carpeta de salida: {carpeta_salida}")
        
        # 5. Generar dashboard
        self.generar_dashboard(df_metricas, carpeta_salida)
        
        # 6. Generar gráfico PnL acumulado
        self.generar_pnl_acumulado(carpeta_salida)
        
        # 7. Exportar a Excel
        self.exportar_excel(df_metricas, carpeta_salida)
        
        print("\n" + "="*60)
        print("✅ ANÁLISIS COMPLETO GENERADO EXITOSAMENTE")
        print("="*60)
        print(f"\n📊 Resumen General:")
        print(f"   Total de pares analizados: {len(df_metricas)}")
        print(f"   Total de trades: {len(self.trades_df)}")
        print(f"   PnL Total: ${df_metricas['PnL_Neto'].sum():.2f} USDT")
        print(f"   Win Rate Promedio: {df_metricas['Win_Rate'].mean():.1f}%")
        print(f"\n📁 Archivos generados en: {carpeta_salida}")
        print("="*60 + "\n")


def main():
    """Función principal"""
    print("="*60)
    print("      🤖 ANALIZADOR DE TRADES - BOT TRADING")
    print("="*60)
    print()
    
    # Solicitar periodo
    try:
        horas = int(input("¿Cuántas horas hacia atrás deseas analizar? (ej: 24): "))
        if horas <= 0:
            print("❌ El número debe ser mayor a 0")
            return
    except ValueError:
        print("❌ Debes ingresar un número válido")
        return
    
    print()
    
    # Ejecutar análisis
    analizador = AnalizadorTrades()
    analizador.ejecutar_analisis_completo(horas)


if __name__ == "__main__":
    main()
