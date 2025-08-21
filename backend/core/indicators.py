import pandas as pd
import numpy as np


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    df = df.sort_values("trade_date").reset_index(drop=True)
    px = df["close"].astype(float).values

    period = 14
    delta = np.diff(px, prepend=px[0])
    up = np.where(delta > 0, delta, 0.0)
    down = np.where(delta < 0, -delta, 0.0)
    roll_up = pd.Series(up).rolling(period).mean()
    roll_down = pd.Series(down).rolling(period).mean()
    rs = roll_up / (roll_down + 1e-9)
    rsi = 100.0 - (100.0 / (1.0 + rs))

    ema12 = pd.Series(px).ewm(span=12, adjust=False).mean()
    ema26 = pd.Series(px).ewm(span=26, adjust=False).mean()
    dif = ema12 - ema26
    dea = dif.ewm(span=9, adjust=False).mean()
    macd = (dif - dea) * 2

    ma20 = pd.Series(px).rolling(20).mean()
    std20 = pd.Series(px).rolling(20).std(ddof=0)
    upper = ma20 + 2 * std20
    lower = ma20 - 2 * std20

    df["rsi14"] = rsi.values
    df["dif"] = dif.values
    df["dea"] = dea.values
    df["macd"] = macd.values
    df["ma20"] = ma20.values
    df["boll_up"] = upper.values
    df["boll_dn"] = lower.values
    return df


def build_tech_signal(row: pd.Series) -> str:
    sig = []
    rsi = row.get("rsi14")
    if pd.notna(rsi):
        if rsi < 30:
            sig.append("RSI<30（超卖）")
        elif rsi > 70:
            sig.append("RSI>70（超买）")
    dif, dea = row.get("dif"), row.get("dea")
    if pd.notna(dif) and pd.notna(dea):
        if dif > dea:
            sig.append("DIF>DEA（偏多）")
        elif dif < dea:
            sig.append("DIF<DEA（偏空）")
    close, up, dn = row.get("close"), row.get("boll_up"), row.get("boll_dn")
    if pd.notna(close) and pd.notna(up) and pd.notna(dn):
        if close >= up:
            sig.append("收盘>=上轨（强势/风险）")
        elif close <= dn:
            sig.append("收盘<=下轨（弱势/反弹）")
    return "；".join(sig) if sig else "无明显信号"


