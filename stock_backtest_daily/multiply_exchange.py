import pandas as pd
from pathlib import Path

# ==========================================
# 設定
# ==========================================

BASE_DIR = Path.home() / "git/ludwig125-9/finance/stock_backtest_daily"

TARGETS = [
    {
        "name": "nasdaq100",
        "input": BASE_DIR / "nasdaq100/nq100_daily_data.csv",
        "output": BASE_DIR / "nasdaq100/nq100_daily_yen.csv",
    },
    {
        "name": "sox",
        "input": BASE_DIR / "sox/sox_daily_data.csv",
        "output": BASE_DIR / "sox/sox_daily_yen.csv",
    },
    {
        "name": "sp500",
        "input": BASE_DIR / "sp500/sp500_daily_data.csv",
        "output": BASE_DIR / "sp500/sp500_daily_yen.csv",
    },
    {
        "name": "msci",
        "input": BASE_DIR / "msci/msci_daily_data.csv",
        "output": BASE_DIR / "msci/msci_daily_yen.csv",
    },
]

USDJPY_FILE = BASE_DIR / "usd_jpy/usdjpy_daily_data.csv"

# ==========================================
# 為替データ読み込み
# ==========================================

fx = pd.read_csv(USDJPY_FILE)

# # timezone除去
# fx["Date"] = (
#     pd.to_datetime(fx["Date"], utc=True)
#     .dt.tz_convert(None)
#     .dt.normalize()
# )
# 文字列として先頭10文字 (2026-04-30 など) だけを抜き出して日付型にする
# これによりサマータイムによる「前日への逆戻り」を物理的に防ぐ
fx["Date"] = pd.to_datetime(fx["Date"].astype(str).str[:10])

fx = fx.sort_values("Date").reset_index(drop=True)

fx = fx[["Date", "Close"]].rename(
    columns={"Close": "USDJPY_Close"}
)

print(f"FX rows: {len(fx)}")

# ==========================================
# 各指数を円換算
# ==========================================

for target in TARGETS:

    print("\n===================================")
    print(target["name"])
    print("===================================")

    # 読み込み
    df = pd.read_csv(target["input"])

    # timezone除去
    # df["Date"] = (
    #     pd.to_datetime(df["Date"], utc=True)
    #     .dt.tz_convert(None)
    #     .dt.normalize()
    # )
    df["Date"] = pd.to_datetime(df["Date"].astype(str).str[:10])

    df = df.sort_values("Date").reset_index(drop=True)

    print(f"Stock rows: {len(df)}")

    # ==========================================
    # 直近営業日のドル円を採用
    # merge_asof:
    #   左(df)の日付以下で最も近いfxを使う
    # ==========================================

    merged = pd.merge_asof(
        df,
        fx,
        on="Date",
        direction="backward"
    )

    print(f"Merged rows: {len(merged)}")

    # 欠損確認
    missing_fx = merged["USDJPY_Close"].isna().sum()

    print(f"Missing FX rows: {missing_fx}")

    # ==========================================
    # 円換算
    # ==========================================

    merged["Close_Yen"] = (
        merged["Close"] * merged["USDJPY_Close"]
    )

    # 出力
    out_df = merged[[
        "Date",
        "Close",
        "USDJPY_Close",
        "Close_Yen"
    ]]

    # 保存
    target["output"].parent.mkdir(
        parents=True,
        exist_ok=True
    )

    out_df.to_csv(target["output"], index=False)

    print(f"Saved: {target['output']}")

print("\nDone.")

# 結果
# (.venv) [~/git/ludwig125-9/finance/stock_backtest_daily] $python3 multiply_exchange.py
# FX rows: 7102

# ===================================
# nasdaq100
# ===================================
# Stock rows: 6879
# Merged rows: 6879
# Missing FX rows: 0
# Saved: ludwig125-9/finance/stock_backtest_daily/nasdaq100/nq100_daily_yen.csv

# ===================================
# sox
# ===================================
# Stock rows: 6878
# Merged rows: 6878
# Missing FX rows: 0
# Saved: ludwig125-9/finance/stock_backtest_daily/sox/sox_daily_yen.csv

# ===================================
# sp500
# ===================================
# Stock rows: 6879
# Merged rows: 6879
# Missing FX rows: 0
# Saved: ludwig125-9/finance/stock_backtest_daily/sp500/sp500_daily_yen.csv

# Done.
