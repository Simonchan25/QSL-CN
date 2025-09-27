from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


def _fmt_number(value: Optional[float], digits: int = 2, unit: str = "") -> Optional[str]:
    try:
        if value is None:
            return None
        return f"{float(value):.{digits}f}{unit}"
    except (TypeError, ValueError):
        return None


def _fmt_pct(value: Optional[float], digits: int = 1) -> Optional[str]:
    try:
        if value is None:
            return None
        return f"{float(value):.{digits}f}%"
    except (TypeError, ValueError):
        return None


def _calc_yoy(records: List[Dict[str, Any]], field: str) -> Optional[float]:
    values: List[float] = []
    for row in records:
        raw = row.get(field)
        if raw is None:
            continue
        try:
            values.append(float(raw))
        except (TypeError, ValueError):
            continue
        if len(values) >= 2:
            break
    if len(values) < 2 or values[1] == 0:
        return None
    return (values[0] - values[1]) / abs(values[1]) * 100


def _latest_record(records: List[Dict[str, Any]], *fields: str) -> Dict[str, Any]:
    if not records:
        return {}
    record = {}
    for key in fields:
        record[key] = records[0].get(key)
    return record


def _pick_positive(items: List[str]) -> List[str]:
    return [item for item in items if item]


def build_stock_insights(payload: Dict[str, Any]) -> Dict[str, Any]:
    basic = payload.get("basic", {})
    technical = payload.get("technical", {})
    fundamental = payload.get("fundamental", {})
    sentiment = payload.get("sentiment", {})
    capital_flow = payload.get("capital_flow", {})
    dividend = payload.get("dividend", {})
    holders = payload.get("holders", {})

    price_points: List[str] = []
    momentum_points: List[str] = []

    last_close = technical.get("tech_last_close")
    change_1d = technical.get("tech_return_1d")
    change_5d = technical.get("tech_return_5d")
    change_20d = technical.get("tech_return_20d")
    change_60d = technical.get("tech_return_60d")
    high_52w = technical.get("tech_52w_high")
    low_52w = technical.get("tech_52w_low")

    if last_close is not None:
        price_points.append(f"收盘价：{_fmt_number(last_close, 2, '元')}")
    if change_1d is not None:
        price_points.append(f"日涨跌幅：{_fmt_pct(change_1d)}")
    if change_5d is not None:
        momentum_points.append(f"5日累计：{_fmt_pct(change_5d)}")
    if change_20d is not None:
        momentum_points.append(f"20日累计：{_fmt_pct(change_20d)}")
    if change_60d is not None:
        momentum_points.append(f"60日累计：{_fmt_pct(change_60d)}")
    if high_52w is not None and last_close is not None:
        distance = (last_close - high_52w) / high_52w * 100 if high_52w else None
        if distance is not None:
            momentum_points.append(f"距52周高点：{_fmt_pct(distance)}")
    if low_52w is not None and last_close is not None:
        rebound = (last_close - low_52w) / low_52w * 100 if low_52w else None
        if rebound is not None:
            momentum_points.append(f"距52周低点反弹：{_fmt_pct(rebound)}")

    valuation = fundamental.get("valuation", {})
    fina_indicator = fundamental.get("fina_indicator_latest", {})
    income_recent = fundamental.get("income_recent", [])
    cashflow_recent = fundamental.get("cashflow_recent", [])
    balance_recent = fundamental.get("balance_recent", [])

    fundamental_points: List[str] = []
    roe = fina_indicator.get("roe")
    net_margin = fina_indicator.get("netprofit_margin")
    gross_margin = fina_indicator.get("grossprofit_margin")
    debt_ratio = None
    if balance_recent:
        debt_ratio = balance_recent[0].get("debt_ratio")

    if roe is not None:
        level = "卓越" if roe >= 20 else "优秀" if roe >= 15 else "稳健" if roe >= 10 else "一般"
        fundamental_points.append(f"ROE：{_fmt_pct(roe)}（{level}）")
    if net_margin is not None:
        fundamental_points.append(f"净利率：{_fmt_pct(net_margin)}")
    if gross_margin is not None:
        fundamental_points.append(f"毛利率：{_fmt_pct(gross_margin)}")
    if valuation.get("pe_ttm"):
        fundamental_points.append(f"PE(TTM)：{_fmt_number(valuation['pe_ttm'], 1)}倍")
    if valuation.get("pb"):
        fundamental_points.append(f"PB：{_fmt_number(valuation['pb'], 2)}倍")
    if valuation.get("ps_ttm"):
        fundamental_points.append(f"PS(TTM)：{_fmt_number(valuation['ps_ttm'], 2)}倍")

    revenue_yoy = _calc_yoy(income_recent, "revenue") if income_recent else None
    profit_yoy = _calc_yoy(income_recent, "n_income") if income_recent else None
    cashflow_yoy = _calc_yoy(cashflow_recent, "n_cashflow_act") if cashflow_recent else None

    growth_points: List[str] = []
    if revenue_yoy is not None:
        growth_points.append(f"营收同比：{_fmt_pct(revenue_yoy)}")
    if profit_yoy is not None:
        growth_points.append(f"净利同比：{_fmt_pct(profit_yoy)}")
    if cashflow_yoy is not None:
        growth_points.append(f"经营现金流同比：{_fmt_pct(cashflow_yoy)}")

    risk_points: List[str] = []
    if debt_ratio is not None:
        debt_pct = debt_ratio * 100 if debt_ratio <= 1 else debt_ratio
        qualifier = "偏高" if debt_pct > 65 else "适中" if debt_pct > 35 else "偏低"
        risk_points.append(f"资产负债率：{_fmt_pct(debt_pct)}（{qualifier}）")
    quick_ratio = fina_indicator.get("quick_ratio")
    if quick_ratio is not None:
        qualifier = "充裕" if quick_ratio >= 1.5 else "尚可" if quick_ratio >= 1.0 else "偏紧"
        risk_points.append(f"速动比率：{_fmt_number(quick_ratio, 2)}（{qualifier}）")

    capital_points: List[str] = []
    flow = capital_flow.get("tushare", {})
    if flow:
        net_amount = flow.get("net_amount")
        if net_amount is not None:
            capital_points.append(f"最新主力净流入：{_fmt_number(net_amount / 10000, 2, '万元')}")
    ths_flow = capital_flow.get("ths", {})
    if ths_flow:
        net_amount = ths_flow.get("net_amount")
        if net_amount is not None:
            capital_points.append(f"同花顺净流入：{_fmt_number(net_amount / 10000, 2, '万元')}")
    sentiment_score = sentiment.get("sentiment_score")
    if sentiment_score is not None:
        capital_points.append(f"综合情绪得分：{_fmt_number(sentiment_score, 1)}分（{sentiment.get('sentiment_level', '')}）")

    if holders.get("top10_holders"):
        first = holders["top10_holders"][0]
        holder_pct = first.get("hold_ratio")
        if holder_pct is not None:
            capital_points.append(f"第一大股东持股：{_fmt_pct(holder_pct)}")

    dividend_points: List[str] = []
    if dividend.get("recent_dividends"):
        latest_div = dividend["recent_dividends"][0]
        cash = latest_div.get("cash_div")
        if cash is not None:
            dividend_points.append(f"最新分红：每10股派{_fmt_number(cash, 2)}元")

    opportunities: List[str] = []
    if change_20d and change_20d > 10:
        opportunities.append("阶段性动能显著，短期趋势偏强")
    if revenue_yoy and revenue_yoy > 20:
        opportunities.append("营收增速高于20%，增长势头具备弹性")
    if sentiment_score and sentiment_score >= 65:
        opportunities.append("资金情绪偏乐观，主力流入信号积极")

    if not opportunities and change_5d and change_5d > 5:
        opportunities.append("近期涨幅领先行业，存在交易性机会")

    risks: List[str] = []
    if debt_ratio and debt_ratio > 0.65:
        risks.append("资产负债率高于65%，财务杠杆偏高")
    if sentiment_score and sentiment_score < 40:
        risks.append("情绪得分低于40，短线承压迹象明显")
    if change_20d and change_20d < -10:
        risks.append("近20日跌幅超过10%，技术面仍在下行通道")
    if profit_yoy is not None and profit_yoy < 0:
        risks.append("净利润同比为负，需要留意盈利修复节奏")

    summary_text: List[str] = []
    name = basic.get("name") or basic.get("ts_code", "该股")
    if last_close is not None and change_20d is not None and roe is not None:
        summary_text.append(
            f"{name}收盘{_fmt_number(last_close, 2, '元')}，近20日{_fmt_pct(change_20d)}；ROE为{_fmt_pct(roe)}，"
            f"净利率{_fmt_pct(net_margin)}，估值PE(TTM){_fmt_number(valuation.get('pe_ttm'), 1)}倍。"
        )
    elif last_close is not None:
        summary_text.append(f"{name}最新收盘{_fmt_number(last_close, 2, '元')}，短期趋势{_fmt_pct(change_5d)}。")
    if opportunities:
        summary_text.append("机会聚焦：" + "；".join(opportunities))
    if risks:
        summary_text.append("核心风险：" + "；".join(risks))

    return {
        "price_overview": _pick_positive(price_points),
        "momentum": _pick_positive(momentum_points),
        "fundamentals": _pick_positive(fundamental_points),
        "growth": _pick_positive(growth_points),
        "capital": _pick_positive(capital_points),
        "dividend": _pick_positive(dividend_points),
        "opportunities": opportunities,
        "risks": risks,
        "summary": "".join(summary_text)
    }


def build_hotspot_insights(hotspot_payload: Dict[str, Any]) -> Dict[str, Any]:
    stocks = hotspot_payload.get("stocks") or hotspot_payload.get("related_stocks") or []
    news_sentiment = hotspot_payload.get("news_sentiment", {})
    keyword = hotspot_payload.get("keyword")

    if not stocks:
        return {
            "keyword": keyword,
            "summary": f"暂未检索到与{keyword}相关的A股标的，建议关注后续上市公司公告或概念库更新。",
            "leaders": [],
            "risks": ["缺乏直接受益标的，交易机会有限"]
        }

    def _score(item: Dict[str, Any]) -> float:
        val = item.get("final_score")
        if val is None:
            val = item.get("total_score")
        if val is None:
            return 0.0
        try:
            return float(val)
        except (TypeError, ValueError):
            return 0.0

    top_by_score = sorted(stocks, key=lambda x: _score(x), reverse=True)[:5]
    top_by_momentum = sorted(stocks, key=lambda x: x.get("price_change_pct", 0) or 0, reverse=True)[:3]

    avg_score = sum(_score(s) for s in stocks) / len(stocks)
    avg_price_change = sum((s.get("price_change_pct") or 0) for s in stocks) / len(stocks)

    sentiment_tag = news_sentiment.get("overall")
    sentiment_desc = {
        "positive": "舆情偏正面",
        "negative": "舆情偏负面",
        "neutral": "舆情中性"
    }.get(sentiment_tag, "舆情数据有限")

    leaders = [
        f"{item.get('name', item.get('ts_code'))}（综合{_fmt_number(_score(item), 1)}分，日变动{_fmt_pct(item.get('price_change_pct'))}）"
        for item in top_by_score
        if item
    ]

    momentum_leaders = [
        f"{item.get('name', item.get('ts_code'))}（当日{_fmt_pct(item.get('price_change_pct'))}）"
        for item in top_by_momentum
        if item
    ]

    opportunities: List[str] = []
    if avg_price_change > 1:
        opportunities.append("概念内标的整体呈现正回报，资金关注度回升")
    if avg_score > 70:
        opportunities.append("龙头股多维评分高于70分，具备延续性")
    if sentiment_tag == "positive":
        opportunities.append("新闻舆情正向，可作为事件驱动线索")

    risks: List[str] = []
    if avg_price_change < 0:
        risks.append("多数个股回调，追高需谨慎")
    if sentiment_tag == "negative":
        risks.append("负面舆情占主导，短线波动风险上升")

    summary_parts: List[str] = []
    summary_parts.append(
        f"{keyword}概念覆盖{len(stocks)}只核心标的，平均日变动{_fmt_pct(avg_price_change)}，平均综合得分{_fmt_number(avg_score, 1)}分。"
    )
    if leaders:
        summary_parts.append("领先梯队：" + "；".join(leaders))
    if momentum_leaders:
        summary_parts.append("短线强势：" + "；".join(momentum_leaders))
    summary_parts.append(f"舆情观察：{sentiment_desc}")
    if opportunities:
        summary_parts.append("交易思路：" + "；".join(opportunities))
    if risks:
        summary_parts.append("风险提示：" + "；".join(risks))

    return {
        "keyword": keyword,
        "leaders": leaders,
        "momentum_leaders": momentum_leaders,
        "avg_score": round(avg_score, 1),
        "avg_price_change": round(avg_price_change, 2),
        "opportunities": opportunities,
        "risks": risks,
        "summary": "".join(summary_parts)
    }


def build_report_summary(sections: Dict[str, Any]) -> Dict[str, Any]:
    board_info = sections.get("board_analysis", {})
    capital_flow = sections.get("capital_flow", {})
    hotspots = sections.get("hot_sectors", {})
    sentiment = sections.get("market_sentiment", {})

    highlights: List[str] = []

    if board_info:
        leading = board_info.get("top_boards") or board_info.get("boards")
        if leading:
            first = leading[0]
            name = first.get("name") or first.get("board_name")
            limit_up = first.get("limit_up_count") or first.get("limit_up")
            if name and limit_up is not None:
                highlights.append(f"连板梯队由{name}领跑，今日涨停{int(limit_up)}家")

    if capital_flow:
        north = capital_flow.get("northbound")
        if north and north.get("total_net") is not None:
            highlights.append(f"北向资金{_fmt_number(north['total_net'], 2, '亿元')}净流入")
        main_capital = capital_flow.get("main_capital")
        if main_capital and main_capital.get("net_main") is not None:
            amount = _fmt_number(main_capital.get("net_main"), 2, "亿元")
            highlights.append(f"主力资金净{ '流入' if (main_capital.get('net_main') or 0) >= 0 else '流出'}{amount}")

    if hotspots:
        exceptional = hotspots.get("top_sectors") or hotspots.get("sectors")
        if exceptional:
            names = [item.get("name") for item in exceptional[:3] if item.get("name")]
            if names:
                highlights.append("热点板块集中在：" + "、".join(names))

    if sentiment:
        sentiment_level = sentiment.get("sentiment_level") or sentiment.get("market_sentiment_level")
        if sentiment_level:
            highlights.append(f"市场情绪定位：{sentiment_level}")

    return {
        "highlights": highlights,
        "summary": "；".join(highlights) if highlights else "市场数据有限，建议稍后重试"
    }
