import os
import time
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta

# --- CONFIGURACIÓN VISUAL (MODO CLEAN & PASTEL) ---
sns.set_theme(style="whitegrid") # Fondo blanco con rejilla suave
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Verdana']
plt.rcParams['text.color'] = '#333333' # Texto gris oscuro para contraste
plt.rcParams['axes.labelcolor'] = '#333333'
plt.rcParams['xtick.color'] = '#333333'
plt.rcParams['ytick.color'] = '#333333'

class GestorAuditoria:
    def __init__(self, bot_controller):
        self.bot = bot_controller
        self.root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.ruta_temp_img = os.path.join(self.root_dir, "temp_audit_chart.png")
        self.ruta_temp_csv = os.path.join(self.root_dir, "temp_resumen_auditoria.csv")

    def obtener_trades_binance(self, horas=24):
        """Descarga trades crudos desde Binance."""
        pares_activos = list(self.bot.config_pares.keys())
        inicio_ms = int((datetime.now() - timedelta(hours=horas)).timestamp() * 1000)
        todos_trades = []

        print(f"📡 Auditoría: Descargando trades ({horas}h)...")

        for simbolo in pares_activos:
            try:
                trades = self.bot.gestor_ejecucion.exchange.fetch_my_trades(simbolo, since=inicio_ms)
                for t in trades:
                    info = t.get('info', {})
                    todos_trades.append({
                        'Fecha': datetime.fromtimestamp(t['timestamp'] / 1000),
                        'Par': simbolo,
                        'Lado': t.get('side', '').upper(),
                        'Precio': float(t.get('price', 0)),
                        'Cantidad': float(t.get('amount', 0)),
                        'PnL': float(info.get('realizedPnl', 0)),
                        'Comision': float(info.get('commission', 0))
                    })
                time.sleep(0.1) 
            except Exception as e:
                print(f"⚠️ Error en {simbolo}: {e}")

        return pd.DataFrame(todos_trades)

    def _calcular_metricas(self, df):
        """Calcula KPIs financieros avanzados por par."""
        reporte_data = []
        if df.empty: return pd.DataFrame()

        for par, grupo in df.groupby('Par'):
            trades_cerrados = grupo[grupo['PnL'] != 0]
            
            ops_cerradas = len(trades_cerrados)
            pnl_bruto = grupo['PnL'].sum()
            comisiones = grupo['Comision'].sum()
            pnl_neto = pnl_bruto - comisiones
            
            wins = trades_cerrados[trades_cerrados['PnL'] > 0]
            losses = trades_cerrados[trades_cerrados['PnL'] <= 0]
            
            winrate = (len(wins) / ops_cerradas * 100) if ops_cerradas > 0 else 0
            
            gross_profit = wins['PnL'].sum()
            gross_loss = abs(losses['PnL'].sum())
            profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else 99.99
            if gross_loss == 0 and gross_profit == 0: profit_factor = 0

            # Drawdown
            grupo_sorted = grupo.sort_values('Fecha')
            grupo_sorted['Acumulado'] = grupo_sorted['PnL'].cumsum()
            grupo_sorted['Max_Acumulado'] = grupo_sorted['Acumulado'].cummax()
            grupo_sorted['DD'] = grupo_sorted['Acumulado'] - grupo_sorted['Max_Acumulado']
            max_drawdown = grupo_sorted['DD'].min()
            if pd.isna(max_drawdown): max_drawdown = 0.0

            veredicto = "❓"
            if pnl_neto > 10: veredicto = "✅ EXCELENTE"
            elif pnl_neto > 0: veredicto = "🆗 APROBADO"
            elif pnl_neto > -5: veredicto = "⚠️ REVISAR"
            else: veredicto = "⛔ APAGAR"

            reporte_data.append({
                'Par': par,
                'Ops': ops_cerradas,
                'WinRate': round(winrate, 1),
                'PF': profit_factor,
                'PnL Neto': round(pnl_neto, 2),
                'DD': round(max_drawdown, 2),
                'Veredicto': veredicto
            })
            
        return pd.DataFrame(reporte_data)

    def generar_csv_resumen(self, horas=24):
        """Genera CSV físico para descargar."""
        df = self.obtener_trades_binance(horas)
        if df.empty: return None, "📉 No hay data."
        
        df_metricas = self._calcular_metricas(df)
        if df_metricas.empty: return None, "📉 Sin operaciones cerradas."
        df_metricas = df_metricas.sort_values('PnL Neto', ascending=True)
        df_metricas.to_csv(self.ruta_temp_csv, index=False, encoding='utf-8-sig')
        return self.ruta_temp_csv, "✅ Reporte generado."

    def generar_grafica_top5(self, horas=24):
        """Genera Dashboard 4 Cuadrantes (WinRate, PF, DD, PnL) con estilo Pastel/Blanco."""
        df = self.obtener_trades_binance(horas)
        if df.empty: return None, f"📉 Sin trades ({horas}h)."

        df_metricas = self._calcular_metricas(df)
        if df_metricas.empty: return None, "⚠️ Sin operaciones cerradas para graficar."

        # Top 5 por PnL Absoluto para mostrar lo más relevante
        df_top = df_metricas.sort_values('PnL Neto', ascending=False).head(5)

        # Configurar Figura (2x2 Grid)
        fig, axs = plt.subplots(2, 2, figsize=(14, 10))
        fig.patch.set_facecolor('white') # Fondo Blanco Puro
        axs = axs.flatten() # Aplanamos para acceder fácil: axs[0], axs[1]...

        # Definir Paleta Pastel (Seaborn Pastel: 0=Azul, 1=Naranja, 2=Verde, 3=Rojo, 4=Morado)
        pastel = sns.color_palette("pastel")
        
        # --- CUADRANTE 1: WIN RATE (Arriba Izq) ---
        ax1 = axs[0]
        sns.barplot(x='Par', y='WinRate', data=df_top, ax=ax1, color=pastel[0], edgecolor='gray') # Azul Pastel
        ax1.set_title("1. Win Rate (%)", fontsize=12, fontweight='bold', color='#333333')
        ax1.set_ylabel("%")
        ax1.set_xlabel("")
        ax1.tick_params(axis='x', rotation=15)
        for container in ax1.containers:
            ax1.bar_label(container, fmt='%.1f%%', padding=3, color='#333333', fontweight='bold')

        # --- CUADRANTE 2: PROFIT FACTOR (Arriba Der) ---
        ax2 = axs[1]
        sns.barplot(x='Par', y='PF', data=df_top, ax=ax2, color=pastel[4], edgecolor='gray') # Morado Pastel
        ax2.set_title("2. Profit Factor", fontsize=12, fontweight='bold', color='#333333')
        ax2.set_ylabel("Ratio")
        ax2.set_xlabel("")
        ax2.tick_params(axis='x', rotation=15)
        ax2.axhline(1, color='gray', linestyle='--', linewidth=1, label='BreakEven')
        for container in ax2.containers:
            ax2.bar_label(container, fmt='%.2f', padding=3, color='#333333', fontweight='bold')

        # --- CUADRANTE 3: MAX DRAWDOWN (Abajo Izq) ---
        ax3 = axs[2]
        # Usamos Naranja Pastel para Drawdown
        sns.barplot(x='Par', y='DD', data=df_top, ax=ax3, color=pastel[1], edgecolor='gray') 
        ax3.set_title("3. Max Drawdown ($)", fontsize=12, fontweight='bold', color='#333333')
        ax3.set_ylabel("USDT")
        ax3.set_xlabel("")
        ax3.tick_params(axis='x', rotation=15)
        for container in ax3.containers:
            ax3.bar_label(container, fmt='$%.2f', padding=3, color='#333333', fontweight='bold')

        # --- CUADRANTE 4: PNL NETO (Abajo Der) ---
        ax4 = axs[3]
        # Colores condicionales: Verde Pastel (Ganancia) / Rojo Pastel (Pérdida)
        colors_pnl = [pastel[2] if y >= 0 else pastel[3] for y in df_top['PnL Neto']]
        
        # Usamos barplot directo de matplotlib para control total de colores individuales
        bars = ax4.bar(df_top['Par'], df_top['PnL Neto'], color=colors_pnl, edgecolor='gray')
        ax4.set_title("4. PnL Neto ($)", fontsize=12, fontweight='bold', color='#333333')
        ax4.set_ylabel("USDT")
        ax4.axhline(0, color='black', linewidth=0.8)
        ax4.set_xticks(range(len(df_top['Par'])))
        ax4.set_xticklabels(df_top['Par'], rotation=15)
        
        # Etiquetas PnL
        for bar in bars:
            height = bar.get_height()
            offset = 3 if height >= 0 else -15 # Ajuste para que no tape la barra
            ax4.text(
                bar.get_x() + bar.get_width()/2., 
                height + (height * 0.02), # Pequeño offset porcentual
                f"${height:.2f}",
                ha='center', va='bottom' if height >= 0 else 'top', 
                color='#333333', fontweight='bold'
            )

        # Ajuste Final y Guardado
        plt.tight_layout()
        plt.savefig(self.ruta_temp_img, dpi=100, bbox_inches='tight', facecolor='white')
        plt.close()

        # Resumen texto corto
        resumen_texto = f"📊 **Dashboard Ejecutivo ({horas}h)**\nTotal Neto: **${df_metricas['PnL Neto'].sum():.2f}**"
        return self.ruta_temp_img, resumen_texto