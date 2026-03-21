# finance

## install & execute
```
sudo apt update
sudo apt install -y python3-pip python3-venv
cd /home/shingo/git/finance
python3 -m venv .venv
source .venv/bin/activate
pip install pandas
pip install matplotlib
python dollar-yen.py

```
実行例

```
$ python dollar-yen.py
last date: 2026-02-01
              usdjpy  spread_policy  spread_3m  spread_10y
date
2025-12-01  155.9150          3.163    2.51727        2.08
2026-01-01  156.6505          2.912    2.45364        1.97
2026-02-01  155.1016          2.912    2.37000        2.02
/home/shingo/git/finance/dollar-yen.py:76: UserWarning: FigureCanvasAgg is non-interactive, and thus cannot be shown
  plt.show(block=True)

Correlation (level) with USDJPY:
 usdjpy           1.000000
spread_3m        0.736666
spread_policy    0.570512
spread_10y       0.518014
Name: usdjpy, dtype: float64

Correlation (12m change) with USDJPY 12m change:
 usdjpy_12m    1.000000
10y_12m       0.534193
3m_12m        0.488824
policy_12m    0.486095
Name: usdjpy_12m, dtype: float64

Saved: usdjpy_spreads_last30y.csv
```

`~/git/finance$ explorer.exe .` でWindows側でフォルダを開ける
