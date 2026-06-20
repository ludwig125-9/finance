from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional, Sequence

import pandas as pd

try:
    from stock_buy_rules.backtest_sp500_vix_buy_rule import prepare_signal_data
    from stock_buy_rules.sp500_vix_buy_rule import (
        BUY_SIGNAL_THRESHOLD,
        DEFAULT_SP500_CSV,
        DEFAULT_VIX_CSV,
    )
except ModuleNotFoundError:
    from backtest_sp500_vix_buy_rule import prepare_signal_data
    from sp500_vix_buy_rule import (
        BUY_SIGNAL_THRESHOLD,
        DEFAULT_SP500_CSV,
        DEFAULT_VIX_CSV,
    )


def calculate_forward_returns(
    years: int,
    signal_data: pd.DataFrame,
    buy_signal_threshold: int = BUY_SIGNAL_THRESHOLD,
) -> pd.DataFrame:
    if years <= 0:
        raise ValueError("years は1以上にしてください")

    df = signal_data.sort_values("Date").reset_index(drop=True)
    buy_signals = df[df["Signal_Score"] >= buy_signal_threshold].copy()
    if buy_signals.empty:
        return pd.DataFrame()

    buy_signals["Target_Date"] = buy_signals["Date"] + pd.DateOffset(years=years)

    future_prices = df[["Date", "SP500_Close"]].rename(
        columns={"Date": "Future_Date", "SP500_Close": "Future_Close"}
    )

    returns = pd.merge_asof(
        buy_signals.sort_values("Target_Date"),
        future_prices,
        left_on="Target_Date",
        right_on="Future_Date",
        direction="forward",
    )
    returns = returns.dropna(subset=["Future_Close"]).copy()
    returns["Holding_Years"] = years
    returns["Total_Return"] = returns["Future_Close"] / returns["SP500_Close"] - 1

    return returns[
        [
            "Holding_Years",
            "Date",
            "Target_Date",
            "Future_Date",
            "Signal_Score",
            "SP500_Point",
            "VIX_Point",
            "SP500_Close",
            "Future_Close",
            "Total_Return",
        ]
    ].reset_index(drop=True)


def summarize_forward_returns(forward_returns: pd.DataFrame) -> pd.DataFrame:
    if forward_returns.empty:
        return pd.DataFrame()

    summary = (
        forward_returns.groupby(
            ["Holding_Years", "Signal_Score", "SP500_Point", "VIX_Point"],
            as_index=False,
        )
        .agg(
            signal_count=("Total_Return", "size"),
            total_return_avg=("Total_Return", "mean"),
            total_return_median=("Total_Return", "median"),
            total_return_min=("Total_Return", "min"),
            total_return_max=("Total_Return", "max"),
        )
        .rename(
            columns={
                "Holding_Years": "holding_years",
                "Signal_Score": "score",
                "SP500_Point": "sp500_point",
                "VIX_Point": "vix_point",
            }
        )
        .sort_values(["holding_years", "score", "sp500_point", "vix_point"])
        .reset_index(drop=True)
    )
    return summary


def run_forward_return_summary(
    years_list: Sequence[int],
    sp500_csv_path: Path | str = DEFAULT_SP500_CSV,
    vix_csv_path: Path | str = DEFAULT_VIX_CSV,
    buy_signal_threshold: int = BUY_SIGNAL_THRESHOLD,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    signal_data = prepare_signal_data(
        sp500_csv_path=sp500_csv_path,
        vix_csv_path=vix_csv_path,
        buy_signal_threshold=buy_signal_threshold,
    )

    forward_returns_list = [
        calculate_forward_returns(years, signal_data, buy_signal_threshold)
        for years in years_list
    ]
    forward_returns = pd.concat(forward_returns_list, ignore_index=True)
    summary = summarize_forward_returns(forward_returns)
    return summary, forward_returns


def format_summary(summary: pd.DataFrame) -> str:
    if summary.empty:
        return "forward return result is empty"

    display = summary.copy()
    for column in [
        "total_return_avg",
        "total_return_median",
        "total_return_min",
        "total_return_max",
    ]:
        display[column] = display[column].map(lambda value: f"{value * 100:.2f}%")

    return display.to_string(index=False)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="買いシグナル発生日から1年後/3年後/10年後のリターンをスコア別に集計します。"
    )
    parser.add_argument(
        "--years",
        type=int,
        nargs="+",
        default=[1, 3, 10],
        help="保有年数。複数指定できます。例: --years 1 3 10",
    )
    parser.add_argument("--sp500-csv", default=str(DEFAULT_SP500_CSV), help="S&P500の日足CSV")
    parser.add_argument("--vix-csv", default=str(DEFAULT_VIX_CSV), help="VIXの日足CSV")
    parser.add_argument(
        "--threshold",
        type=int,
        default=BUY_SIGNAL_THRESHOLD,
        help="買いシグナル判定のスコア閾値",
    )
    parser.add_argument("--output-csv", help="集計結果CSVの出力先")
    parser.add_argument("--detail-csv", help="シグナルごとのフォワードリターン明細CSVの出力先")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    summary, detail = run_forward_return_summary(
        years_list=args.years,
        sp500_csv_path=args.sp500_csv,
        vix_csv_path=args.vix_csv,
        buy_signal_threshold=args.threshold,
    )

    print(format_summary(summary))

    if args.output_csv:
        summary.to_csv(args.output_csv, index=False, encoding="utf-8-sig")
        print(f"output_csv: {args.output_csv}")
    if args.detail_csv:
        detail.to_csv(args.detail_csv, index=False, encoding="utf-8-sig")
        print(f"detail_csv: {args.detail_csv}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
