# 結論から言うと、

# * **`buy_the_dip_daily_trigger_cache_buy_nd100_sox2.py` があるなら、`buy_the_dip_daily_trigger_only_vix_buy_nd100_sox.py` は検証用途以外では不要**です。
# * また、**`buy_the_dip_daily_trigger_only_vix_buy_nd100_sox.py` は avg_return_pct が高く出る原因になりそうなバグ（あるいはロジック上の問題）が複数あります。**

# コード全体を見て気付いた点を順番に説明します。

# ---

# ## ① 最大の問題

# ### MaxDrawdown の計算が壊れています

# 最後で

# ```python
# portfolio_values = (
#     nq_shares * nq_price[start_idx:]
#     + sox_shares * sox_price[start_idx:]
#     + cash
# )
# ```

# となっています。

# しかし、この

# ```
# nq_shares
# sox_shares
# cash
# ```

# は

# **全て買い終わった後の値**

# です。

# つまり

# ```
# 2008
# ↓
# VIX30で買う
# ↓
# 2010
# VIX35で買う
# ↓
# 2012
# さらに買う
# ↓
# 2015終了
# ```

# なのに、

# ```
# 2008年時点にも
# 2012年に買った株を
# 持っていたことになっている
# ```

# という未来情報を使っています。

# これは完全に未来を見ています。

# 正しくは

# ```
# for idx in range(...)
# ```

# の中で毎日の評価額を保存しなければいけません。

# つまり元コードの

# ```python
# portfolio_values.append(value)
# ```

# 方式です。

# ---

# ## ② avg_return が高い最大の原因

# こちらの方がさらに重要です。

# 元コード

# ```
# buy_the_dip_daily_trigger_cache_buy_nd100_sox2.py
# ```

# では

# 10年間だけ評価しています。

# ```
# start
# ↓
# 10年後
# 終了
# ```

# しかし

# only_vix

# では

# ```
# start
# ↓
# 2026年まで
# ```

# 評価しています。

# つまり

# 2000年開始

# なら

# 26年間保有

# になります。

# なので

# ```
# avg_return
# ```

# は当然大きくなります。

# さらに

# ```
# CAGR
# ```

# だけは

# ```
# years=(len(df)-start)/252
# ```

# で補正していますが

# ```
# avg_return_pct
# ```

# は補正なしです。

# なので

# ```
# 1999開始
# +1500%

# 2015開始
# +80%
# ```

# これを平均してしまっています。

# 当然ものすごく高くなります。

# ---

# ## ③ 開始日が公平ではない

# 元コードは

# ```
# 10年窓
# ```

# なので

# ```
# 1999→2009
# 2000→2010
# ...
# 2016→2026
# ```

# 全て

# 10年間

# です。

# ところがonly_vixは

# ```
# 1999→2026

# 2005→2026

# 2015→2026
# ```

# となっています。

# つまり

# 昔ほど有利

# です。

# これも平均リターンを押し上げます。

# ---

# ## ④ trigger_count が進まない

# ここ

# ```python
# if cash < buy_cash:
#     continue
# ```

# となっています。

# 例えば

# ```
# 5回目

# 残金80

# 買付100
# ```

# になると

# ```
# continue
# ```

# なので

# trigger_count

# が増えません。

# つまり

# 次のVIXでも

# また100円買おうとします。

# 結果

# 最後まで買えません。

# 元コードは

# ```
# buy_cash=min(...)
# ```

# なので

# ```
# 80円だけ買う
# ```

# になります。

# こちらの方が自然です。

# ---

# ## ⑤ 初回投資だけBuy&Holdになっている

# ```
# INITIAL_RATIO
# ```

# だけ

# 開始日に

# 一括投資しています。

# 例えば

# ```
# 0.4
# ```

# なら

# 400円

# 開始日に買います。

# 残りだけ

# VIX待ち。

# これは仕様なので問題ありませんが、

# 元コードにはありません。

# 比較するときは

# 別戦略

# になります。

# ---

# ## ⑥ trigger_days_cacheは元コードの方が優秀

# only_vixでは

# ```
# trigger_days = trigger_days_all[
#     trigger_days_all >= start_idx
# ]
# ```

# 毎回やっています。

# 元コードでは

# ```
# for idx in range(...)
# ```

# だけなので

# 実は十分速いです。

# 速度差はほとんどありません。

# ---

# ## ⑦ 元コードの方がバックテストとして正しい

# 元コード

# ```
# simulate_vix_trigger()
# ```

# は

# 毎日

# ```
# 評価額
# ```

# を更新しています。

# そのため

# * CAGR
# * Return
# * MaxDrawdown

# 全て同じロジックで計算できます。

# only_vixは

# 最後に

# ```
# 最終株数
# ```

# だけから逆算しているので、

# 途中経過がありません。

# そのため

# MaxDrawdownも正しく出ません。

# ---

# # 私ならこうします

# 私は

# **`buy_the_dip_daily_trigger_cache_buy_nd100_sox2.py` をベースに一本化**します。

# その上で

# ```
# if STRATEGY == "BUY_HOLD":
# ```

# ```
# if STRATEGY == "DCA":
# ```

# ```
# if STRATEGY == "VIX":
# ```

# のように分岐させます。

# さらに

# ```
# INITIAL_RATIO
# ```

# だけを追加します。

# つまり

# ```python
# cash = INITIAL_CASH

# initial_buy = INITIAL_CASH * initial_ratio

# cash -= initial_buy
# ```

# だけ最初に入れ、

# その後は

# ```
# simulate_vix_trigger()
# ```

# をそのまま使います。

# こうすると

# * 10年窓
# * Drawdown
# * CAGR
# * Return
# * Buy&Hold
# * DCA
# * VIX

# すべて同じ評価条件になり、比較が公平になります。

# ---

# ## 最も怪しいバグ（優先順位）

# `avg_return_pct` が不自然に高い原因として疑う順番は次の通りです。

# 1. **評価期間が「10年固定」ではなく「開始日からデータ末尾まで」になっている（最も影響が大きい）**
# 2. **開始年が古いほど有利になるため、平均リターンが大きく歪む**
# 3. **MaxDrawdown計算で未来の保有株数を使っている**
# 4. **`cash < buy_cash` のときにスキップしてしまい、残金を使い切れない**
# 5. **初回一括投資（INITIAL_RATIO）が入っており、元コードとは戦略自体が異なる**

# この中では、**①と②だけでも `avg_return_pct` が極端に高く見える十分な理由**になります。公平な比較をしたいのであれば、評価期間を元コードと同じ「開始から10年間」に揃えることを強くおすすめします。


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
