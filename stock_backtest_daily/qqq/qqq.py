import yfinance as yf
import pandas as pd

# 1. QQQのティッカーを指定
ticker_symbol = "QQQ"
qqq = yf.Ticker(ticker_symbol)

print(f"{ticker_symbol} のデータを取得中...")

# 2. データの取得（1990年頃からデータがあります）
# ここでは日足(1d)で取得
df = qqq.history(start="1999-01-01", interval="1d")

# 3. データの整形（古い順に並べ替え）
df = df.sort_index(ascending=True)

# 4. 保存
filename = "qqq_daily_data.csv"
df.to_csv(filename, encoding='utf-8-sig')

print(f"--- 保存完了: {filename} ---")
print(df.tail()) # 直近の数値を確認
