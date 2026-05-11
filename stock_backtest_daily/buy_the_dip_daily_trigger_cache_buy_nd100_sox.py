import pandas as pd
import numpy as np
from itertools import product

# =========================
# Files
# =========================

SP500_FILE = "sp500/sp500_daily_yen.csv"
NQ100_FILE = "nasdaq100/nq100_daily_yen.csv"
SOX_FILE = "sox/sox_daily_yen.csv"
VIX_FILE = "vix/vix_daily_data.csv"

OUTPUT_FILE = "buy_the_dip_daily_trigger_cache.csv"

# =========================
# Parameters
# =========================

INITIAL_CASH = 1000

INITIAL_RATIOS = [0.0, 0.2, 0.4]

BUY_AMOUNTS_LIST = [
    (100, 100, 200, 200, 300),
    (200, 200, 200, 200, 200),
]

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

VIX_THRESHOLDS = [None, 30, 35]

# 下落率条件
DROP_LEVELS = [-0.1, -0.2, -0.3, -0.4, -0.5]

# =========================
# 買う対象の比率
# =========================

BUY_TARGET_RATIOS = [
    (0.3, 0.7),  # NQ100 30%, SOX 70%
    (0.5, 0.5),
    (0.7, 0.3),
]

# =========================
# Load Data
# =========================

sp = pd.read_csv(SP500_FILE)
nq = pd.read_csv(NQ100_FILE)
sox = pd.read_csv(SOX_FILE)
vix = pd.read_csv(VIX_FILE)

sp["Date"] = pd.to_datetime(sp["Date"])
nq["Date"] = pd.to_datetime(nq["Date"])
sox["Date"] = pd.to_datetime(sox["Date"])

# VIXは日付部分のみ
vix["Date"] = pd.to_datetime(vix["Date"].astype(str).str[:10])

# merge
df = (
    sp[["Date", "Close"]]
    .rename(columns={"Close": "SP500"})
    .merge(
        nq[["Date", "Close"]].rename(columns={"Close": "NQ100"}),
        on="Date",
    )
    .merge(
        sox[["Date", "Close"]].rename(columns={"Close": "SOX"}),
        on="Date",
    )
    .merge(
        vix[["Date", "Close"]].rename(columns={"Close": "VIX"}),
        on="Date",
    )
)

df = df.sort_values("Date").reset_index(drop=True)

dates = df["Date"].values

sp_price = df["SP500"].values
nq_price = df["NQ100"].values
sox_price = df["SOX"].values
vix_close = df["VIX"].values

print(f"営業日数: {len(df)}")
print(f"期間: {dates[0]} ～ {dates[-1]}")
print()

# =========================
# 1. 下落率を事前計算
# =========================

sp_peak = np.maximum.accumulate(sp_price)
nq_peak = np.maximum.accumulate(nq_price)
sox_peak = np.maximum.accumulate(sox_price)

sp_drop = sp_price / sp_peak - 1.0
nq_drop = nq_price / nq_peak - 1.0
sox_drop = sox_price / sox_peak - 1.0

# =========================
# 2. bool条件を事前生成
# =========================

sp_drop_masks = {}
nq_drop_masks = {}
sox_drop_masks = {}

for level in DROP_LEVELS:
    sp_drop_masks[level] = sp_drop <= level
    nq_drop_masks[level] = nq_drop <= level
    sox_drop_masks[level] = sox_drop <= level

# =========================
# 3. VIX条件も事前生成
# =========================

vix_masks = {
    None: np.ones(len(df), dtype=bool),
    30: vix_close >= 30,
    35: vix_close >= 35,
}

# =========================
# 4. 発動日一覧を事前生成
# =========================

trigger_days_cache = {}

# 条件例:
# SP500 -20%
# NQ100 -20%
# SOX -20%
#
# 必要ならここを追加可能

condition_patterns = [
    ("SP500", -0.2),
    ("SP500", -0.3),
    ("NQ100", -0.2),
    ("NQ100", -0.3),
    ("SOX", -0.2),
    ("SOX", -0.3),
]

for vix_th in VIX_THRESHOLDS:

    vix_mask = vix_masks[vix_th]

    for market, level in condition_patterns:

        if market == "SP500":
            mask = sp_drop_masks[level]

        elif market == "NQ100":
            mask = nq_drop_masks[level]

        elif market == "SOX":
            mask = sox_drop_masks[level]

        final_mask = mask & vix_mask

        trigger_days = np.where(final_mask)[0]

        trigger_days_cache[(vix_th, market, level)] = trigger_days

# =========================
# 開始日
# 月次にするとさらに高速
# =========================

START_INTERVAL = 21

start_indices = np.arange(0, len(df), START_INTERVAL)

print(f"開始ケース数: {len(start_indices)}")
print()

# =========================
# Simulation
# =========================

results = []

patterns = list(
    product(
        VIX_THRESHOLDS,
        INITIAL_RATIOS,
        BUY_AMOUNTS_LIST,
        BUY_RATIOS_LIST,
        BUY_TARGET_RATIOS,
        condition_patterns,
    )
)

print(f"総パターン数: {len(patterns)}")

pattern_count = 0

for (
    vix_th,
    initial_ratio,
    buy_amounts,
    buy_ratios,
    buy_target_ratio,
    condition_pattern,
) in patterns:

    pattern_count += 1

    if pattern_count % 10 == 0:
        print(f"progress {pattern_count}/{len(patterns)}")

    market, level = condition_pattern

    trigger_days_all = trigger_days_cache[
        (vix_th, market, level)
    ]

    total_returns = []
    cagrs = []
    max_drawdowns = []
    unused_cash_list = []
    trigger_counts = []

    for start_idx in start_indices:

        initial_nq_ratio, initial_sox_ratio = buy_target_ratio

        initial_nq_cash = (
            INITIAL_CASH
            * initial_ratio
            * initial_nq_ratio
        )

        initial_sox_cash = (
            INITIAL_CASH
            * initial_ratio
            * initial_sox_ratio
        )

        cash = INITIAL_CASH - (
            initial_nq_cash + initial_sox_cash
        )

        nq_shares = (
            initial_nq_cash / nq_price[start_idx]
        )

        sox_shares = (
            initial_sox_cash / sox_price[start_idx]
        )

        trigger_count = 0

        # 開始日以降だけに絞る
        trigger_days = trigger_days_all[
            trigger_days_all >= start_idx
        ]

        for idx in trigger_days:

            tranche = min(trigger_count, 4)

            amount = buy_amounts[tranche]
            ratio = buy_ratios[tranche]

            buy_cash = amount * ratio

            if cash < buy_cash:
                continue

            nq_ratio, sox_ratio = buy_target_ratio

            nq_buy_cash = buy_cash * nq_ratio
            sox_buy_cash = buy_cash * sox_ratio

            nq_shares += (
                nq_buy_cash / nq_price[idx]
            )

            sox_shares += (
                sox_buy_cash / sox_price[idx]
            )

            cash -= buy_cash

            trigger_count += 1

        final_value = (
            nq_shares * nq_price[-1]
            + sox_shares * sox_price[-1]
            + cash
        )

        total_return_pct = (
            (final_value / INITIAL_CASH) - 1
        ) * 100

        years = (len(df) - start_idx) / 252

        cagr = (
            (final_value / INITIAL_CASH)
            ** (1 / years)
            - 1
        ) * 100

        # Max Drawdown
        portfolio_values = (
            nq_shares * nq_price[start_idx:]
            + sox_shares * sox_price[start_idx:]
            + cash
        )

        running_max = np.maximum.accumulate(portfolio_values)

        drawdowns = (
            portfolio_values / running_max - 1
        )

        max_dd = abs(np.min(drawdowns)) * 100

        total_returns.append(total_return_pct)
        cagrs.append(cagr)
        max_drawdowns.append(max_dd)
        unused_cash_list.append(cash)
        trigger_counts.append(trigger_count)

    results.append({
        "vix_threshold": vix_th,
        "condition_market": market,
        "condition_drop": level,
        "initial_ratio": initial_ratio,
        "amounts": buy_amounts,
        "ratios": buy_ratios,
        "buy_target_ratio": buy_target_ratio,
        "avg_return_pct": np.mean(total_returns),
        "median_return_pct": np.median(total_returns),
        "min_return_pct": np.min(total_returns),
        "max_return_pct": np.max(total_returns),
        "avg_cagr_pct": np.mean(cagrs),
        "avg_max_drawdown_pct": np.mean(max_drawdowns),
        "worst_drawdown_pct": np.max(max_drawdowns),
        "avg_unused_cash": np.mean(unused_cash_list),
        "avg_trigger_count": np.mean(trigger_counts),
    })

# =========================
# Output
# =========================

result_df = pd.DataFrame(results)

result_df = result_df.sort_values(
    "avg_return_pct",
    ascending=False,
)

print()
print("==============================================")
print("Top 50 Best Strategies")
print("==============================================")

print(result_df.head(50).to_string(index=False))

result_df.to_csv(OUTPUT_FILE, index=False)

print()
print(f"Saved: {OUTPUT_FILE}")
