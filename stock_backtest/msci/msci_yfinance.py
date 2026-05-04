import pandas as pd
import yfinance as yf # pip install yfinance が必要

# SOX指数データを取得
sox = yf.Ticker("%5E990100-USD-STRD")
df = sox.history(start="1999-01-01", interval="1mo")

# CSVとして保存
df.to_csv("msci_data.csv")
print("保存完了: msci.csv")
