"""增强技术面分析模块"""
from __future__ import annotations

import datetime as dt
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np

from .tushare_client import daily, stk_limit, index_daily
from .indicators import compute_indicators, build_tech_signal


def analyze_limit_status(ts_code: str, days_back: int = 30) -> Dict[str, Any]:
    """分析涨跌停状态和连板情况"""
    end_date = dt.date.today().strftime("%Y%m%d")
    start_date = (dt.date.today() - dt.timedelta(days=days_back)).strftime("%Y%m%d")
    
    # 获取涨跌停数据
    limit_data = stk_limit(ts_code=ts_code)
    
    result = {
        "has_limit_history": False,
        "recent_limit_count": 0,
        "max_continuous_limit": 0,
        "last_limit_date": None,
        "limit_details": []
    }
    
    if limit_data is not None and not limit_data.empty:
        # 筛选近期数据
        limit_data["trade_date"] = pd.to_datetime(limit_data["trade_date"], format="%Y%m%d")
        start_dt = pd.to_datetime(start_date, format="%Y%m%d")
        recent_limits = limit_data[limit_data["trade_date"] >= start_dt]
        
        if not recent_limits.empty:
            result["has_limit_history"] = True
            result["recent_limit_count"] = len(recent_limits)
            
            # 按日期排序
            recent_limits = recent_limits.sort_values("trade_date")
            result["last_limit_date"] = recent_limits.iloc[-1]["trade_date"].strftime("%Y%m%d")
            
            # 计算连板
            continuous = 1
            max_continuous = 1
            prev_date = None
            
            for _, row in recent_limits.iterrows():
                curr_date = row["trade_date"]
                
                if prev_date and (curr_date - prev_date).days == 1:
                    continuous += 1
                    max_continuous = max(max_continuous, continuous)
                else:
                    continuous = 1
                
                limit_type = "涨停" if row.get("up_limit", 0) > 0 else "跌停"
                result["limit_details"].append({
                    "date": curr_date.strftime("%Y%m%d"),
                    "type": limit_type,
                    "limit_price": row.get("up_limit") or row.get("down_limit")
                })
                
                prev_date = curr_date
            
            result["max_continuous_limit"] = max_continuous
    
    return result


def analyze_vs_index(ts_code: str, index_code: str = "000001.SH", days: int = 60) -> Dict[str, Any]:
    """分析个股相对指数的强弱"""
    end_date = dt.date.today().strftime("%Y%m%d")
    start_date = (dt.date.today() - dt.timedelta(days=days)).strftime("%Y%m%d")
    
    # 获取个股数据
    stock_data = daily(ts_code, start_date, end_date)
    # 获取指数数据
    index_data = index_daily(index_code, start_date, end_date)
    
    result = {
        "relative_strength": None,
        "stock_return": None,
        "index_return": None,
        "outperform": None,
        "correlation": None
    }
    
    if (stock_data is not None and not stock_data.empty and 
        index_data is not None and not index_data.empty):
        
        # 计算收益率
        stock_data = stock_data.sort_values("trade_date")
        index_data = index_data.sort_values("trade_date")
        
        if len(stock_data) >= 2 and len(index_data) >= 2:
            stock_start = float(stock_data.iloc[0]["close"])
            stock_end = float(stock_data.iloc[-1]["close"])
            stock_return = (stock_end - stock_start) / stock_start * 100
            
            index_start = float(index_data.iloc[0]["close"])
            index_end = float(index_data.iloc[-1]["close"])
            index_return = (index_end - index_start) / index_start * 100
            
            result["stock_return"] = round(stock_return, 2)
            result["index_return"] = round(index_return, 2)
            result["outperform"] = round(stock_return - index_return, 2)
            
            # 计算相对强弱
            if index_return != 0:
                result["relative_strength"] = round(stock_return / index_return, 2)
            
            # 计算相关性
            if len(stock_data) >= 10 and len(index_data) >= 10:
                # 对齐数据
                merged = pd.merge(
                    stock_data[["trade_date", "pct_chg"]].rename(columns={"pct_chg": "stock_pct"}),
                    index_data[["trade_date", "pct_chg"]].rename(columns={"pct_chg": "index_pct"}),
                    on="trade_date"
                )
                if len(merged) >= 10:
                    correlation = merged["stock_pct"].corr(merged["index_pct"])
                    result["correlation"] = round(correlation, 3)
    
    return result


def analyze_volume_pattern(px_data: pd.DataFrame) -> Dict[str, Any]:
    """分析成交量模式"""
    if px_data is None or px_data.empty or len(px_data) < 20:
        return {"volume_trend": "insufficient_data"}
    
    px_data = px_data.sort_values("trade_date").tail(60)  # 最近60天
    
    # 计算成交量均线
    px_data["vol_ma5"] = px_data["vol"].rolling(5).mean()
    px_data["vol_ma20"] = px_data["vol"].rolling(20).mean()
    
    result = {
        "volume_trend": "normal",
        "recent_volume_ratio": None,
        "volume_signal": []
    }
    
    if len(px_data) >= 20:
        recent = px_data.tail(5)
        avg_recent_vol = recent["vol"].mean()
        avg_20d_vol = px_data.tail(20)["vol"].mean()
        
        if avg_20d_vol > 0:
            vol_ratio = avg_recent_vol / avg_20d_vol
            result["recent_volume_ratio"] = round(vol_ratio, 2)
            
            if vol_ratio > 2.0:
                result["volume_trend"] = "heavy"
                result["volume_signal"].append("放量明显")
            elif vol_ratio > 1.5:
                result["volume_trend"] = "increasing"
                result["volume_signal"].append("温和放量")
            elif vol_ratio < 0.5:
                result["volume_trend"] = "shrinking"
                result["volume_signal"].append("缩量明显")
            elif vol_ratio < 0.7:
                result["volume_trend"] = "decreasing"
                result["volume_signal"].append("温和缩量")
        
        # 检查量价配合
        last_row = px_data.iloc[-1]
        if last_row["pct_chg"] > 2 and vol_ratio > 1.3:
            result["volume_signal"].append("量价齐升")
        elif last_row["pct_chg"] < -2 and vol_ratio > 1.3:
            result["volume_signal"].append("放量下跌")
        elif abs(last_row["pct_chg"]) < 1 and vol_ratio < 0.7:
            result["volume_signal"].append("缩量横盘")
    
    return result


def calculate_volatility(px_data: pd.DataFrame, period: int = 20) -> float:
    """计算历史波动率"""
    if px_data is None or px_data.empty or len(px_data) < period:
        return None
    
    px_data = px_data.sort_values("trade_date").tail(period * 2)
    returns = px_data["pct_chg"] / 100
    
    # 年化波动率 (假设252个交易日)
    volatility = returns.std() * np.sqrt(252)
    return round(volatility, 4)


def enhanced_technical_analysis(ts_code: str, px_data: pd.DataFrame = None) -> Dict[str, Any]:
    """增强技术面分析"""
    result = {
        "limit_analysis": {},
        "relative_strength": {},
        "volume_pattern": {},
        "volatility": None,
        "technical_score": 0
    }
    
    # 获取价格数据
    if px_data is None:
        end = dt.date.today().strftime("%Y%m%d")
        start = (dt.date.today() - dt.timedelta(days=120)).strftime("%Y%m%d")
        px_data = daily(ts_code, start, end)
    
    # 涨跌停分析
    result["limit_analysis"] = analyze_limit_status(ts_code)
    
    # 相对强弱分析
    result["relative_strength"] = analyze_vs_index(ts_code)
    
    # 成交量模式
    if px_data is not None and not px_data.empty:
        result["volume_pattern"] = analyze_volume_pattern(px_data)
        result["volatility"] = calculate_volatility(px_data)
    
    # 计算技术评分
    score = 50  # 基础分
    
    # 涨跌停加分
    if result["limit_analysis"]["recent_limit_count"] > 0:
        score += min(10, result["limit_analysis"]["recent_limit_count"] * 2)
    
    # 相对强弱加分
    if result["relative_strength"]["outperform"] is not None:
        if result["relative_strength"]["outperform"] > 10:
            score += 15
        elif result["relative_strength"]["outperform"] > 5:
            score += 10
        elif result["relative_strength"]["outperform"] > 0:
            score += 5
        else:
            score -= 5
    
    # 成交量加分
    if result["volume_pattern"].get("volume_trend") == "heavy":
        score += 10
    elif result["volume_pattern"].get("volume_trend") == "increasing":
        score += 5
    elif result["volume_pattern"].get("volume_trend") == "shrinking":
        score -= 5
    
    # 波动率调整
    if result["volatility"] is not None:
        if result["volatility"] < 0.3:
            score += 5  # 低波动
        elif result["volatility"] > 0.6:
            score -= 5  # 高波动
    
    result["technical_score"] = min(100, max(0, score))
    
    return result