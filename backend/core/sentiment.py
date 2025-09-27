"""增强情绪面分析模块"""
from __future__ import annotations

import datetime as dt
from typing import Dict, Any, List, Optional
import pandas as pd

from .tushare_client import moneyflow, margin_detail, moneyflow_hsgt
from .news import analyze_news_sentiment


def analyze_moneyflow(ts_code: str, days: int = 20) -> Dict[str, Any]:
    """分析个股资金流向"""
    end_date = dt.date.today().strftime("%Y%m%d")
    start_date = (dt.date.today() - dt.timedelta(days=days)).strftime("%Y%m%d")
    
    mf = moneyflow(ts_code, start_date, end_date)
    
    result = {
        "has_data": False,
        "net_inflow_days": 0,
        "total_net_inflow": 0,
        "main_net_inflow": 0,  # 主力净流入
        "retail_net_inflow": 0,  # 散户净流入
        "flow_trend": "neutral",
        "flow_signals": []
    }
    
    if mf is not None and not mf.empty:
        result["has_data"] = True
        mf = mf.sort_values("trade_date")
        
        # 计算净流入天数
        mf["net_amount"] = mf["buy_elg_amount"] + mf["buy_lg_amount"] + mf["buy_md_amount"] + mf["buy_sm_amount"] - \
                          mf["sell_elg_amount"] - mf["sell_lg_amount"] - mf["sell_md_amount"] - mf["sell_sm_amount"]
        
        result["net_inflow_days"] = len(mf[mf["net_amount"] > 0])
        result["total_net_inflow"] = round(mf["net_amount"].sum() / 10000, 2)  # 转换为万元
        
        # 主力资金（超大单+大单）
        mf["main_net"] = mf["buy_elg_amount"] + mf["buy_lg_amount"] - mf["sell_elg_amount"] - mf["sell_lg_amount"]
        result["main_net_inflow"] = round(mf["main_net"].sum() / 10000, 2)
        
        # 散户资金（中单+小单）
        mf["retail_net"] = mf["buy_md_amount"] + mf["buy_sm_amount"] - mf["sell_md_amount"] - mf["sell_sm_amount"]
        result["retail_net_inflow"] = round(mf["retail_net"].sum() / 10000, 2)
        
        # 判断资金流向趋势
        recent_5d = mf.tail(5)
        recent_main_net = recent_5d["main_net"].sum()
        
        if recent_main_net > 0:
            if recent_main_net > mf["main_net"].mean() * 5 * 2:
                result["flow_trend"] = "strong_inflow"
                result["flow_signals"].append("主力大幅流入")
            else:
                result["flow_trend"] = "inflow"
                result["flow_signals"].append("主力温和流入")
        elif recent_main_net < 0:
            if abs(recent_main_net) > abs(mf["main_net"].mean()) * 5 * 2:
                result["flow_trend"] = "strong_outflow"
                result["flow_signals"].append("主力大幅流出")
            else:
                result["flow_trend"] = "outflow"
                result["flow_signals"].append("主力温和流出")
        
        # 主力与散户背离
        if result["main_net_inflow"] > 0 and result["retail_net_inflow"] < 0:
            result["flow_signals"].append("主力吸筹，散户离场")
        elif result["main_net_inflow"] < 0 and result["retail_net_inflow"] > 0:
            result["flow_signals"].append("主力出货，散户接盘")
    
    return result


def analyze_margin_trading(ts_code: str) -> Dict[str, Any]:
    """分析融资融券数据"""
    today = dt.date.today().strftime("%Y%m%d")
    
    margin = margin_detail(ts_code=ts_code, trade_date=today)
    if margin.empty:
        # 尝试获取最近的数据
        margin = margin_detail(ts_code=ts_code)
    
    result = {
        "has_data": False,
        "margin_balance": None,  # 融资余额
        "short_balance": None,   # 融券余额
        "margin_ratio": None,    # 融资占比
        "margin_signal": []
    }
    
    if margin is not None and not margin.empty:
        margin = margin.sort_values("trade_date", ascending=False).reset_index(drop=True)
        latest = margin.iloc[0]
        
        result["has_data"] = True
        result["margin_balance"] = round(float(latest.get("rzye", 0)) / 100000000, 2) if latest.get("rzye") else None  # 亿元
        result["short_balance"] = round(float(latest.get("rqye", 0)) / 100000000, 4) if latest.get("rqye") else None   # 亿元
        
        if result["margin_balance"] and result["short_balance"]:
            total = result["margin_balance"] + result["short_balance"]
            if total > 0:
                result["margin_ratio"] = round(result["margin_balance"] / total * 100, 2)
        
        # 分析信号
        if len(margin) >= 5:
            recent_margin = margin.head(5)["rzye"].mean()
            prev_margin = margin.iloc[5:10]["rzye"].mean() if len(margin) >= 10 else recent_margin
            
            if recent_margin > prev_margin * 1.1:
                result["margin_signal"].append("融资余额增加，看多情绪升温")
            elif recent_margin < prev_margin * 0.9:
                result["margin_signal"].append("融资余额减少，看多情绪降温")
    
    return result


def analyze_northbound_flow() -> Dict[str, Any]:
    """分析北向资金流向"""
    result = {
        "has_data": False,
        "hgt_net": None,  # 沪股通净流入
        "sgt_net": None,  # 深股通净流入
        "total_net": None,  # 总净流入
        "north_signal": []
    }
    
    try:
        # 获取最近几天的数据，不指定具体日期
        end_date = dt.date.today().strftime("%Y%m%d")
        start_date = (dt.date.today() - dt.timedelta(days=7)).strftime("%Y%m%d")
        
        hsgt = moneyflow_hsgt(start_date=start_date, end_date=end_date)
        if hsgt.empty:
            # 如果还是空，尝试更大的时间范围
            start_date = (dt.date.today() - dt.timedelta(days=15)).strftime("%Y%m%d")
            hsgt = moneyflow_hsgt(start_date=start_date, end_date=end_date)
    except Exception as e:
        # 如果API失败，返回空数据
        print(f"Warning: 北向资金数据获取失败: {e}")
        return result
    
    if hsgt is not None and not hsgt.empty:
        hsgt = hsgt.sort_values("trade_date", ascending=False).reset_index(drop=True)
        
        # 计算最近5日累计
        recent_5d = hsgt.head(5)
        
        result["has_data"] = True
        result["hgt_net"] = round(recent_5d["hgt_net"].sum() / 100, 2) if "hgt_net" in recent_5d.columns else None  # 亿元
        result["sgt_net"] = round(recent_5d["sgt_net"].sum() / 100, 2) if "sgt_net" in recent_5d.columns else None  # 亿元
        
        if result["hgt_net"] is not None and result["sgt_net"] is not None:
            result["total_net"] = round(result["hgt_net"] + result["sgt_net"], 2)
            
            if result["total_net"] > 100:
                result["north_signal"].append("北向资金大幅流入")
            elif result["total_net"] > 50:
                result["north_signal"].append("北向资金温和流入")
            elif result["total_net"] < -100:
                result["north_signal"].append("北向资金大幅流出")
            elif result["total_net"] < -50:
                result["north_signal"].append("北向资金温和流出")
            else:
                result["north_signal"].append("北向资金流向平稳")
    
    return result


def calculate_sentiment_score(
    news_sentiment: Dict[str, Any],
    moneyflow_data: Dict[str, Any],
    margin_data: Dict[str, Any],
    north_data: Dict[str, Any]
) -> float:
    """计算情绪综合评分"""
    score = 50  # 基础分
    
    # 新闻情绪（权重30%）
    if news_sentiment:
        overall = news_sentiment.get("overall")
        if overall == "positive":
            score += 15
        elif overall == "negative":
            score -= 15
        
        pos_pct = news_sentiment.get("percentages", {}).get("positive", 0)
        if pos_pct > 60:
            score += 10
        elif pos_pct > 40:
            score += 5
        elif pos_pct < 20:
            score -= 10
    
    # 资金流向（权重40%）
    if moneyflow_data.get("has_data"):
        if moneyflow_data["flow_trend"] == "strong_inflow":
            score += 20
        elif moneyflow_data["flow_trend"] == "inflow":
            score += 10
        elif moneyflow_data["flow_trend"] == "outflow":
            score -= 10
        elif moneyflow_data["flow_trend"] == "strong_outflow":
            score -= 20
        
        # 主力散户背离
        if "主力吸筹" in str(moneyflow_data.get("flow_signals", [])):
            score += 5
        elif "主力出货" in str(moneyflow_data.get("flow_signals", [])):
            score -= 5
    
    # 融资融券（权重15%）
    if margin_data.get("has_data"):
        for signal in margin_data.get("margin_signal", []):
            if "看多情绪升温" in signal:
                score += 8
            elif "看多情绪降温" in signal:
                score -= 8
    
    # 北向资金（权重15%）
    if north_data.get("has_data"):
        for signal in north_data.get("north_signal", []):
            if "大幅流入" in signal:
                score += 10
            elif "温和流入" in signal:
                score += 5
            elif "大幅流出" in signal:
                score -= 10
            elif "温和流出" in signal:
                score -= 5
    
    return min(100, max(0, score))


def enhanced_sentiment_analysis(
    ts_code: str,
    news_data: Dict[str, Any] = None
) -> Dict[str, Any]:
    """增强情绪面分析"""
    
    # 新闻情绪分析
    news_sentiment = {}
    if news_data:
        news_sentiment = analyze_news_sentiment(news_data)
    
    # 资金流向分析
    moneyflow_data = analyze_moneyflow(ts_code)
    
    # 融资融券分析
    margin_data = analyze_margin_trading(ts_code)
    
    # 北向资金分析
    north_data = analyze_northbound_flow()
    
    # 计算综合情绪评分
    sentiment_score = calculate_sentiment_score(
        news_sentiment,
        moneyflow_data,
        margin_data,
        north_data
    )
    
    return {
        "news_sentiment": news_sentiment,
        "moneyflow": moneyflow_data,
        "margin_trading": margin_data,
        "northbound": north_data,
        "sentiment_score": round(sentiment_score, 1),
        "sentiment_level": (
            "极度乐观" if sentiment_score >= 80 else
            "乐观" if sentiment_score >= 65 else
            "中性偏多" if sentiment_score >= 55 else
            "中性" if sentiment_score >= 45 else
            "中性偏空" if sentiment_score >= 35 else
            "悲观" if sentiment_score >= 20 else
            "极度悲观"
        )
    }