import pandas as pd
import numpy as np
from itertools import product

# =========================
# Files
# =========================

NQ100_FILE = "nasdaq100/nq100_daily_yen.csv"
SOX_FILE = "sox/sox_daily_yen.csv"
VIX_FILE = "vix/vix_daily_data.csv"

OUTPUT_FILE = "buy_vix_trigger_only.csv"

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

# =========================
# VIX条件のみ
# =========================

VIX_THRESHOLDS = [30, 35]

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

nq = pd.read_csv(NQ100_FILE)
sox = pd.read_csv(SOX_FILE)
vix = pd.read_csv(VIX_FILE)

nq["Date"] = pd.to_datetime(nq["Date"])
sox["Date"] = pd.to_datetime(sox["Date"])

# VIXの日付部分のみ利用
vix["Date"] = pd.to_datetime(
    vix["Date"].astype(str).str[:10]
)

# =========================
# Merge
# =========================

# df = (
#     nq[["Date", "Close"]]
#     .rename(columns={"Close": "NQ100"})
#     .merge(
#         sox[["Date", "Close"]]
#         .rename(columns={"Close": "SOX"}),
#         on="Date",
#     )
#     .merge(
#         vix[["Date", "Close"]]
#         .rename(columns={"Close": "VIX"}),
#         on="Date",
#     )
# )

# df = df.sort_values("Date").reset_index(drop=True)

# 関数定義（後者のロジック）
def load_price_csv(file_path, price_col="Close_Yen"):
    df = pd.read_csv(file_path)
    # 日付の正規化
    df["Date"] = pd.to_datetime(df["Date"].astype(str).str[:10])
    # カンマ除去と数値化
    df[price_col] = df[price_col].astype(str).str.replace(",", "").astype(float)
    df = df.sort_values("Date").reset_index(drop=True)
    return df[["Date", price_col]]

# データロード
# sp500 = load_price_csv(SP500_FILE, "Close_Yen").rename(columns={"Close_Yen": "SP500"})
nq100 = load_price_csv(NQ100_FILE, "Close_Yen").rename(columns={"Close_Yen": "NQ100"})
sox   = load_price_csv(SOX_FILE,   "Close_Yen").rename(columns={"Close_Yen": "SOX"})

# マージ（一気に繋げる）
df = (
    # sp500
    # .merge(nq100, on="Date", how="inner")
    nq100
    .merge(sox,   on="Date", how="inner")
)

# VIXはClose_YenではなくCloseなので個別に
vix = pd.read_csv(VIX_FILE)
vix["Date"] = pd.to_datetime(vix["Date"].astype(str).str[:10])
vix["VIX"] = vix["Close"].astype(str).str.replace(",", "").astype(float)

df = df.merge(vix[["Date", "VIX"]], on="Date", how="inner")

dates = df["Date"].values

nq_price = df["NQ100"].values
sox_price = df["SOX"].values
vix_close = df["VIX"].values

print(f"営業日数: {len(df)}")
print(f"期間: {dates[0]} ～ {dates[-1]}")
print()

# =========================
# VIX条件を事前生成
# =========================

vix_masks = {
    30: vix_close >= 30,
    35: vix_close >= 35,
}

# =========================
# Trigger Days Cache
# =========================

trigger_days_cache = {}

for vix_th in VIX_THRESHOLDS:

    mask = vix_masks[vix_th]

    trigger_days = np.where(mask)[0]

    trigger_days_cache[vix_th] = trigger_days

# =========================
# 開始日
# 月次間隔
# =========================

START_INTERVAL = 21

start_indices = np.arange(
    0,
    len(df),
    START_INTERVAL
)

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
) in patterns:

    pattern_count += 1

    if pattern_count % 10 == 0:
        print(
            f"progress "
            f"{pattern_count}/{len(patterns)}"
        )

    trigger_days_all = trigger_days_cache[vix_th]

    total_returns = []
    cagrs = []
    max_drawdowns = []
    unused_cash_list = []
    trigger_counts = []

    # =========================
    # 発動日リスト
    # =========================

    # trigger_date_strings = [
    #     str(df.iloc[idx]["Date"].date())
    #     for idx in trigger_days_all
    # ]
    # # 日まで出すと多いので月までにする: 2002-07-22 -> 2002-07
    # trigger_date_strings = (
    #     df.iloc[trigger_days_all]["Date"]
    #     .astype(str)
    #     .str[:7]
    #     .unique()
    #     .tolist()
    # )

    for start_idx in start_indices:

        initial_nq_ratio, initial_sox_ratio = (
            buy_target_ratio
        )

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
            initial_nq_cash
            + initial_sox_cash
        )

        nq_shares = (
            initial_nq_cash
            / nq_price[start_idx]
        )

        sox_shares = (
            initial_sox_cash
            / sox_price[start_idx]
        )

        trigger_count = 0

        # =========================
        # 開始日以降だけ
        # =========================

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

            nq_ratio, sox_ratio = (
                buy_target_ratio
            )

            nq_buy_cash = (
                buy_cash * nq_ratio
            )

            sox_buy_cash = (
                buy_cash * sox_ratio
            )

            nq_shares += (
                nq_buy_cash
                / nq_price[idx]
            )

            sox_shares += (
                sox_buy_cash
                / sox_price[idx]
            )

            cash -= buy_cash

            trigger_count += 1

        # =========================
        # Final Value
        # =========================

        final_value = (
            nq_shares * nq_price[-1]
            + sox_shares * sox_price[-1]
            + cash
        )

        total_return_pct = (
            (final_value / INITIAL_CASH) - 1
        ) * 100

        years = (
            (len(df) - start_idx)
            / 252
        )

        cagr = (
            (final_value / INITIAL_CASH)
            ** (1 / years)
            - 1
        ) * 100

        # =========================
        # Max Drawdown
        # =========================

        portfolio_values = (
            nq_shares
            * nq_price[start_idx:]
            + sox_shares
            * sox_price[start_idx:]
            + cash
        )

        running_max = np.maximum.accumulate(
            portfolio_values
        )

        drawdowns = (
            portfolio_values
            / running_max
            - 1
        )

        max_dd = (
            abs(np.min(drawdowns))
            * 100
        )

        total_returns.append(total_return_pct)
        cagrs.append(cagr)
        max_drawdowns.append(max_dd)
        unused_cash_list.append(cash)
        trigger_counts.append(trigger_count)

    # =========================
    # 結果保存
    # =========================

    results.append({
        "vix_threshold": vix_th,
        "initial_ratio": initial_ratio,
        "amounts": buy_amounts,
        "ratios": buy_ratios,
        "buy_target_ratio": buy_target_ratio,

        "avg_return_pct":
            np.mean(total_returns),

        "median_return_pct":
            np.median(total_returns),

        "min_return_pct":
            np.min(total_returns),

        "max_return_pct":
            np.max(total_returns),

        "avg_cagr_pct":
            np.mean(cagrs),

        "avg_max_drawdown_pct":
            np.mean(max_drawdowns),

        "worst_drawdown_pct":
            np.max(max_drawdowns),

        "avg_unused_cash":
            np.mean(unused_cash_list),

        "avg_trigger_count":
            np.mean(trigger_counts),

        # =========================
        # 発動日一覧
        # =========================

        # "trigger_dates":
        #     " | ".join(trigger_date_strings),
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

print(
    result_df.head(50).to_string(index=False)
)

print()
print("==============================================")
print("VIX Trigger Months")
print("==============================================")

for vix_th in [30, 35]:

    trigger_days = np.where(vix_masks[vix_th])[0]

    trigger_months = (
        df.iloc[trigger_days]["Date"]
        .astype(str)
        .str[:7]
    )

    month_counts = (
        trigger_months
        .value_counts()
        .sort_index()
    )

    month_strings = [
        f"{month} {count}"
        for month, count in month_counts.items()
    ]

    print()
    print(
        f"VIX{vix_th}: "
        f"[{', '.join(month_strings)}]"
    )

result_df.to_csv(
    OUTPUT_FILE,
    index=False,
)

print()
print(f"Saved: {OUTPUT_FILE}")
