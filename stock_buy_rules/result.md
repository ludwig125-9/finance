# このルールの平均３年リターン

```
(.venv) [~/git/ludwig125-9/finance/stock_buy_rules] $python3 backtest_sp500_vix_buy_rule.py rolling --years 3
rolling_cases: 292
total_return_avg: 26.48%
total_return_median: 25.56%
total_return_min: -23.65%
total_return_max: 78.76%
cagr_avg: 7.75%
cagr_median: 7.90%
cagr_min: -8.61%
cagr_max: 21.40%
max_drawdown_avg: -9.44%
max_drawdown_median: -9.40%
max_drawdown_min: -17.61%
max_drawdown_max: 0.00%
lump_sum_return_avg: 23.67%
lump_sum_return_median: 29.74%
lump_sum_return_min: -43.07%
lump_sum_return_max: 96.07%
daily_dca_return_avg: 11.35%
daily_dca_return_median: 14.38%
daily_dca_return_min: -42.38%
daily_dca_return_max: 42.00%
buy_count_avg: 182.75
total_invested_avg: 784933.56

```

かなり良い結果に見えます。特に「3年ローリングで平均CAGR 7.75%」かつ「一括投資平均 23.67% に対して、この戦略の平均 total_return が 26.48%」なので、少なくともこの検証条件では、下落時買いルールが一括投資を少し上回っています。

注目点はここです。

**良い点**

- `total_return_avg: 26.48%`
  - 3年間で平均 +26.48%。悪くないです。
- `cagr_avg: 7.75%`
  - 年率平均で約7.8%。S&P500の長期平均に近い水準です。
- `total_return_avg 26.48% > lump_sum_return_avg 23.67%`
  - 平均では一括投資より良い。
- `total_return_min: -23.65%`
  - 一括投資の `lump_sum_return_min: -43.07%` よりかなり浅い。
- `max_drawdown_avg: -9.44%`
  - 戦略上の評価額下落は比較的抑えられています。
- `daily_dca_return_avg: 11.35%` よりかなり良い
  - 同じ総投資額を毎日均等に買うより、下落時に寄せる効果が出ています。

つまり、この戦略はかなり「守りながら買う」性格です。
大きく負けるケースを減らしつつ、平均でもそれなりに勝てている。

**気になる点**

一方で、`lump_sum_return_max: 96.07%` に対して `total_return_max: 78.76%` なので、強い上昇相場では一括投資に負けます。これは当然で、下落を待つ戦略なので、上がり続ける相場では資金投入が遅れます。

また、`buy_count_avg: 182.75` は3年でかなり多いです。営業日ベースで約750日のうち180日以上買っているので、「暴落時だけ買う」というより「弱い局面でかなり継続的に買う」戦略になっています。

`total_invested_avg: 784933.56` も重要です。スコアをそのまま買付額にしているので、かなり大きな買付量になります。実運用では、これを例えば以下のように正規化した方が良いです。

```python
buy_amount = signal_score * 1000
```

または、待機資金上限を決めて、

```python
buy_amount = min(signal_score, remaining_cash)
```

のようにする必要があります。

**総合評価**

この結果だけ見ると、ルールは有望です。

特に良いのは、

```text
平均リターン: 戦略 > 一括投資 > 毎日積立
最悪リターン: 戦略が一括投資よりかなり浅い
```

という点です。

ただし、次に見るべきなのは「10年ローリング」です。
3年では下落時買いが効きやすいですが、10年では一括投資の複利に負ける可能性があります。

私なら次に以下を確認します。

```bash
python3 backtest_sp500_vix_buy_rule.py rolling --years 10
python3 backtest_sp500_vix_buy_rule.py rolling --years 1
```

そして判断軸はこうです。

- 1年: 暴落後の短期反発を取れているか
- 3年: 実用的な中期戦略として強いか
- 10年: 長期で一括投資に勝てるか、または守りとして意味があるか

現時点の評価は、「かなり堅実。上昇相場では機会損失があるが、下落耐性と平均成績のバランスが良い」です。


# このルールの平均10年リターン
```
(.venv) [~/git/ludwig125-9/finance/stock_buy_rules] $python3 backtest_sp500_vix_buy_rule.py rolling --years 10
rolling_cases: 208
total_return_avg: 87.97%
total_return_median: 86.68%
total_return_min: -24.46%
total_return_max: 219.70%
cagr_avg: 6.12%
cagr_median: 6.44%
cagr_min: -2.77%
cagr_max: 12.33%
max_drawdown_avg: -20.97%
max_drawdown_median: -17.64%
max_drawdown_min: -39.07%
max_drawdown_max: -10.33%
lump_sum_return_avg: 111.30%
lump_sum_return_median: 81.28%
lump_sum_return_min: -40.53%
lump_sum_return_max: 300.06%
daily_dca_return_avg: 55.59%
daily_dca_return_median: 60.33%
daily_dca_return_min: -38.08%
daily_dca_return_max: 113.72%
buy_count_avg: 524.59
total_invested_avg: 2398770.91
```

10年ローリングの評価は、かなりはっきり性格が出ています。

**結論**

この戦略は、10年では「一括投資に平均リターンで負けるが、下落耐性はかなり良い」戦略です。

数字で見ると：

```text
戦略 total_return_avg: 87.97%
一括 lump_sum_return_avg: 111.30%
毎日積立 daily_dca_return_avg: 55.59%
```

なので、長期平均では、

```text
一括投資 > この戦略 > 毎日積立
```

です。

ただし最悪ケースを見るとかなり良いです。

```text
戦略 total_return_min: -24.46%
一括 lump_sum_return_min: -40.53%
毎日積立 daily_dca_return_min: -38.08%
```

つまり、10年という長期でも、悪い開始タイミングでは一括投資よりかなり損失を抑えています。

**良い点**

- `daily_dca_return_avg: 55.59%` より `total_return_avg: 87.97%` がかなり高い
  - 単純な毎日積立より、下落時に厚く買う効果は明確に出ています。
- `total_return_min: -24.46%`
  - 一括投資の最悪 `-40.53%` よりかなり改善。
- `cagr_avg: 6.12%`
  - 守備的な戦略としては悪くないです。
- `total_return_median: 86.68%` が一括の `81.28%` より高い
  - 平均では一括に負けていますが、中央値では勝っています。これはかなり面白いです。

**気になる点**

- `lump_sum_return_avg: 111.30%` に対して、戦略は `87.97%`
  - 強い上昇相場では現金待機が機会損失になります。
- `lump_sum_return_max: 300.06%` に対して、戦略は `219.70%`
  - 長期の大上昇をフルに取り切れない。
- `buy_count_avg: 524.59`
  - 10年で約525日買っているので、かなり頻繁です。暴落時だけというより「調整局面で厚めに分散買い」ですね。

**総合評価**

この戦略は、長期で資産最大化だけを狙うなら一括投資に劣ります。
ただし、「暴落開始直前に一括投資してしまうリスクを避けたい」「待機資金を心理的に納得して投入したい」という目的にはかなり合っています。

特に重要なのはここです。

```text
平均: 一括投資に負ける
中央値: 一括投資に勝つ
最悪: 一括投資よりかなり良い
```

なので、これはリターン最大化戦略というより、**タイミングリスクを抑えた下落時投入戦略**として評価するのが自然です。

次に改善するなら、私はこの2つを試します。

1. 平常時の定額積立を少し混ぜる
   例: 毎月ベース投資 + 暴落時はシグナル買い

2. 買付額を `signal_score` そのままではなく、スコア帯で段階投入にする
   READMEに書いてある `20% / 40% / 40%` 方式です。

今の結果を見る限り、「全部を待機資金にして暴落待ち」より、「通常積立 + このシグナルで追加投入」の方が長期では強くなりそうです。


# このルールの平均１年リターン
```
(.venv) [~/git/ludwig125-9/finance/stock_buy_rules] $python3 backtest_sp500_vix_buy_rule.py rolling --years 1
rolling_cases: 316
total_return_avg: 8.18%
total_return_median: 3.61%
total_return_min: -23.27%
total_return_max: 46.34%
cagr_avg: 8.21%
cagr_median: 3.62%
cagr_min: -23.34%
cagr_max: 46.53%
max_drawdown_avg: -4.35%
max_drawdown_median: -4.62%
max_drawdown_min: -11.37%
max_drawdown_max: 0.00%
lump_sum_return_avg: 7.66%
lump_sum_return_median: 11.09%
lump_sum_return_min: -44.79%
lump_sum_return_max: 62.71%
daily_dca_return_avg: 1.72%
daily_dca_return_median: 0.00%
daily_dca_return_min: -34.15%
daily_dca_return_max: 21.03%
buy_count_avg: 59.41
total_invested_avg: 250732.44
(.venv) [~/git/ludwig125-9/finance/stock_buy_rules] $
```

1年ローリングも、かなりこの戦略らしい結果です。

**評価**

1年では、この戦略はかなり良いです。

```text
戦略 total_return_avg: 8.18%
一括 lump_sum_return_avg: 7.66%
毎日積立 daily_dca_return_avg: 1.72%
```

平均では一括投資を少し上回り、毎日積立には大きく勝っています。
特に重要なのは最悪ケースです。

```text
戦略 total_return_min: -23.27%
一括 lump_sum_return_min: -44.79%
毎日積立 daily_dca_return_min: -34.15%
```

1年という短期でも、暴落開始タイミングに巻き込まれた場合のダメージをかなり抑えています。

**かなり良い点**

- `total_return_avg` が一括投資を上回っている
- `max_drawdown_avg: -4.35%` と浅い
- `total_return_min` が一括投資より約21ポイント良い
- 毎日積立より平均・中央値・最悪の全部で良い

一方で、

```text
戦略 total_return_median: 3.61%
一括 lump_sum_return_median: 11.09%
```

中央値では一括投資に大きく負けています。
これは「多くの普通の1年」では、あまり買い場が来ず、資金投入が遅れるためです。

つまり1年では、

```text
平均: 戦略が少し勝つ
中央値: 一括がかなり勝つ
最悪: 戦略がかなり勝つ
最大: 一括が勝つ
```

です。

**総合すると**

この戦略は、1年では「暴落・調整がある年に強く、平穏な上昇年では弱い」タイプです。
ただし平均で一括投資を上回っているので、短中期の待機資金投入ルールとしてはかなり有望です。

1年・3年・10年をまとめると、今のところこう見えます。

```text
1年: 平均で一括に少し勝つ。守りが強い。
3年: 平均・最悪ともにかなり良い。最も相性が良さそう。
10年: 平均では一括に負けるが、中央値と最悪は良い。
```

私の評価では、このルールは「全資産をこれで運用する主戦略」より、**待機資金・追加投資資金をいつ入れるか決めるルール**としてかなり優秀です。
