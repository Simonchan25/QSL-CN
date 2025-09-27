from __future__ import annotations

import datetime as dt
from typing import Dict, Any, List, Optional
import pandas as pd

from .tushare_client import daily, moneyflow_dc
from .indicators import compute_indicators


def _ymd(days_back: int = 0) -> str:
    d = dt.date.today() - dt.timedelta(days=days_back)
    return d.strftime("%Y%m%d")


def _float(v: Any) -> Optional[float]:
    try:
        x = float(v)
        if pd.notna(x):
            return x
        return None
    except Exception:
        return None


def _last_row(px: pd.DataFrame) -> Dict[str, Any]:
    if px is None or px.empty:
        return {}
    row = px.iloc[-1].to_dict()
    return row


def build_trading_plan(ts_code: str) -> Dict[str, Any]:
    """为单个标的生成可执行交易计划卡片（仅用真实数据，不编造）。

    逻辑：
      - 趋势判定：close vs MA20，MACD（dif-dea）
      - 介入条件：回踩MA5/MA10、放量突破、连板延续情况下的高开回落承接
      - 止损：MA10/MA20 下破或-3%~5%
      - 失效条件：跌破MA20、MACD死叉、主力净流入转负（如可得）
    """
    end = _ymd(0)
    start = (dt.date.today() - dt.timedelta(days=120)).strftime("%Y%m%d")
    px = daily(ts_code, start, end)
    if px is None or px.empty:
        return {"ts_code": ts_code, "note": "价格数据缺失"}

    px = px.sort_values("trade_date").reset_index(drop=True)
    px = compute_indicators(px)
    # 额外均线
    try:
        px["ma5"] = pd.to_numeric(px["close"], errors="coerce").rolling(5).mean()
        px["ma10"] = pd.to_numeric(px["close"], errors="coerce").rolling(10).mean()
    except Exception:
        pass
    last = _last_row(px)
    if not last:
        return {"ts_code": ts_code, "note": "指标计算失败"}

    close = _float(last.get("close"))
    ma5 = _float(last.get("ma5"))
    ma10 = _float(last.get("ma10"))
    ma20 = _float(last.get("ma20"))
    rsi14 = _float(last.get("rsi14"))
    dif = _float(last.get("dif"))
    dea = _float(last.get("dea"))
    macd = _float(last.get("macd"))
    ub = _float(last.get("boll_up")) if last.get("boll_up") is not None else None
    mb = ma20
    lb = _float(last.get("boll_dn")) if last.get("boll_dn") is not None else None

    # 趋势
    trend = "unknown"
    if close is not None and ma20 is not None:
        trend = "up" if close > ma20 else "down" if close < ma20 else "side"
    macd_bias = None
    if dif is not None and dea is not None:
        macd_bias = "bullish" if dif > dea else "bearish"

    # 介入建议（价格仅作参考区间，非指令）
    entries: List[Dict[str, Any]] = []
    if close and ma5 and ma10:
        if trend == "up" and macd_bias == "bullish":
            # 强势回踩
            entries.append({
                "type": "回踩介入",
                "zone": [round(ma5 * 0.995, 2), round(ma5 * 1.005, 2)],
                "rationale": f"close>{'MA20' if ma20 else '均线'} 且 DIF>DEA；回踩MA5承接"
            })
            entries.append({
                "type": "二次确认",
                "zone": [round(ma10 * 0.995, 2), round(ma10 * 1.005, 2)],
                "rationale": "回踩MA10不破并放量（需结合当日量）"
            })
        else:
            # 弱势观望，等待均线夺回
            entries.append({
                "type": "突破跟随",
                "zone": [round(ma20 * 1.005, 2), None] if ma20 else [None, None],
                "rationale": "站回MA20并放量再考虑"
            })

    # 止损位与失效条件
    stops: List[Dict[str, Any]] = []
    invalid: List[str] = []
    if ma10:
        stops.append({"type": "技术止损", "price": round(ma10 * 0.985, 2), "rationale": "跌破MA10且收盘确认"})
    if ma20:
        invalid.append("收盘跌破MA20两日")
    if macd_bias == "bearish":
        invalid.append("MACD死叉并放量下跌")

    # 资金（可选）
    flow_note = None
    try:
        mf = moneyflow_dc(ts_code=ts_code, start_date=start, end_date=end)
        if mf is not None and not mf.empty and "net_amount" in mf.columns:
            last_mf = float(mf.iloc[0]["net_amount"]) if pd.notna(mf.iloc[0]["net_amount"]) else 0.0
            flow_note = f"最新净流入 {round(last_mf/1e6,2)} 百万"
            if last_mf < 0:
                invalid.append("主力净流入转负（当日）")
    except Exception:
        pass

    snapshot = {
        "close": close,
        "ma5": ma5,
        "ma10": ma10,
        "ma20": ma20,
        "rsi14": rsi14,
        "dif": dif,
        "dea": dea,
        "macd": macd,
        "bb_up": ub,
        "bb_mid": mb,
        "bb_low": lb,
    }

    plan = {
        "ts_code": ts_code,
        "trend": trend,
        "macd": macd_bias,
        "entries": entries,
        "stops": stops,
        "invalid_conditions": invalid,
        "notes": [flow_note] if flow_note else [],
        "snapshot": snapshot,
    }
    return plan


def build_trading_plans_for_picks(picks: List[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for item in picks[:max(1, int(limit))]:
        ts_code = item.get("ts_code")
        if not ts_code:
            continue
        plan = build_trading_plan(ts_code)
        plan["name"] = item.get("name")
        plan["score"] = item.get("score")
        out.append(plan)
    return out
