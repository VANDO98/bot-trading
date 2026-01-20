import ccxt
import pandas as pd
from datetime import datetime, timedelta
import os

# Configuración
simbolo = "BTC/USDT"
timeframe = "15m"
dias = 730 # 2 años

print(f"Bajando {simbolo} en {timeframe}...")
exchange = ccxt.binance({'options': {'defaultType': 'future'}})
desde = int((datetime.now() - timedelta(days=dias)).timestamp() * 1000)
velas = []

while True:
    new_velas = exchange.fetch_ohlcv(simbolo, timeframe, since=desde, limit=1000)
    if not new_velas: break
    velas += new_velas
    desde = new_velas[-1][0] + 1
    if len(new_velas) < 1000: break
    print(f"Bolas: {len(velas)}", end='\r')

df = pd.DataFrame(velas, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
df.to_csv(f"Data/Historico/BTCUSDT_{timeframe}.csv", index=False)
print("\n¡Listo!")