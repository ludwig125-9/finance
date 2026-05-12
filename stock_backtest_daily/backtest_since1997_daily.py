import pandas as pd
import numpy as np
import os
from itertools import product

# ============================================================
# 設定
# ============================================================

TOTAL_CAPITAL = 10_000_000

# 「その他40%」を積立投入する
INVEST_CAPITAL = TOTAL_CAPITAL * 0.40

# 積立期間
DCA_YEARS_LIST = [1, 3, 5]

# 保有終了まで
HOLD_YEARS = 10
HOLD_DAYS_APPROX = HOLD_YEARS * 252

# 初期保有
BASE_ORUCAN_RATIO = 0.50
BASE_CASH_RATIO = 0.10

# ============================================================
# ファイル
# 日足データ
# Date,Close
# ============================================================

ASSET_FILES = {
    "ORUCAN": "msci/msci_daily_yen.csv",
    "QQQ": "nasdaq100/nq100_daily_yen.csv",
    "SOX": "sox/sox_daily_yen.csv",
}


# ============================================================
# 積立配分候補
# ============================================================

# 例:
# ORUCAN 0.5
# QQQ    0.3
# SOX    0.2

WEIGHT_CANDIDATES = [
    (1.0, 0.0, 0.0),
    (0.7, 0.3, 0.0),
    (0.5, 0.5, 0.0),
    (0.5, 0.3, 0.2),
    (0.4, 0.4, 0.2),
    (0.3, 0.5, 0.2),
    (0.3, 0.4, 0.3),
    (0.2, 0.5, 0.3),
    (0.2, 0.4, 0.4),
    (0.0, 0.7, 0.3),
    (0.0, 0.5, 0.5),
    (0.0, 0.3, 0.7),
]

# ============================================================
# データ読み込み (修正版)
# ============================================================

def load_asset(file_path):
    # CSV読み込み
    df = pd.read_csv(file_path)

    # 日付処理
    df["Date"] = pd.to_datetime(df["Date"].astype(str).str[:10])

    # Close_Yen列のクリーニングと数値化
    # 文字列として読み込まれた場合のカンマ除去と、数値への変換
    df["Close_Yen"] = (
        df["Close_Yen"]
        .astype(str)
        .str.replace(",", "")
        .replace("nan", np.nan) # 文字列のnanを変換
    )
    df["Close_Yen"] = pd.to_numeric(df["Close_Yen"], errors="coerce")

    # 欠損値（数値化できなかった行）を削除
    df = df.dropna(subset=["Close_Yen"])

    # ソートとインデックスリセット
    df = df.sort_values("Date").reset_index(drop=True)

    # 必要列だけ取り出し、名前を共通の "Close" に統一
    df = df[["Date", "Close_Yen"]].copy()
    df.columns = ["Date", "Close"]

    return df

merged = None

# 各ファイルを読み込んでマージ
for asset_name, file_path in ASSET_FILES.items():
    df = load_asset(file_path)
    df = df.rename(columns={"Close": asset_name})

    if merged is None:
        merged = df
    else:
        # すべてのアセットに共通する日付のみを残す (inner join)
        merged = pd.merge(merged, df, on="Date", how="inner")

merged = merged.sort_values("Date").reset_index(drop=True)

# デバッグ表示
print("--- Merged Columns ---")
print(merged.columns)
print(merged.head())

# 日付リスト
dates = merged["Date"].dt.strftime("%Y-%m-%d").tolist()
N = len(merged)

# アセット価格の辞書作成 (バグ修正箇所)
asset_prices = {}
for asset in ASSET_FILES.keys():
    # 正しくループ内の asset 名をキーにして格納する
    asset_prices[asset] = merged[asset].to_numpy().flatten()
    print(f"Loaded {asset}: size={len(asset_prices[asset])}")

print(f"\n共通営業日数: {N}")
print(f"期間: {dates[0]} ～ {dates[-1]}")

# ============================================================
# 指標関数
# ============================================================

def calc_max_drawdown(values):

    peak = values[0]
    max_dd = 0.0

    for v in values:

        if v > peak:
            peak = v

        dd = (peak - v) / peak

        if dd > max_dd:
            max_dd = dd

    return max_dd * 100


def calc_cagr(initial, final, days):

    years = days / 252

    return ((final / initial) ** (1 / years) - 1) * 100


# ============================================================
# 積立シミュレーション
# ============================================================

def simulate_dca_strategy(
    start_idx,
    dca_years,
    weights
):

    hold_end_idx = start_idx + HOLD_DAYS_APPROX

    if hold_end_idx >= N:
        return None

    # ----------------------------
    # 初期状態
    # ----------------------------

    units = {
        "ORUCAN": 0.0,
        "QQQ": 0.0,
        "SOX": 0.0,
    }

    # 初期50%オルカン保有
    initial_orucan_amount = TOTAL_CAPITAL * BASE_ORUCAN_RATIO

    # print('--- asset_prices["ORUCAN"][start_idx]')
    # print(asset_prices["ORUCAN"][start_idx])

    units["ORUCAN"] += (
        initial_orucan_amount
        / asset_prices["ORUCAN"][start_idx]
    )

    # 積立対象
    dca_capital = INVEST_CAPITAL

    # 積立営業日数
    dca_days = int(dca_years * 252)

    if dca_days <= 0:
        return None

    daily_amount = dca_capital / dca_days

    path = []

    # ----------------------------
    # 日次シミュレーション
    # ----------------------------

    for t in range(start_idx, hold_end_idx + 1):

        elapsed = t - start_idx

        # 積立期間中
        if elapsed < dca_days:

            for asset_name, w in zip(
                ["ORUCAN", "QQQ", "SOX"],
                weights
            ):

                invest_amount = daily_amount * w

                if invest_amount > 0:

                    # units[asset_name] += (
                    #     invest_amount
                    #     / asset_prices[asset_name][t]
                    # )
                    units[asset_name] += float(
                        invest_amount
                        / asset_prices[asset_name][t]
                    )

        # 評価額
        total_value = 0.0

        for asset_name in units.keys():

            # total_value += (
            #     units[asset_name]
            #     * asset_prices[asset_name][t]
            # )
            total_value += float(
                units[asset_name]
                * asset_prices[asset_name][t]
            )

        # 現金10%
        total_value += TOTAL_CAPITAL * BASE_CASH_RATIO

        # path.append(total_value)
        path.append(float(total_value))

    path = np.array(path)

    final_value = path[-1]

    return {
        "dca_years": dca_years,
        "weights": weights,
        "final_value": final_value,
        "return_pct": (
            (final_value / TOTAL_CAPITAL - 1)
            * 100
        ),
        "cagr_pct": calc_cagr(
            TOTAL_CAPITAL,
            final_value,
            HOLD_DAYS_APPROX
        ),
        "max_drawdown_pct": calc_max_drawdown(path)
    }


# ============================================================
# 全ケース実行
# ============================================================

rows = []

case_no = 0

for dca_years in DCA_YEARS_LIST:

    for weights in WEIGHT_CANDIDATES:

        case_no += 1

        print(
            f"Running Case {case_no} "
            f"DCA={dca_years}y "
            f"Weights={weights}"
        )

        for start_idx in range(N - HOLD_DAYS_APPROX):

            r = simulate_dca_strategy(
                start_idx,
                dca_years,
                weights
            )

            if r:
                rows.append(r)

# ============================================================
# 集計
# ============================================================

results = pd.DataFrame(rows)

summary = (
    results
    .groupby(
        ["dca_years", "weights"]
    )
    .agg(
        avg_return_pct=("return_pct", "mean"),
        median_return_pct=("return_pct", "median"),
        min_return_pct=("return_pct", "min"),
        max_return_pct=("return_pct", "max"),
        avg_cagr_pct=("cagr_pct", "mean"),
        avg_max_drawdown_pct=("max_drawdown_pct", "mean"),
        worst_drawdown_pct=("max_drawdown_pct", "max"),
    )
    .reset_index()
)

summary = summary.sort_values(
    "avg_return_pct",
    ascending=False
)

# ============================================================
# 保存
# ============================================================

results.to_csv(
    "daily_dca_detail.csv",
    index=False
)

summary.to_csv(
    "daily_dca_summary.csv",
    index=False
)

# ============================================================
# 表示
# ============================================================

print("\n")
print("=" * 60)
print("Top 50 Best Strategies")
print("=" * 60)

print(
    summary.head(50).to_string(index=False)
)

print("\nSaved:")
print("daily_dca_detail.csv")
print("daily_dca_summary.csv")
