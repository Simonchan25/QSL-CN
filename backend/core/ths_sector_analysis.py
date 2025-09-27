"""
同花顺板块指数分析模块
利用5000积分权限增强热点分析
"""
import datetime as dt
from typing import Dict, Any, List, Optional
import pandas as pd

from .advanced_data_client import AdvancedDataClient
advanced_client = AdvancedDataClient()


def get_sector_performance_ranking(days: int = 5) -> List[Dict[str, Any]]:
    """获取板块表现排行榜
    
    参数:
        days: 统计天数
    
    返回:
        板块表现排行
    """
    result = []
    
    try:
        # 获取同花顺概念指数
        concept_indices = advanced_client.ths_index(exchange="A", type="N")  # N-概念指数
        
        if concept_indices.empty:
            return result
        
        # 获取最近几天的行情数据
        end_date = dt.date.today().strftime("%Y%m%d")
        start_date = (dt.date.today() - dt.timedelta(days=days)).strftime("%Y%m%d")
        
        for _, index_info in concept_indices.head(50).iterrows():  # 前50个概念
            ts_code = index_info.get("ts_code")
            name = index_info.get("name", "")
            
            if ts_code:
                daily_data = advanced_client.ths_daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
                
                if not daily_data.empty:
                    daily_data = daily_data.sort_values("trade_date")
                    
                    if len(daily_data) >= 2:
                        latest = daily_data.iloc[-1]
                        earliest = daily_data.iloc[0]
                        
                        # 计算涨跌幅
                        pct_change = ((latest.get("close", 0) - earliest.get("close", 1)) / earliest.get("close", 1) * 100) if earliest.get("close", 1) > 0 else 0
                        
                        # 计算平均成交量
                        avg_vol = daily_data["vol"].mean() if "vol" in daily_data.columns else 0
                        
                        result.append({
                            "sector_code": ts_code,
                            "sector_name": name,
                            "pct_change": round(pct_change, 2),
                            "latest_close": latest.get("close", 0),
                            "avg_volume": round(avg_vol, 2),
                            "total_mv": latest.get("total_mv", 0),  # 总市值
                            "days": days
                        })
        
        # 按涨跌幅排序
        result.sort(key=lambda x: x["pct_change"], reverse=True)
        
    except Exception as e:
        print(f"获取板块表现排行失败: {e}")
    
    return result


def analyze_sector_rotation() -> Dict[str, Any]:
    """分析板块轮动情况
    
    返回:
        板块轮动分析结果
    """
    result = {
        "hot_sectors": [],
        "cold_sectors": [],
        "rotation_signals": [],
        "market_style": "均衡"
    }
    
    try:
        # 获取短期和中期表现
        short_term = get_sector_performance_ranking(days=3)
        medium_term = get_sector_performance_ranking(days=10)
        
        if short_term and medium_term:
            # 热门板块（短期涨幅前10）
            result["hot_sectors"] = short_term[:10]
            
            # 冷门板块（短期涨幅后10）
            result["cold_sectors"] = short_term[-10:]
            
            # 分析轮动信号
            top_short = [s["sector_name"] for s in short_term[:5]]
            top_medium = [s["sector_name"] for s in medium_term[:5]]
            
            # 检查是否有新的热点出现
            new_hot = set(top_short) - set(top_medium)
            if new_hot:
                result["rotation_signals"].append(f"新热点板块: {', '.join(new_hot)}")
            
            # 检查市场风格
            hot_avg = sum([s["pct_change"] for s in short_term[:10]]) / 10
            cold_avg = sum([s["pct_change"] for s in short_term[-10:]]) / 10
            
            if hot_avg > 5 and hot_avg - cold_avg > 8:
                result["market_style"] = "强势轮动"
                result["rotation_signals"].append("市场呈现明显的板块轮动特征")
            elif hot_avg < -2:
                result["market_style"] = "整体下跌"
                result["rotation_signals"].append("市场整体较弱")
            else:
                result["market_style"] = "震荡分化"
    
    except Exception as e:
        print(f"板块轮动分析失败: {e}")
    
    return result


def get_sector_constituents(sector_name: str, limit: int = 20) -> List[Dict[str, Any]]:
    """获取板块成分股
    
    参数:
        sector_name: 板块名称
        limit: 返回数量限制
    
    返回:
        成分股列表
    """
    result = []
    
    try:
        # 首先找到对应的板块代码
        concept_indices = advanced_client.ths_index(exchange="A", type="N")
        
        if concept_indices.empty:
            return result
        
        # 搜索匹配的板块
        matched = concept_indices[concept_indices["name"].str.contains(sector_name, na=False)]
        
        if matched.empty:
            return result
        
        # 取第一个匹配的板块
        sector_code = matched.iloc[0]["ts_code"]
        
        # 获取成分股
        members = advanced_client.ths_member(ts_code=sector_code)
        
        if not members.empty:
            # 筛选最新的成分股
            current_members = members[members["is_new"] == "Y"] if "is_new" in members.columns else members
            
            for _, member in current_members.head(limit).iterrows():
                result.append({
                    "stock_code": member.get("code", ""),
                    "stock_name": member.get("name", ""),
                    "weight": float(member.get("weight", 0)) if member.get("weight") else 0,
                    "in_date": member.get("in_date", ""),
                })
    
    except Exception as e:
        print(f"获取板块成分股失败: {e}")
    
    return result


def enhanced_hotspot_analysis(keyword: str) -> Dict[str, Any]:
    """增强版热点分析
    
    参数:
        keyword: 热点关键词
    
    返回:
        增强分析结果
    """
    result = {
        "sector_performance": None,
        "constituents": [],
        "rotation_analysis": None,
        "investment_logic": []
    }
    
    try:
        # 1. 获取相关板块表现
        sectors = get_sector_performance_ranking()
        related_sectors = [s for s in sectors if keyword in s["sector_name"]]
        if related_sectors:
            result["sector_performance"] = related_sectors[0]
        
        # 2. 获取成分股
        result["constituents"] = get_sector_constituents(keyword)
        
        # 3. 板块轮动分析
        result["rotation_analysis"] = analyze_sector_rotation()
        
        # 4. 生成投资逻辑
        if result["sector_performance"]:
            perf = result["sector_performance"]
            if perf["pct_change"] > 10:
                result["investment_logic"].append("板块短期涨幅较大，注意高位风险")
            elif perf["pct_change"] > 5:
                result["investment_logic"].append("板块表现强势，可关注回调机会")
            elif perf["pct_change"] > 0:
                result["investment_logic"].append("板块表现平稳，可适度关注")
            else:
                result["investment_logic"].append("板块表现较弱，等待企稳信号")
        
        # 5. 成分股分析
        if result["constituents"]:
            high_weight = [c for c in result["constituents"] if c["weight"] > 5]
            if high_weight:
                result["investment_logic"].append(f"重点关注权重股: {', '.join([c['stock_name'] for c in high_weight[:3]])}")
    
    except Exception as e:
        print(f"增强热点分析失败: {e}")
    
    return result


def get_market_sector_overview() -> Dict[str, Any]:
    """获取市场板块概览
    
    返回:
        市场板块概览
    """
    result = {
        "sector_count": 0,
        "rising_count": 0,
        "falling_count": 0,
        "top_performers": [],
        "worst_performers": [],
        "market_breadth": 0
    }
    
    try:
        sectors = get_sector_performance_ranking(days=1)  # 单日表现
        
        if sectors:
            result["sector_count"] = len(sectors)
            result["rising_count"] = len([s for s in sectors if s["pct_change"] > 0])
            result["falling_count"] = len([s for s in sectors if s["pct_change"] < 0])
            
            result["top_performers"] = sectors[:5]
            result["worst_performers"] = sectors[-5:]
            
            # 市场广度（上涨板块占比）
            result["market_breadth"] = round((result["rising_count"] / result["sector_count"]) * 100, 1) if result["sector_count"] > 0 else 0
    
    except Exception as e:
        print(f"获取市场板块概览失败: {e}")
    
    return result