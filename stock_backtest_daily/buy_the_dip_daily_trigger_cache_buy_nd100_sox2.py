import pandas as pd
import numpy as np
from itertools import product

# =========================
# Files
# =========================
NQ100_FILE = "nasdaq100/nq100_daily_yen.csv"
SOX_FILE = "sox/sox_daily_yen.csv"
VIX_FILE = "vix/vix_daily_data.csv"

OUTPUT_FILE = "compare_vix_dca_buyhold_10y.csv"

# =========================
# Parameters
# =========================

INITIAL_CASH = 1000
INITIAL_RATIOS = [0.0, 0.2, 0.4]

WINDOW_YEARS = 10
START_INTERVAL = 21  # 約1か月ごとに開始

VIX_THRESHOLDS = [30, 35]

# VIX発動時の基準買付額
# buy_cash = BUY_AMOUNT_PER_TRIGGER * buy_ratio
BUY_AMOUNT_PER_TRIGGER = 200

BUY_RATIOS_LIST = [
    (0.3, 0.3, 0.3, 0.3, 0.3),
    (0.3, 0.3, 0.5, 0.5, 0.7),
    (0.5, 0.5, 0.3, 0.3, 0.3),
    (0.3, 0.5, 0.5, 0.7, 0.7),
    (0.7, 0.5, 0.3, 0.3, 0.3),
    (0.5, 0.5, 0.5, 0.5, 0.5),
    (0.3, 0.5, 0.7, 0.7, 0.7),
    (0.7, 0.5, 0.5, 0.3, 0.3),
    (0.7, 0.7, 0.5, 0.5, 0.3),
    (0.7, 0.7, 0.7, 0.7, 0.7),
]

BUY_TARGET_RATIOS = [
    (0.7, 0.3),  # NQ100 70%, SOX 30%
    (0.5, 0.5),
    (0.3, 0.7),
]

# 単純DCAは10年間で毎月均等投資
DCA_MONTHS = WINDOW_YEARS * 12

# =========================
# Load Data
# =========================

def load_price_csv(file_path, price_col="Close_Yen"):
    df = pd.read_csv(file_path)
    df["Date"] = pd.to_datetime(df["Date"].astype(str).str[:10])
    df[price_col] = (
        df[price_col]
        .astype(str)
        .str.replace(",", "")
        .astype(float)
    )
    df = df.sort_values("Date").reset_index(drop=True)
    return df[["Date", price_col]]

nq100 = (
    load_price_csv(NQ100_FILE, "Close_Yen")
    .rename(columns={"Close_Yen": "NQ100"})
)

sox = (
    load_price_csv(SOX_FILE, "Close_Yen")
    .rename(columns={"Close_Yen": "SOX"})
)

vix = pd.read_csv(VIX_FILE)
vix["Date"] = pd.to_datetime(vix["Date"].astype(str).str[:10])
vix["VIX"] = (
    vix["Close"]
    .astype(str)
    .str.replace(",", "")
    .astype(float)
)

df = (
    nq100
    .merge(sox, on="Date", how="inner")
    .merge(vix[["Date", "VIX"]], on="Date", how="inner")
    .sort_values("Date")
    .reset_index(drop=True)
)

dates = df["Date"].values
nq_price = df["NQ100"].values
sox_price = df["SOX"].values
vix_close = df["VIX"].values

print(f"営業日数: {len(df)}")
print(f"期間: {df['Date'].iloc[0].date()} ～ {df['Date'].iloc[-1].date()}")
print()

# =========================
# Utility
# =========================

def calc_metrics(portfolio_values, initial_cash):
    final_value = portfolio_values[-1]

    total_return_pct = (final_value / initial_cash - 1) * 100

    running_max = np.maximum.accumulate(portfolio_values)
    drawdowns = portfolio_values / running_max - 1
    max_drawdown_pct = abs(np.min(drawdowns)) * 100

    cagr_pct = (
        (final_value / initial_cash) ** (1 / WINDOW_YEARS)
        -1
    ) * 100

    return total_return_pct, cagr_pct, max_drawdown_pct


def get_10y_windows(df):
    windows = []

    start_indices = np.arange(0, len(df), START_INTERVAL)

    for start_idx in start_indices:
        start_date = df.loc[start_idx, "Date"]
        end_date = start_date + pd.DateOffset(years=WINDOW_YEARS)

        candidates = df.index[df["Date"] <= end_date]

        if len(candidates) == 0:
            continue

        end_idx = candidates[-1]

        # 10年後の日付がデータ末尾を超えている場合は除外
        if df.loc[end_idx, "Date"] < end_date - pd.Timedelta(days=7):
            continue

        if end_idx <= start_idx:
            continue

        windows.append((start_idx, end_idx))

    return windows


windows = get_10y_windows(df)

print(f"10年評価ケース数: {len(windows)}")
print(f"最初の10年窓: {df.loc[windows[0][0], 'Date'].date()} ～ {df.loc[windows[0][1], 'Date'].date()}")
print(f"最後の10年窓: {df.loc[windows[-1][0], 'Date'].date()} ～ {df.loc[windows[-1][1], 'Date'].date()}")
print()

# =========================
# Strategy: Buy & Hold
# =========================

def simulate_buy_hold(start_idx, end_idx, target_ratio):
    nq_ratio, sox_ratio = target_ratio

    cash = 0.0

    nq_cash = INITIAL_CASH * nq_ratio
    sox_cash = INITIAL_CASH * sox_ratio

    nq_shares = nq_cash / nq_price[start_idx]
    sox_shares = sox_cash / sox_price[start_idx]

    portfolio_values = (
        nq_shares * nq_price[start_idx:end_idx + 1]
        + sox_shares * sox_price[start_idx:end_idx + 1]
        + cash
    )

    return portfolio_values, cash, 1


# =========================
# Strategy: Simple DCA
# =========================

def simulate_dca(start_idx, end_idx, target_ratio):
    nq_ratio, sox_ratio = target_ratio

    cash = INITIAL_CASH
    nq_shares = 0.0
    sox_shares = 0.0

    monthly_buy_cash = INITIAL_CASH / DCA_MONTHS

    portfolio_values = []
    buy_count = 0

    # 約21営業日ごとに買付
    dca_buy_indices = set(
        range(start_idx, end_idx + 1, START_INTERVAL)
    )

    for idx in range(start_idx, end_idx + 1):

        if idx in dca_buy_indices and buy_count < DCA_MONTHS:
            buy_cash = min(monthly_buy_cash, cash)

            nq_buy_cash = buy_cash * nq_ratio
            sox_buy_cash = buy_cash * sox_ratio

            nq_shares += nq_buy_cash / nq_price[idx]
            sox_shares += sox_buy_cash / sox_price[idx]

            cash -= buy_cash
            buy_count += 1

        value = (
            nq_shares * nq_price[idx]
            + sox_shares * sox_price[idx]
            + cash
        )

        portfolio_values.append(value)

    return np.array(portfolio_values), cash, buy_count


# =========================
# Strategy: VIX Trigger
# =========================

def simulate_vix_trigger(
    start_idx,
    end_idx,
    vix_threshold,
    buy_ratios,
    target_ratio,
    initial_ratio,
):
    nq_ratio, sox_ratio = target_ratio

    # --------------------------
    # 初回一括投資
    # --------------------------
    initial_buy_cash = INITIAL_CASH * initial_ratio

    cash = INITIAL_CASH - initial_buy_cash

    nq_buy_cash = initial_buy_cash * nq_ratio
    sox_buy_cash = initial_buy_cash * sox_ratio

    nq_shares = nq_buy_cash / nq_price[start_idx]
    sox_shares = sox_buy_cash / sox_price[start_idx]
    # initial_buy = INITIAL_CASH * initial_ratio

    # cash = INITIAL_CASH - initial_buy
    # nq_shares = (initial_buy * nq_ratio) / nq_price[start_idx]
    # sox_shares = (initial_buy * sox_ratio) / sox_price[start_idx]
    # cash = INITIAL_CASH
    # nq_shares = 0.0
    # sox_shares = 0.0

    portfolio_values = []
    trigger_count = 0

    for idx in range(start_idx, end_idx + 1):

        if vix_close[idx] >= vix_threshold:
            tranche = min(trigger_count, len(buy_ratios) - 1)
            buy_ratio = buy_ratios[tranche]

            buy_cash = BUY_AMOUNT_PER_TRIGGER * buy_ratio
            buy_cash = min(buy_cash, cash)

            if buy_cash > 0:
                nq_buy_cash = buy_cash * nq_ratio
                sox_buy_cash = buy_cash * sox_ratio

                nq_shares += nq_buy_cash / nq_price[idx]
                sox_shares += sox_buy_cash / sox_price[idx]

                cash -= buy_cash
                trigger_count += 1

        value = (
            nq_shares * nq_price[idx]
            + sox_shares * sox_price[idx]
            + cash
        )

        portfolio_values.append(value)

    return np.array(portfolio_values), cash, trigger_count


# =========================
# Run Backtest
# =========================

results = []

# -------------------------
# Buy & Hold
# -------------------------

for target_ratio in BUY_TARGET_RATIOS:
    returns = []
    cagrs = []
    drawdowns = []
    unused_cash = []
    buy_counts = []

    for start_idx, end_idx in windows:
        pv, cash, buy_count = simulate_buy_hold(
            start_idx,
            end_idx,
            target_ratio,
        )

        total_return, cagr, max_dd = calc_metrics(pv, INITIAL_CASH)

        returns.append(total_return)
        cagrs.append(cagr)
        drawdowns.append(max_dd)
        unused_cash.append(cash)
        buy_counts.append(buy_count)

    results.append({
        "strategy": "BuyHold",
        "vix_threshold": None,
        "buy_ratios": None,
        "buy_target_ratio": target_ratio,

        "avg_return_pct": np.mean(returns),
        "median_return_pct": np.median(returns),
        "min_return_pct": np.min(returns),
        "max_return_pct": np.max(returns),

        "avg_cagr_pct": np.mean(cagrs),
        "median_cagr_pct": np.median(cagrs),
        "min_cagr_pct": np.min(cagrs),
        "max_cagr_pct": np.max(cagrs),

        "avg_max_drawdown_pct": np.mean(drawdowns),
        "worst_drawdown_pct": np.max(drawdowns),

        "avg_unused_cash": np.mean(unused_cash),
        "avg_buy_count": np.mean(buy_counts),
        "window_count": len(windows),
    })


# -------------------------
# Simple DCA
# -------------------------

for target_ratio in BUY_TARGET_RATIOS:
    returns = []
    cagrs = []
    drawdowns = []
    unused_cash = []
    buy_counts = []

    for start_idx, end_idx in windows:
        pv, cash, buy_count = simulate_dca(
            start_idx,
            end_idx,
            target_ratio,
        )

        total_return, cagr, max_dd = calc_metrics(pv, INITIAL_CASH)

        returns.append(total_return)
        cagrs.append(cagr)
        drawdowns.append(max_dd)
        unused_cash.append(cash)
        buy_counts.append(buy_count)

    results.append({
        "strategy": "DCA",
        "vix_threshold": None,
        "buy_ratios": None,
        "buy_target_ratio": target_ratio,

        "avg_return_pct": np.mean(returns),
        "median_return_pct": np.median(returns),
        "min_return_pct": np.min(returns),
        "max_return_pct": np.max(returns),

        "avg_cagr_pct": np.mean(cagrs),
        "median_cagr_pct": np.median(cagrs),
        "min_cagr_pct": np.min(cagrs),
        "max_cagr_pct": np.max(cagrs),

        "avg_max_drawdown_pct": np.mean(drawdowns),
        "worst_drawdown_pct": np.max(drawdowns),

        "avg_unused_cash": np.mean(unused_cash),
        "avg_buy_count": np.mean(buy_counts),
        "window_count": len(windows),
    })


# -------------------------
# VIX Trigger
# -------------------------

for vix_threshold, initial_ratio, buy_ratios, target_ratio in product(
    VIX_THRESHOLDS,
    INITIAL_RATIOS,
    BUY_RATIOS_LIST,
    BUY_TARGET_RATIOS,
):
    returns = []
    cagrs = []
    drawdowns = []
    unused_cash = []
    buy_counts = []

    for start_idx, end_idx in windows:
        pv, cash, buy_count = simulate_vix_trigger(
            start_idx,
            end_idx,
            vix_threshold,
            buy_ratios,
            target_ratio,
            initial_ratio,
        )

        total_return, cagr, max_dd = calc_metrics(pv, INITIAL_CASH)

        returns.append(total_return)
        cagrs.append(cagr)
        drawdowns.append(max_dd)
        unused_cash.append(cash)
        buy_counts.append(buy_count)

    results.append({
        "strategy": "VIX",
        "vix_threshold": vix_threshold,
        "buy_ratios": buy_ratios,
        "buy_target_ratio": target_ratio,
        "initial_ratio": initial_ratio,

        "avg_return_pct": np.mean(returns),
        "median_return_pct": np.median(returns),
        "min_return_pct": np.min(returns),
        "max_return_pct": np.max(returns),

        "avg_cagr_pct": np.mean(cagrs),
        "median_cagr_pct": np.median(cagrs),
        "min_cagr_pct": np.min(cagrs),
        "max_cagr_pct": np.max(cagrs),

        "avg_max_drawdown_pct": np.mean(drawdowns),
        "worst_drawdown_pct": np.max(drawdowns),

        "avg_unused_cash": np.mean(unused_cash),
        "avg_buy_count": np.mean(buy_counts),
        "window_count": len(windows),
    })


# =========================
# Output
# =========================

result_df = pd.DataFrame(results)

result_df = result_df.sort_values(
    ["avg_cagr_pct", "median_cagr_pct"],
    ascending=False,
)

print()
print("==============================================")
print("Top Strategies by 10Y Avg CAGR")
print("==============================================")
print(result_df.head(50).to_string(index=False))

print()
print("==============================================")
print("Best by Strategy Type")
print("==============================================")

best_by_strategy = (
    result_df
    .sort_values("avg_cagr_pct", ascending=False)
    .groupby("strategy")
    .head(5)
)

print(best_by_strategy.to_string(index=False))

print()
print("==============================================")
print("VIX30 vs VIX35 Best")
print("==============================================")

vix_only = result_df[result_df["strategy"] == "VIX"]

best_vix = (
    vix_only
    .sort_values("avg_cagr_pct", ascending=False)
    .groupby("vix_threshold")
    .head(10)
)

print(best_vix.to_string(index=False))

result_df.to_csv(OUTPUT_FILE, index=False)

print()
print(f"Saved: {OUTPUT_FILE}")
