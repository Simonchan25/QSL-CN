from __future__ import annotations

import datetime as dt
from typing import List, Dict, Any, Optional
import pandas as pd

from .tushare_client import (
    daily_basic, moneyflow_dc, limit_list_d, ths_hot, stock_basic
)
from .trading_date_helper import get_recent_trading_dates


def _today_ymd() -> str:
    return dt.date.today().strftime("%Y%m%d")


def _to_ymd(date_str: Optional[str]) -> str:
    if not date_str:
        return _today_ymd()
    return date_str.replace("-", "")


def _safe_rank(series: pd.Series, ascending: bool = True) -> pd.Series:
    try:
        sr = pd.to_numeric(series, errors="coerce")
        pct = sr.rank(pct=True, ascending=ascending)
        return (pct * 100.0).fillna(0.0)
    except Exception:
        return pd.Series([0.0] * len(series), index=series.index)


def _extract_boards(up_stat: Any) -> int:
    try:
        s = str(up_stat or "")
        if "/" in s:
            return int(s.split("/")[0])
        if s.isdigit():
            return int(s)
        return 0
    except Exception:
        return 0


def get_top_picks(trade_date: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
    """多维度选股（估值/动量/资金/连板/热度），严格只用当期数据。

    Args:
        trade_date: YYYYMMDD 或 YYYY-MM-DD；为空则用最近交易日
        limit: 返回数量
    """
    # 选定交易日
    td = _to_ymd(trade_date)
    if not trade_date:
        dates = get_recent_trading_dates(1)
        if dates:
            td = dates[0]

    # 1) 横截面基础面/估值（若指定日期无数据，向前查找最近有数据的交易日）
    db = daily_basic(trade_date=td)
    if db is None or db.empty:
        # 向前寻找最近的有效交易日（不使用缓存或旧数据文件，仅查询API）
        for dt0 in get_recent_trading_dates(10):
            db = daily_basic(trade_date=dt0)
            if db is not None and not db.empty:
                td = dt0
                break
        if db is None or db.empty:
            return []
    base = stock_basic()
    names = {}
    if base is not None and not base.empty:
        names = {r.ts_code: r.name for _, r in base.iterrows() if r.get("list_status") == "L"}

    df = db.copy()
    # 2) 资金与动量（东方财富个股资金流）
    try:
        mf = moneyflow_dc(trade_date=td)
        if mf is not None and not mf.empty:
            mf = mf[[c for c in mf.columns if c in ("ts_code", "net_amount", "pct_change")]]
            df = df.merge(mf, on="ts_code", how="left")
    except Exception:
        pass

    # 3) 涨停与连板
    try:
        lmt = limit_list_d(trade_date=td, limit_type='U')
        if lmt is not None and not lmt.empty:
            lmt = lmt[[c for c in lmt.columns if c in ("ts_code", "up_stat", "limit_times", "pct_chg")]].copy()
            lmt["boards"] = lmt["up_stat"].map(_extract_boards)
            df = df.merge(lmt[["ts_code", "boards", "limit_times"]], on="ts_code", how="left")
    except Exception:
        pass

    # 4) 同花顺热榜标记
    try:
        th = ths_hot(trade_date=td)
        if th is not None and not th.empty:
            hot_stocks = set(th[th['data_type'] == '热股']["ts_code"].dropna().tolist())
            df["is_ths_hot"] = df["ts_code"].isin(hot_stocks).astype(int)
        else:
            df["is_ths_hot"] = 0
    except Exception:
        df["is_ths_hot"] = 0

    # 因子工程
    # 估值（低更好）：PE、PB
    df["pe_val"] = _safe_rank(df.get("pe"), ascending=True)
    df["pb_val"] = _safe_rank(df.get("pb"), ascending=True)
    df["val_score"] = (100 - df[["pe_val", "pb_val"]].mean(axis=1)).fillna(0)

    # 动量（高更好）：当日涨跌幅（来自资金流或limit列表），换手率
    mom_src = df.get("pct_change") if "pct_change" in df.columns else df.get("pct_chg")
    df["mom_chg"] = _safe_rank(mom_src, ascending=True)  # 当日涨幅越高分越高
    df["mom_turn"] = _safe_rank(df.get("turnover_rate"), ascending=True)
    df["mom_score"] = df[["mom_chg", "mom_turn"]].mean(axis=1).fillna(0)

    # 资金（高更好）：净流入绝对额（可选做市值归一，这里直接排名）
    df["flow_score"] = _safe_rank(df.get("net_amount"), ascending=True)

    # 连板：boards、limit_times
    df["boards"] = pd.to_numeric(df.get("boards"), errors="coerce").fillna(0)
    df["limit_times"] = pd.to_numeric(df.get("limit_times"), errors="coerce").fillna(0)
    df["board_score"] = (df["boards"] * 12 + df["limit_times"] * 4).clip(lower=0)

    # 热度
    df["hype_score"] = df.get("is_ths_hot", 0) * 20

    # 风险惩罚：极端估值/特殊处理
    pe = pd.to_numeric(df.get("pe"), errors="coerce")
    pb = pd.to_numeric(df.get("pb"), errors="coerce")
    penalty = 0.0
    df["risk_penalty"] = (
        (pe.gt(80).fillna(False)).astype(int) * 10 +
        (pb.gt(8).fillna(False)).astype(int) * 6
    )

    # 组合得分（0-100+）
    df["final_score"] = (
        df["val_score"] * 0.25 +
        df["mom_score"] * 0.25 +
        df["flow_score"] * 0.25 +
        df["board_score"] * 0.15 +
        df["hype_score"] * 0.10 -
        df["risk_penalty"]
    )

    # 基本过滤：排除无流通市值、价格/估值缺失严重者
    df = df[df.get("circ_mv").notna()]

    # 补充名称与证据
    def _row_to_pick(r: pd.Series) -> Dict[str, Any]:
        code = r.get("ts_code")
        return {
            "ts_code": code,
            "name": names.get(code) or str(code),
            "score": round(float(r.get("final_score", 0)), 2),
            "scores": {
                "valuation": round(float(r.get("val_score", 0)), 1),
                "momentum": round(float(r.get("mom_score", 0)), 1),
                "capital": round(float(r.get("flow_score", 0)), 1),
                "boards": round(float(r.get("board_score", 0)), 1),
                "hype": round(float(r.get("hype_score", 0)), 1),
                "risk_penalty": round(float(r.get("risk_penalty", 0)), 1),
            },
            "evidence": {
                "pe": r.get("pe"),
                "pb": r.get("pb"),
                "turnover_rate": r.get("turnover_rate"),
                "net_amount": r.get("net_amount"),
                "pct_change": (r.get("pct_change") if pd.notna(r.get("pct_change")) else r.get("pct_chg")),
                "boards": int(r.get("boards", 0) or 0),
                "limit_times": int(r.get("limit_times", 0) or 0),
                "is_ths_hot": bool(r.get("is_ths_hot", 0) == 1),
                "trade_date": td,
            }
        }

    # 排序并输出
    df = df.sort_values("final_score", ascending=False)
    picks = [_row_to_pick(r) for _, r in df.head(max(1, int(limit))).iterrows()]
    return picks
