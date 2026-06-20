import numpy as np
import pandas as pd
import random
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt

# =========================
# 基本設定
# =========================

INITIAL_PRICE = 100.0
TOTAL_CAPITAL = 1_000_000

INITIAL_FX = 160.0

Y_VALUES = range(0, 11)
M1_VALUES = range(1, 19)
M2_VALUES = range(1, 19)
P_VALUES = [10, 20, 30, 40, 50]

DCA_MONTHS_LIST = [1, 3, 6, 12, 24, 36, 60, 120]
UPFRONT_RATIOS = [0.0, 0.25, 0.5, 0.75, 1.0]

CASH_ANNUAL_RETURN = 0.0

SHOW_PLOTS = True

# =========================
# Y重み（近い将来の暴落を重視）
# =========================

Y_WEIGHTS = {
    0: 0.18,
    1: 0.16,
    2: 0.14,
    3: 0.12,
    4: 0.10,
    5: 0.08,
    6: 0.07,
    7: 0.06,
    8: 0.04,
    9: 0.03,
    10: 0.02
}

# =========================
# 将来10年後の最終倍率の不確実性
# =========================

FINAL_MULTIPLES = [1.2, 1.5, 2.0, 2.5, 3.0]
FINAL_WEIGHTS   = [0.10, 0.20, 0.35, 0.20, 0.15]

# =========================
# 第二暴落設定
# =========================

SECOND_CRASH_PROB = 0.35

# =========================
# 株価パス生成
# =========================

def build_price_path(Y, M1, M2, P):
    final_multiple = random.choices(FINAL_MULTIPLES, weights=FINAL_WEIGHTS)[0]

    total_months = (Y + 10) * 12
    crash_start = Y * 12
    crash_bottom = crash_start + M1
    recovery_end = crash_bottom + M2

    p = P / 100.0
    final_price = INITIAL_PRICE * final_multiple

    price = np.empty(total_months + 1)

    if total_months > 0:
        peak_price = INITIAL_PRICE * (final_multiple ** (crash_start / total_months))
    else:
        peak_price = INITIAL_PRICE

    # 調整開始まで
    if crash_start > 0:
        for t in range(crash_start + 1):
            price[t] = INITIAL_PRICE * ((peak_price / INITIAL_PRICE) ** (t / crash_start))
    else:
        price[0] = INITIAL_PRICE

    # 第一暴落
    bottom_price = peak_price * (1.0 - p)
    for t in range(crash_start + 1, min(crash_bottom, total_months) + 1):
        frac = (t - crash_start) / M1
        price[t] = peak_price + (bottom_price - peak_price) * frac

    # 第一回復
    for t in range(crash_bottom + 1, min(recovery_end, total_months) + 1):
        frac = (t - crash_bottom) / M2
        price[t] = bottom_price + (peak_price - bottom_price) * frac

    if recovery_end <= total_months:
        price[recovery_end] = peak_price
        remaining = total_months - recovery_end

        for t in range(recovery_end + 1, total_months + 1):
            frac = (t - recovery_end) / max(1, remaining)
            price[t] = peak_price * ((final_price / peak_price) ** frac)

    # 第二暴落追加
    if random.random() < SECOND_CRASH_PROB:
        second_start = random.randint(recovery_end + 6, max(recovery_end + 6, total_months - 12))
        second_len = random.randint(3, 12)
        second_recovery = random.randint(3, 12)
        second_p = random.choice([0.08, 0.12, 0.15, 0.20])

        second_bottom = min(total_months, second_start + second_len)
        second_end = min(total_months, second_bottom + second_recovery)

        peak2 = price[second_start]
        bottom2 = peak2 * (1 - second_p)

        for t in range(second_start + 1, second_bottom + 1):
            frac = (t - second_start) / second_len
            price[t] = peak2 + (bottom2 - peak2) * frac

        for t in range(second_bottom + 1, second_end + 1):
            frac = (t - second_bottom) / second_recovery
            price[t] = bottom2 + (peak2 - bottom2) * frac

        remain2 = total_months - second_end
        if remain2 > 0:
            for t in range(second_end + 1, total_months + 1):
                frac = (t - second_end) / remain2
                price[t] = peak2 * ((final_price / peak2) ** frac)

    return price


# =========================
# 為替パス生成
# =========================

def build_fx_path(Y, M1, M2):
    total_months = (Y + 10) * 12
    fx = np.empty(total_months + 1)

    crash_start = Y * 12
    yen_spike = crash_start + M1
    fx_bottom = 145
    final_fx = 140

    # 暴落前
    if crash_start > 0:
        for t in range(crash_start + 1):
            fx[t] = INITIAL_FX - 5 * (t / crash_start)
    else:
        fx[0] = INITIAL_FX

    # 暴落中円高
    for t in range(crash_start + 1, min(yen_spike, total_months) + 1):
        frac = (t - crash_start) / M1
        fx[t] = 155 + (fx_bottom - 155) * frac

    # 回復中
    for t in range(yen_spike + 1, min(yen_spike + M2, total_months) + 1):
        frac = (t - yen_spike) / M2
        fx[t] = fx_bottom + (155 - fx_bottom) * frac

    # 長期で140へ
    recovery_end = yen_spike + M2
    remaining = total_months - recovery_end
    if remaining > 0:
        for t in range(recovery_end + 1, total_months + 1):
            frac = (t - recovery_end) / remaining
            fx[t] = 155 + (final_fx - 155) * frac

    return fx


# =========================
# 戦略シミュレーション
# =========================

def simulate_strategy(price, fx, upfront_ratio, dca_months, trigger_extra=False):
    total_months = len(price) - 1
    capital = TOTAL_CAPITAL
    cash = capital
    units = 0.0

    # 一括部分
    if upfront_ratio > 0:
        invest_amount = capital * upfront_ratio
        effective_price = price[0] * fx[0] / INITIAL_FX
        units += invest_amount / effective_price
        cash -= invest_amount

    remaining_capital = capital * (1.0 - upfront_ratio)

    if remaining_capital > 0 and dca_months > 0:
        monthly_invest = remaining_capital / dca_months
        monthly_cash_return = (1.0 + CASH_ANNUAL_RETURN) ** (1 / 12) - 1

        for t in range(dca_months):
            if t > total_months:
                break

            if t > 0:
                cash *= (1.0 + monthly_cash_return)

            invest_amount = min(monthly_invest, cash)

            # トリガー追加投資
            if trigger_extra:
                drawdown = (max(price[:t+1]) - price[t]) / max(price[:t+1])
                yen_gain = (INITIAL_FX - fx[t]) / INITIAL_FX

                if drawdown >= 0.10 or yen_gain >= 0.05:
                    invest_amount = min(invest_amount * 2.0, cash)

            effective_price = price[t] * fx[t] / INITIAL_FX
            units += invest_amount / effective_price
            cash -= invest_amount

        remaining_months = max(0, total_months - dca_months + 1)
        cash *= (1.0 + monthly_cash_return) ** remaining_months

    final_effective_price = price[-1] * fx[-1] / INITIAL_FX
    final_value = units * final_effective_price + cash
    return final_value


def strategy_name(upfront_ratio, dca_months, trigger_extra):
    base = ""
    if upfront_ratio >= 1.0:
        base = "LumpSum"
    elif upfront_ratio == 0.0:
        base = f"DCA_{dca_months}m"
    else:
        base = f"Hybrid_{int(upfront_ratio*100)}pct_DCA{dca_months}m"

    if trigger_extra:
        base += "_Trigger"

    return base


# =========================
# 戦略一覧
# =========================

strategies = []

for trigger_extra in [False, True]:
    for upfront_ratio in UPFRONT_RATIOS:
        if upfront_ratio >= 1.0:
            strategies.append((1.0, 0, trigger_extra))
        else:
            for dca_months in DCA_MONTHS_LIST:
                strategies.append((upfront_ratio, dca_months, trigger_extra))

# =========================
# 全シナリオ実行
# =========================

rows = []

for Y in Y_VALUES:
    for M1 in M1_VALUES:
        for M2 in M2_VALUES:
            for P in P_VALUES:
                price = build_price_path(Y, M1, M2, P)
                fx = build_fx_path(Y, M1, M2)

                values = {}

                for upfront_ratio, dca_months, trigger_extra in strategies:
                    name = strategy_name(upfront_ratio, dca_months, trigger_extra)
                    final_value = simulate_strategy(price, fx, upfront_ratio, dca_months, trigger_extra)
                    values[name] = final_value

                best_value = max(values.values())
                lump_value = values["LumpSum"]

                for name, final_value in values.items():
                    rows.append({
                        "Y": Y,
                        "M1": M1,
                        "M2": M2,
                        "P": P,
                        "weight": Y_WEIGHTS[Y],
                        "strategy": name,
                        "final_value": final_value,
                        "return_pct": (final_value / TOTAL_CAPITAL - 1.0) * 100,
                        "regret_pct": (best_value - final_value) / best_value * 100,
                        "beats_lump": final_value > lump_value,
                    })

results = pd.DataFrame(rows)

# =========================
# 重み付き集計
# =========================

def weighted_summary(df):
    grouped = []
    for name, g in df.groupby("strategy"):
        w = g["weight"]
        grouped.append({
            "strategy": name,
            "weighted_avg_return_pct": np.average(g["return_pct"], weights=w),
            "weighted_avg_regret_pct": np.average(g["regret_pct"], weights=w),
            "win_rate_vs_lump": np.average(g["beats_lump"], weights=w) * 100,
            "p05_return_pct": np.percentile(g["return_pct"], 5),
            "max_regret_pct": g["regret_pct"].max()
        })
    return pd.DataFrame(grouped)

summary = weighted_summary(results)

print("\n=== Weighted Average Return Top ===")
print(summary.sort_values("weighted_avg_return_pct", ascending=False).head(20).to_string(index=False))

print("\n=== Lowest Max Regret Top ===")
print(summary.sort_values("max_regret_pct", ascending=True).head(20).to_string(index=False))

results.to_csv("realistic_scenario_results.csv", index=False)
summary.to_csv("realistic_strategy_summary.csv", index=False)

print("\nSaved: realistic_scenario_results.csv")
print("Saved: realistic_strategy_summary.csv")

# =========================
# グラフ
# =========================

if SHOW_PLOTS:
    top_strategies = summary.sort_values("weighted_avg_return_pct", ascending=False).head(10)["strategy"].tolist()

    fig, ax = plt.subplots(figsize=(14,6))

    for s in top_strategies:
        vals = results[results["strategy"] == s]["return_pct"].values
        ax.plot(sorted(vals), label=s)

    ax.set_title("Return Distribution (Realistic Weighted Scenario)")
    ax.set_ylabel("Return %")
    ax.legend(bbox_to_anchor=(1.05,1), loc="upper left")
    ax.grid(True, linestyle="--", alpha=0.4)
    plt.tight_layout()
    plt.show(block=True)
