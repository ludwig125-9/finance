# stock_buy_rules_revise2

`stock_buy_rules_revise` のポイント表ベースの実験を、条件セルベースに作り直した版です。

この版では、S&P500の直近1年高値からの下落率とVIXをそれぞれ4段階に分け、合計16個の市場状態セルを作ります。

```text
S&P500 drawdown: 10%-15%, 15%-20%, 20%-25%, 25%+
VIX:              20-25, 25-30, 30-35, 35+
```

そのうえで、「下落が深いほど、またVIXが高いほど買いやすい」という単調性だけを守る買いルールを70通り自動生成して比較します。
任意のポイント配分を先に決めないため、どの市場状態が強いのかを読みやすくなります。

## Run

```bash
python3 sp500_vix_grid_rule.py
```

CSVに保存する場合:

```bash
python3 sp500_vix_grid_rule.py \
  --cell-summary-csv grid_cell_summary.csv \
  --rule-summary-csv monotone_rule_summary.csv
```

## Outputs

* `grid_cell_summary.csv`: 16個の市場状態セルごとのフォワードリターン
* `monotone_rule_summary.csv`: 単調な買いルール70通りごとのフォワードリターン

`rule_description` は、各S&P500下落率セルで最低どのVIX水準から買うかを表します。


## 結果


Sランク（全力）
15〜20 ×35+
25+ ×35+
10〜15 ×35+
25+ ×30〜35

ここは期待値がかなり高い

Aランク（多め）
20〜25 ×30〜35
20〜25 ×25〜30
15〜20 ×30〜35
10〜15 ×30〜35

Bランク（普通）
25+ ×25〜30
15〜20 ×25〜30
10〜15 ×25〜30
