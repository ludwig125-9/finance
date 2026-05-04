QQQ長期価格
https://www.nasdaq.com/market-activity/etf/qqq/advanced-charting


yfinanceは取得できなかった
https://finance.yahoo.com/quote/NQ%3DF/history/
> Date shouldn't be prior to "Sep 18, 2000"

ドル円
https://fred.stlouisfed.org/series/EXJPUS/


yfinanceのドル円は
https://finance.yahoo.com/quote/JPY%3DX/history/
Date shouldn't be prior to "Oct 30, 1996"


QQQ長期価格
https://www.nasdaq.com/market-activity/etf/qqq/advanced-charting


yfinanceは取得できなかった
https://finance.yahoo.com/quote/NQ%3DF/history/
> Date shouldn't be prior to "Sep 18, 2000"

ドル円
https://fred.stlouisfed.org/series/EXJPUS/


yfinanceのドル円は
https://finance.yahoo.com/quote/JPY%3DX/history/
Date shouldn't be prior to "Oct 30, 1996"

# historical_backtest_10years.py

(.venv) ~/git/finance/qqq_backtest$ python3 historical_backtest_10years.py

=== Historical 10-Year Fixed Horizon COMPLETE Summary ===
       strategy  avg_return_pct  median_return_pct  min_return_pct  max_return_pct  avg_cagr_pct  avg_max_drawdown_pct  worst_drawdown_pct  win_rate_vs_lump
        LumpSum      333.214176         243.041212      -66.302772      942.697565     12.860207             42.700551           78.566182          0.000000
 Hybrid25pct_3y      286.954019         317.870301      -39.693685      667.154140     12.501246             37.747216           67.893553         32.019704
         DCA_3y      271.533967         307.780473      -37.966440      582.555880     12.262076             36.758847           62.338820         32.019704
 Hybrid25pct_5y      257.327481         289.888979      -25.559092      570.619921     11.881622             35.259155           59.881944         34.975369
         DCA_5y      232.031917         279.134979      -19.120317      470.587406     11.356962             33.723239           59.881944         34.975369
 Hybrid25pct_7y      229.633926         247.758661      -26.309881      510.258091     11.162024             32.949042           59.881944         28.078818
         DCA_7y      195.107176         222.201919      -17.154014      381.767217     10.306722             30.694602           59.881944         28.078818
Hybrid25pct_10y      193.862510         196.561179      -24.980139      444.716497     10.104120             29.201297           56.655506         17.733990
        DCA_10y      147.411955         165.882814      -16.287818      283.039938      8.688756             25.615991           55.886884         17.733990

最終順位
LumpSum
Hybrid25% + 3年DCA
DCA3年
Hybrid25% + 5年DCA
DCA5年
以下長期DCAほど不利


> 例えばDCA_10yでもmin_return_pctが-16.287818ですが、 これはどういう場合だと思いますか？

開始から10年間固定評価なので

2000/01開始
2000/01〜2009/12まで120回積立
2010/01時点で評価

です。

ここで終わり。

つまり重要なのは

積立終了後のNASDAQ黄金期（2010〜2026）をまだ享受していない



> 仮に一括投資した日がITバブル崩壊の時だとしても、一括投資（LumpSum）の方がいいということでしょうか？


ここが非常に重要な読み違えポイントです。
結論から言うと、

> **いいえ、「ITバブル崩壊のような最悪の天井でも一括の方がいい」という意味ではありません。**

この表はそうは言っていません。

この表が言っているのはもっと限定的で、

> **全開始時点を平均すると、一括投資の期待値が最も高い**

です。

平均の話です。
個別の最悪局面では別です。

ここを分けて考える必要があります。

---

# まず min_return を見てください

## LumpSum

min_return = **-66.3%**

つまり最悪の開始月では

> 1000万円 → 337万円

です。

これは10年間投資してこの結果。

かなり厳しい。

---

## DCA_10y

min_return = **-16.3%**

最悪でも

> 1000万円 → 837万円

で済んでいる。

---

## DCA_5y

min_return = **-19.1%**

---

つまり

> ITバブル天井のような「超悪い開始点」に限れば、積立の方が圧倒的に被害が小さい

のです。

これは表にははっきり出ています。

---

# ではなぜ平均ではLumpSumが勝つのか

理由は単純です。

歴史323か月のうち、

> ITバブル天井のような極端な最悪局面は少数派

だからです。

多くの月ではNASDAQ円建ては長期上昇しています。

そのため

> 大多数の普通の開始月では、早く全額市場に置いたLumpSumが複利勝ちする。

この多数派が平均を押し上げる。

---

# つまり統計的にはこう

## LumpSum = 高期待値・低勝率ではない、高期待値・高分散

* 平均は高い
* でも事故ると致命傷

---

## DCA = 期待値を削って事故回避

* 平均は落ちる
* でも最悪値が大幅改善

---

# これは保険の関係と同じ

積立投資は言ってしまうと

> 「期待値を少し捨ててタイミング保険を買っている」

のです。

その保険料が

* LumpSum avg_return 333%
* DCA5y avg_return 232%

この差。

約100%分の期待値を払って安心を買っている。

---

# あなたが本当に知りたい問いに変換すると

重要なのは

> 「今がITバブル級天井である確率をどう見るか」

です。

もし今が普通の高値なら一括有利。

もし今が歴史的大天井なら積立有利。

つまり問題は戦略そのものより

> 現在局面の異常度

です。

---

# そして今は普通の局面ではないのも事実

あなたが最初から気にしている通り

* 円安極端
* NASDAQ高バリュエーション
* AI相場過熱
* 米国株集中

で、

> 歴史平均的な「どこかの1か月」と同列には扱いにくい。

ここが本質です。

平均統計だけで一括GOとは言えない。

---

# だから見るべきなのは平均ではなく左端

この表で投資家が見るべきは avg_return より

> min_return
> worst_drawdown

です。

なぜなら人は最悪局面で脱落するから。

---

LumpSum:

* min -66%
* worstDD -78%

これは相当きつい。

普通の人は途中で耐えられない。

---

Hybrid25%_5y:

* min -25%
* worstDD -59%

まだきついが現実的。

---

DCA10y:

* min -16%
* worstDD -55%

かなり防御的。

---

# 実務的な答え

だから

> 「もし今がITバブル天井級だったら？」

に備えるなら、一括が良いとは全く言えません。

むしろ危険。

このバックテストは

> 一括は平均で勝つが、最悪ケースの破壊力が極端

と示しています。

---

# 投資判断としてはこうなる

### 強気前提

LumpSum

### 中立〜慎重

Hybrid25% + 3〜5年DCA

### 天井警戒強い

DCA5〜10年

---
