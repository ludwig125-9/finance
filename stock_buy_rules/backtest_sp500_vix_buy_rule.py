from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

import pandas as pd

try:
    from stock_buy_rules.sp500_vix_buy_rule import (
        BUY_SIGNAL_THRESHOLD,
        DEFAULT_SP500_CSV,
        DEFAULT_VIX_CSV,
        MAX_SIGNAL_SCORE,
        calculate_sp500_drawdown_point,
        calculate_vix_point,
        load_daily_price_csv,
        parse_yyyymmdd,
    )
except ModuleNotFoundError:
    from sp500_vix_buy_rule import (
        BUY_SIGNAL_THRESHOLD,
        DEFAULT_SP500_CSV,
        DEFAULT_VIX_CSV,
        MAX_SIGNAL_SCORE,
        calculate_sp500_drawdown_point,
        calculate_vix_point,
        load_daily_price_csv,
        parse_yyyymmdd,
    )


@dataclass(frozen=True)
class BacktestResult:
    start_date: pd.Timestamp
    end_date: pd.Timestamp
    years: float
    trading_days: int
    buy_count: int
    total_invested: float
    final_value: float
    profit: float
    total_return: float
    cagr: float
    max_drawdown: float
    average_buy_score: float
    max_signal_score: int
    final_close: float
    lump_sum_return: float
    daily_dca_return: float


def _normalize_date(date_value: str | pd.Timestamp) -> pd.Timestamp:
    if isinstance(date_value, str):
        return parse_yyyymmdd(date_value)
    return pd.Timestamp(date_value).normalize()


def prepare_signal_data(
    sp500_csv_path: Path | str = DEFAULT_SP500_CSV,
    vix_csv_path: Path | str = DEFAULT_VIX_CSV,
    buy_signal_threshold: int = BUY_SIGNAL_THRESHOLD,
) -> pd.DataFrame:
    sp500 = load_daily_price_csv(sp500_csv_path)
    vix = load_daily_price_csv(vix_csv_path)

    sp500 = sp500[["Date", "High", "Close"]].rename(
        columns={"High": "SP500_High", "Close": "SP500_Close"}
    )
    vix = vix[["Date", "High"]].rename(columns={"High": "VIX_High"})

    df = sp500.merge(vix, on="Date", how="inner").sort_values("Date").reset_index(drop=True)
    df["SP500_1Y_High"] = df.rolling("365D", on="Date")["SP500_High"].max()
    df["SP500_Drawdown_Rate"] = (
        df["SP500_1Y_High"] - df["SP500_Close"]
    ) / df["SP500_1Y_High"]
    df["SP500_Point"] = df["SP500_Drawdown_Rate"].map(calculate_sp500_drawdown_point)
    df["VIX_Point"] = df["VIX_High"].map(calculate_vix_point)
    df["Signal_Score"] = (df["SP500_Point"] * df["VIX_Point"]).clip(upper=MAX_SIGNAL_SCORE)
    df["Buy_Amount"] = df["Signal_Score"].where(
        df["Signal_Score"] >= buy_signal_threshold,
        0,
    )
    return df


def calculate_max_drawdown(values: pd.Series) -> float:
    if values.empty or values.max() <= 0:
        return 0.0
    running_max = values.cummax()
    drawdowns = values / running_max - 1
    return float(drawdowns.min())


def run_backtest(
    start_date: str | pd.Timestamp,
    end_date: str | pd.Timestamp,
    signal_data: Optional[pd.DataFrame] = None,
    sp500_csv_path: Path | str = DEFAULT_SP500_CSV,
    vix_csv_path: Path | str = DEFAULT_VIX_CSV,
    buy_signal_threshold: int = BUY_SIGNAL_THRESHOLD,
) -> tuple[BacktestResult, pd.DataFrame]:
    start = _normalize_date(start_date)
    end = _normalize_date(end_date)
    if start >= end:
        raise ValueError("start_date は end_date より前にしてください")

    df = signal_data
    if df is None:
        df = prepare_signal_data(sp500_csv_path, vix_csv_path, buy_signal_threshold)

    period = df[(df["Date"] >= start) & (df["Date"] <= end)].copy().reset_index(drop=True)
    if period.empty:
        raise ValueError(f"対象期間のデータがありません: {start.date()} ～ {end.date()}")

    period["Units_Bought"] = period["Buy_Amount"] / period["SP500_Close"]
    period["Total_Units"] = period["Units_Bought"].cumsum()
    period["Total_Invested"] = period["Buy_Amount"].cumsum()
    period["Portfolio_Value"] = period["Total_Units"] * period["SP500_Close"]
    period["Profit"] = period["Portfolio_Value"] - period["Total_Invested"]
    period["Return"] = period["Portfolio_Value"] / period["Total_Invested"].replace(0, pd.NA) - 1

    total_invested = float(period["Total_Invested"].iloc[-1])
    final_value = float(period["Portfolio_Value"].iloc[-1])
    profit = final_value - total_invested
    total_return = final_value / total_invested - 1 if total_invested > 0 else 0.0
    years = max((period["Date"].iloc[-1] - period["Date"].iloc[0]).days / 365.25, 0.0)
    cagr = (final_value / total_invested) ** (1 / years) - 1 if total_invested > 0 and years > 0 else 0.0
    max_drawdown = calculate_max_drawdown(period["Portfolio_Value"])

    buy_days = period[period["Buy_Amount"] > 0]
    average_buy_score = float(buy_days["Signal_Score"].mean()) if not buy_days.empty else 0.0
    max_signal_score = int(period["Signal_Score"].max()) if not period.empty else 0

    start_close = float(period["SP500_Close"].iloc[0])
    final_close = float(period["SP500_Close"].iloc[-1])
    lump_sum_return = final_close / start_close - 1

    daily_dca_amount = total_invested / len(period) if len(period) > 0 else 0.0
    daily_dca_units = (daily_dca_amount / period["SP500_Close"]).sum() if daily_dca_amount > 0 else 0.0
    daily_dca_value = daily_dca_units * final_close
    daily_dca_return = daily_dca_value / total_invested - 1 if total_invested > 0 else 0.0

    result = BacktestResult(
        start_date=period["Date"].iloc[0],
        end_date=period["Date"].iloc[-1],
        years=years,
        trading_days=len(period),
        buy_count=int((period["Buy_Amount"] > 0).sum()),
        total_invested=total_invested,
        final_value=final_value,
        profit=profit,
        total_return=total_return,
        cagr=cagr,
        max_drawdown=max_drawdown,
        average_buy_score=average_buy_score,
        max_signal_score=max_signal_score,
        final_close=final_close,
        lump_sum_return=lump_sum_return,
        daily_dca_return=daily_dca_return,
    )
    return result, period


def run_rolling_backtest(
    years: int,
    signal_data: Optional[pd.DataFrame] = None,
    sp500_csv_path: Path | str = DEFAULT_SP500_CSV,
    vix_csv_path: Path | str = DEFAULT_VIX_CSV,
    buy_signal_threshold: int = BUY_SIGNAL_THRESHOLD,
    step_months: int = 1,
) -> pd.DataFrame:
    if years <= 0:
        raise ValueError("years は1以上にしてください")
    if step_months <= 0:
        raise ValueError("step_months は1以上にしてください")

    df = signal_data
    if df is None:
        df = prepare_signal_data(sp500_csv_path, vix_csv_path, buy_signal_threshold)

    first_date = df["Date"].min()
    last_date = df["Date"].max()
    starts = pd.date_range(first_date, last_date - pd.DateOffset(years=years), freq=f"{step_months}MS")

    rows = []
    for start in starts:
        end = start + pd.DateOffset(years=years)
        try:
            result, _ = run_backtest(
                start,
                end,
                signal_data=df,
                buy_signal_threshold=buy_signal_threshold,
            )
        except ValueError:
            continue
        rows.append(backtest_result_to_dict(result))

    return pd.DataFrame(rows)


def backtest_result_to_dict(result: BacktestResult) -> dict[str, float | int | str]:
    return {
        "start_date": result.start_date.date().isoformat(),
        "end_date": result.end_date.date().isoformat(),
        "years": result.years,
        "trading_days": result.trading_days,
        "buy_count": result.buy_count,
        "total_invested": result.total_invested,
        "final_value": result.final_value,
        "profit": result.profit,
        "total_return": result.total_return,
        "cagr": result.cagr,
        "max_drawdown": result.max_drawdown,
        "average_buy_score": result.average_buy_score,
        "max_signal_score": result.max_signal_score,
        "final_close": result.final_close,
        "lump_sum_return": result.lump_sum_return,
        "daily_dca_return": result.daily_dca_return,
    }


def format_percent(value: float) -> str:
    return f"{value * 100:.2f}%"


def format_backtest_result(result: BacktestResult) -> str:
    return "\n".join(
        [
            f"period: {result.start_date.date()} -> {result.end_date.date()} ({result.years:.2f} years)",
            f"trading_days: {result.trading_days}",
            f"buy_count: {result.buy_count}",
            f"total_invested: {result.total_invested:.2f}",
            f"final_value: {result.final_value:.2f}",
            f"profit: {result.profit:.2f}",
            f"total_return: {format_percent(result.total_return)}",
            f"cagr: {format_percent(result.cagr)}",
            f"max_drawdown: {format_percent(result.max_drawdown)}",
            f"average_buy_score: {result.average_buy_score:.2f}",
            f"max_signal_score: {result.max_signal_score}",
            f"lump_sum_return: {format_percent(result.lump_sum_return)}",
            f"daily_dca_return_same_total_invested: {format_percent(result.daily_dca_return)}",
        ]
    )


def summarize_rolling_results(results: pd.DataFrame) -> str:
    if results.empty:
        return "rolling result is empty"

    lines = [f"rolling_cases: {len(results)}"]
    for column in ["total_return", "cagr", "max_drawdown", "lump_sum_return", "daily_dca_return"]:
        series = results[column]
        lines.extend(
            [
                f"{column}_avg: {format_percent(float(series.mean()))}",
                f"{column}_median: {format_percent(float(series.median()))}",
                f"{column}_min: {format_percent(float(series.min()))}",
                f"{column}_max: {format_percent(float(series.max()))}",
            ]
        )
    lines.append(f"buy_count_avg: {results['buy_count'].mean():.2f}")
    lines.append(f"total_invested_avg: {results['total_invested'].mean():.2f}")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="S&P500/VIX買いルールのバックテストを実行します。"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    single = subparsers.add_parser("single", help="指定した開始日と終了日の成績を計算")
    single.add_argument("--start", required=True, help="開始日。yyyymmdd形式。例: 20150101")
    single.add_argument("--end", required=True, help="終了日。yyyymmdd形式。例: 20250101")
    single.add_argument("--detail-csv", help="日次明細CSVの出力先")

    rolling = subparsers.add_parser("rolling", help="1年/3年/10年などのローリング成績を計算")
    rolling.add_argument("--years", type=int, required=True, help="検証年数。例: 1, 3, 10")
    rolling.add_argument("--step-months", type=int, default=1, help="開始日をずらす月数")
    rolling.add_argument("--output-csv", help="ローリング結果CSVの出力先")

    for subparser in [single, rolling]:
        subparser.add_argument("--sp500-csv", default=str(DEFAULT_SP500_CSV), help="S&P500の日足CSV")
        subparser.add_argument("--vix-csv", default=str(DEFAULT_VIX_CSV), help="VIXの日足CSV")
        subparser.add_argument(
            "--threshold",
            type=int,
            default=BUY_SIGNAL_THRESHOLD,
            help="買いシグナル判定のスコア閾値",
        )

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    signal_data = prepare_signal_data(args.sp500_csv, args.vix_csv, args.threshold)

    if args.command == "single":
        result, detail = run_backtest(
            args.start,
            args.end,
            signal_data=signal_data,
            buy_signal_threshold=args.threshold,
        )
        print(format_backtest_result(result))
        if args.detail_csv:
            detail.to_csv(args.detail_csv, index=False, encoding="utf-8-sig")
            print(f"detail_csv: {args.detail_csv}")
        return 0

    if args.command == "rolling":
        results = run_rolling_backtest(
            args.years,
            signal_data=signal_data,
            buy_signal_threshold=args.threshold,
            step_months=args.step_months,
        )
        print(summarize_rolling_results(results))
        if args.output_csv:
            results.to_csv(args.output_csv, index=False, encoding="utf-8-sig")
            print(f"output_csv: {args.output_csv}")
        return 0

    raise ValueError(f"unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
