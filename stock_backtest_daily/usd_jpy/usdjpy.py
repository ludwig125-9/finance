import pandas as pd
import yfinance as yf

# 1. ティッカーシンボルの指定（JPY=X がドル円）
ticker_symbol = "JPY=X"
ticker = yf.Ticker(ticker_symbol)

print(f"{ticker_symbol} のデータを取得中...")

# 2. 日足（1d）データの取得
# start="1999-01-01" で1999年以降の全データを取得
df = ticker.history(start="1999-01-01", interval="1d")

# 3. データの整形
# 古い順に並べ替え
df = df.sort_index(ascending=True)

# 4. CSVとして保存
filename = "usdjpy_daily_data.csv"
# encoding='utf-8-sig' をつけると日本のExcelでダブルクリックしても文字化けしない
df.to_csv(filename, encoding='utf-8-sig')

print(f"--- 保存完了: {filename} ---")
print(df.tail())  # 最新の数日分を表示して確認
