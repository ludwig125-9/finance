import pandas as pd
import yfinance as yf # pip install yfinance が必要

# SOX指数データを取得
sox = yf.Ticker("JPY%3DX")
df = sox.history(start="1999-01-01", interval="1mo")

# CSVとして保存
df.to_csv("usdypy_data.csv")
print("保存完了: usdjpy.csv")
