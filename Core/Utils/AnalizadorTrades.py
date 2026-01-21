#!/usr/bin/env python3
"""
Analizador de Trades
Descarga trades del exchange y genera reportes completos (Excel + Gráficos)
Puede usarse como módulo importable o script standalone
"""

import os
import sys
import ccxt
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Configurar estilo de gráficos
sns.set_style("darkgrid")
plt.rcParams['figure.figsize'] = (16, 10)
plt.rcParams['font.size'] = 10

load_dotenv()


class AnalizadorTrades:
    """Clase principal para descargar y analizar trades"""
    
    def __init__(self, exchange_instance=None):
        """
        Inicializa la conexión con el exchange
        
        Args:
            exchange_instance: Instancia de ccxt.Exchange (opcional). Si no se proporciona, se crea una nueva.
        """
        self.exchange = exchange_instance
        self.trades_df = None
        self.config = None
        
        if self.exchange is None:
            self._conectar_exchange()
        else:
            # Si se proporciona un exchange, cargamos solo la config
            from Core.Utils.Config import Config
            self.config = Config.cargar_configuracion()
    
    def _conectar_exchange(self):
        """Establece conexión con Binance Futures"""
        from Core.Utils.Config import Config
        
        key = os.getenv("BINANCE_API_KEY")
        secret = os.getenv("BINANCE_SECRET_KEY")
        
        if not key or not secret:
            raise ValueError("No hay API keys en .env")
        
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
            raise ConnectionError(f"Error conectando al exchange: {e}")
    
    def _limpiar_nombre_par(self, simbolo):
        """Elimina el sufijo :USDT de los nombres de pares"""
        return simbolo.replace(':USDT', '').replace('/USDT', '')
    
    def descargar_trades(self, horas_atras, silent=False):
        """
        Descarga todos los trades del periodo especificado
        
        Args:
            horas_atras (int): Número de horas hacia atrás
            silent (bool): Si True, no imprime mensajes
            
        Returns:
            bool: True si se descargaron trades, False si no hay datos
        """
        if not silent:
            print(f"📥 Descargando trades de las últimas {horas_atras} horas...\n")
        
        # Calcular timestamp de inicio
        ahora = datetime.now()
        inicio = ahora - timedelta(hours=horas_atras)
        since = int(inicio.timestamp() * 1000)
        
        # Obtener pares activos de la configuración
        pares = self.config.get('pares', {})
        simbolos_activos = [par for par, cfg in pares.items() if cfg.get('activo', False)]
        
        if not silent:
            print(f"Pares a consultar: {len(simbolos_activos)}")
        
        todos_los_trades = []
        
        for simbolo in simbolos_activos:
            try:
                if not silent:
                    print(f"  ➤ Descargando {simbolo}...", end=" ")
                
                trades = self.exchange.fetch_my_trades(
                    symbol=simbolo,
                    since=since,
                    limit=1000
                )
                
                if trades:
                    todos_los_trades.extend(trades)
                    if not silent:
                        print(f"✅ {len(trades)} trades")
                else:
                    if not silent:
                        print("⚪ Sin trades")
                    
            except Exception as e:
                if not silent:
                    print(f"❌ Error: {e}")
        
        if not todos_los_trades:
            if not silent:
                print("\n⚠️ No se encontraron trades en el periodo especificado")
            return False
        
        # Convertir a DataFrame
        self.trades_df = pd.DataFrame(todos_los_trades)
        if not silent:
            print(f"\n✅ Total descargado: {len(self.trades_df)} trades")
        
        return True
    
    def procesar_datos(self):
        """Procesa y calcula métricas de los trades"""
        if self.trades_df is None or self.trades_df.empty:
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
    
    def calcular_metricas_por_par(self):
        """
        Calcula métricas clave agrupadas por par
        
        Returns:
            DataFrame con métricas por par
        """
        metricas_por_par = []
        
        for simbolo in self.trades_df['symbol'].unique():
            trades_par = self.trades_df[self.trades_df['symbol'] == simbolo].copy()
            trades_par = trades_par.sort_values('timestamp')
            
            # Calcular PnL simulando entradas/salidas
            posicion_actual = 0
            precio_entrada = 0
            trades_cerrados = []
            
            for _, trade in trades_par.iterrows():
                if trade['side'] == 'buy':
                    if posicion_actual <= 0:
                        if posicion_actual < 0:
                            pnl = (precio_entrada - trade['price']) * abs(posicion_actual)
                            trades_cerrados.append(pnl - trade['fee_usdt'])
                            posicion_actual = 0
                        precio_entrada = trade['price']
                        posicion_actual = trade['amount']
                    else:
                        precio_entrada = (precio_entrada * posicion_actual + trade['price'] * trade['amount']) / (posicion_actual + trade['amount'])
                        posicion_actual += trade['amount']
                else:  # sell
                    if posicion_actual >= 0:
                        if posicion_actual > 0:
                            pnl = (trade['price'] - precio_entrada) * posicion_actual
                            trades_cerrados.append(pnl - trade['fee_usdt'])
                            posicion_actual = 0
                        precio_entrada = trade['price']
                        posicion_actual = -trade['amount']
                    else:
                        precio_entrada = (precio_entrada * abs(posicion_actual) + trade['price'] * trade['amount']) / (abs(posicion_actual) + trade['amount'])
                        posicion_actual -= trade['amount']
            
            # Calcular métricas
            if trades_cerrados:
                pnl_neto = sum(trades_cerrados)
                trades_ganadores = [t for t in trades_cerrados if t > 0]
                trades_perdedores = [t for t in trades_cerrados if t < 0]
                
                win_rate = (len(trades_ganadores) / len(trades_cerrados)) * 100 if trades_cerrados else 0
                
                # Max Drawdown
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
                
                # Limpiar nombre del par
                nombre_limpio = self._limpiar_nombre_par(simbolo)
                
                metricas_por_par.append({
                    'Par': nombre_limpio,
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
            
        Returns:
            str: Ruta del archivo generado
        """
        if df_metricas.empty:
            return None
        
        # Ordenar por PnL para mejor visualización
        df_metricas = df_metricas.sort_values('PnL_Neto', ascending=False)
        
        # Crear figura con 4 subplots (2x2)
        fig, axes = plt.subplots(2, 2, figsize=(16, 10))
        fig.suptitle('Dashboard de Rendimiento por Par', fontsize=20, fontweight='bold', y=0.995)
        
        # Definir colores
        color_positivo = '#4CAF50'
        color_negativo = '#F44336'
        
        # 1. PnL Neto (Top-Left)
        ax1 = axes[0, 0]
        colores_pnl = [color_positivo if x > 0 else color_negativo for x in df_metricas['PnL_Neto']]
        ax1.barh(df_metricas['Par'], df_metricas['PnL_Neto'], color=colores_pnl)
        ax1.set_xlabel('PnL (USDT)', fontweight='bold')
        ax1.set_title('PnL Neto (USDT)', fontsize=14, fontweight='bold', pad=10)
        ax1.axvline(x=0, color='black', linestyle='-', linewidth=0.8)
        ax1.grid(axis='x', alpha=0.3)
        
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
        
        for i, v in enumerate(df_metricas['Win_Rate']):
            ax2.text(v, i, f' {v:.1f}%', va='center', fontsize=9)
        
        # 3. Max Drawdown (Bottom-Left)
        ax3 = axes[1, 0]
        ax3.barh(df_metricas['Par'], df_metricas['Max_Drawdown'], color=color_negativo)
        ax3.set_xlabel('Max Drawdown (USDT)', fontweight='bold')
        ax3.set_title('Max Drawdown (USDT)', fontsize=14, fontweight='bold', pad=10)
        ax3.grid(axis='x', alpha=0.3)
        
        for i, v in enumerate(df_metricas['Max_Drawdown']):
            ax3.text(v, i, f' ${v:.2f}', va='center', fontsize=9)
        
        # 4. Profit Factor (Bottom-Right)
        ax4 = axes[1, 1]
        colores_pf = [color_positivo if x > 1 else color_negativo for x in df_metricas['Profit_Factor']]
        df_metricas_pf = df_metricas.copy()
        df_metricas_pf['Profit_Factor'] = df_metricas_pf['Profit_Factor'].clip(upper=10)
        ax4.barh(df_metricas_pf['Par'], df_metricas_pf['Profit_Factor'], color=colores_pf)
        ax4.set_xlabel('Profit Factor', fontweight='bold')
        ax4.set_title('Profit Factor', fontsize=14, fontweight='bold', pad=10)
        ax4.axvline(x=1, color='orange', linestyle='--', linewidth=1.5, label='Break Even (1.0)')
        ax4.grid(axis='x', alpha=0.3)
        ax4.legend(loc='lower right')
        
        for i, v in enumerate(df_metricas['Profit_Factor']):
            display_val = min(v, 10)
            label = f' {v:.2f}+' if v > 10 else f' {v:.2f}'
            ax4.text(display_val, i, label, va='center', fontsize=9)
        
        plt.tight_layout()
        
        # Guardar
        ruta_dashboard = os.path.join(carpeta_salida, 'dashboard_rendimiento.png')
        plt.savefig(ruta_dashboard, dpi=150, bbox_inches='tight')
        plt.close()
        
        return ruta_dashboard
    
    def exportar_excel(self, df_metricas, carpeta_salida):
        """
        Exporta los resultados a un archivo Excel
        
        Args:
            df_metricas (DataFrame): Métricas por par
            carpeta_salida (str): Ruta donde guardar el archivo
            
        Returns:
            str: Ruta del archivo generado
        """
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
        
        return ruta_excel
    
    def generar_reporte(self, horas, carpeta_base='Registros'):
        """
        Función principal para generar reporte completo (para Telegram)
        
        Args:
            horas (int): Horas hacia atrás
            carpeta_base (str): Directorio base donde crear la carpeta de análisis
            
        Returns:
            dict: Diccionario con las rutas y resumen
                {
                    'excel': ruta_excel,
                    'dashboard': ruta_dashboard,
                    'resumen': {
                        'pnl_total': float,
                        'win_rate_promedio': float,
                        'num_pares': int,
                        'num_trades': int
                    },
                    'carpeta': carpeta_salida
                }
        """
        # 1. Descargar trades
        if not self.descargar_trades(horas, silent=True):
            return None
        
        # 2. Procesar datos
        self.procesar_datos()
        
        # 3. Calcular métricas
        df_metricas = self.calcular_metricas_por_par()
        
        if df_metricas.empty:
            return None
        
        # 4. Crear carpeta de salida
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Determinar el directorio base correcto
        if os.path.isabs(carpeta_base):
            base_dir = carpeta_base
        else:
            # Si es relativo, usar el path del proyecto raíz
            root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            base_dir = os.path.join(root_dir, carpeta_base)
        
        carpeta_salida = os.path.join(base_dir, f"Analisis_{timestamp}")
        os.makedirs(carpeta_salida, exist_ok=True)
        
        # 5. Generar dashboard
        ruta_dashboard = self.generar_dashboard(df_metricas, carpeta_salida)
        
        # 6. Exportar a Excel
        ruta_excel = self.exportar_excel(df_metricas, carpeta_salida)
        
        # 7. Preparar resumen
        resumen = {
            'pnl_total': df_metricas['PnL_Neto'].sum(),
            'win_rate_promedio': df_metricas['Win_Rate'].mean(),
            'num_pares': len(df_metricas),
            'num_trades': len(self.trades_df)
        }
        
        return {
            'excel': ruta_excel,
            'dashboard': ruta_dashboard,
            'resumen': resumen,
            'carpeta': carpeta_salida
        }
    
    def ejecutar_analisis_completo(self, horas):
        """
        Ejecuta el flujo completo de análisis (para CLI)
        
        Args:
            horas (int): Horas hacia atrás
        """
        # 1. Descargar trades
        if not self.descargar_trades(horas):
            return
        
        # 2. Procesar datos
        print("\n🔄 Procesando datos...")
        self.procesar_datos()
        print("✅ Datos procesados correctamente")
        
        # 3. Calcular métricas
        print("📊 Calculando métricas por par...")
        df_metricas = self.calcular_metricas_por_par()
        
        if df_metricas.empty:
            print("⚠️ No hay trades cerrados para analizar")
            return
        
        # 4. Crear carpeta de salida
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Si estamos en Core/Utils, ir dos niveles arriba para llegar a Registros
        if 'Core' in script_dir:
            root_dir = os.path.dirname(os.path.dirname(script_dir))
            carpeta_salida = os.path.join(root_dir, 'Registros', f"Analisis_{timestamp}")
        else:
            carpeta_salida = os.path.join(script_dir, f"Analisis_{timestamp}")
            
        os.makedirs(carpeta_salida, exist_ok=True)
        print(f"\n📁 Carpeta de salida: {carpeta_salida}")
        
        # 5. Generar dashboard
        print("📈 Generando dashboard de rendimiento...")
        ruta_dashboard = self.generar_dashboard(df_metricas, carpeta_salida)
        if ruta_dashboard:
            print(f"✅ Dashboard guardado: {ruta_dashboard}")
        
        # 6. Exportar a Excel
        print("📄 Generando archivo Excel...")
        ruta_excel = self.exportar_excel(df_metricas, carpeta_salida)
        print(f"✅ Excel guardado: {ruta_excel}")
        
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
    """Función principal para uso standalone"""
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
