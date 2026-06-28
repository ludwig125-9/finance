from __future__ import annotations

import argparse
import csv
import statistics
from pathlib import Path

from sp500_vix_grid_rule import (
    DEFAULT_SP500_CSV,
    DEFAULT_VIX_CSV,
    DailyMarket,
    prepare_market_data,
)

from strategy import (
    BuyStrategy,
    PortfolioSimulator,
    SimulationResult,
    create_all_strategies,
    percentile,
    signal_counts_to_string,
)

# ============================================================
# constants
# ============================================================

DEFAULT_INITIAL_CASH = 1000.0

DEFAULT_HOLDING_YEARS = (3, 10)


# ============================================================
# one simulation
# ============================================================


def simulate_one_period(
    market_data: list[DailyMarket],
    start_index: int,
    holding_years: int,
    strategy: BuyStrategy,
    initial_cash: float,
) -> SimulationResult | None:
    """
    開始日を固定した1回分のバックテスト

    Returns
    -------
    SimulationResult

        1開始日分のバックテスト結果。

    holding_years後のデータが存在しない場合は None を返す。
    """

    start_day = market_data[start_index]

    end_index = start_day.future_indices.get(holding_years)

    if end_index is None:
        return None

    simulator = PortfolioSimulator(
        strategy=strategy,
        initial_cash=initial_cash,
    )

    #
    # simulate
    #

    for market in market_data[start_index : end_index + 1]:
        simulator.process_day(market)

    final_close = market_data[end_index].sp500_close

    return simulator.build_result(final_close)


# ============================================================
# strategy simulation
# ============================================================


def simulate_strategy(
    market_data: list[DailyMarket],
    holding_years: int,
    strategy: BuyStrategy,
    initial_cash: float,
) -> list[SimulationResult]:
    """
    ある1つのBuyStrategyについて、
    全開始日でシミュレーションを実施する。
    """

    results = []

    for start_index in range(len(market_data)):

        result = simulate_one_period(
            market_data=market_data,
            start_index=start_index,
            holding_years=holding_years,
            strategy=strategy,
            initial_cash=initial_cash,
        )

        if result is not None:
            results.append(result)

    return results


# ============================================================
# aggregate
# ============================================================


def aggregate_results(
    results: list[SimulationResult],
    strategy: BuyStrategy,
    holding_years: int,
) -> dict:
    """
    全開始日の結果をCSV1行に集計する。
    """

    if not results:
        raise ValueError("results is empty")

    returns = [r.total_return * 100 for r in results]

    remain = [r.remain_pct for r in results]

    invested = [r.invested_pct for r in results]

    avg_cash = [r.average_cash_pct for r in results]

    avg_stock = [r.average_stock_pct for r in results]

    buy_count = [r.executed_buy_count for r in results]
    signal_count = [sum(r.signal_counts) for r in results]

    #
    # signal count
    #

    signal_counts = [0] * 11

    for r in results:
        for i in range(11):
            signal_counts[i] += r.signal_counts[i]

    signal_counts = [round(v / len(results)) for v in signal_counts]

    return {
        "holding_years": holding_years,
        "buy_pct_by_rank": strategy.key,
        "count_by_rank": signal_counts_to_string(signal_counts),
        "signal_count": statistics.mean(signal_count),
        "executed_buy_count": statistics.mean(buy_count),
        "invested_total_pct": statistics.mean(invested),
        "remain_pct": statistics.mean(remain),
        "average_cash_pct": statistics.mean(avg_cash),
        "average_invested_pct": statistics.mean(avg_stock),
        "total_return_avg_pct": statistics.mean(returns),
        "total_return_median_pct": statistics.median(returns),
        "total_return_5pct": percentile(returns, 0.05),
        "total_return_min_pct": min(returns),
        "total_return_max_pct": max(returns),
    }


# ============================================================
# Result Accumulator
# ============================================================


class ResultAccumulator:

    def _init_(
        self,
        strategy: BuyStrategy,
        holding_years: int,
    ):

        self.strategy = strategy
        self.holding_years = holding_years

        self.returns = []

        self.remain = []

        self.invested = []

        self.avg_cash = []

        self.avg_stock = []

        self.buy_counts = []

        self.signal_total_counts = []

        self.signal_counts = [0] * 11

        self.simulation_count = 0

    # ---------------------------------------------------------

    def add(
        self,
        result: SimulationResult,
    ) -> None:

        self.simulation_count += 1

        self.returns.append(result.total_return * 100)

        self.remain.append(result.remain_pct)

        self.invested.append(result.invested_pct)

        self.avg_cash.append(result.average_cash_pct)

        self.avg_stock.append(result.average_stock_pct)

        self.buy_counts.append(result.executed_buy_count)

        counts = result.signal_counts
        self.signal_total_counts.append(sum(counts))

        for i in range(11):
            self.signal_counts[i] += counts[i]

    # ---------------------------------------------------------

    def build(self) -> dict:

        avg_signal_counts = [
            round(v / self.simulation_count) for v in self.signal_counts
        ]

        return {
            "holding_years": self.holding_years,
            "buy_pct_by_rank": self.strategy.key,
            "count_by_rank": signal_counts_to_string(avg_signal_counts),
            "signal_count": statistics.mean(self.signal_total_counts),
            "executed_buy_count": statistics.mean(self.buy_counts),
            "invested_total_pct": statistics.mean(self.invested),
            "remain_pct": statistics.mean(self.remain),
            "average_cash_pct": statistics.mean(self.avg_cash),
            "average_invested_pct": statistics.mean(self.avg_stock),
            "total_return_avg_pct": statistics.mean(self.returns),
            "total_return_median_pct": statistics.median(self.returns),
            "total_return_5pct": percentile(self.returns, 0.05),
            "total_return_min_pct": min(self.returns),
            "total_return_max_pct": max(self.returns),
        }


# ============================================================
# Run one strategy
# ============================================================


def run_one_strategy(
    market_data: list[DailyMarket],
    strategy: BuyStrategy,
    holding_years: int,
    initial_cash: float,
) -> dict:

    accumulator = ResultAccumulator(
        strategy,
        holding_years,
    )

    for start_index in range(len(market_data)):

        result = simulate_one_period(
            market_data=market_data,
            start_index=start_index,
            holding_years=holding_years,
            strategy=strategy,
            initial_cash=initial_cash,
        )

        if result is None:
            continue

        accumulator.add(result)

    return accumulator.build()


# ============================================================
# Run all strategies
# ============================================================


def run_all_strategies(
    market_data: list[DailyMarket],
    initial_cash: float,
) -> list[dict]:
    """
    全1331戦略をバックテストし、
    CSV出力用の行を返す。
    """

    rows: list[dict] = []

    strategies = list(create_all_strategies())

    total = len(strategies) * len(DEFAULT_HOLDING_YEARS)

    current = 0

    for strategy in strategies:

        for holding_years in DEFAULT_HOLDING_YEARS:

            current += 1

            print(
                f"\rRunning {current}/{total} "
                f"(sp={strategy.sp}, "
                f"ap={strategy.ap}, "
                f"bp={strategy.bp}, "
                f"{holding_years}y)",
                end="",
                flush=True,
            )

            row = run_one_strategy(
                market_data=market_data,
                strategy=strategy,
                holding_years=holding_years,
                initial_cash=initial_cash,
            )

            rows.append(row)

    print()

    columns = [
        "holding_years",
        "buy_pct_by_rank",
        "count_by_rank",
        "signal_count",
        "executed_buy_count",
        "invested_total_pct",
        "remain_pct",
        "average_cash_pct",
        "average_invested_pct",
        "total_return_avg_pct",
        "total_return_median_pct",
        "total_return_5pct",
        "total_return_min_pct",
        "total_return_max_pct",
    ]

    return [{column: row[column] for column in columns} for row in rows]


# ============================================================
# CLI
# ============================================================


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Buy strategy backtest")

    parser.add_argument(
        "--sp500-csv",
        type=Path,
        default=DEFAULT_SP500_CSV,
        help="SP500 csv path",
    )

    parser.add_argument(
        "--vix-csv",
        type=Path,
        default=DEFAULT_VIX_CSV,
        help="VIX csv path",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path("buy_strategy_result.csv"),
        help="Output csv path",
    )

    parser.add_argument(
        "--initial-cash",
        type=float,
        default=DEFAULT_INITIAL_CASH,
        help="Initial cash",
    )

    return parser.parse_args()


# ============================================================
# main
# ============================================================


def main() -> None:

    args = parse_args()

    print("Loading market data...")

    market_data = prepare_market_data(
        sp500_csv=args.sp500_csv,
        vix_csv=args.vix_csv,
        years_list=DEFAULT_HOLDING_YEARS,
    )

    print(f"Loaded {len(market_data)} trading days")

    print("Running backtest...")

    rows = run_all_strategies(
        market_data=market_data,
        initial_cash=args.initial_cash,
    )

    print(f"Writing {args.output}")

    with args.output.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print()

    print("Finished")

    print(f"Rows: {len(rows)}")

    print(f"Output: {args.output.resolve()}")


if __name__ == "__main__":
    main()
