import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ==========================================
# 設定
# ==========================================

CSV_FILE = "daily_dca_detail.csv"

TOP_N_STRATEGIES = 12

# グラフサイズ
FIG_W = 16
FIG_H = 8

# ==========================================
# CSV読み込み
# ==========================================

df = pd.read_csv(CSV_FILE)

# weights を文字列化して扱いやすく
df["strategy"] = (
    "DCA"
    + df["dca_years"].astype(str)
    + "y_"
    + df["weights"].astype(str)
)

# ==========================================
# 上位戦略抽出
# 平均CAGR上位のみ表示
# ==========================================

top_strategies = (
    df.groupby("strategy")["cagr_pct"]
    .mean()
    .sort_values(ascending=False)
    .head(TOP_N_STRATEGIES)
    .index
)

plot_df = df[df["strategy"].isin(top_strategies)].copy()

# ==========================================
# 下位10% CAGR計算
# ==========================================

summary_rows = []

for strategy in top_strategies:

    sub = plot_df[plot_df["strategy"] == strategy]

    summary_rows.append({
        "strategy": strategy,

        "avg_cagr": sub["cagr_pct"].mean(),

        "median_cagr": sub["cagr_pct"].median(),

        "worst_10pct_cagr": np.percentile(
            sub["cagr_pct"],
            10
        ),

        "best_10pct_cagr": np.percentile(
            sub["cagr_pct"],
            90
        ),

        "avg_maxdd": sub["max_drawdown_pct"].mean(),

        "worst_maxdd": sub["max_drawdown_pct"].max(),
    })

summary_df = pd.DataFrame(summary_rows)

summary_df = summary_df.sort_values(
    "avg_cagr",
    ascending=False
)

# ==========================================
# 表示
# ==========================================

print("\n")
print("=" * 80)
print("Strategy Summary")
print("=" * 80)

print(summary_df.to_string(index=False))

# ==========================================
# CAGR 箱ひげ図
# ==========================================

plt.figure(figsize=(FIG_W, FIG_H))

plot_df.boxplot(
    column="cagr_pct",
    by="strategy",
    rot=90
)

plt.title("CAGR Distribution by Strategy")
plt.suptitle("")

plt.ylabel("CAGR %")

plt.tight_layout()

plt.savefig(
    "cagr_boxplot.png",
    dpi=150
)

print("\nSaved: cagr_boxplot.png")

# ==========================================
# Max Drawdown 箱ひげ図
# ==========================================

plt.figure(figsize=(FIG_W, FIG_H))

plot_df.boxplot(
    column="max_drawdown_pct",
    by="strategy",
    rot=90
)

plt.title("Max Drawdown Distribution by Strategy")
plt.suptitle("")

plt.ylabel("Max Drawdown %")

plt.tight_layout()

plt.savefig(
    "maxdd_boxplot.png",
    dpi=150
)

print("Saved: maxdd_boxplot.png")

# ==========================================
# 下位10% CAGR グラフ
# ==========================================

summary_df = summary_df.sort_values(
    "worst_10pct_cagr",
    ascending=False
)

plt.figure(figsize=(FIG_W, FIG_H))

plt.bar(
    summary_df["strategy"],
    summary_df["worst_10pct_cagr"]
)

plt.xticks(rotation=90)

plt.ylabel("Worst 10% CAGR")

plt.title("Worst 10% CAGR by Strategy")

plt.tight_layout()

plt.savefig(
    "worst10pct_cagr.png",
    dpi=150
)

print("Saved: worst10pct_cagr.png")

# ==========================================
# CSV保存
# ==========================================

summary_df.to_csv(
    "strategy_distribution_summary.csv",
    index=False
)

print("Saved: strategy_distribution_summary.csv")
