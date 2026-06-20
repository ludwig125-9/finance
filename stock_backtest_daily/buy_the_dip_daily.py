import pandas as pd
import numpy as np
import itertools

# =========================================================
# Fast Daily Backtest
# =========================================================
#
# 高速化ポイント
# -------------------------
# ・日足データ使用
# ・開始日は「月初のみ」
# ・暴落判定は「月末のみ」
# ・drawdown事前計算
# ・NumPy配列化
# ・dictアクセス削減
#
# =========================================================

# =========================================================
# 設定
# =========================================================

TOTAL_CAPITAL = 10_000_000

HOLD_YEARS = 10
TRADING_DAYS_PER_YEAR = 252

HOLD_DAYS = HOLD_YEARS * TRADING_DAYS_PER_YEAR

# ---------------------------------------------------------
# ファイル
# ---------------------------------------------------------

SP500_FILE = "sp500/sp500_daily_yen.csv"
NQ100_FILE = "nasdaq100/nq100_daily_yen.csv"
SOX_FILE = "sox/sox_daily_yen.csv"

# ---------------------------------------------------------
# 初期投資
# ---------------------------------------------------------

INITIAL_INVEST_RATIOS = [
    0.0,
    0.2,
    0.4,
    0.6,
]

# ---------------------------------------------------------
# 初期ポートフォリオ
# ---------------------------------------------------------

INITIAL_PORTFOLIO = {
    "SP500": 0.60,
    "NQ100": 0.30,
    "SOX": 0.10,
}

# ---------------------------------------------------------
# 暴落トリガー
# ---------------------------------------------------------

DRAW_DOWN_LEVELS = [10, 15, 20, 25, 30]

# ---------------------------------------------------------
# 暴落時投入額候補（万円）
# ---------------------------------------------------------

AMOUNT_CANDIDATES = [
    (100, 100, 100, 100, 100),
    (100, 100, 200, 200, 300),
    (200, 200, 200, 200, 200),
]

# ---------------------------------------------------------
# NQ100比率候補
# 残りはSOX
# ---------------------------------------------------------

RATIO_CANDIDATES = []

for combo in itertools.product([0.3, 0.5, 0.7], repeat=5):

    # 暴落が深くなるほどSOX寄り
    if (
        combo[0] >= combo[1]
        >= combo[2]
        >= combo[3]
        >= combo[4]
    ):
        RATIO_CANDIDATES.append(combo)

# =========================================================
# データ読み込み
# =========================================================

def load_daily_csv(path, asset_name):

    df = pd.read_csv(path)

    df["Date"] = pd.to_datetime(df["Date"])

    df = df.rename(columns={
        "Close_Yen": asset_name
    })

    return df[["Date", asset_name]]

# =========================================================
# 読み込み
# =========================================================

sp500 = load_daily_csv(SP500_FILE, "SP500")
nq100 = load_daily_csv(NQ100_FILE, "NQ100")
sox = load_daily_csv(SOX_FILE, "SOX")

# =========================================================
# マージ
# =========================================================

merged = sp500

merged = pd.merge(
    merged,
    nq100,
    on="Date",
    how="inner"
)

merged = pd.merge(
    merged,
    sox,
    on="Date",
    how="inner"
)

merged = merged.sort_values("Date").reset_index(drop=True)

# =========================================================
# 月末判定用フラグ
# =========================================================

merged["YearMonth"] = merged["Date"].dt.to_period("M")

month_end_indices = (
    merged
    .groupby("YearMonth")
    .tail(1)
    .index
    .tolist()
)

month_start_indices = (
    merged
    .groupby("YearMonth")
    .head(1)
    .index
    .tolist()
)

month_end_set = set(month_end_indices)

# =========================================================
# NumPy化
# =========================================================

dates = merged["Date"].values

sp500_prices = merged["SP500"].values
nq100_prices = merged["NQ100"].values
sox_prices = merged["SOX"].values

N = len(merged)

print()
print(f"営業日数: {N}")
print(f"期間: {dates[0]} ～ {dates[-1]}")

# =========================================================
# drawdown事前計算
# =========================================================

rolling_peak = np.maximum.accumulate(sp500_prices)

drawdowns = (
    (rolling_peak - sp500_prices)
    / rolling_peak
) * 100

# =========================================================
# 指標
# =========================================================

def calc_max_drawdown(values):

    values = np.array(values)

    peaks = np.maximum.accumulate(values)

    dds = (peaks - values) / peaks

    return np.max(dds) * 100

def calc_cagr(initial, final, days):

    years = days / TRADING_DAYS_PER_YEAR

    return (
        ((final / initial) ** (1 / years)) - 1
    ) * 100

# =========================================================
# シミュレーション
# =========================================================

def simulate_case(
    start_idx,
    initial_ratio,
    amounts,
    nq_ratios
):

    end_idx = start_idx + HOLD_DAYS

    if end_idx >= N:
        return None

    # -----------------------------------------------------
    # 初期投資
    # -----------------------------------------------------

    initial_invest = TOTAL_CAPITAL * initial_ratio

    sp500_units = (
        initial_invest
        * INITIAL_PORTFOLIO["SP500"]
        / sp500_prices[start_idx]
    )

    nq100_units = (
        initial_invest
        * INITIAL_PORTFOLIO["NQ100"]
        / nq100_prices[start_idx]
    )

    sox_units = (
        initial_invest
        * INITIAL_PORTFOLIO["SOX"]
        / sox_prices[start_idx]
    )

    cash = TOTAL_CAPITAL - initial_invest

    # -----------------------------------------------------
    # trigger
    # -----------------------------------------------------

    triggered = np.zeros(len(DRAW_DOWN_LEVELS), dtype=bool)

    path = []

    trigger_count = 0

    # -----------------------------------------------------
    # 日次ループ
    # -----------------------------------------------------

    for t in range(start_idx, end_idx + 1):

        # -------------------------------------------------
        # 月末だけ trigger 判定
        # -------------------------------------------------

        if t in month_end_set:

            dd = drawdowns[t]

            for i, level in enumerate(DRAW_DOWN_LEVELS):

                if triggered[i]:
                    continue

                if dd >= level:

                    invest_amount = amounts[i] * 10_000

                    if invest_amount > cash:
                        invest_amount = cash

                    nq_ratio = nq_ratios[i]

                    sox_ratio = 1 - nq_ratio

                    nq_amount = invest_amount * nq_ratio
                    sox_amount = invest_amount * sox_ratio

                    nq100_units += (
                        nq_amount / nq100_prices[t]
                    )

                    sox_units += (
                        sox_amount / sox_prices[t]
                    )

                    cash -= invest_amount

                    triggered[i] = True

                    trigger_count += 1

        # -------------------------------------------------
        # 総資産
        # -------------------------------------------------

        total = (
            cash
            + sp500_units * sp500_prices[t]
            + nq100_units * nq100_prices[t]
            + sox_units * sox_prices[t]
        )

        path.append(total)

    final_value = path[-1]

    return {
        "return_pct":
            (final_value / TOTAL_CAPITAL - 1) * 100,

        "cagr_pct":
            calc_cagr(
                TOTAL_CAPITAL,
                final_value,
                HOLD_DAYS
            ),

        "max_drawdown_pct":
            calc_max_drawdown(path),

        "unused_cash":
            cash,

        "trigger_count":
            trigger_count,
    }

# =========================================================
# 全探索
# =========================================================

rows = []

total_patterns = (
    len(INITIAL_INVEST_RATIOS)
    * len(AMOUNT_CANDIDATES)
    * len(RATIO_CANDIDATES)
)

print()
print(f"総パターン数: {total_patterns}")

pattern_no = 0

# 月初だけ開始
valid_start_indices = []

for idx in month_start_indices:

    if idx + HOLD_DAYS < N:
        valid_start_indices.append(idx)

print(f"開始ケース数: {len(valid_start_indices)}")

# =========================================================
# 総当たり
# =========================================================

for initial_ratio in INITIAL_INVEST_RATIOS:

    for amounts in AMOUNT_CANDIDATES:

        if sum(amounts) > 1000:
            continue

        for ratios in RATIO_CANDIDATES:

            pattern_no += 1

            results = []

            for start_idx in valid_start_indices:

                r = simulate_case(
                    start_idx,
                    initial_ratio,
                    amounts,
                    ratios
                )

                if r:
                    results.append(r)

            if len(results) == 0:
                continue

            df = pd.DataFrame(results)

            rows.append({

                "initial_ratio":
                    initial_ratio,

                "amounts":
                    str(amounts),

                "ratios":
                    str(ratios),

                "avg_return_pct":
                    df["return_pct"].mean(),

                "median_return_pct":
                    df["return_pct"].median(),

                "min_return_pct":
                    df["return_pct"].min(),

                "max_return_pct":
                    df["return_pct"].max(),

                "avg_cagr_pct":
                    df["cagr_pct"].mean(),

                "avg_max_drawdown_pct":
                    df["max_drawdown_pct"].mean(),

                "worst_drawdown_pct":
                    df["max_drawdown_pct"].max(),

                "avg_unused_cash":
                    df["unused_cash"].mean(),

                "avg_trigger_count":
                    df["trigger_count"].mean(),
            })

            if pattern_no % 10 == 0:

                print(
                    f"progress "
                    f"{pattern_no}/{total_patterns}"
                )

# =========================================================
# 結果
# =========================================================

summary = pd.DataFrame(rows)

summary = summary.sort_values(
    ["avg_return_pct", "min_return_pct"],
    ascending=[False, False]
)

# =========================================================
# 保存
# =========================================================

output_file = "daily_fast_backtest.csv"

summary.to_csv(
    output_file,
    index=False
)

# =========================================================
# 表示
# =========================================================

print()
print("==============================================")
print("Top 50 Best Strategies")
print("==============================================")

print(
    summary.head(50).to_string(index=False)
)

print()
print(f"Saved: {output_file}")
