import pandas as pd
import numpy as np
import itertools

# ==========================================
# 設定
# ==========================================

TOTAL_CASH = 10_000_000
HOLD_YEARS = 10
HOLD_MONTHS = HOLD_YEARS * 12

MSCI_FILE = "orucan_multiply_dollar_yen_since199907.txt"
QQQ_FILE = "qqq_multiply_dollar_yen_since199907.txt"
SOX_FILE = "sox_multiply_dollar_yen_since199907.txt"

TRIGGERS = [0.10, 0.15, 0.20, 0.25, 0.30]

AMOUNT_CANDIDATES = [0, 100, 200, 300, 400]
NASDAQ_RATIO_CANDIDATES = [0.3, 0.5, 0.7]

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

msci = load_asset(MSCI_FILE)
qqq = load_asset(QQQ_FILE)
sox = load_asset(SOX_FILE)

merged = msci.rename(columns={"Price": "MSCI"})
merged = pd.merge(merged, qqq.rename(columns={"Price": "QQQ"}), on="Date", how="inner")
merged = pd.merge(merged, sox.rename(columns={"Price": "SOX"}), on="Date", how="inner")
merged = merged.sort_values("Date").reset_index(drop=True)

dates = merged["Date"].dt.strftime("%Y-%m").tolist()
N = len(merged)

msci_prices = merged["MSCI"].values
qqq_prices = merged["QQQ"].values
sox_prices = merged["SOX"].values

print(f"\n共通で使える月数: {N}")
print(f"期間: {dates[0]} ～ {dates[-1]}")

# ==========================================
# 指標
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
# 単一ケース
# ==========================================

def simulate_one_case(start_idx, invest_amounts, nasdaq_ratios):
    end_idx = start_idx + HOLD_MONTHS
    if end_idx >= N:
        return None

    cash = TOTAL_CASH
    qqq_units = 0.0
    sox_units = 0.0

    triggered = [False] * len(TRIGGERS)
    path = []

    rolling_peak = msci_prices[start_idx]

    for t in range(start_idx, end_idx + 1):

        if msci_prices[t] > rolling_peak:
            rolling_peak = msci_prices[t]

        drawdown = (rolling_peak - msci_prices[t]) / rolling_peak

        for i, trig in enumerate(TRIGGERS):
            if (not triggered[i]) and (drawdown >= trig):
                invest = invest_amounts[i] * 10000

                if invest > cash:
                    invest = cash

                nasdaq_part = invest * nasdaq_ratios[i]
                sox_part = invest - nasdaq_part

                qqq_units += nasdaq_part / qqq_prices[t]
                sox_units += sox_part / sox_prices[t]

                cash -= invest
                triggered[i] = True

        total_value = cash + qqq_units * qqq_prices[t] + sox_units * sox_prices[t]
        path.append(total_value)

    final_value = path[-1]

    return {
        "final_value": final_value,
        "return_pct": (final_value / TOTAL_CASH - 1) * 100,
        "cagr_pct": calc_cagr(TOTAL_CASH, final_value, HOLD_MONTHS),
        "max_drawdown_pct": calc_max_drawdown(path),
        "unused_cash": cash,
        "trigger_count": sum(triggered)
    }

# ==========================================
# 全期間バックテスト
# ==========================================

def backtest_strategy(invest_amounts, nasdaq_ratios):
    rows = []

    for start_idx in range(N - HOLD_MONTHS):
        r = simulate_one_case(start_idx, invest_amounts, nasdaq_ratios)
        if r:
            rows.append(r)

    df = pd.DataFrame(rows)

    return {
        "amounts": invest_amounts,
        "ratios": nasdaq_ratios,
        "avg_return_pct": df["return_pct"].mean(),
        "median_return_pct": df["return_pct"].median(),
        "min_return_pct": df["return_pct"].min(),
        "max_return_pct": df["return_pct"].max(),
        "avg_cagr_pct": df["cagr_pct"].mean(),
        "avg_max_drawdown_pct": df["max_drawdown_pct"].mean(),
        "worst_drawdown_pct": df["max_drawdown_pct"].max(),
        "avg_unused_cash": df["unused_cash"].mean(),
        "avg_trigger_count": df["trigger_count"].mean()
    }

# ==========================================
# 合理的候補生成
# ==========================================

candidate_amount_patterns = []

for combo in itertools.product(AMOUNT_CANDIDATES, repeat=5):
    if (
        combo[0] <= combo[1] <= combo[2] <= combo[3] <= combo[4]
        and sum(combo) <= 1000
    ):
        candidate_amount_patterns.append(combo)

candidate_ratio_patterns = []

for combo in itertools.product(NASDAQ_RATIO_CANDIDATES, repeat=5):
    if combo[0] >= combo[1] >= combo[2] >= combo[3] >= combo[4]:
        candidate_ratio_patterns.append(combo)

print(f"\n投入額候補パターン数: {len(candidate_amount_patterns)}")
print(f"NASDAQ比率候補パターン数: {len(candidate_ratio_patterns)}")
print(f"総戦略数: {len(candidate_amount_patterns) * len(candidate_ratio_patterns)}")

# ==========================================
# 総当たり探索
# ==========================================

all_results = []
count = 0
total_patterns = len(candidate_amount_patterns) * len(candidate_ratio_patterns)

for invest_amounts in candidate_amount_patterns:
    for nasdaq_ratios in candidate_ratio_patterns:
        count += 1

        result = backtest_strategy(invest_amounts, nasdaq_ratios)
        all_results.append(result)

        if count % 20 == 0:
            print(f"checked {count}/{total_patterns}")

summary = pd.DataFrame(all_results)

summary = summary.sort_values(
    ["avg_return_pct", "min_return_pct"],
    ascending=[False, False]
).reset_index(drop=True)

summary.to_csv("crash_buy_strategy_ranking_fast.csv", index=False)

print("\n==============================================")
print("Top 30 Best Crash Buy Strategies")
print("==============================================")
print(summary.head(30).to_string(index=False))

print("\nSaved: crash_buy_strategy_ranking_fast.csv")
