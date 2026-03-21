import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

YEARS = 30  # ★ここを変えるだけで期間を切り替え可能

def fred_csv(series_id: str) -> str:
    return f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"

SERIES = {
    "usdjpy": "EXJPUS",
    "fedfunds": "FEDFUNDS",
    "us_3m": "TB3MS",
    "us_2y": "GS2",
    "us_10y": "GS10",
    "jp_call": "IRSTCI01JPM156N",
    "jp_3m": "IR3TIB01JPM156N",
    "jp_10y": "IRLTLT01JPM156N",
}

# 1) download
dfs = []
for col, sid in SERIES.items():
    df = pd.read_csv(fred_csv(sid))
    df.columns = ["date", col]
    df["date"] = pd.to_datetime(df["date"])
    df[col] = pd.to_numeric(df[col], errors="coerce")
    dfs.append(df)

# 2) merge
data = dfs[0]
for df in dfs[1:]:
    data = data.merge(df, on="date", how="outer")
data = data.sort_values("date")

# 3) last N years
end = data["date"].max()
start = end - pd.DateOffset(years=YEARS)
dataN = data[(data["date"] >= start) & (data["date"] <= end)].copy()

# date を index にしてズレ事故を防ぐ
dataN = dataN.set_index("date")

# 4) spreads
dataN["spread_policy"]   = dataN["fedfunds"] - dataN["jp_call"]
dataN["spread_3m"]       = dataN["us_3m"] - dataN["jp_3m"]
dataN["spread_10y"]      = dataN["us_10y"] - dataN["jp_10y"]
dataN["spread_2y_proxy"] = dataN["us_2y"] - dataN["jp_call"]

print("last date:", dataN.index.max().date())
print(dataN.tail(3)[["usdjpy","spread_policy","spread_3m","spread_10y"]])

def plot_two(ax_left_series, ax_right_series, left_label, right_label, title):
    fig, ax1 = plt.subplots(figsize=(12, 6))

    lns1 = ax1.plot(dataN.index, ax_left_series, color="#1f77b4",
                    linewidth=2, label=left_label)
    ax1.set_ylabel(left_label, color="#1f77b4", fontweight='bold')
    ax1.tick_params(axis='y', labelcolor="#1f77b4")
    ax1.grid(True, which='major', linestyle='--', alpha=0.5)

    ax2 = ax1.twinx()
    lns2 = ax2.plot(dataN.index, ax_right_series, color="#ff7f0e",
                    linewidth=2, alpha=0.8, label=right_label)
    ax2.set_ylabel(right_label, color="#ff7f0e", fontweight='bold')
    ax2.tick_params(axis='y', labelcolor="#ff7f0e")

    lns = lns1 + lns2
    labs = [l.get_label() for l in lns]
    ax1.legend(lns, labs, loc='upper left', frameon=True, shadow=True)

    plt.title(title, fontsize=14, pad=20)
    fig.tight_layout()
    plt.show(block=True)

plot_two(dataN["usdjpy"], dataN["spread_policy"],
         "USDJPY (JPY per USD)", "US-JP policy spread (pp)",
         f"USDJPY vs Policy Rate Differential (last {YEARS}y)")

plot_two(dataN["usdjpy"], dataN["spread_3m"],
         "USDJPY (JPY per USD)", "US-JP 3M spread (pp)",
         f"USDJPY vs 3M Rate Differential (last {YEARS}y)")

plot_two(dataN["usdjpy"], dataN["spread_10y"],
         "USDJPY (JPY per USD)", "US-JP 10Y spread (pp)",
         f"USDJPY vs 10Y Yield Differential (last {YEARS}y)")

# 7) correlation (levels)
cols = ["usdjpy","spread_policy","spread_3m","spread_10y"]
corr_level = dataN[cols].corr(numeric_only=True)["usdjpy"].sort_values(ascending=False)
print("\nCorrelation (level) with USDJPY:\n", corr_level)

# 7b) correlation (12m changes)
chg2 = pd.DataFrame(index=dataN.index)
chg2["usdjpy_12m"] = dataN["usdjpy"].diff(12)
chg2["policy_12m"] = dataN["spread_policy"].diff(12)
chg2["3m_12m"]     = dataN["spread_3m"].diff(12)
chg2["10y_12m"]    = dataN["spread_10y"].diff(12)

corr_chg = chg2.dropna().corr(numeric_only=True)["usdjpy_12m"].sort_values(ascending=False)
print("\nCorrelation (12m change) with USDJPY 12m change:\n", corr_chg)

# Save
out_csv = f"usdjpy_spreads_last{YEARS}y.csv"
dataN.to_csv(out_csv)
print(f"\nSaved: {out_csv}")
