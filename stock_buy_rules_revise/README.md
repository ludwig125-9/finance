README.md

# stock_buy_rules_revise

S&P500の直近1年高値からの下落率とVIXのHighを組み合わせて、買いシグナルの点数パターンを比較する実験用ディレクトリです。

## 主なファイル


sp500_vix_buy_rule.py: 1日分の買いシグナル判定と、シグナル計算に使う共通処理
forward_return_by_score.py: 点数パターン別に、シグナル発生日から1年後・3年後・10年後のリターンを集計
result.md: revise_forward_summary.csv をもとにした分析メモ


## 実行例

```bash
python3 stock_buy_rules_revise/sp500_vix_buy_rule.py 20260508
python3 stock_buy_rules_revise/forward_return_by_score.py --years 1 3 10 \
  --output-csv stock_buy_rules_revise/revise_forward_summary.csv \
  --detail-csv stock_buy_rules_revise/revise_forward_detail.csv
```
