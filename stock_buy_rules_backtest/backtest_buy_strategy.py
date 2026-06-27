from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from market import (
    DEFAULT_SP500_CSV,
    DEFAULT_VIX_CSV,
    DailyMarket,
    prepare_market_data,
)

from strategy import (
    BuyStrategy,
    PortfolioSimulator,
    create_all_strategies,
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
) -> dict | None:
    """
    開始日を固定した1回分のバックテスト

    Returns
    -------
    dict

        {
            "total_return": ...,
            "remain_pct": ...,
            ...
        }

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
) -> list[dict]:
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
    results: list[dict],
    strategy: BuyStrategy,
    holding_years: int,
) -> dict:
    """
    全開始日の結果をCSV1行に集計する。
    """

    if not results:
        raise ValueError("results is empty")

    returns = [r["total_return"] * 100 for r in results]

    remain = [r["remain_pct"] for r in results]

    invested = [r["invested_pct"] for r in results]

    avg_cash = [r["average_cash_pct"] for r in results]

    avg_stock = [r["average_stock_pct"] for r in results]

    buy_count = [r["executed_buy_count"] for r in results]

    #
    # signal count
    #

    signal_counts = [0] * 11

    for r in results:
        for i in range(11):
            signal_counts[i] += r["signal_counts"][i]

    signal_counts = [round(v / len(results)) for v in signal_counts]

    return {
        "holding_years": holding_years,
        "sp": strategy.sp,
        "ap": strategy.ap,
        "bp": strategy.bp,
        "remain_pct": sum(remain) / len(remain),
        "invested_pct": sum(invested) / len(invested),
        "average_cash_pct": sum(avg_cash) / len(avg_cash),
        "average_stock_pct": sum(avg_stock) / len(avg_stock),
        "executed_buy_count": sum(buy_count) / len(buy_count),
        "total_return_avg_pct": sum(returns) / len(returns),
        "total_return_median_pct": pd.Series(returns).median(),
        "total_return_min_pct": min(returns),
        "total_return_max_pct": max(returns),
        "s1_count": signal_counts[0],
        "s2_count": signal_counts[1],
        "s3_count": signal_counts[2],
        "s4_count": signal_counts[3],
        "a1_count": signal_counts[4],
        "a2_count": signal_counts[5],
        "a3_count": signal_counts[6],
        "a4_count": signal_counts[7],
        "b1_count": signal_counts[8],
        "b2_count": signal_counts[9],
        "b3_count": signal_counts[10],
    }


import statistics

# ============================================================
# Result Accumulator
# ============================================================


class ResultAccumulator:

    def __init__(
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

        self.signal_counts = [0] * 11

        self.simulation_count = 0

    # ---------------------------------------------------------

    def add(
        self,
        result: dict,
    ) -> None:

        self.simulation_count += 1

        self.returns.append(result["total_return"] * 100)

        self.remain.append(result["remain_pct"])

        self.invested.append(result["invested_pct"])

        self.avg_cash.append(result["average_cash_pct"])

        self.avg_stock.append(result["average_stock_pct"])

        self.buy_counts.append(result["executed_buy_count"])

        counts = result["signal_counts"]

        for i in range(11):
            self.signal_counts[i] += counts[i]

    # ---------------------------------------------------------

    def build(self) -> dict:

        avg_signal_counts = [
            round(v / self.simulation_count) for v in self.signal_counts
        ]

        return {
            "holding_years": self.holding_years,
            "sp": self.strategy.sp,
            "ap": self.strategy.ap,
            "bp": self.strategy.bp,
            "remain_pct": statistics.mean(self.remain),
            "invested_pct": statistics.mean(self.invested),
            "average_cash_pct": statistics.mean(self.avg_cash),
            "average_stock_pct": statistics.mean(self.avg_stock),
            "executed_buy_count": statistics.mean(self.buy_counts),
            "total_return_avg_pct": statistics.mean(self.returns),
            "total_return_median_pct": statistics.median(self.returns),
            "total_return_min_pct": min(self.returns),
            "total_return_max_pct": max(self.returns),
            "s1_count": avg_signal_counts[0],
            "s2_count": avg_signal_counts[1],
            "s3_count": avg_signal_counts[2],
            "s4_count": avg_signal_counts[3],
            "a1_count": avg_signal_counts[4],
            "a2_count": avg_signal_counts[5],
            "a3_count": avg_signal_counts[6],
            "a4_count": avg_signal_counts[7],
            "b1_count": avg_signal_counts[8],
            "b2_count": avg_signal_counts[9],
            "b3_count": avg_signal_counts[10],
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
) -> pd.DataFrame:
    """
    全1331戦略をバックテストし、
    DataFrame を返す。
    """

    rows: list[dict] = []

    strategies = create_all_strategies()

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

    df = pd.DataFrame(rows)

    #
    # 並び順を固定
    #

    columns = [
        "holding_years",
        "sp",
        "ap",
        "bp",
        "remain_pct",
        "invested_pct",
        "average_cash_pct",
        "average_stock_pct",
        "executed_buy_count",
        "total_return_avg_pct",
        "total_return_median_pct",
        "total_return_min_pct",
        "total_return_max_pct",
        "s1_count",
        "s2_count",
        "s3_count",
        "s4_count",
        "a1_count",
        "a2_count",
        "a3_count",
        "a4_count",
        "b1_count",
        "b2_count",
        "b3_count",
    ]

    return df[columns]


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

    df = run_all_strategies(
        market_data=market_data,
        initial_cash=args.initial_cash,
    )

    print(f"Writing {args.output}")

    df.to_csv(
        args.output,
        index=False,
        float_format="%.6f",
    )

    print()

    print("Finished")

    print(f"Rows: {len(df)}")

    print(f"Output: {args.output.resolve()}")


if __name__ == "__main__":
    main()
