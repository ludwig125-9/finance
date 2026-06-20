import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('TkAgg')  # または 'Qt5Agg'
import matplotlib.pyplot as plt
# matplotlib.use("Agg")
# import matplotlib.pyplot as plt


# =========================
# 設定
# =========================

INITIAL_PRICE = 100.0
FINAL_MULTIPLE = 2.0
TOTAL_CAPITAL = 1_000_000

# Y: 0〜10年
Y_VALUES = range(0, 11)

# M1, M2: 1〜18か月
M1_VALUES = range(1, 19)
M2_VALUES = range(1, 19)

# Pはユーザー条件に範囲指定が無かったため、ここで自由に変更
# 例：10%, 20%, 30%, 40%, 50%
P_VALUES = [10, 20, 30, 40, 50]

# 積立期間候補
DCA_MONTHS_LIST = [1, 3, 6, 12, 24, 36, 60, 120]

# 一部一括投資の比率
# 0.0 = 全額積立
# 1.0 = 全額一括
UPFRONT_RATIOS = [0.0, 0.25, 0.5, 0.75, 1.0]

# 待機資金の金利。まずは0%で置く
CASH_ANNUAL_RETURN = 0.0

# グラフ表示
SHOW_PLOTS = True


# =========================
# 株価パスを作る
# =========================

def build_price_path(Y, M1, M2, P):
    """
    現在100。
    Y年後に調整開始。
    M1か月でP%下落。
    M2か月で元のピーク水準に回復。
    Y+10年後に最終的に200。
    """
    total_months = (Y + 10) * 12
    crash_start = Y * 12
    crash_bottom = crash_start + M1
    recovery_end = crash_bottom + M2

    p = P / 100.0
    final_price = INITIAL_PRICE * FINAL_MULTIPLE

    price = np.empty(total_months + 1)

    # 調整開始時点のピーク価格
    # 「調整がなければ、最終的に2倍へ向かって滑らかに上がる」と仮定
    if total_months > 0:
        peak_price = INITIAL_PRICE * (FINAL_MULTIPLE ** (crash_start / total_months))
    else:
        peak_price = INITIAL_PRICE

    # 調整開始まで
    if crash_start > 0:
        for t in range(crash_start + 1):
            price[t] = INITIAL_PRICE * ((peak_price / INITIAL_PRICE) ** (t / crash_start))
    else:
        price[0] = INITIAL_PRICE

    # 下落局面
    bottom_price = peak_price * (1.0 - p)
    for t in range(crash_start + 1, min(crash_bottom, total_months) + 1):
        frac = (t - crash_start) / M1
        price[t] = peak_price + (bottom_price - peak_price) * frac

    # 回復局面
    for t in range(crash_bottom + 1, min(recovery_end, total_months) + 1):
        frac = (t - crash_bottom) / M2
        price[t] = bottom_price + (peak_price - bottom_price) * frac

    # 回復後、最終価格200へ
    if recovery_end <= total_months:
        price[recovery_end] = peak_price
        remaining = total_months - recovery_end

        if remaining > 0:
            for t in range(recovery_end + 1, total_months + 1):
                frac = (t - recovery_end) / remaining
                price[t] = peak_price * ((final_price / peak_price) ** frac)
    else:
        # 通常この条件では起きないが、念のため
        price[-1] = final_price

    return price


# =========================
# 投資戦略をシミュレーション
# =========================

def simulate_strategy(price, upfront_ratio, dca_months):
    """
    upfront_ratio:
        1.0なら全額一括
        0.5なら半分を今すぐ一括、残り半分をdca_monthsで積立
        0.0なら全額積立

    dca_months:
        残り資金を何か月に分けて投資するか
    """
    total_months = len(price) - 1
    capital = TOTAL_CAPITAL
    cash = capital
    units = 0.0

    # 一括部分
    if upfront_ratio > 0:
        invest_amount = capital * upfront_ratio
        units += invest_amount / price[0]
        cash -= invest_amount

    # 積立部分
    remaining_capital = capital * (1.0 - upfront_ratio)

    if remaining_capital > 0 and dca_months > 0:
        monthly_invest = remaining_capital / dca_months
        monthly_cash_return = (1.0 + CASH_ANNUAL_RETURN) ** (1 / 12) - 1

        for t in range(dca_months):
            if t > total_months:
                break

            # 前月から持ち越した現金に金利を付ける
            if t > 0:
                cash *= (1.0 + monthly_cash_return)

            invest_amount = min(monthly_invest, cash)
            units += invest_amount / price[t]
            cash -= invest_amount

        # 余った現金があれば最終月まで金利を付ける
        remaining_months = max(0, total_months - dca_months + 1)
        cash *= (1.0 + monthly_cash_return) ** remaining_months

    final_value = units * price[-1] + cash
    return final_value


def strategy_name(upfront_ratio, dca_months):
    if upfront_ratio >= 1.0:
        return "LumpSum"

    if upfront_ratio == 0.0:
        return f"DCA_{dca_months}m"

    return f"Hybrid_{int(upfront_ratio * 100)}pct_DCA{dca_months}m"


# =========================
# 戦略一覧を作る
# =========================

strategies = []

for upfront_ratio in UPFRONT_RATIOS:
    if upfront_ratio >= 1.0:
        strategies.append((1.0, 0, "LumpSum"))
    else:
        for dca_months in DCA_MONTHS_LIST:
            strategies.append(
                (upfront_ratio, dca_months, strategy_name(upfront_ratio, dca_months))
            )

# 重複除去
unique = {}
for upfront_ratio, dca_months, name in strategies:
    unique[name] = (upfront_ratio, dca_months, name)

strategies = list(unique.values())


# =========================
# 全シナリオを実行
# =========================

rows = []

for Y in Y_VALUES:
    for M1 in M1_VALUES:
        for M2 in M2_VALUES:
            for P in P_VALUES:
                price = build_price_path(Y=Y, M1=M1, M2=M2, P=P)

                values = {}
                for upfront_ratio, dca_months, name in strategies:
                    final_value = simulate_strategy(
                        price=price,
                        upfront_ratio=upfront_ratio,
                        dca_months=dca_months
                    )
                    values[name] = final_value

                best_value = max(values.values())
                lump_value = values["LumpSum"]

                for name, final_value in values.items():
                    rows.append({
                        "Y": Y,
                        "M1": M1,
                        "M2": M2,
                        "P": P,
                        "strategy": name,
                        "final_value": final_value,
                        "return_pct": (final_value / TOTAL_CAPITAL - 1.0) * 100,
                        "regret_pct": (best_value - final_value) / best_value * 100,
                        "beats_lump": final_value > lump_value,
                        "underperforms_lump": final_value < lump_value,
                    })

results = pd.DataFrame(rows)


# =========================
# 集計
# =========================

# 共通の集計関数を定義（コードをスッキリさせるため）
def get_summary(df, group_cols):
    return (
        df.groupby(group_cols)
        .agg(
            avg_return_pct=("return_pct", "mean"),
            median_return_pct=("return_pct", "median"),
            p05_return_pct=("return_pct", lambda x: np.percentile(x, 5)),
            min_return_pct=("return_pct", "min"),
            max_return_pct=("return_pct", "max"),
            avg_regret_pct=("regret_pct", "mean"),
            max_regret_pct=("regret_pct", "max"),
            win_rate_vs_lump=("beats_lump", "mean"),
        )
        .reset_index()
    )

# 1. 全体平均（以前と同じもの）
summary = get_summary(results, "strategy")
summary["win_rate_vs_lump"] *= 100

# 2. P（下落率）ごとの詳細集計
summary_by_P = get_summary(results, ["P", "strategy"])
summary_by_P["win_rate_vs_lump"] *= 100

print("\n=== 平均リターン上位 ===")
print(
    summary
    .sort_values("avg_return_pct", ascending=False)
    .head(15)
    .to_string(index=False)
)

print("\n=== 5パーセンタイル・リターン上位（悪いシナリオに強い順） ===")
print(
    summary
    .sort_values("p05_return_pct", ascending=False)
    .head(15)
    .to_string(index=False)
)

print("\n=== 最大後悔率が小さい順 ===")
print(
    summary
    .sort_values("max_regret_pct", ascending=True)
    .head(15)
    .to_string(index=False)
)


# =========================
# CSV保存
# =========================

results.to_csv("scenario_results.csv", index=False)
summary.to_csv("strategy_summary.csv", index=False)

print("\nSaved: scenario_results.csv")
print("Saved: strategy_summary.csv")

# =========================
# グラフ
# =========================

if SHOW_PLOTS:
    # 1. 元々の箱ひげ図（全シナリオ込みの分布）
    top_strategies = (
        summary
        .sort_values("avg_return_pct", ascending=False)
        .head(10)["strategy"]
        .tolist()
    )

    plot_data = results[results["strategy"].isin(top_strategies)].copy()
    fig1, ax1 = plt.subplots(figsize=(14, 6))

    data_for_box = [
        plot_data.loc[plot_data["strategy"] == s, "return_pct"].values
        for s in top_strategies
    ]

    ax1.boxplot(data_for_box, tick_labels=top_strategies, showfliers=False)
    ax1.axhline(100, color='red', linestyle='--', linewidth=1, label="LumpSum (100%)")
    ax1.set_title("Overall Return distribution by strategy (All P values)")
    ax1.set_ylabel("Return (%)")
    ax1.tick_params(axis="x", rotation=45)
    ax1.grid(True, linestyle="--", alpha=0.4)
    fig1.tight_layout()

    # ---------------------------------------------------------
    # 2. 【追加】P（下落率）の変化によるリターンの推移グラフ
    # ---------------------------------------------------------
    fig2, ax2 = plt.subplots(figsize=(12, 6))

    # summary_by_P を使って、主要な戦略のリターン推移を描画
    for s in top_strategies:
        strat_data = summary_by_P[summary_by_P["strategy"] == s]
        ax2.plot(strat_data["P"], strat_data["avg_return_pct"], marker='o', label=s)

    ax2.set_title("How Downside (P%) affects Average Return")
    ax2.set_xlabel("Market Drop Percentage (P %)")
    ax2.set_ylabel("Average Return (%)")
    ax2.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    ax2.grid(True, linestyle="--", alpha=0.4)
    fig2.tight_layout()

    # 表示（または保存）
    plt.show(block=True)
