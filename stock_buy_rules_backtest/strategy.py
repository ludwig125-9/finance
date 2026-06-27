from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

# ============================================================
# Signal
# ============================================================


class Signal(Enum):
    """
    Buy signal.

    value:
        (rank, index)

    rank:
        S / A / B / NONE

    index:
        signal_counts のインデックス
    """

    NONE = ("NONE", -1)

    S1 = ("S", 0)
    S2 = ("S", 1)
    S3 = ("S", 2)
    S4 = ("S", 3)

    A1 = ("A", 4)
    A2 = ("A", 5)
    A3 = ("A", 6)
    A4 = ("A", 7)

    B1 = ("B", 8)
    B2 = ("B", 9)
    B3 = ("B", 10)

    def __init__(self, rank: str, index: int):
        self.rank = rank
        self.index = index

    @property
    def is_buy_signal(self) -> bool:
        return self != Signal.NONE

    # @property
    # def is_s(self) -> bool:
    #     return self.rank == "S"

    # @property
    # def is_a(self) -> bool:
    #     return self.rank == "A"

    # @property
    # def is_b(self) -> bool:
    #     return self.rank == "B"

    @property
    def label(self) -> str:
        return self.name.lower()

    @property
    def rank_label(self) -> str:
        return self.rank


# ============================================================
# Buy Strategy
# ============================================================


@dataclass(frozen=True, slots=True)
class BuyStrategy:
    """
    Parameters
    ----------
    sp
        Sランクシグナル発生時に投入する割合（初期資産比 %）

    ap
        Aランクシグナル発生時に投入する割合（初期資産比 %）

    bp
        Bランクシグナル発生時に投入する割合（初期資産比 %）

    Example
    -------
    BuyStrategy(
        sp=10,
        ap=5,
        bp=2,
    )

    初期資産1000万円なら

    S →100万円

    A →50万円

    B →20万円
    """

    sp: int
    ap: int
    bp: int

    def buy_ratio(self, signal: Signal) -> float:
        """
        Returns
        -------
        float

        購入割合 (0.0〜1.0)
        """

        if signal.is_s:
            return self.sp / 100.0

        if signal.is_a:
            return self.ap / 100.0

        if signal.is_b:
            return self.bp / 100.0

        return 0.0

    # def planned_buy_amount(
    #     self,
    #     signal: Signal,
    #     initial_cash: float,
    # ) -> float:
    #     """
    #     シグナル発生時に購入したい金額
    #     （残高不足は考慮しない）
    #     """

    #     return initial_cash * self.buy_ratio(signal)

    # def actual_buy_amount(
    #     self,
    #     signal: Signal,
    #     initial_cash: float,
    #     remain_cash: float,
    # ) -> float:
    #     """
    #     実際に購入する金額。

    #     残金が不足している場合は残金を全額投入する。
    #     """

    #     return min(
    #         self.planned_buy_amount(signal, initial_cash),
    #         remain_cash,
    #     )
    def buy_amount(
        self,
        signal: Signal,
        initial_cash: float,
        remain_cash: float,
    ) -> float:

        ratio = self.buy_ratio(signal)

        return min(
            initial_cash * ratio,
            remain_cash,
        )

    @property
    def key(self) -> str:
        """
        CSV出力用の戦略キー
        """

        return f"(sp_{self.sp},ap_{self.ap},bp_{self.bp})"

    def __str__(self) -> str:
        return self.key

    __repr__ = __str__


# ============================================================
# Utility
# ============================================================


# def create_all_strategies() -> list[BuyStrategy]:
#     """
#     sp, ap, bp を 0〜10% (1%刻み) の全組み合わせで生成する。

#     Returns
#     -------
#     list[BuyStrategy]

#     11 × 11 × 11 = 1331 パターン
#     """

#     return [
#         BuyStrategy(sp, ap, bp)
#         for sp in range(11)
#         for ap in range(11)
#         for bp in range(11)
#     ]
from collections.abc import Iterator


def create_all_strategies() -> Iterator[BuyStrategy]:

    for sp in range(11):
        for ap in range(11):
            for bp in range(11):
                yield BuyStrategy(sp, ap, bp)


# ============================================================
# Signal Judge
# ============================================================


class SignalJudge:
    """
    Drawdown率とVIXから買いシグナルを判定する。

    Drawdownは割合で指定する。

    例
        0.15 = 15%
        0.25 = 25%

    VIXは実数値。
    """

    @staticmethod
    def judge_values(
        drawdown_rate: float,
        vix_high: float,
    ) -> Signal:

        d = drawdown_rate
        v = vix_high

        #
        # ===========================
        # S Rank
        # ===========================
        #

        # s1 : 15〜20 × 35+
        if 0.15 <= d < 0.20 and v >= 35:
            return Signal.S1

        # s2 : 25+ × 35+
        if d >= 0.25 and v >= 35:
            return Signal.S2

        # s3 : 10〜15 × 35+
        if 0.10 <= d < 0.15 and v >= 35:
            return Signal.S3

        # s4 : 25+ × 30〜35
        if d >= 0.25 and 30 <= v < 35:
            return Signal.S4

        #
        # ===========================
        # A Rank
        # ===========================
        #

        # a1 : 20〜25 × 30〜35
        if 0.20 <= d < 0.25 and 30 <= v < 35:
            return Signal.A1

        # a2 : 20〜25 × 25〜30
        if 0.20 <= d < 0.25 and 25 <= v < 30:
            return Signal.A2

        # a3 : 15〜20 × 30〜35
        if 0.15 <= d < 0.20 and 30 <= v < 35:
            return Signal.A3

        # a4 : 10〜15 × 30〜35
        if 0.10 <= d < 0.15 and 30 <= v < 35:
            return Signal.A4

        #
        # ===========================
        # B Rank
        # ===========================
        #

        # b1 : 25+ × 25〜30
        if d >= 0.25 and 25 <= v < 30:
            return Signal.B1

        # b2 : 15〜20 × 25〜30
        if 0.15 <= d < 0.20 and 25 <= v < 30:
            return Signal.B2

        # b3 : 10〜15 × 25〜30
        if 0.10 <= d < 0.15 and 25 <= v < 30:
            return Signal.B3

        return Signal.NONE


from dataclasses import dataclass

# ============================================================
# Simulation Result
# ============================================================


@dataclass(slots=True)
class SimulationResult:
    """
    1回のバックテスト結果
    """

    final_asset: float

    total_return: float

    remain_pct: float

    invested_pct: float

    average_cash_pct: float

    average_stock_pct: float

    executed_buy_count: int

    signal_counts: list[int]


# ============================================================
# Portfolio Simulator
# ============================================================


class PortfolioSimulator:

    def __init__(
        self,
        strategy: BuyStrategy,
        initial_cash: float = 1000.0,
    ):

        self.strategy = strategy

        self.initial_cash = initial_cash

        self.cash = initial_cash

        self.shares = 0.0

        self.executed_buy_count = 0

        #
        # signal count
        #

        self.signal_counts = [0] * 11

        #
        # average allocation
        #

        self.cash_ratio_sum = 0.0

        self.stock_ratio_sum = 0.0

        self.day_count = 0

    # ---------------------------------------------------------

    def process_day(
        self,
        market: DailyMarket,
    ) -> None:

        signal = market.signal

        #
        # signal count
        #

        if signal.is_buy_signal:
            self.signal_counts[signal.index] += 1

        #
        # buy
        #

        # buy_amount = self.strategy.actual_buy_amount(
        #     signal,
        #     self.initial_cash,
        #     self.cash,
        # )
        buy_amount = self.strategy.buy_amount(
            signal,
            self.initial_cash,
            self.cash,
        )

        if buy_amount > 0:

            self.cash -= buy_amount

            self.shares += buy_amount / market.sp500_close

            self.executed_buy_count += 1

        #
        # allocation
        #

        self._record_allocation(
            market.sp500_close,
        )

    # ---------------------------------------------------------

    def _record_allocation(
        self,
        close: float,
    ) -> None:

        stock_value = self.shares * close

        total_asset = stock_value + self.cash

        if total_asset <= 0:
            return

        self.cash_ratio_sum += self.cash / total_asset

        self.stock_ratio_sum += stock_value / total_asset

        self.day_count += 1

    # ---------------------------------------------------------

    def build_result(
        self,
        final_close: float,
    ) -> SimulationResult:

        stock_value = self.shares * final_close

        final_asset = stock_value + self.cash

        total_return = final_asset / self.initial_cash - 1.0

        remain_pct = self.cash / self.initial_cash * 100

        invested_pct = (self.initial_cash - self.cash) / self.initial_cash * 100

        if self.day_count:

            avg_cash = self.cash_ratio_sum / self.day_count * 100

            avg_stock = self.stock_ratio_sum / self.day_count * 100

        else:

            avg_cash = 0.0

            avg_stock = 0.0

        return SimulationResult(
            final_asset=final_asset,
            total_return=total_return,
            remain_pct=remain_pct,
            invested_pct=invested_pct,
            average_cash_pct=avg_cash,
            average_stock_pct=avg_stock,
            executed_buy_count=self.executed_buy_count,
            signal_counts=self.signal_counts.copy(),
        )


from statistics import mean, median
from typing import Iterable

# ============================================================
# Utility
# ============================================================


SIGNAL_ORDER = [
    Signal.S1,
    Signal.S2,
    Signal.S3,
    Signal.S4,
    Signal.A1,
    Signal.A2,
    Signal.A3,
    Signal.A4,
    Signal.B1,
    Signal.B2,
    Signal.B3,
]


def signal_counts_to_string(signal_counts: list[int]) -> str:
    """
    signal_counts を

    (s1_5,s2_3,...)

    の形式へ変換する。
    """

    parts = []

    for signal in SIGNAL_ORDER:
        parts.append(f"{signal.label}_{signal_counts[signal.index]}")

    return "(" + ",".join(parts) + ")"


def summarize_results(
    results: Iterable[SimulationResult],
    strategy: BuyStrategy,
    holding_years: int,
) -> dict:
    """
    CSVへ1行出力するための集計を行う。
    """

    results = list(results)

    if not results:
        raise ValueError("results is empty")

    returns = [r.total_return * 100 for r in results]

    remain = [r.remain_pct for r in results]

    invested = [r.invested_pct for r in results]

    avg_cash = [r.average_cash_pct for r in results]

    avg_stock = [r.average_stock_pct for r in results]

    buy_counts = [r.executed_buy_count for r in results]

    #
    # signal count
    #

    signal_counts = [0] * 11

    for r in results:

        for i in range(11):
            signal_counts[i] += r.signal_counts[i]

    signal_counts = [round(x / len(results)) for x in signal_counts]

    return {
        "holding_years": holding_years,
        "count_by_rank": signal_counts_to_string(signal_counts),
        "buy_pct_by_rank": strategy.key,
        "remain_pct": mean(remain),
        "invested_pct": mean(invested),
        "average_cash_pct": mean(avg_cash),
        "average_stock_pct": mean(avg_stock),
        "executed_buy_count": mean(buy_counts),
        "total_return_avg_pct": mean(returns),
        "total_return_median_pct": median(returns),
        "total_return_min_pct": min(returns),
        "total_return_max_pct": max(returns),
    }
