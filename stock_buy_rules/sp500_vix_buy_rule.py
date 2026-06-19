from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SP500_CSV = REPO_ROOT / "stock_backtest_daily" / "sp500" / "sp500_daily_data.csv"
DEFAULT_VIX_CSV = REPO_ROOT / "stock_backtest_daily" / "vix" / "vix_daily_data.csv"

BUY_SIGNAL_THRESHOLD = 1000
MAX_SIGNAL_SCORE = 10000


@dataclass(frozen=True)
class BuySignalResult:
    target_date: pd.Timestamp
    sp500_highest_high: float
    sp500_nearest_close: float
    sp500_close_date: pd.Timestamp
    sp500_drawdown_rate: float
    sp500_drawdown_percent: float
    sp500_point: int
    vix_high: float
    vix_date: pd.Timestamp
    vix_point: int
    signal_score: int
    is_buy_signal: bool


def parse_yyyymmdd(date_text: str) -> pd.Timestamp:
    """Parse yyyymmdd text into a normalized pandas Timestamp."""
    try:
        return pd.to_datetime(date_text, format="%Y%m%d").normalize()
    except ValueError as exc:
        raise ValueError(f"日付は yyyymmdd 形式で指定してください: {date_text}") from exc


def load_daily_price_csv(csv_path: Path | str) -> pd.DataFrame:
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    required_columns = {"Date", "Open", "High", "Low", "Close"}
    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"CSVに必要な列がありません: {missing}")

    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"].astype(str).str[:10])
    for column in ["Open", "High", "Low", "Close"]:
        df[column] = pd.to_numeric(
            df[column].astype(str).str.replace(",", "", regex=False),
            errors="coerce",
        )

    return (
        df.dropna(subset=["Date", "Open", "High", "Low", "Close"])
        .sort_values("Date")
        .reset_index(drop=True)
    )


def get_sp500_last_year_monthly_data(
    target_date: str | pd.Timestamp,
    csv_path: Path | str = DEFAULT_SP500_CSV,
) -> pd.DataFrame:
    """Return S&P 500 monthly OHLC rows for the year ending at target_date."""
    target = parse_yyyymmdd(target_date) if isinstance(target_date, str) else pd.Timestamp(target_date).normalize()
    start = target - pd.DateOffset(years=1)
    daily = load_daily_price_csv(csv_path)
    target_daily = daily[(daily["Date"] >= start) & (daily["Date"] <= target)]
    if target_daily.empty:
        raise ValueError(f"S&P500データがありません: {start.date()} ～ {target.date()}")

    monthly = (
        target_daily.assign(Month=target_daily["Date"].dt.to_period("M"))
        .groupby("Month", as_index=False)
        .agg(
            Date=("Date", "max"),
            Open=("Open", "first"),
            High=("High", "max"),
            Low=("Low", "min"),
            Close=("Close", "last"),
        )
        .drop(columns=["Month"])
        .sort_values("Date")
        .reset_index(drop=True)
    )
    return monthly


def get_vix_data_for_date(
    target_date: str | pd.Timestamp,
    csv_path: Path | str = DEFAULT_VIX_CSV,
) -> pd.DataFrame:
    """Return the latest VIX daily row on or before target_date."""
    target = parse_yyyymmdd(target_date) if isinstance(target_date, str) else pd.Timestamp(target_date).normalize()
    daily = load_daily_price_csv(csv_path)
    vix_data = daily[daily["Date"] <= target].tail(1).reset_index(drop=True)
    if vix_data.empty:
        raise ValueError(f"VIXデータがありません: {target.date()} 以前")
    return vix_data


def get_sp500_high_and_nearest_close(
    sp500_monthly_data: pd.DataFrame,
    target_date: str | pd.Timestamp,
) -> tuple[float, float, pd.Timestamp]:
    """Return the highest High and the Close closest to target_date."""
    if sp500_monthly_data.empty:
        raise ValueError("S&P500データが空です")

    target = parse_yyyymmdd(target_date) if isinstance(target_date, str) else pd.Timestamp(target_date).normalize()
    df = sp500_monthly_data.copy()
    df["Date"] = pd.to_datetime(df["Date"]).dt.normalize()
    nearest_index = (df["Date"] - target).abs().idxmin()
    nearest_row = df.loc[nearest_index]

    return (
        float(df["High"].max()),
        float(nearest_row["Close"]),
        pd.Timestamp(nearest_row["Date"]),
    )


def get_vix_high(vix_data: pd.DataFrame) -> tuple[float, pd.Timestamp]:
    if vix_data.empty:
        raise ValueError("VIXデータが空です")
    row = vix_data.iloc[-1]
    return float(row["High"]), pd.Timestamp(row["Date"])


def calculate_sp500_drawdown_point(drawdown_rate: float) -> int:
    if drawdown_rate >= 0.25:
        return 100
    if drawdown_rate >= 0.20:
        return 80
    if drawdown_rate >= 0.15:
        return 50
    if drawdown_rate >= 0.10:
        return 30
    return 0


def calculate_vix_point(vix_high: float) -> int:
    if vix_high >= 35:
        return 100
    if vix_high >= 30:
        return 80
    if vix_high >= 25:
        return 50
    if vix_high >= 20:
        return 35
    return 0


def evaluate_buy_signal(
    target_date: str | pd.Timestamp,
    sp500_csv_path: Path | str = DEFAULT_SP500_CSV,
    vix_csv_path: Path | str = DEFAULT_VIX_CSV,
    buy_signal_threshold: int = BUY_SIGNAL_THRESHOLD,
) -> BuySignalResult:
    target = parse_yyyymmdd(target_date) if isinstance(target_date, str) else pd.Timestamp(target_date).normalize()

    sp500_monthly_data = get_sp500_last_year_monthly_data(target, sp500_csv_path)
    vix_data = get_vix_data_for_date(target, vix_csv_path)

    sp500_highest_high, sp500_nearest_close, sp500_close_date = get_sp500_high_and_nearest_close(
        sp500_monthly_data,
        target,
    )
    vix_high, vix_date = get_vix_high(vix_data)

    drawdown_rate = (sp500_highest_high - sp500_nearest_close) / sp500_highest_high
    sp500_point = calculate_sp500_drawdown_point(drawdown_rate)
    vix_point = calculate_vix_point(vix_high)
    signal_score = min(sp500_point * vix_point, MAX_SIGNAL_SCORE)

    return BuySignalResult(
        target_date=target,
        sp500_highest_high=sp500_highest_high,
        sp500_nearest_close=sp500_nearest_close,
        sp500_close_date=sp500_close_date,
        sp500_drawdown_rate=drawdown_rate,
        sp500_drawdown_percent=drawdown_rate * 100,
        sp500_point=sp500_point,
        vix_high=vix_high,
        vix_date=vix_date,
        vix_point=vix_point,
        signal_score=signal_score,
        is_buy_signal=signal_score >= buy_signal_threshold,
    )


def format_result(result: BuySignalResult) -> str:
    signal_text = "BUY" if result.is_buy_signal else "NO BUY"
    return "\n".join(
        [
            f"date: {result.target_date.date()}",
            f"signal: {signal_text}",
            f"score: {result.signal_score} / {MAX_SIGNAL_SCORE}",
            f"sp500_highest_high_1y: {result.sp500_highest_high:.2f}",
            f"sp500_nearest_close: {result.sp500_nearest_close:.2f} ({result.sp500_close_date.date()})",
            f"sp500_drawdown: {result.sp500_drawdown_percent:.2f}%",
            f"sp500_point: {result.sp500_point}",
            f"vix_high: {result.vix_high:.2f} ({result.vix_date.date()})",
            f"vix_point: {result.vix_point}",
        ]
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="S&P500の下落率とVIXのHighから株の買いシグナルを判定します。"
    )
    parser.add_argument("date", help="判定対象日。yyyymmdd形式。例: 20260508")
    parser.add_argument("--sp500-csv", default=str(DEFAULT_SP500_CSV), help="S&P500の日足CSV")
    parser.add_argument("--vix-csv", default=str(DEFAULT_VIX_CSV), help="VIXの日足CSV")
    parser.add_argument(
        "--threshold",
        type=int,
        default=BUY_SIGNAL_THRESHOLD,
        help="買いシグナル判定のスコア閾値",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    result = evaluate_buy_signal(
        args.date,
        sp500_csv_path=args.sp500_csv,
        vix_csv_path=args.vix_csv,
        buy_signal_threshold=args.threshold,
    )
    print(format_result(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
