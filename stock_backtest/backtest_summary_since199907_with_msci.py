import pandas as pd
import numpy as np
import os

# =========================
# 設定
# =========================

FILE_PATHS = [
    "qqq_multiply_dollar_yen_since199907.txt",
    "spy_multiply_dollar_yen_since199907.txt",
    "sox_multiply_dollar_yen_since199907.txt",
    "orucan_multiply_dollar_yen_since199907.txt",
    "topix_since199907.txt",
]

TOTAL_CAPITAL = 10_000_000

DCA_YEARS_LIST = [3, 5, 7, 10]
HYBRID_UPFRONT = 0.25
HOLD_YEARS = 10
HOLD_MONTHS = HOLD_YEARS * 12

# 統合保存用
all_summary_rows = []

# =========================
# 指標関数
# =========================

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


# =========================
# メインバックテスト関数
# =========================

def run_backtest(file_path):

    global all_summary_rows

    print("\n" + "=" * 60)
    print(f"FILE: {os.path.basename(file_path)}")
    print("=" * 60)

    # -------------------------
    # データ読み込み
    # -------------------------
    df = pd.read_csv(file_path, sep=r"\s+")
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date").reset_index(drop=True)

    prices = df["Close"].values
    dates = df["Date"].dt.strftime("%Y-%m").tolist()

    N = len(df)

    # -------------------------
    # 月次資産推移作成
    # -------------------------
    def build_portfolio_path(start_idx, dca_months=0, upfront_ratio=1.0):
        end_idx = start_idx + HOLD_MONTHS
        if end_idx >= N:
            return None

        units = 0.0
        cash = TOTAL_CAPITAL
        path = []

        if upfront_ratio > 0:
            upfront_amount = TOTAL_CAPITAL * upfront_ratio
            units += upfront_amount / prices[start_idx]
            cash -= upfront_amount

        monthly_amount = 0.0
        if dca_months > 0:
            monthly_amount = cash / dca_months

        for t in range(start_idx, end_idx + 1):
            month_no = t - start_idx

            if month_no < dca_months:
                invest_amount = monthly_amount
                units += invest_amount / prices[t]
                cash -= invest_amount

            total_value = units * prices[t] + cash
            path.append(total_value)

        return np.array(path)

    # -------------------------
    # 戦略シミュレーション
    # -------------------------
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

    # -------------------------
    # 全ケース実行
    # -------------------------
    rows = []

    for start_idx in range(N - HOLD_MONTHS):

        r = simulate_strategy(start_idx, "LumpSum", dca_years=0, upfront_ratio=1.0)
        if r:
            rows.append(r)

        for years in DCA_YEARS_LIST:
            r2 = simulate_strategy(start_idx, f"DCA_{years}y", dca_years=years, upfront_ratio=0.0)
            if r2:
                rows.append(r2)

            r3 = simulate_strategy(start_idx, f"Hybrid25pct_{years}y", dca_years=years, upfront_ratio=HYBRID_UPFRONT)
            if r3:
                rows.append(r3)

    results = pd.DataFrame(rows)

    # -------------------------
    # LumpSum比較
    # -------------------------
    lump_lookup = results[results["strategy"] == "LumpSum"][["start_date", "final_value"]]
    lump_lookup = lump_lookup.rename(columns={"final_value": "lump_final"})
    results = results.merge(lump_lookup, on="start_date", how="left")
    results["beats_lump"] = results["final_value"] > results["lump_final"]

    # -------------------------
    # 集計
    # -------------------------
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

    # asset名追加して統合用へ
    asset_name = os.path.splitext(os.path.basename(file_path))[0]
    summary["asset"] = asset_name
    all_summary_rows.append(summary)

    # -------------------------
    # 保存
    # -------------------------
    base = asset_name

    detail_name = f"{base}_historical_detail.csv"
    summary_name = f"{base}_historical_summary.csv"

    results.to_csv(detail_name, index=False)
    summary.to_csv(summary_name, index=False)

    # -------------------------
    # 表示
    # -------------------------
    print("\n=== Historical 10-Year Fixed Horizon COMPLETE Summary ===")
    print(summary.sort_values("avg_return_pct", ascending=False).to_string(index=False))

    print(f"\nSaved: {detail_name}")
    print(f"Saved: {summary_name}")


# =========================
# 複数ファイル実行
# =========================

for fp in FILE_PATHS:
    run_backtest(fp)

# =========================
# 統合summary出力
# =========================

combined_summary = pd.concat(all_summary_rows, ignore_index=True)

combined_summary = combined_summary[
    [
        "asset",
        "strategy",
        "avg_return_pct",
        "median_return_pct",
        "min_return_pct",
        "max_return_pct",
        "avg_cagr_pct",
        "avg_max_drawdown_pct",
        "worst_drawdown_pct",
        "win_rate_vs_lump"
    ]
]

combined_summary.to_csv("ALL_ASSETS_COMBINED_SUMMARY.csv", index=False)

print("\n" + "=" * 70)
print("ALL ASSETS COMBINED SUMMARY")
print("=" * 70)
print(combined_summary.sort_values(["strategy", "avg_return_pct"], ascending=[True, False]).to_string(index=False))

print("\nSaved: ALL_ASSETS_COMBINED_SUMMARY.csv")
