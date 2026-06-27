from __future__ import annotations

import argparse
import csv
from bisect import bisect_left
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from itertools import combinations_with_replacement
from pathlib import Path
from statistics import mean, median
from typing import Iterable, Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SP500_CSV = (
    REPO_ROOT / "stock_backtest_daily" / "sp500" / "sp500_daily_data.csv"
)
DEFAULT_VIX_CSV = REPO_ROOT / "stock_backtest_daily" / "vix" / "vix_daily_data.csv"
DEFAULT_YEARS = (1, 3, 10)


@dataclass(frozen=True)
class Bucket:
    index: int
    code: str
    label: str
    lower: float
    upper: Optional[float]

    def contains(self, value: float) -> bool:
        if value < self.lower:
            return False
        if self.upper is None:
            return True
        return value < self.upper


DRAWDOWN_BUCKETS = (
    Bucket(0, "dd_10_15", "10%-15%", 0.10, 0.15),
    Bucket(1, "dd_15_20", "15%-20%", 0.15, 0.20),
    Bucket(2, "dd_20_25", "20%-25%", 0.20, 0.25),
    Bucket(3, "dd_25_plus", "25%+", 0.25, None),
)

VIX_BUCKETS = (
    Bucket(0, "vix_20_25", "20-25", 20.0, 25.0),
    Bucket(1, "vix_25_30", "25-30", 25.0, 30.0),
    Bucket(2, "vix_30_35", "30-35", 30.0, 35.0),
    Bucket(3, "vix_35_plus", "35+", 35.0, None),
)

NO_BUY = len(VIX_BUCKETS)


@dataclass(frozen=True)
class PriceRow:
    date: date
    high: float
    close: float


@dataclass(frozen=True)
class DailyMarket:
    date: date
    sp500_high: float
    sp500_close: float
    vix_high: float
    sp500_1y_high: float
    drawdown_rate: float
    drawdown_bucket: Optional[Bucket]
    vix_bucket: Optional[Bucket]
    future_closes: dict[int, tuple[date, float]]
    signal_rank: SignalRank
    signal_name: SignalName

    future_indices: dict[int, int]

    def total_return(self, years: int) -> Optional[float]:
        future = self.future_closes.get(years)
        if future is None:
            return None
        return future[1] / self.sp500_close - 1


@dataclass(frozen=True)
class MonotoneRule:
    rule_id: str
    min_vix_index_by_drawdown: tuple[int, ...]

    @property
    def buy_cell_count(self) -> int:
        return sum(
            len(VIX_BUCKETS) - min_vix_index
            for min_vix_index in self.min_vix_index_by_drawdown
            if min_vix_index < NO_BUY
        )

    @property
    def description(self) -> str:
        parts = []
        for drawdown_bucket, min_vix_index in zip(
            DRAWDOWN_BUCKETS, self.min_vix_index_by_drawdown
        ):
            if min_vix_index == NO_BUY:
                continue
            vix_bucket = VIX_BUCKETS[min_vix_index]
            parts.append(
                f"drawdown {drawdown_bucket.label}: VIX >= {vix_bucket.lower:g}"
            )
        return "never buy" if not parts else " / ".join(parts)

    def matches(self, row: DailyMarket) -> bool:
        if row.drawdown_bucket is None or row.vix_bucket is None:
            return False

        min_vix_index = self.min_vix_index_by_drawdown[row.drawdown_bucket.index]
        return row.vix_bucket.index >= min_vix_index


def parse_date(value: str) -> date:
    return datetime.strptime(value[:10], "%Y-%m-%d").date()


def parse_float(value: str) -> float:
    return float(value.replace(",", ""))


def load_price_rows(csv_path: Path | str) -> list[PriceRow]:
    rows = []
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        required = {"Date", "High", "Close"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"CSV is missing columns: {', '.join(sorted(missing))}")

        for raw in reader:
            rows.append(
                PriceRow(
                    date=parse_date(raw["Date"]),
                    high=parse_float(raw["High"]),
                    close=parse_float(raw["Close"]),
                )
            )

    return sorted(rows, key=lambda row: row.date)


def find_bucket(value: float, buckets: Sequence[Bucket]) -> Optional[Bucket]:
    for bucket in buckets:
        if bucket.contains(value):
            return bucket
    return None


def add_years(day: date, years: int) -> date:
    try:
        return day.replace(year=day.year + years)
    except ValueError:
        return day.replace(year=day.year + years, month=2, day=28)


def prepare_market_data(
    sp500_csv: Path | str = DEFAULT_SP500_CSV,
    vix_csv: Path | str = DEFAULT_VIX_CSV,
    years_list: Sequence[int] = DEFAULT_YEARS,
) -> list[DailyMarket]:
    sp500_rows = load_price_rows(sp500_csv)
    vix_high_by_date = {row.date: row.high for row in load_price_rows(vix_csv)}

    merged_rows = [row for row in sp500_rows if row.date in vix_high_by_date]
    dates = [row.date for row in merged_rows]
    closes = [row.close for row in merged_rows]

    market_data = []
    for index, row in enumerate(merged_rows):
        day = row.date
        window_start = day - timedelta(days=365)
        first_window_index = bisect_left(dates, window_start)
        sp500_1y_high = max(
            previous.high for previous in merged_rows[first_window_index : index + 1]
        )
        drawdown_rate = (sp500_1y_high - row.close) / sp500_1y_high

        future_closes = {}
        future_indices = {}
        for years in years_list:
            future_index = bisect_left(dates, add_years(day, years))

            if future_index < len(merged_rows):
                future_closes[years] = (
                    dates[future_index],
                    closes[future_index],
                )

                future_indices[years] = future_index

        signal_rank, signal_name = SignalJudge.judge_values(
            drawdown_rate,
            vix_high_by_date[day],
        )
        market_data.append(
            DailyMarket(
                date=day,
                sp500_high=row.high,
                sp500_close=row.close,
                vix_high=vix_high_by_date[day],
                sp500_1y_high=sp500_1y_high,
                drawdown_rate=drawdown_rate,
                drawdown_bucket=find_bucket(drawdown_rate, DRAWDOWN_BUCKETS),
                vix_bucket=find_bucket(vix_high_by_date[day], VIX_BUCKETS),
                future_closes=future_closes,
                # ★追加
                signal_rank=signal_rank,
                signal_name=signal_name,
                # ★追加
                future_indices=future_indices,
            )
        )

    return market_data


def build_monotone_rules() -> list[MonotoneRule]:
    rules = []
    combinations = combinations_with_replacement(range(NO_BUY + 1), 4)
    for index, combination in enumerate(combinations, 1):
        min_vix_indexes = tuple(reversed(combination))
        encoded = "".join(str(value) for value in min_vix_indexes)
        rules.append(MonotoneRule(f"R{index:03d}_{encoded}", min_vix_indexes))
    return rules


def summarize_values(values: Iterable[float]) -> dict[str, Optional[float] | int]:
    collected = list(values)
    if not collected:
        return {
            "signal_count": 0,
            "total_return_avg_pct": None,
            "total_return_median_pct": None,
            "total_return_min_pct": None,
            "total_return_max_pct": None,
        }

    return {
        "signal_count": len(collected),
        "total_return_avg_pct": mean(collected) * 100,
        "total_return_median_pct": median(collected) * 100,
        "total_return_min_pct": min(collected) * 100,
        "total_return_max_pct": max(collected) * 100,
    }


def returns_for_rows(rows: Iterable[DailyMarket], years: int) -> list[float]:
    returns = []
    for row in rows:
        total_return = row.total_return(years)
        if total_return is not None:
            returns.append(total_return)
    return returns


def summarize_grid_cells(
    market_data: Sequence[DailyMarket],
    years_list: Sequence[int],
) -> list[dict[str, object]]:
    summaries = []
    for years in years_list:
        for drawdown_bucket in DRAWDOWN_BUCKETS:
            for vix_bucket in VIX_BUCKETS:
                rows = [
                    row
                    for row in market_data
                    if row.drawdown_bucket == drawdown_bucket
                    and row.vix_bucket == vix_bucket
                ]
                summaries.append(
                    {
                        "holding_years": years,
                        "drawdown_bucket": drawdown_bucket.code,
                        "drawdown_label": drawdown_bucket.label,
                        "vix_bucket": vix_bucket.code,
                        "vix_label": vix_bucket.label,
                        **summarize_values(returns_for_rows(rows, years)),
                    }
                )
    return summaries


def summarize_monotone_rules(
    market_data: Sequence[DailyMarket],
    years_list: Sequence[int],
    rules: Sequence[MonotoneRule],
) -> list[dict[str, object]]:
    summaries = []
    for rule in rules:
        matching_rows = [row for row in market_data if rule.matches(row)]
        for years in years_list:
            summaries.append(
                {
                    "holding_years": years,
                    "rule_id": rule.rule_id,
                    "buy_cell_count": rule.buy_cell_count,
                    "rule_description": rule.description,
                    **summarize_values(returns_for_rows(matching_rows, years)),
                }
            )
    return summaries


def write_csv(path: Path | str, rows: Sequence[dict[str, object]]) -> None:
    if not rows:
        return

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def percent(value: object) -> str:
    if value is None:
        return ""
    return f"{float(value):.2f}%"


def format_top_rules(
    rule_summary: Sequence[dict[str, object]],
    holding_years: int,
    top: int,
    min_signals: int,
) -> str:
    rows = [
        row
        for row in rule_summary
        if row["holding_years"] == holding_years
        and int(row["signal_count"]) >= min_signals
    ]
    rows.sort(
        key=lambda row: (
            row["total_return_min_pct"] is not None,
            row["total_return_min_pct"] or -999,
            row["total_return_median_pct"] or -999,
        ),
        reverse=True,
    )

    lines = [
        f"Top monotone rules for {holding_years}Y returns",
        "rule_id, cells, signals, avg, median, min, max, rule",
    ]
    for row in rows[:top]:
        lines.append(
            ", ".join(
                [
                    str(row["rule_id"]),
                    str(row["buy_cell_count"]),
                    str(row["signal_count"]),
                    percent(row["total_return_avg_pct"]),
                    percent(row["total_return_median_pct"]),
                    percent(row["total_return_min_pct"]),
                    percent(row["total_return_max_pct"]),
                    str(row["rule_description"]),
                ]
            )
        )
    return "\n".join(lines)


def format_cell_summary(
    cell_summary: Sequence[dict[str, object]],
    holding_years: int,
) -> str:
    rows = [row for row in cell_summary if row["holding_years"] == holding_years]
    rows.sort(
        key=lambda row: (
            str(row["drawdown_bucket"]),
            str(row["vix_bucket"]),
        )
    )

    lines = [
        f"Grid cell summary for {holding_years}Y returns",
        "drawdown, vix, signals, avg, median, min, max",
    ]
    for row in rows:
        lines.append(
            ", ".join(
                [
                    str(row["drawdown_label"]),
                    str(row["vix_label"]),
                    str(row["signal_count"]),
                    percent(row["total_return_avg_pct"]),
                    percent(row["total_return_median_pct"]),
                    percent(row["total_return_min_pct"]),
                    percent(row["total_return_max_pct"]),
                ]
            )
        )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Classify S&P500 drawdown and VIX into a 4x4 grid, then summarize "
            "all monotone buy rules over that grid."
        )
    )
    parser.add_argument("--sp500-csv", default=str(DEFAULT_SP500_CSV))
    parser.add_argument("--vix-csv", default=str(DEFAULT_VIX_CSV))
    parser.add_argument("--years", type=int, nargs="+", default=list(DEFAULT_YEARS))
    parser.add_argument("--cell-summary-csv")
    parser.add_argument("--rule-summary-csv")
    parser.add_argument("--print-year", type=int, default=3)
    parser.add_argument("--top", type=int, default=20)
    parser.add_argument("--min-signals", type=int, default=10)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    years_list = tuple(args.years)
    print_year = args.print_year if args.print_year in years_list else years_list[0]

    market_data = prepare_market_data(args.sp500_csv, args.vix_csv, years_list)
    rules = build_monotone_rules()
    cell_summary = summarize_grid_cells(market_data, years_list)
    rule_summary = summarize_monotone_rules(market_data, years_list, rules)

    print(format_cell_summary(cell_summary, print_year))
    print()
    print(format_top_rules(rule_summary, print_year, args.top, args.min_signals))

    if args.cell_summary_csv:
        write_csv(args.cell_summary_csv, cell_summary)
        print(f"cell_summary_csv: {args.cell_summary_csv}")
    if args.rule_summary_csv:
        write_csv(args.rule_summary_csv, rule_summary)
        print(f"rule_summary_csv: {args.rule_summary_csv}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
