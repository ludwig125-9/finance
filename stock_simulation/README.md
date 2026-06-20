
```
sudo apt update
sudo apt install python3-tk
python3 -m venv .venv
source .venv/bin/activate
pip install numpy
pip install pandas
pip install matplotlib
python
```


stock_simulateの1と2の違い

```
素晴らしいです。
ここからがこのシミュレーションを**本当に使える判断材料に変える部分**です。

今のコードはよくできていますが、まだ

> 「きれいすぎる教科書相場」

なんです。

現実の投資判断に近づけるには、

> **“現実の相場が持つ嫌らしさ”を入れる**

必要があります。

私は修正ポイントを4つ推奨します。
この4つを入れるとかなり別物になります。

---

# 修正① Y（暴落開始時期）を均等分布にしない

ここが最重要です。

今は

```python
Y_VALUES = range(0, 11)
```

で全部同じ重み。

つまり

* 今年暴落
* 10年後暴落

が同確率。

これは今の高バリュエーション相場では不自然です。

現実には

> 近い数年ほど調整が起きやすい

と考えるのが自然。

---

## 修正方法：重みを付ける

例えばこうします。

```python
Y_WEIGHTS = {
    0: 0.18,
    1: 0.16,
    2: 0.14,
    3: 0.12,
    4: 0.10,
    5: 0.08,
    6: 0.07,
    7: 0.06,
    8: 0.04,
    9: 0.03,
    10:0.02
}
```

近い年ほど高確率。

---

## 集計時にweighted averageへ変更

単純meanではなく：

```python
weight = Y_WEIGHTS[Y]
```

を各rowに持たせて、

weighted meanを計算します。

これだけで結果はかなり変わります。

おそらく

> LumpSumの順位が下がり
> 6〜12か月DCA優位が強く出る

はずです。

---

# 修正② 為替（ドル円）パスを追加する

これはあなたに必須。

今の悩みは株だけではなく

> 「160円でドルを買う怖さ」

だからです。

---

## 為替モデルを別に作る

株価パスと同じ考えで

* 現在160円
* 将来10年後140円程度へ平均回帰
* 途中で130〜170を揺れる
* 株調整時には円高になりやすい

を入れる。

簡易版なら：

```python
def build_fx_path(Y, M1, M2):
    INITIAL_FX = 160
    FINAL_FX = 140

    total_months = (Y + 10) * 12
    fx = np.empty(total_months + 1)

    crash_start = Y * 12
    yen_spike = crash_start + M1   # 株安時に円高進行

    fx_bottom = 145  # 例：危機時円高

    # 暴落開始まで緩やかに160→155
    for t in range(crash_start + 1):
        fx[t] = 160 - 5 * (t / max(1, crash_start))

    # 株下落中に155→145
    for t in range(crash_start + 1, yen_spike + 1):
        frac = (t - crash_start) / M1
        fx[t] = 155 + (fx_bottom - 155) * frac

    # 回復中145→155
    for t in range(yen_spike + 1, yen_spike + M2 + 1):
        frac = (t - yen_spike) / M2
        fx[t] = fx_bottom + (155 - fx_bottom) * frac

    # 長期で140へ
    remaining = total_months - (yen_spike + M2)
    for t in range(yen_spike + M2 + 1, total_months + 1):
        frac = (t - (yen_spike + M2)) / max(1, remaining)
        fx[t] = 155 + (140 - 155) * frac

    return fx
```

---

## 投資時の口数計算を変更

ドル資産購入価格を

```python
effective_price = stock_price[t] * fx[t] / fx[0]
```

で円換算。

これで

> 株が下がらなくても円高で買いやすくなる

が反映される。

かなり現実的になります。

---

# 修正③ 暴落を1回ではなく2回まで許容する

現実の相場はV字一回で終わりません。

例えば

* 2022下落
* 戻る
* 再下落

みたいなパターンが普通。

---

## モデル例

* Y1年後にP1%下落
* 2〜4年後にさらにP2%下落

をランダム追加。

簡易には：

```python
SECOND_CRASH_PROB = 0.35
```

35%で第二調整発生。

これを `build_price_path()` 内で追加。

すると長期DCAの評価が少し改善します。

なぜなら複数谷を拾えるから。

---

# 修正④ 「10年後必ず2倍」を固定しない

ここも大事です。

現実は将来リターンも不確実。

なのでFINAL_MULTIPLEを固定2.0ではなく分布にする。

例えば

```python
FINAL_MULTIPLES = [1.2, 1.5, 2.0, 2.5, 3.0]
FINAL_WEIGHTS   = [0.10,0.20,0.35,0.20,0.15]
```

ランダムに選ぶ。

---

これで

* 不調の10年
* 普通の10年
* 強気の10年

を混ぜられる。

現実感が一気に上がる。

---

# 修正後このシミュレーションは何を見るものになるか

単なる

「どの戦略が平均高いか」

ではなく、

> **今の高値圏・円安圏で後悔しにくい投入期間は何か**

を測る道具になります。

私はかなり高確率で

### 最適帯は

6か月〜12か月DCA
＋一部待機資金温存

になると予想しています。

今よりもっと明確に出るはず。

---

# さらに1個、かなり効く修正がある

実は今のコードは
「毎月機械的に積立するだけ」ですが、

あなたが本当にやりたいのは

> 円高や暴落が来たら追加投入する条件付き戦略

ですよね。

つまり単純DCAではなく

> **トリガー発動型戦略**

これを戦わせると一気に面白くなる。

これはかなり実践的です。

```




２の結果
```
(.venv) ~/git/finance/stock$ python3 stock_simulate2.py

=== Weighted Average Return Top ===
                   strategy  weighted_avg_return_pct  weighted_avg_regret_pct  win_rate_vs_lump  p05_return_pct  max_regret_pct
            DCA_36m_Trigger                87.893592                 5.691229         40.600000        4.106950       43.104659
            DCA_24m_Trigger                87.694721                 5.859944         34.059259        4.410676       39.890941
                    DCA_12m                86.401222                 6.346639         20.806173        4.716968       38.589642
Hybrid_25pct_DCA36m_Trigger                86.154780                 6.340600         40.600000        4.330213       43.474991
Hybrid_25pct_DCA24m_Trigger                86.005626                 6.467136         34.059259        4.558007       41.064702
            DCA_12m_Trigger                85.923160                 6.545892         20.806173        4.716968       32.953515
                     DCA_6m                85.642346                 6.552722         20.806173        4.871080       32.535147
                    DCA_24m                85.473031                 6.726151         34.062963        4.410676       42.842761
        Hybrid_25pct_DCA12m                85.035502                 6.832157         20.806173        4.787726       40.088728
             DCA_6m_Trigger                84.948840                 6.824784         20.806173        4.871080       31.587789
Hybrid_25pct_DCA12m_Trigger                84.676956                 6.981597         20.806173        4.787726       35.861633
         Hybrid_25pct_DCA6m                84.466345                 6.986720         20.806173        4.903310       35.547857
Hybrid_50pct_DCA36m_Trigger                84.415967                 6.989971         40.600000        4.553475       43.845323
        Hybrid_25pct_DCA24m                84.339359                 7.116791         34.062963        4.558007       43.278567
Hybrid_50pct_DCA24m_Trigger                84.316532                 7.074329         34.059259        4.705338       42.238464
 Hybrid_25pct_DCA6m_Trigger                83.946215                 7.190767         20.806173        4.903310       32.748029
            DCA_60m_Trigger                83.807170                 7.155356         48.039506        3.507160       46.583946
                     DCA_3m                83.783431                 7.231556         20.806173        4.948378       34.754865
        Hybrid_50pct_DCA12m                83.669782                 7.317676         20.806173        4.858484       41.587815
             DCA_3m_Trigger                83.459707                 7.350364         20.806173        4.948378       34.754865

=== Lowest Max Regret Top ===
                   strategy  weighted_avg_return_pct  weighted_avg_regret_pct  win_rate_vs_lump  p05_return_pct  max_regret_pct
             DCA_6m_Trigger                84.948840                 6.824784         20.806173        4.871080       31.587789
                     DCA_6m                85.642346                 6.552722         20.806173        4.871080       32.535147
 Hybrid_25pct_DCA6m_Trigger                83.946215                 7.190767         20.806173        4.903310       32.748029
            DCA_12m_Trigger                85.923160                 6.545892         20.806173        4.716968       32.953515
                     DCA_3m                83.783431                 7.231556         20.806173        4.948378       34.754865
             DCA_3m_Trigger                83.459707                 7.350364         20.806173        4.948378       34.754865
 Hybrid_50pct_DCA6m_Trigger                82.943591                 7.556749         20.806173        4.935540       34.871380
         Hybrid_25pct_DCA6m                84.466345                 6.986720         20.806173        4.903310       35.547857
         Hybrid_25pct_DCA3m                83.072159                 7.495845         20.806173        4.961284       35.853452
Hybrid_25pct_DCA12m_Trigger                84.676956                 6.981597         20.806173        4.787726       35.861633
 Hybrid_25pct_DCA3m_Trigger                82.829366                 7.584951         20.806173        4.961284       36.195052
         Hybrid_50pct_DCA3m                82.360887                 7.760134         20.806173        4.974189       37.568978
 Hybrid_50pct_DCA3m_Trigger                82.199025                 7.819539         20.806173        4.974189       38.260598
         Hybrid_50pct_DCA6m                83.290344                 7.420718         20.806173        4.935540       38.560567
                    DCA_12m                86.401222                 6.346639         20.806173        4.716968       38.589642
Hybrid_50pct_DCA12m_Trigger                83.430751                 7.417303         20.806173        4.858484       38.769751
 Hybrid_75pct_DCA6m_Trigger                81.940967                 7.922731         20.806173        4.967770       38.825277
         Hybrid_75pct_DCA3m                81.649615                 8.024424         20.806173        4.987095       39.394862
            DCA_24m_Trigger                87.694721                 5.859944         34.059259        4.410676       39.890941
        Hybrid_25pct_DCA12m                85.035502                 6.832157         20.806173        4.787726       40.088728

Saved: realistic_scenario_results.csv
Saved: realistic_strategy_summary.csv
```
