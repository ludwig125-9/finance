import os
import io
import urllib.request
import pandas as pd
import numpy as np
import statsmodels.api as sm
import zipfile
import matplotlib
matplotlib.use("MacOSX")  # MacでGUIウィンドウ
import matplotlib.pyplot as plt

# ------------- 設定 -------------
YEARS = 30

# 金利差モデル：どのスプレッドでUSDJPYを説明するか
# （あなたの前の回帰に合わせるなら policy + 10y が無難）
RATE_MODEL_FACTORS = ["spread_policy", "spread_10y"]
# RATE_MODEL_FACTORS = ["spread_3m", "spread_10y"]  # こっちにしてもOK

# 乖離（ギャップ）の定義：ユーザー要望に合わせて「予測値 - 実績」
GAP_DEF = "pred_minus_actual"   # 予測 - 実績（あなたの要望通り）
# GAP_DEF = "actual_minus_pred" # 実績 - 予測（通常の残差）

# CFTCポジション：legacy（Noncommercial）を使う
CFTC_MODE = "legacy"  # "legacy" 推奨。TFFを使いたければ後述の関数を参照

# ------------- FRED取得 -------------
def fred_csv(series_id: str) -> str:
    return f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"

def download_fred(series_id: str, colname: str) -> pd.DataFrame:
    df = pd.read_csv(fred_csv(series_id))
    df.columns = ["date", colname]
    df["date"] = pd.to_datetime(df["date"])
    df[colname] = pd.to_numeric(df[colname], errors="coerce")
    return df

def to_monthly(df: pd.DataFrame, value_col: str, how: str = "mean") -> pd.Series:
    s = df.set_index("date")[value_col].sort_index()
    if how == "mean":
        return s.resample("MS").mean()
    elif how == "last":
        return s.resample("MS").last()
    else:
        raise ValueError("how must be 'mean' or 'last'")

# ------------- CFTC COT（ポジション）取得 -------------

def read_csv_with_ua(url: str, **read_csv_kwargs) -> pd.DataFrame:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/123.0 Safari/537.36"
        },
    )
    with urllib.request.urlopen(req) as resp:
        raw = resp.read()
    return pd.read_csv(io.BytesIO(raw), **read_csv_kwargs)


def download_bytes_with_ua(url: str) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/123.0 Safari/537.36"
        },
    )
    with urllib.request.urlopen(req) as resp:
        return resp.read()

def load_cftc_jpy_positions_legacy() -> pd.DataFrame:
    """
    CFTC legacy futures-only 1986-2016 zip内 FUT86_16.txt をCSV（カンマ区切り）として読む版
    Noncommercial net（Long-Short）と net/OI を月次（MS）平均で返す
    """
    url = "https://www.cftc.gov/files/dea/history/deacot1986_2016.zip"
    zbytes = download_bytes_with_ua(url)

    with zipfile.ZipFile(io.BytesIO(zbytes)) as z:
        name = "FUT86_16.txt"
        if name not in z.namelist():
            raise RuntimeError("FUT86_16.txt not found. Members:\n" + "\n".join(z.namelist()))
        with z.open(name) as f:
            raw = f.read()

    # 文字コード（まずutf-8、だめならlatin-1）
    try:
        text = raw.decode("utf-8", errors="replace")
    except Exception:
        text = raw.decode("latin-1", errors="replace")

    # ★ここが肝：CSVとして読む
    # df = pd.read_csv(io.StringIO(text), sep=",", engine="python", low_memory=False)
    df = pd.read_csv(io.StringIO(text), sep=",", low_memory=False)

    # 列名の前後の " を剥がす（入っている場合）
    df.columns = [str(c).strip().strip('"') for c in df.columns]

    # あなたの列名一覧に一致させる
    #market_col = "Market_and_Exchange_Names"
    #date_col   = "As_of_Date_in_Form_YYMMDD"
    #oi_col     = "Open_Interest_(All)"
    #ncl_col    = "Noncommercial_Positions-Long_(All)"
    #ncs_col    = "Noncommercial_Positions-Short_(All)"
    market_col = "Market and Exchange Names"
    date_col   = "As of Date in Form YYMMDD"
    oi_col     = "Open Interest (All)"
    ncl_col    = "Noncommercial Positions-Long (All)"
    ncs_col    = "Noncommercial Positions-Short (All)"

    # 念のため存在チェック
    for c in [market_col, date_col, oi_col, ncl_col, ncs_col]:
        if c not in df.columns:
            raise RuntimeError(
                f"Expected column not found: {c}\nColumns are:\n" + "\n".join(df.columns.astype(str)[:200])
            )

    # 日本円（CME）
    df = df[df[market_col].astype(str).str.contains("JAPANESE YEN", case=False, na=False)].copy()

    # 日付（YYMMDD）→ YYYYMMDD（86〜99は19xx、00〜16は20xx）
    s_num = pd.to_numeric(df[date_col], errors="coerce")

    def yymmdd_to_datetime(x):
        if pd.isna(x):
            return pd.NaT
        x = str(int(x)).zfill(6)  # YYMMDD
        yy = int(x[:2])
        prefix = "19" if yy >= 86 else "20"
        return pd.to_datetime(prefix + x, format="%Y%m%d", errors="coerce")

    df["date"] = s_num.apply(yymmdd_to_datetime)
    df = df.dropna(subset=["date"])

    for c in [oi_col, ncl_col, ncs_col]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df["pos_net"] = df[ncl_col] - df[ncs_col]
    df["pos_net_pct_oi"] = df["pos_net"] / df[oi_col]

    # 週次→月次平均
    m = (
        df.set_index("date")[["pos_net", "pos_net_pct_oi"]]
          .sort_index()
          .resample("MS")
          .mean()
    )
    m.index.name = "date"
    return m
# （参考）TFF（レバレッジドファンド等）を使いたい場合
def load_cftc_jpy_positions_tff() -> pd.DataFrame:
    """
    Traders in Financial Futures Futures-Only (FinFutWk.txt)
    フィールド（0-based index）：
      0: Market_and_Exchange_Names
      2: Report_Date (YYYY-MM-DD等)
      7: Open_Interest_All
      14: Lev_Money_Positions_Long_All
      15: Lev_Money_Positions_Short_All
    """
    url = "https://www.cftc.gov/dea/newcot/FinFutWk.txt"
    usecols = [0, 2, 7, 14, 15]
    df = pd.read_csv(
        url,
        header=None,
        usecols=usecols,
        skipinitialspace=True,
        low_memory=False
    )
    df.columns = ["market", "date", "oi", "lev_long", "lev_short"]

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])

    for c in ["oi", "lev_long", "lev_short"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df = df[df["market"].str.contains("JAPANESE YEN", case=False, na=False)].copy()

    df["pos_net"] = df["lev_long"] - df["lev_short"]
    df["pos_net_pct_oi"] = df["pos_net"] / df["oi"]

    m = df.set_index("date")[["pos_net", "pos_net_pct_oi"]].sort_index().resample("MS").mean()
    m.index.name = "date"
    return m

# ------------- ① USDJPY & 金利差データ（あなたの作り方を踏襲）-------------
SERIES_BASE = {
    "usdjpy": "EXJPUS",      # monthly avg
    "fedfunds": "FEDFUNDS",  # monthly
    "us_3m": "TB3MS",        # monthly
    "us_2y": "GS2",          # monthly
    "us_10y": "GS10",        # monthly
    "jp_call": "IRSTCI01JPM156N",
    "jp_3m": "IR3TIB01JPM156N",
    "jp_10y": "IRLTLT01JPM156N",
}

dfs = []
for col, sid in SERIES_BASE.items():
    dfs.append(download_fred(sid, col))

data = dfs[0]
for df in dfs[1:]:
    data = data.merge(df, on="date", how="outer")
data = data.sort_values("date")

end = data["date"].max()
start = end - pd.DateOffset(years=YEARS)
dataN = data[(data["date"] >= start) & (data["date"] <= end)].copy()
dataN = dataN.set_index("date").sort_index()

# spreads
dataN["spread_policy"] = dataN["fedfunds"] - dataN["jp_call"]
dataN["spread_3m"]     = dataN["us_3m"] - dataN["jp_3m"]
dataN["spread_10y"]    = dataN["us_10y"] - dataN["jp_10y"]

# ------------- ② 金利差モデルで「予測値」と「乖離（ギャップ）」を作る -------------
reg_base = dataN.dropna(subset=["usdjpy"] + RATE_MODEL_FACTORS).copy()

y = np.log(reg_base["usdjpy"])
X = sm.add_constant(reg_base[RATE_MODEL_FACTORS])
model_rates = sm.OLS(y, X).fit()

reg_base["log_pred"] = model_rates.predict(X)
reg_base["log_actual"] = y

if GAP_DEF == "pred_minus_actual":
    reg_base["gap_log"] = reg_base["log_pred"] - reg_base["log_actual"]
else:
    reg_base["gap_log"] = reg_base["log_actual"] - reg_base["log_pred"]

# （参考）円ベースのギャップも欲しければ
reg_base["pred_usdjpy"] = np.exp(reg_base["log_pred"])
reg_base["gap_yen"] = reg_base["pred_usdjpy"] - reg_base["usdjpy"]

print("\n=== Rate Model (log USDJPY ~ spreads) ===")
print(model_rates.summary())
print("\nRate-model sample:", reg_base.index.min().date(), "->", reg_base.index.max().date(), "n=", len(reg_base))

# ------------- ③ VIX / Dollar Index / Position を作る -------------
# VIX（日次→月次平均）
vix_df = download_fred("VIXCLS", "vix")
vix_m = to_monthly(vix_df, "vix", how="mean")

# Dollar index proxy：DTWEXBGS（2006-） + TWEXB（～2019）をスプライス
dt_df = download_fred("DTWEXBGS", "dtwexbgs")
tw_df = download_fred("TWEXB", "twexb")  # discontinued, but long history

dt_m = to_monthly(dt_df, "dtwexbgs", how="mean")
tw_m = to_monthly(tw_df, "twexb", how="mean")

# スケール合わせ（重なり期間でTWEXBをDTWEXBGSに“近づける”）
overlap = pd.concat([dt_m, tw_m], axis=1).dropna()
if len(overlap) >= 12:
    mu_dt, sd_dt = overlap["dtwexbgs"].mean(), overlap["dtwexbgs"].std(ddof=0)
    mu_tw, sd_tw = overlap["twexb"].mean(), overlap["twexb"].std(ddof=0)
    tw_adj = (tw_m - mu_tw) / sd_tw * sd_dt + mu_dt
    usd_index = dt_m.combine_first(tw_adj).rename("usd_index_proxy")
else:
    # 重なりが取れない場合はDTWEXBGSのみ（この場合、2006以降だけになります）
    usd_index = dt_m.rename("usd_index_proxy")

# CFTC Position（週次→月次平均）
if CFTC_MODE == "legacy":
    pos_m = load_cftc_jpy_positions_legacy()
    print("pos_m:", pos_m.index.min().date(), "->", pos_m.index.max().date(), "n=", len(pos_m))
    print(pos_m.tail())
else:
    pos_m = load_cftc_jpy_positions_tff()

print("\n--- availability check ---")
print("reg_base:", reg_base.index.min().date(), "->", reg_base.index.max().date(), "n=", len(reg_base))
print("vix_m   :", vix_m.index.min().date(), "->", vix_m.index.max().date(), "n=", len(vix_m.dropna()))
print("usd_idx :", usd_index.index.min().date(), "->", usd_index.index.max().date(), "n=", len(usd_index.dropna()))
print("pos_m   :", pos_m.index.min().date(), "->", pos_m.index.max().date(), "n=", len(pos_m.dropna()))
print("pos_m tail:\n", pos_m.tail())

# ------------- ④ ギャップ（残差）を VIX/Dollar/Position で回帰 -------------
df = reg_base[["gap_log", "gap_yen"]].join(
    pd.concat([vix_m.rename("vix"), usd_index, pos_m], axis=1),
    how="inner"
).dropna()

# 変数の形：ログや標準化（スケール差で係数が読みにくくなるのを防ぐ）
df["vix_log"] = np.log(df["vix"])
df["usd_log"] = np.log(df["usd_index_proxy"])

## ===== PLOTS (single window) =====
#import matplotlib
#matplotlib.use("MacOSX")
#import matplotlib.pyplot as plt

if len(df) == 0:
    print("df is empty; cannot plot.")
else:
    plot_df = df.copy()
    plot_df["gap_bp"] = plot_df["gap_log"] * 100  # 便宜上（log差×100）

    fig, ax1 = plt.subplots(figsize=(14, 6))

    ax1.plot(plot_df.index, plot_df["gap_bp"], linewidth=2.0, label="Gap (pred-actual, log*100)")
    ax1.axhline(0, linewidth=1)
    ax1.set_ylabel("gap (log*100)")
    ax1.grid(True, linestyle="--", alpha=0.4)

    ax2 = ax1.twinx()
    ax2.plot(plot_df.index, plot_df["usd_index_proxy"], linewidth=1.6, alpha=0.8, label="USD Index (proxy)")
    ax2.plot(plot_df.index, plot_df["vix"], linewidth=1.6, alpha=0.8, label="VIX")
    ax2.set_ylabel("USD index / VIX")

    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="upper left")

    ax1.set_title("USDJPY Gap vs USD Index (proxy) & VIX (monthly)")
    fig.tight_layout()
    plt.show(block=True)

def zscore(s: pd.Series) -> pd.Series:
    return (s - s.mean()) / s.std(ddof=0)

# ポジション無し版（まず回す）
df["vix_log"] = np.log(df["vix"])
df["usd_log"] = np.log(df["usd_index_proxy"])

def zscore(s):
    return (s - s.mean()) / s.std(ddof=0)

df["vix_z"] = zscore(df["vix_log"])
df["usd_z"] = zscore(df["usd_log"])

Y = df["gap_log"]
X = sm.add_constant(df[["vix_z", "usd_z"]])

model_gap = sm.OLS(Y, X).fit(cov_type="HAC", cov_kwds={"maxlags": 12})
print(model_gap.summary())
#df["vix_z"] = zscore(df["vix_log"])
#df["usd_z"] = zscore(df["usd_log"])
#df["pos_z"] = zscore(df["pos_net_pct_oi"])  # OIで割ったネットを推奨（スケール安定）
#
#Y = df["gap_log"]
#X = sm.add_constant(df[["vix_z", "usd_z", "pos_z"]])
#
## 月次で自己相関が出やすいので Newey-West(HAC) を推奨（maxlags=12）
#model_gap = sm.OLS(Y, X).fit(cov_type="HAC", cov_kwds={"maxlags": 12})
#
#print("\n=== Gap Regression (gap_log ~ VIX + USD + Position) ===")
#print(model_gap.summary())
#print("\nGap-reg sample:", df.index.min().date(), "->", df.index.max().date(), "n=", len(df))

# ------------- ⑤ ついでに「12か月差分」でも回帰（頑健性チェック）-------------
df_chg = df[["gap_log", "vix_log", "usd_log", "pos_net_pct_oi"]].diff(12).dropna()
df_chg["vix_z"] = zscore(df_chg["vix_log"])
df_chg["usd_z"] = zscore(df_chg["usd_log"])
df_chg["pos_z"] = zscore(df_chg["pos_net_pct_oi"])

Y2 = df_chg["gap_log"]
X2 = sm.add_constant(df_chg[["vix_z", "usd_z", "pos_z"]])
model_gap_12m = sm.OLS(Y2, X2).fit(cov_type="HAC", cov_kwds={"maxlags": 12})

print("\n=== Gap Regression (12m diff) ===")
print(model_gap_12m.summary())
print("\n12m-diff sample:", df_chg.index.min().date(), "->", df_chg.index.max().date(), "n=", len(df_chg))

# ------------- 保存 -------------
out_csv = f"usdjpy_gap_regression_last{YEARS}y.csv"
df_out = df.copy()
df_out.to_csv(out_csv)
print(f"\nSaved: {out_csv}")
