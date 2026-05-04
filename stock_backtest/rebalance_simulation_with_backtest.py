import pandas as pd
import numpy as np

# ==========================================
# 設定（自由変更）
# ==========================================

TOTAL_CAPITAL = 10_000_000
HOLD_YEARS = 10
HOLD_MONTHS = HOLD_YEARS * 12

DCA_YEARS_LIST = [3, 5, 7, 10]
HYBRID_UPFRONT = 0.25

# 毎年何月にリバランスするか（0=start month基準で12か月ごと）
REBALANCE_EVERY_MONTHS = 12

ASSET_FILES = {
    "ORUCAN": "orucan_multiply_dollar_yen_since199907.txt",
    "QQQ": "qqq_multiply_dollar_yen_since199907.txt",
    "SOX": "sox_multiply_dollar_yen_since199907.txt",
    "TOPIX": "topix_since199907.txt",
}

PORTFOLIO_WEIGHTS = {
    "ORUCAN": 0.3,
    "QQQ": 0.4,
    "SOX": 0.25,
    "TOPIX": 0.05,
}

# ==========================================
# データ読み込み
# ==========================================

def load_asset(file_path):
    df = pd.read_csv(file_path, sep=r"\s+|,|\t", engine="python")

    cols = list(df.columns)
    date_col = cols[0]
    price_col = cols[1]

    df = df.rename(columns={date_col: "Date", price_col: "Price"})

    try:
        df["Date"] = pd.to_datetime(df["Date"], format="%Y-%m")
    except:
        try:
            df["Date"] = pd.to_datetime(df["Date"], format="%m/%Y")
        except:
            df["Date"] = pd.to_datetime(df["Date"])

    df = df.sort_values("Date").reset_index(drop=True)
    return df[["Date", "Price"]]

merged = None

for asset_name, file_path in ASSET_FILES.items():
    df = load_asset(file_path)
    df = df.rename(columns={"Price": asset_name})

    if merged is None:
        merged = df
    else:
        merged = pd.merge(merged, df, on="Date", how="inner")

merged = merged.sort_values("Date").reset_index(drop=True)

dates = merged["Date"].dt.strftime("%Y-%m").tolist()
N = len(merged)

asset_prices = {}
for asset_name in ASSET_FILES.keys():
    asset_prices[asset_name] = merged[asset_name].values

print(f"\n共通で使える月数: {N}")
print(f"期間: {dates[0]} ～ {dates[-1]}")

# ==========================================
# 指標関数
# ==========================================

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


def calc_cagr(initial, final, months):
    years = months / 12
    return ((final / initial) ** (1 / years) - 1) * 100

# ==========================================
# 年1回リバランス付きポートフォリオ推移
# ==========================================

def rebalance_units(units, t):
    total_value = 0.0

    for asset in PORTFOLIO_WEIGHTS.keys():
        total_value += units[asset] * asset_prices[asset][t]

    new_units = {}

    for asset, w in PORTFOLIO_WEIGHTS.items():
        target_value = total_value * w
        new_units[asset] = target_value / asset_prices[asset][t]

    return new_units


def build_portfolio_path(start_idx, dca_months=0, upfront_ratio=1.0):
    end_idx = start_idx + HOLD_MONTHS
    if end_idx >= N:
        return None

    units = {asset: 0.0 for asset in PORTFOLIO_WEIGHTS.keys()}
    cash = TOTAL_CAPITAL
    path = []

    # 初回一括
    if upfront_ratio > 0:
        upfront_amount = TOTAL_CAPITAL * upfront_ratio

        for asset, w in PORTFOLIO_WEIGHTS.items():
            invest_amount = upfront_amount * w
            units[asset] += invest_amount / asset_prices[asset][start_idx]

        cash -= upfront_amount

    monthly_amount = 0.0
    if dca_months > 0:
        monthly_amount = cash / dca_months

    for t in range(start_idx, end_idx + 1):
        month_no = t - start_idx

        # 積立
        if month_no < dca_months:
            invest_amount = monthly_amount

            for asset, w in PORTFOLIO_WEIGHTS.items():
                part = invest_amount * w
                units[asset] += part / asset_prices[asset][t]

            cash -= invest_amount

        # 年1回リバランス（開始月は除く）
        if month_no > 0 and month_no % REBALANCE_EVERY_MONTHS == 0:
            units = rebalance_units(units, t)

        total_value = cash
        for asset in PORTFOLIO_WEIGHTS.keys():
            total_value += units[asset] * asset_prices[asset][t]

        path.append(total_value)

    return np.array(path)

# ==========================================
# 単一ケース
# ==========================================

def simulate_strategy(start_idx, strategy_name, dca_years=0, upfront_ratio=1.0):
    dca_months = dca_years * 12

    path = build_portfolio_path(start_idx, dca_months, upfront_ratio)
    if path is None:
        return None

    end_idx = start_idx + HOLD_MONTHS
    final_value = path[-1]

    return {
        "strategy": strategy_name,
        "start_date": dates[start_idx],
        "end_date": dates[end_idx],
        "final_value": final_value,
        "return_pct": (final_value / TOTAL_CAPITAL - 1) * 100,
        "cagr_pct": calc_cagr(TOTAL_CAPITAL, final_value, HOLD_MONTHS),
        "max_drawdown_pct": calc_max_drawdown(path)
    }

# ==========================================
# 全ケース実行
# ==========================================

rows = []

for start_idx in range(N - HOLD_MONTHS):

    r = simulate_strategy(start_idx, "LumpSum", 0, 1.0)
    if r:
        rows.append(r)

    for years in DCA_YEARS_LIST:
        r2 = simulate_strategy(start_idx, f"DCA_{years}y", years, 0.0)
        if r2:
            rows.append(r2)

        r3 = simulate_strategy(start_idx, f"Hybrid25pct_{years}y", years, HYBRID_UPFRONT)
        if r3:
            rows.append(r3)

results = pd.DataFrame(rows)

# ==========================================
# LumpSum比較
# ==========================================

lump_lookup = results[results["strategy"] == "LumpSum"][["start_date", "final_value"]]
lump_lookup = lump_lookup.rename(columns={"final_value": "lump_final"})

results = results.merge(lump_lookup, on="start_date", how="left")
results["beats_lump"] = results["final_value"] > results["lump_final"]

# ==========================================
# 集計
# ==========================================

summary = (
    results.groupby("strategy")
    .agg(
        avg_return_pct=("return_pct", "mean"),
        median_return_pct=("return_pct", "median"),
        min_return_pct=("return_pct", "min"),
        max_return_pct=("return_pct", "max"),
        avg_cagr_pct=("cagr_pct", "mean"),
        avg_max_drawdown_pct=("max_drawdown_pct", "mean"),
        worst_drawdown_pct=("max_drawdown_pct", "max"),
        win_rate_vs_lump=("beats_lump", "mean")
    )
    .reset_index()
)

summary["win_rate_vs_lump"] *= 100

# ==========================================
# 保存
# ==========================================

results.to_csv("portfolio_rebalance_backtest_detail.csv", index=False)
summary.to_csv("portfolio_rebalance_backtest_summary.csv", index=False)

print("\n======================================")
print("Portfolio Weights")
print(PORTFOLIO_WEIGHTS)
print("Annual Rebalance: ON")
print("======================================")

print("\n=== Historical Portfolio 10-Year Backtest (Annual Rebalance) Summary ===")
print(summary.sort_values("avg_return_pct", ascending=False).to_string(index=False))

print("\nSaved: portfolio_rebalance_backtest_detail.csv")
print("Saved: portfolio_rebalance_backtest_summary.csv")
