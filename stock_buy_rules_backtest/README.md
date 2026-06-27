# SP500 暴落時積立戦略バックテスト仕様

## 目的

SP500の下落率とVIXを用いた買いシグナルに従って待機資金を段階的に投入する戦略を、過去データを用いて検証する。

各シグナルランクごとの投入割合を総当たりで試し、

* 平均リターン
* 最悪ケース
* 投資機会
* 待機資金の残り具合

を比較し、最も効率の良い資金配分を探索する。

---

## シグナルランク

### Sランク

* s1 : Drawdown 15〜20% × VIX35+
* s2 : Drawdown 25%+ × VIX35+
* s3 : Drawdown 10〜15% × VIX35+
* s4 : Drawdown 25%+ × VIX30〜35

### Aランク

* a1 : Drawdown 20〜25% × VIX30〜35
* a2 : Drawdown 20〜25% × VIX25〜30
* a3 : Drawdown 15〜20% × VIX30〜35
* a4 : Drawdown 10〜15% × VIX30〜35

### Bランク

* b1 : Drawdown 25%+ × VIX25〜30
* b2 : Drawdown 15〜20% × VIX25〜30
* b3 : Drawdown 10〜15% × VIX25〜30

---

## 初期条件

初期待機資金

1000万円

開始日はバックテスト対象期間中の全営業日とする。

保有期間は

* 3年
* 10年

の2種類。

---

## 売買ルール

各営業日についてシグナルを判定する。

シグナルが発生した場合、

Sランクなら

sp%

Aランクなら

ap%

Bランクなら

bp%

を初期資産1000万円に対する固定割合として購入する。

例

sp=10%

なら

毎回100万円購入する。

---

## 資金不足

購入額より残金が少ない場合は、

残っている待機資金を全額投入する。

シグナルはスキップしない。

---

## 保有方法

購入したSP500は売却しない。

保有期間終了日にのみ、

その時点の評価額を計算する。

実際に売却することは想定しないが、

戦略比較のため全ポジションを終了日に評価する。

---

## 待機資金

待機資金は現金として保有する。

利息は考慮しない。

最終資産

=

株式評価額

*

残っている現金

とする。

---

## パラメータ探索

以下を全探索する。

sp

0〜10%

1%刻み

ap

0〜10%

1%刻み

bp

0〜10%

1%刻み

合計

11 × 11 × 11

=1331通り

---

## 出力

CSVとして以下を出力する。

holding_years

buy_pct_by_rank

count_by_rank

signal_count

executed_buy_count

invested_total_pct

remain_pct

average_cash_pct

average_invested_pct

total_return_avg_pct

total_return_median_pct

total_return_5pct

total_return_min_pct

total_return_max_pct

---

## count_by_rank

各シグナルが発生した回数。

例

(s1_15,s2_4,a1_18,b3_12)

---

## buy_pct_by_rank

例

(sp_10,ap_5,bp_2)

---

## invested_total_pct

保有期間終了までに投資された初期資産割合。

---

## remain_pct

保有期間終了時点で残った待機資金割合。

---

## average_cash_pct

保有期間中の平均現金比率。

---

## average_invested_pct

保有期間中の平均株式比率。

---

## total_return_xxx

開始日ごとの最終資産リターンを集計した統計値。

リターンは

(最終資産−初期資産)/初期資産

で算出する。
