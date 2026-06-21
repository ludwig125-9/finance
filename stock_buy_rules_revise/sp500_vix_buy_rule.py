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
class PointPattern:
    name: str
    s25: int; s20: int; s15: int; s10: int
    v35: int; v30: int; v25: int; v20: int

    @property
    def max_signal_score(self) -> int:
        return self.s25 * self.v35

    def scaled_buy_signal_threshold(self, threshold: int = BUY_SIGNAL_THRESHOLD) -> int:
        if self.max_signal_score <= 0:
            return 0
        return max(1, int(round(self.max_signal_score * threshold / MAX_SIGNAL_SCORE)))


DEFAULT_POINT_PATTERN = PointPattern(
    name="S_A__V_A",
    s25=100, s20=80, s15=50, s10=30,
    v35=100, v30=80, v25=50, v20=35,
)

SP500_POINT_PATTERNS = {
    "S_A": (100, 80, 50, 30), "S_B": (60, 40, 20, 0), "S_C": (40, 25, 10, 0),
    "S_D": (30, 30, 30, 0), "S_E": (50, 30, 0, 0), "S_F": (1, 1, 1, 0),
}
VIX_POINT_PATTERNS = {
    "V_A": (100, 80, 50, 35), "V_B": (100, 80, 50, 0), "V_C": (100, 70, 30, 0),
    "V_D": (100, 50, 0, 0), "V_E": (100, 80, 0, 0),
}

def build_point_patterns() -> list[PointPattern]:
    return [
        PointPattern(f"{s_name}__{v_name}", *s_vals, *v_vals)
        for s_name, s_vals in SP500_POINT_PATTERNS.items()
        for v_name, v_vals in VIX_POINT_PATTERNS.items()
    ]

# @dataclass(frozen=True)
# class PointPattern:
#     name: str
#     s25: int
#     s20: int
#     s15: int
#     s10: int
#     v35: int
#     v30: int
#     v25: int
#     v20: int

#     @property
#     def max_signal_score(self) -> int:
#         return self.s25 * self.v35

#     def scaled_buy_signal_threshold(self, threshold: int = BUY_SIGNAL_THRESHOLD) -> int:
#         if self.max_signal_score <= 0:
#             return 0
#         return max(1, int(round(self.max_signal_score * threshold / MAX_SIGNAL_SCORE)))


# DEFAULT_POINT_PATTERN = PointPattern(
#     name="S_A__V_A",
#     s25=100,
#     s20=80,
#     s15=50,
#     s10=30,
#     v35=100,
#     v30=80,
#     v25=50,
#     v20=35,
# )

# SP500_POINT_PATTERNS = {
#     "S_A": (100, 80, 50, 30),
#     "S_B": (60, 40, 20, 0),
#     "S_C": (40, 25, 10, 0),
#     "S_D": (30, 30, 30, 0),
#     "S_E": (50, 30, 0, 0),
#     "S_F": (1, 1, 1, 0),
# }

# VIX_POINT_PATTERNS = {
#     "V_A": (100, 80, 50, 35),
#     "V_B": (100, 80, 50, 0),
#     "V_C": (100, 70, 30, 0),
#     "V_D": (100, 50, 0, 0),
#     "V_E": (100, 80, 0, 0),
# }


# def build_point_patterns() -> list[PointPattern]:
#     patterns = []
#     for s_name, s_values in SP500_POINT_PATTERNS.items():
#         for v_name, v_values in VIX_POINT_PATTERNS.items():
#             patterns.append(
#                 PointPattern(
#                     name=f"{s_name}__{v_name}",
#                     s25=s_values[0],
#                     s20=s_values[1],
#                     s15=s_values[2],
#                     s10=s_values[3],
#                     v35=v_values[0],
#                     v30=v_values[1],
#                     v25=v_values[2],
#                     v20=v_values[3],
#                 )
#             )
#     return patterns




def parse_yyyymmdd(date_text: str) -> pd.Timestamp:
    """Parse yyyymmdd text into a normalized pandas Timestamp."""
    try:
        return pd.to_datetime(date_text, format="%Y%m%d").normalize()
    except ValueError as exc:
        raise ValueError(f"日付は yyyymmdd 形式で指定してください: {date_text}") from exc


def load_daily_price_csv(csv_path: Path | str) -> pd.DataFrame:
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    required = {"Date", "Open", "High", "Low", "Close"}
    if not required.issubset(df.columns):
        raise ValueError(f"CSVに必要な列がありません: {', '.join(sorted(required - set(df.columns)))}")

    df["Date"] = pd.to_datetime(df["Date"].astype(str).str[:10])
    for col in ["Open", "High", "Low", "Close"]:
        df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", "", regex=False), errors="coerce")

    return df.dropna(subset=list(required)).sort_values("Date").reset_index(drop=True)


def get_sp500_daily_data(
    target_date: str | pd.Timestamp,
    csv_path: Path | str = DEFAULT_SP500_CSV,
) -> pd.DataFrame:
    """Return S&P 500 daily OHLC rows for the 365*x days ending at target_date."""
    target = parse_yyyymmdd(target_date) if isinstance(target_date, str) else pd.Timestamp(target_date).normalize()
    start = target - pd.Timedelta(days=365*10)
    daily = load_daily_price_csv(csv_path)
    target_daily = daily[(daily["Date"] >= start) & (daily["Date"] <= target)]
    if target_daily.empty:
        raise ValueError(f"S&P500データがありません: {start.date()} ～ {target.date()}")

    return target_daily.sort_values("Date").reset_index(drop=True)

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
    sp500_daily_data: pd.DataFrame,
    target_date: str | pd.Timestamp,
) -> tuple[float, float, pd.Timestamp]:
    """Return the highest High and the Close closest to target_date."""
    if sp500_daily_data.empty:
        raise ValueError("S&P500データが空です")

    target = parse_yyyymmdd(target_date) if isinstance(target_date, str) else pd.Timestamp(target_date).normalize()
    df = sp500_daily_data.copy()
    df["Date"] = pd.to_datetime(df["Date"]).dt.normalize()
    nearest_row = df[df["Date"] <= target].tail(1)
    if nearest_row.empty:
        nearest_index = (df["Date"] - target).abs().idxmin()
        nearest = df.loc[nearest_index]
    else:
        nearest = nearest_row.iloc[0]

    return (
        float(df["High"].max()),
        float(nearest["Close"]),
        pd.Timestamp(nearest["Date"]),
    )


def get_vix_high(vix_data: pd.DataFrame) -> tuple[float, pd.Timestamp]:
    if vix_data.empty:
        raise ValueError("VIXデータが空です")
    row = vix_data.iloc[-1]
    return float(row["High"]), pd.Timestamp(row["Date"])


def prepare_base_data(sp500_csv: Path | str, vix_csv: Path | str) -> pd.DataFrame:
    """両ファイルで重複していたベースデータ作成ロジックをここに一本化"""
    sp500 = load_daily_price_csv(sp500_csv)[["Date", "High", "Close"]].rename(
        columns={"High": "SP500_High", "Close": "SP500_Close"}
    )
    vix = load_daily_price_csv(vix_csv)[["Date", "High"]].rename(columns={"High": "VIX_High"})

    df = pd.merge(sp500, vix, on="Date", how="inner").sort_values("Date").reset_index(drop=True)
    df["SP500_1Y_High"] = df.rolling("365D", on="Date")["SP500_High"].max()
    df["SP500_Drawdown_Rate"] = (df["SP500_1Y_High"] - df["SP500_Close"]) / df["SP500_1Y_High"]
    return df

# def calculate_sp500_drawdown_point(
#     drawdown_rate: float,
#     point_pattern: PointPattern = DEFAULT_POINT_PATTERN,
# ) -> int:
#     if drawdown_rate >= 0.25:
#         return point_pattern.s25
#     if drawdown_rate >= 0.20:
#         return point_pattern.s20
#     if drawdown_rate >= 0.15:
#         return point_pattern.s15
#     if drawdown_rate >= 0.10:
#         return point_pattern.s10
#     return 0


# def calculate_vix_point(
#     vix_high: float,
#     point_pattern: PointPattern = DEFAULT_POINT_PATTERN,
# ) -> int:
#     if vix_high >= 35:
#         return point_pattern.v35
#     if vix_high >= 30:
#         return point_pattern.v30
#     if vix_high >= 25:
#         return point_pattern.v25
#     if vix_high >= 20:
#         return point_pattern.v20
#     return 0

def calculate_sp500_drawdown_point(rate: float, p: PointPattern) -> int:
    for threshold, point in [(0.25, p.s25), (0.20, p.s20), (0.15, p.s15), (0.10, p.s10)]:
        if rate >= threshold: return point
    return 0

def calculate_vix_point(vix_high: float, p: PointPattern) -> int:
    for threshold, point in [(35, p.v35), (30, p.v30), (25, p.v25), (20, p.v20)]:
        if vix_high >= threshold: return point
    return 0

@dataclass(frozen=True)
class BuySignalResult:
    target_date: pd.Timestamp; sp500_highest_high: float; sp500_nearest_close: float
    sp500_close_date: pd.Timestamp; sp500_drawdown_rate: float; sp500_drawdown_percent: float
    sp500_point: int; vix_high: float; vix_date: pd.Timestamp; vix_point: int
    signal_score: int; max_signal_score: int; buy_signal_threshold: int
    point_pattern_name: str; is_buy_signal: bool

def evaluate_buy_signal(
    target_date: str | pd.Timestamp,
    sp500_csv_path: Path | str = DEFAULT_SP500_CSV,
    vix_csv_path: Path | str = DEFAULT_VIX_CSV,
    buy_signal_threshold: int = BUY_SIGNAL_THRESHOLD,
    point_pattern: PointPattern = DEFAULT_POINT_PATTERN,
) -> BuySignalResult:
    target = pd.to_datetime(target_date, format="%Y%m%d" if isinstance(target_date, str) else None).normalize()
    base_data = prepare_base_data(sp500_csv_path, vix_csv_path)

    # 指定日以前で最も近い営業日のデータを取得
    matched_rows = base_data[base_data["Date"] <= target]
    if matched_rows.empty:
        raise ValueError(f"指定された日付以前のデータがありません: {target.date()}")
    row = matched_rows.iloc[-1]

    sp500_point = calculate_sp500_drawdown_point(row["SP500_Drawdown_Rate"], point_pattern)
    vix_point = calculate_vix_point(row["VIX_High"], point_pattern)
    scaled_threshold = point_pattern.scaled_buy_signal_threshold(buy_signal_threshold)
    signal_score = min(sp500_point * vix_point, point_pattern.max_signal_score)

    return BuySignalResult(
        target_date=target,
        sp500_highest_high=row["SP500_1Y_High"],
        sp500_nearest_close=row["SP500_Close"],
        sp500_close_date=row["Date"],
        sp500_drawdown_rate=row["SP500_Drawdown_Rate"],
        sp500_drawdown_percent=row["SP500_Drawdown_Rate"] * 100,
        sp500_point=sp500_point,
        vix_high=row["VIX_High"],
        vix_date=row["Date"],
        vix_point=vix_point,
        signal_score=signal_score,
        max_signal_score=point_pattern.max_signal_score,
        buy_signal_threshold=scaled_threshold,
        point_pattern_name=point_pattern.name,
        is_buy_signal=signal_score >= scaled_threshold,
    )

def format_result(result: BuySignalResult) -> str:
    signal_text = "BUY" if result.is_buy_signal else "NO BUY"
    return "\n".join(
        [
            f"date: {result.target_date.date()}",
            f"point_pattern: {result.point_pattern_name}",
            f"signal: {signal_text}",
            f"score: {result.signal_score} / {result.max_signal_score}",
            f"buy_signal_threshold: {result.buy_signal_threshold}",
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
