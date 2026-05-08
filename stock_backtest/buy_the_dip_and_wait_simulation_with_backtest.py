import pandas as pd
import numpy as np
import itertools

# =========================================================
# Partial Cash Reserve + Crash Buy Backtest
# =========================================================
#
# 目的
# ----
# ・最初から一部を市場投入
# ・残り現金を暴落時に段階投入
# ・QQQ/SOXへ買い下がり
# ・全期間バックテスト
#
# =========================================================

# =========================================================
# 設定
# =========================================================

TOTAL_CAPITAL = 10_000_000

HOLD_YEARS = 10
HOLD_MONTHS = HOLD_YEARS * 12

# -----------------------------------------
# ファイル
# -----------------------------------------

ASSET_FILES = {
    "MSCI": "orucan_multiply_dollar_yen_since199907.txt",
    "QQQ": "qqq_multiply_dollar_yen_since199907.txt",
    "SOX": "sox_multiply_dollar_yen_since199907.txt",
    "TOPIX": "topix_since199907.txt",
}

# -----------------------------------------
# 初期投資ポートフォリオ
# （最初から市場に入れておく部分）
# -----------------------------------------

INITIAL_PORTFOLIO = {
    "MSCI": 0.50,
    "QQQ": 0.30,
    "SOX": 0.15,
    "TOPIX": 0.05,
}

# -----------------------------------------
# 初期投資率候補
# -----------------------------------------

INITIAL_INVEST_RATIOS = [
    0.0,
    0.2,
    0.4,
    0.6,
]

# -----------------------------------------
# 暴落トリガー
# -----------------------------------------

DRAW_DOWN_LEVELS = [10, 15, 20, 25, 30]

# -----------------------------------------
# 暴落時投入額候補（万円）
# -----------------------------------------

AMOUNT_CANDIDATES = [
    (100, 100, 100, 100, 100),
    (100, 100, 200, 200, 300),
    (200, 200, 200, 200, 200),
]

# -----------------------------------------
# QQQ比率候補
# 残りはSOX
# -----------------------------------------

RATIO_CANDIDATES = list(itertools.product(
    [0.3, 0.5, 0.7],
    repeat=5
))

# =========================================================
# データ読み込み
# =========================================================

def load_asset(file_path):

    df = pd.read_csv(
        file_path,
        sep=r"\s+|,|\t",
        engine="python"
    )

    cols = list(df.columns)

    df = df.rename(columns={
        cols[0]: "Date",
        cols[1]: "Price"
    })

    # ------------------------------
    # 日付変換
    # ------------------------------

    parsed = False

    for fmt in ["%Y-%m", "%m/%Y", "%Y/%m", "%Y-%m-%d"]:

        try:
            df["Date"] = pd.to_datetime(df["Date"], format=fmt)
            parsed = True
            break

        except:
            pass

    if not parsed:
        df["Date"] = pd.to_datetime(df["Date"])

    # ------------------------------
    # 数値化
    # ------------------------------

    df["Price"] = (
        df["Price"]
        .astype(str)
        .str.replace(",", "")
        .astype(float)
    )

    df = df.sort_values("Date").reset_index(drop=True)

    return df[["Date", "Price"]]

# =========================================================
# マージ
# =========================================================

merged = None

for asset, file_path in ASSET_FILES.items():

    df = load_asset(file_path)

    df = df.rename(columns={"Price": asset})

    if merged is None:
        merged = df
    else:
        merged = pd.merge(
            merged,
            df,
            on="Date",
            how="inner"
        )

merged = merged.sort_values("Date").reset_index(drop=True)

dates = merged["Date"].dt.strftime("%Y-%m").tolist()

N = len(merged)

if N == 0:
    raise Exception("共通データがありません")

print()
print(f"共通で使える月数: {N}")
print(f"期間: {dates[0]} ～ {dates[-1]}")

# =========================================================
# 価格配列
# =========================================================

prices = {}

for asset in ASSET_FILES.keys():
    prices[asset] = merged[asset].values

# =========================================================
# 指標関数
# =========================================================

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

    return (
        ((final / initial) ** (1 / years)) - 1
    ) * 100

# =========================================================
# シミュレーション
# =========================================================

def simulate_case(
    start_idx,
    initial_invest_ratio,
    amounts,
    qqq_ratios
):

    end_idx = start_idx + HOLD_MONTHS

    if end_idx >= N:
        return None

    # -------------------------------------------------
    # units
    # -------------------------------------------------

    units = {
        "MSCI": 0.0,
        "QQQ": 0.0,
        "SOX": 0.0,
        "TOPIX": 0.0,
    }

    # -------------------------------------------------
    # 初期投資
    # -------------------------------------------------

    initial_invest = TOTAL_CAPITAL * initial_invest_ratio

    for asset, w in INITIAL_PORTFOLIO.items():

        amount = initial_invest * w

        units[asset] += (
            amount / prices[asset][start_idx]
        )

    cash = TOTAL_CAPITAL - initial_invest

    # -------------------------------------------------
    # MSCI peak tracking
    # -------------------------------------------------

    peak = prices["MSCI"][start_idx]

    triggered = [False] * len(DRAW_DOWN_LEVELS)

    # -------------------------------------------------
    # path
    # -------------------------------------------------

    path = []

    trigger_count = 0

    # -------------------------------------------------
    # 月次ループ
    # -------------------------------------------------

    for t in range(start_idx, end_idx + 1):

        msci_price = prices["MSCI"][t]

        # -----------------------------
        # peak更新
        # -----------------------------

        if msci_price > peak:
            peak = msci_price

        drawdown = (
            (peak - msci_price) / peak
        ) * 100

        # -----------------------------
        # トリガー判定
        # -----------------------------

        for i, level in enumerate(DRAW_DOWN_LEVELS):

            if triggered[i]:
                continue

            if drawdown >= level:

                invest_man = amounts[i]

                invest_amount = invest_man * 10_000

                invest_amount = min(
                    invest_amount,
                    cash
                )

                qqq_ratio = qqq_ratios[i]

                sox_ratio = 1 - qqq_ratio

                # QQQ
                qqq_amount = invest_amount * qqq_ratio

                units["QQQ"] += (
                    qqq_amount / prices["QQQ"][t]
                )

                # SOX
                sox_amount = invest_amount * sox_ratio

                units["SOX"] += (
                    sox_amount / prices["SOX"][t]
                )

                cash -= invest_amount

                triggered[i] = True

                trigger_count += 1

        # -----------------------------
        # 総資産
        # -----------------------------

        total = cash

        for asset in units.keys():

            total += (
                units[asset]
                * prices[asset][t]
            )

        path.append(total)

    final_value = path[-1]

    return {
        "final_value": final_value,
        "return_pct":
            (final_value / TOTAL_CAPITAL - 1) * 100,
        "cagr_pct":
            calc_cagr(
                TOTAL_CAPITAL,
                final_value,
                HOLD_MONTHS
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

for initial_ratio in INITIAL_INVEST_RATIOS:

    for amounts in AMOUNT_CANDIDATES:

        total_amount = sum(amounts)

        if total_amount > 1000:
            continue

        for ratios in RATIO_CANDIDATES:

            pattern_no += 1

            all_results = []

            for start_idx in range(N - HOLD_MONTHS):

                r = simulate_case(
                    start_idx,
                    initial_ratio,
                    amounts,
                    ratios
                )

                if r:
                    all_results.append(r)

            if len(all_results) == 0:
                continue

            df = pd.DataFrame(all_results)

            rows.append({

                "initial_invest_ratio":
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

            if pattern_no % 20 == 0:
                print(
                    f"progress "
                    f"{pattern_no}/{total_patterns}"
                )

# =========================================================
# 結果
# =========================================================

summary = pd.DataFrame(rows)

summary = summary.sort_values(
    "avg_return_pct",
    ascending=False
)

# =========================================================
# 保存
# =========================================================

summary.to_csv(
    "partial_cash_reserve_backtest.csv",
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
print("Saved: partial_cash_reserve_backtest.csv")
