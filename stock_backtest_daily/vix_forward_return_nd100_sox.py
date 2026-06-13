from pathlib import Path

import numpy as np
import pandas as pd


# =========================
# Files
# =========================

BASE_DIR = Path(__file__).resolve().parent

NQ100_FILE = BASE_DIR / "nasdaq100" / "nq100_daily_yen.csv"
SOX_FILE = BASE_DIR / "sox" / "sox_daily_yen.csv"
VIX_FILE = BASE_DIR / "vix" / "vix_daily_data.csv"

OUTPUT_FILE = BASE_DIR / "vix_forward_return_nd100_sox.csv"
DETAIL_OUTPUT_FILE = BASE_DIR / "vix_forward_return_nd100_sox_detail.csv"


# =========================
# Parameters
# =========================

VIX_THRESHOLDS = [25, 30, 35]
HOLDING_YEARS = [1, 3]

BUY_TARGET_RATIOS = [
    ("NQ100", 1.0, 0.0),
    ("SOX", 0.0, 1.0),
    ("NQ100_70_SOX_30", 0.7, 0.3),
    ("NQ100_50_SOX_50", 0.5, 0.5),
    ("NQ100_30_SOX_70", 0.3, 0.7),
]

# 1年後/2年後が休場日の場合は、その日以前の直近営業日で評価する。
# 直近営業日が評価日からこの日数より離れている場合はデータ不足として除外。
MAX_EVALUATION_GAP_DAYS = 7


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


def load_data():
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

    return (
        nq100
        .merge(sox, on="Date", how="inner")
        .merge(vix[["Date", "VIX"]], on="Date", how="inner")
        .sort_values("Date")
        .reset_index(drop=True)
    )


# =========================
# Simulation
# =========================

def find_evaluation_index(df, buy_date, holding_years):
    target_date = buy_date + pd.DateOffset(years=holding_years)
    candidates = df.index[df["Date"] <= target_date]

    if len(candidates) == 0:
        return None

    eval_idx = candidates[-1]
    eval_date = df.loc[eval_idx, "Date"]

    if eval_date < target_date - pd.Timedelta(days=MAX_EVALUATION_GAP_DAYS):
        return None

    return eval_idx


def calc_forward_return(row, eval_row, nq100_ratio, sox_ratio):
    nq100_growth = eval_row["NQ100"] / row["NQ100"]
    sox_growth = eval_row["SOX"] / row["SOX"]

    portfolio_growth = (
        nq100_ratio * nq100_growth
        + sox_ratio * sox_growth
    )

    return (portfolio_growth - 1) * 100


def summarize(values):
    return {
        "max_return_pct": np.max(values),
        "average_return_pct": np.mean(values),
        "min_return_pct": np.min(values),
    }


def main():
    df = load_data()

    print(f"営業日数: {len(df)}")
    print(f"期間: {df['Date'].iloc[0].date()} ～ {df['Date'].iloc[-1].date()}")
    print()

    summary_results = []
    detail_results = []

    for vix_threshold in VIX_THRESHOLDS:
        trigger_df = df[df["VIX"] >= vix_threshold]

        for holding_years in HOLDING_YEARS:
            for target_name, nq100_ratio, sox_ratio in BUY_TARGET_RATIOS:
                returns = []

                for buy_idx, row in trigger_df.iterrows():
                    eval_idx = find_evaluation_index(
                        df,
                        row["Date"],
                        holding_years,
                    )

                    if eval_idx is None:
                        continue

                    eval_row = df.loc[eval_idx]
                    return_pct = calc_forward_return(
                        row,
                        eval_row,
                        nq100_ratio,
                        sox_ratio,
                    )

                    returns.append(return_pct)
                    detail_results.append({
                        "vix_threshold": vix_threshold,
                        "vix_at_buy": row["VIX"],
                        "holding_years": holding_years,
                        "target": target_name,
                        "buy_date": row["Date"].date(),
                        "eval_date": eval_row["Date"].date(),
                        "buy_nq100": row["NQ100"],
                        "eval_nq100": eval_row["NQ100"],
                        "buy_sox": row["SOX"],
                        "eval_sox": eval_row["SOX"],
                        "return_pct": return_pct,
                    })

                if len(returns) == 0:
                    continue

                result = {
                    "vix_threshold": vix_threshold,
                    "holding_years": holding_years,
                    "target": target_name,
                    "nq100_ratio": nq100_ratio,
                    "sox_ratio": sox_ratio,
                    "trigger_count": len(trigger_df),
                    "evaluated_count": len(returns),
                }
                result.update(summarize(returns))
                summary_results.append(result)

    summary_df = pd.DataFrame(summary_results)
    detail_df = pd.DataFrame(detail_results)

    summary_df = summary_df.sort_values(
        ["holding_years", "vix_threshold", "target"]
    )

    print("==============================================")
    print("VIX Trigger Forward Returns")
    print("==============================================")
    print(summary_df.to_string(index=False))

    summary_df.to_csv(OUTPUT_FILE, index=False)
    detail_df.to_csv(DETAIL_OUTPUT_FILE, index=False)

    print()
    print(f"Saved: {OUTPUT_FILE}")
    print(f"Saved: {DETAIL_OUTPUT_FILE}")


if __name__ == "__main__":
    main()
