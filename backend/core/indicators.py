import pandas as pd
import numpy as np


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    df = df.sort_values("trade_date").reset_index(drop=True)
    px = df["close"].astype(float).values

    # RSI指标
    period = 14
    delta = np.diff(px, prepend=px[0])
    up = np.where(delta > 0, delta, 0.0)
    down = np.where(delta < 0, -delta, 0.0)
    roll_up = pd.Series(up).rolling(period).mean()
    roll_down = pd.Series(down).rolling(period).mean()
    rs = roll_up / (roll_down + 1e-9)
    rsi = 100.0 - (100.0 / (1.0 + rs))

    # MACD指标
    ema12 = pd.Series(px).ewm(span=12, adjust=False).mean()
    ema26 = pd.Series(px).ewm(span=26, adjust=False).mean()
    dif = ema12 - ema26
    dea = dif.ewm(span=9, adjust=False).mean()
    macd = (dif - dea) * 2

    # 布林带指标
    ma20 = pd.Series(px).rolling(20).mean()
    std20 = pd.Series(px).rolling(20).std(ddof=0)
    upper = ma20 + 2 * std20
    lower = ma20 - 2 * std20

    # 移动平均线系列
    ma5 = pd.Series(px).rolling(5).mean()
    ma10 = pd.Series(px).rolling(10).mean()
    ma30 = pd.Series(px).rolling(30).mean()
    ma60 = pd.Series(px).rolling(60).mean()

    # 成交量相关指标
    if "vol" in df.columns:
        vol = df["vol"].astype(float).values
        
        # 成交量移动平均
        vol_ma5 = pd.Series(vol).rolling(5).mean()
        vol_ma10 = pd.Series(vol).rolling(10).mean()
        vol_ma20 = pd.Series(vol).rolling(20).mean()
        
        # 价量指标 (Price Volume Trend)
        pct_change = pd.Series(px).pct_change()
        pvt = (pct_change * vol).cumsum()

        # 成交量比率 (Volume Ratio)
        price_diff = pd.Series(px).diff()
        vol_series = pd.Series(vol)
        up_vol = vol_series.where(price_diff > 0, 0.0).rolling(26).sum()
        down_vol = vol_series.where(price_diff < 0, 0.0).rolling(26).sum()
        flat_vol = vol_series.where(price_diff == 0, 0.0).rolling(26).sum()
        vr = (up_vol * 2 + flat_vol) / (down_vol * 2 + 1e-9) * 100
        
        df["vol_ma5"] = vol_ma5.values
        df["vol_ma10"] = vol_ma10.values
        df["vol_ma20"] = vol_ma20.values
        df["pvt"] = pvt.values
        df["vr"] = vr.values

        # 成交量放大倍数
        vol_ma5_series = vol_ma5.replace(0, pd.NA)
        df["vol_ratio"] = (pd.Series(vol) / vol_ma5_series).fillna(1.0).values
    
    # KDJ指标
    if "high" in df.columns and "low" in df.columns:
        high = df["high"].astype(float).values
        low = df["low"].astype(float).values
        
        # 计算RSV
        rsv = pd.Series(index=df.index, dtype=float)
        for i in range(8, len(df)):
            c = px[i]
            h = np.max(high[i-8:i+1])
            l = np.min(low[i-8:i+1])
            if h != l:
                rsv.iloc[i] = (c - l) / (h - l) * 100
            else:
                rsv.iloc[i] = 50
        
        # 计算K、D、J
        k = rsv.ewm(alpha=1/3, adjust=False).mean()
        d = k.ewm(alpha=1/3, adjust=False).mean()
        j = 3 * k - 2 * d
        
        df["kdj_k"] = k.values
        df["kdj_d"] = d.values
        df["kdj_j"] = j.values

    # 威廉指标 (Williams %R)
    if "high" in df.columns and "low" in df.columns:
        wr_period = 14
        wr = pd.Series(index=df.index, dtype=float)
        for i in range(wr_period-1, len(df)):
            hn = np.max(high[i-wr_period+1:i+1])
            ln = np.min(low[i-wr_period+1:i+1])
            if hn != ln:
                wr.iloc[i] = (hn - px[i]) / (hn - ln) * 100
            else:
                wr.iloc[i] = 50
        df["wr"] = wr.values

    # 基本技术指标
    df["rsi14"] = rsi.values
    df["dif"] = dif.values
    df["dea"] = dea.values
    df["macd"] = macd.values
    df["ma5"] = ma5.values
    df["ma10"] = ma10.values
    df["ma20"] = ma20.values
    df["ma30"] = ma30.values
    df["ma60"] = ma60.values
    df["boll_up"] = upper.values
    df["boll_dn"] = lower.values
    df["boll_mid"] = ma20.values
    
    return df


def build_tech_signal(row: pd.Series) -> str:
    sig = []
    
    # RSI信号
    rsi = row.get("rsi14")
    if pd.notna(rsi):
        if rsi < 30:
            sig.append("RSI<30（超卖）")
        elif rsi > 70:
            sig.append("RSI>70（超买）")
        elif rsi < 50:
            sig.append("RSI<50（偏弱）")
        elif rsi > 50:
            sig.append("RSI>50（偏强）")
    
    # MACD信号
    dif, dea = row.get("dif"), row.get("dea")
    if pd.notna(dif) and pd.notna(dea):
        if dif > dea:
            sig.append("DIF>DEA（偏多）")
        elif dif < dea:
            sig.append("DIF<DEA（偏空）")
    
    # 布林带信号
    close, up, dn = row.get("close"), row.get("boll_up"), row.get("boll_dn")
    if pd.notna(close) and pd.notna(up) and pd.notna(dn):
        if close >= up:
            sig.append("收盘>=上轨（强势/风险）")
        elif close <= dn:
            sig.append("收盘<=下轨（弱势/反弹）")
    
    # 移动平均线信号
    ma5, ma10, ma20 = row.get("ma5"), row.get("ma10"), row.get("ma20")
    if pd.notna(close) and pd.notna(ma5) and pd.notna(ma10) and pd.notna(ma20):
        if close > ma5 > ma10 > ma20:
            sig.append("多头排列（强势上涨）")
        elif close < ma5 < ma10 < ma20:
            sig.append("空头排列（弱势下跌）")
        elif close > ma20:
            sig.append("价格>MA20（偏强）")
        elif close < ma20:
            sig.append("价格<MA20（偏弱）")
    
    # KDJ信号
    k, d, j = row.get("kdj_k"), row.get("kdj_d"), row.get("kdj_j")
    if pd.notna(k) and pd.notna(d):
        if k < 20 and d < 20:
            sig.append("KDJ<20（超卖）")
        elif k > 80 and d > 80:
            sig.append("KDJ>80（超买）")
        elif k > d:
            sig.append("K>D（KDJ金叉）")
        elif k < d:
            sig.append("K<D（KDJ死叉）")
    
    # 威廉指标信号
    wr = row.get("wr")
    if pd.notna(wr):
        if wr > 80:
            sig.append("WR>80（超卖）")
        elif wr < 20:
            sig.append("WR<20（超买）")
    
    # 成交量信号
    vol_ratio = row.get("vol_ratio")
    if pd.notna(vol_ratio):
        if vol_ratio > 2:
            sig.append("成交量放大>2倍（放量）")
        elif vol_ratio > 1.5:
            sig.append("成交量放大1.5倍（温和放量）")
        elif vol_ratio < 0.5:
            sig.append("成交量缩减（缩量）")
    
    return "；".join(sig) if sig else "无明显信号"
