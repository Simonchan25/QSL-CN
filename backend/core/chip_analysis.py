"""
筹码分析模块
利用5000积分权限的高级筹码数据接口
"""
import datetime as dt
from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np

from .advanced_data_client import AdvancedDataClient
advanced_client = AdvancedDataClient()


def analyze_chip_distribution(ts_code: str, days: int = 5) -> Dict[str, Any]:
    """分析股票筹码分布
    
    参数:
        ts_code: 股票代码
        days: 分析天数
    
    返回:
        筹码分布分析结果
    """
    result = {
        "has_data": False,
        "cost_analysis": {},
        "winner_rate": None,
        "chip_concentration": None,
        "support_resistance": {},
        "signals": []
    }
    
    try:
        # 获取筹码成本和胜率数据
        end_date = dt.date.today().strftime("%Y%m%d")
        start_date = (dt.date.today() - dt.timedelta(days=days)).strftime("%Y%m%d")
        
        perf_df = advanced_client.cyq_perf(ts_code=ts_code, start_date=start_date, end_date=end_date)
        
        if perf_df is not None and not perf_df.empty:
            result["has_data"] = True
            perf_df = perf_df.sort_values("trade_date", ascending=False)
            
            latest = perf_df.iloc[0] if len(perf_df) > 0 else None
            
            if latest is not None:
                # 成本分析
                result["cost_analysis"] = {
                    "avg_cost": float(latest.get("weight_avg", 0)) if pd.notna(latest.get("weight_avg")) else None,
                    "median_cost": float(latest.get("cost_50pct", 0)) if pd.notna(latest.get("cost_50pct")) else None,
                    "cost_5pct": float(latest.get("cost_5pct", 0)) if pd.notna(latest.get("cost_5pct")) else None,
                    "cost_95pct": float(latest.get("cost_95pct", 0)) if pd.notna(latest.get("cost_95pct")) else None,
                }
                
                # 胜率（获利盘比例）
                result["winner_rate"] = float(latest.get("winner_rate", 0)) if pd.notna(latest.get("winner_rate")) else None
                
                # 筹码集中度（通过成本分布计算）
                if result["cost_analysis"]["cost_95pct"] and result["cost_analysis"]["cost_5pct"]:
                    concentration = (result["cost_analysis"]["cost_95pct"] - result["cost_analysis"]["cost_5pct"]) / result["cost_analysis"]["median_cost"] if result["cost_analysis"]["median_cost"] else 0
                    result["chip_concentration"] = round(concentration * 100, 2)  # 百分比
                
                # 支撑压力位
                result["support_resistance"] = {
                    "strong_support": result["cost_analysis"]["cost_5pct"],  # 强支撑
                    "support": result["cost_analysis"]["median_cost"],  # 支撑
                    "resistance": result["cost_analysis"]["cost_95pct"],  # 压力
                }
                
                # 生成交易信号
                if result["winner_rate"]:
                    if result["winner_rate"] > 80:
                        result["signals"].append("获利盘过高，注意风险")
                    elif result["winner_rate"] < 20:
                        result["signals"].append("套牢盘较多，底部特征")
                    elif 40 <= result["winner_rate"] <= 60:
                        result["signals"].append("筹码分布均衡")
                
                # 分析筹码变化趋势
                if len(perf_df) >= 3:
                    recent_avg = perf_df.head(3)["weight_avg"].mean()
                    prev_avg = perf_df.iloc[3:6]["weight_avg"].mean() if len(perf_df) >= 6 else recent_avg
                    
                    if recent_avg > prev_avg * 1.02:
                        result["signals"].append("成本重心上移")
                    elif recent_avg < prev_avg * 0.98:
                        result["signals"].append("成本重心下移")
        
        # 获取详细筹码分布（可选）
        chips_df = advanced_client.cyq_chips(ts_code=ts_code, trade_date=end_date)
        if chips_df is not None and not chips_df.empty:
            # 计算筹码峰
            chips_peak = chips_df[chips_df["percent"] == chips_df["percent"].max()]
            if not chips_peak.empty:
                result["chip_peak"] = float(chips_peak.iloc[0]["price"])
                result["chip_peak_percent"] = float(chips_peak.iloc[0]["percent"])
    
    except Exception as e:
        print(f"筹码分析失败: {e}")
    
    return result


def analyze_institution_survey(ts_code: str, days: int = 30) -> Dict[str, Any]:
    """分析机构调研情况
    
    参数:
        ts_code: 股票代码
        days: 分析天数
    
    返回:
        机构调研分析结果
    """
    result = {
        "has_data": False,
        "survey_count": 0,
        "recent_surveys": [],
        "institution_interest": "低",
        "signals": []
    }
    
    try:
        end_date = dt.date.today().strftime("%Y%m%d")
        start_date = (dt.date.today() - dt.timedelta(days=days)).strftime("%Y%m%d")
        
        surv_df = advanced_client.stk_surv(ts_code=ts_code, start_date=start_date, end_date=end_date)
        
        if surv_df is not None and not surv_df.empty:
            result["has_data"] = True
            result["survey_count"] = len(surv_df)
            
            # 最近的调研记录
            for _, row in surv_df.head(5).iterrows():
                survey_info = {
                    "date": row.get("surv_date"),
                    "institutions": row.get("fund_visitors", ""),
                    "count": int(row.get("fund_nums", 0)) if pd.notna(row.get("fund_nums")) else 0,
                    "type": row.get("org_type", ""),
                    "mode": row.get("rece_mode", "")
                }
                result["recent_surveys"].append(survey_info)
            
            # 判断机构关注度
            if result["survey_count"] >= 10:
                result["institution_interest"] = "高"
                result["signals"].append("机构密集调研，关注度高")
            elif result["survey_count"] >= 5:
                result["institution_interest"] = "中"
                result["signals"].append("机构有一定关注")
            else:
                result["institution_interest"] = "低"
            
            # 分析调研趋势
            if len(surv_df) >= 2:
                recent_7d = surv_df[surv_df["surv_date"] >= (dt.date.today() - dt.timedelta(days=7)).strftime("%Y%m%d")]
                if len(recent_7d) >= 3:
                    result["signals"].append("近期调研频繁，可能有重要信息")
    
    except Exception as e:
        print(f"机构调研分析失败: {e}")
    
    return result


def analyze_ccass_holding(ts_code: str, days: int = 20) -> Dict[str, Any]:
    """分析中央结算系统持股（港资持股）
    
    参数:
        ts_code: 股票代码
        days: 分析天数
    
    返回:
        港资持股分析结果
    """
    result = {
        "has_data": False,
        "latest_ratio": None,
        "ratio_change": None,
        "holder_change": None,
        "trend": "stable",
        "signals": []
    }
    
    try:
        # 将A股代码转换为可能的港股代码格式
        # 注：这里需要根据实际映射关系调整
        end_date = dt.date.today().strftime("%Y%m%d")
        start_date = (dt.date.today() - dt.timedelta(days=days)).strftime("%Y%m%d")
        
        ccass_df = advanced_client.ccass_hold(ts_code=ts_code, start_date=start_date, end_date=end_date)
        
        if ccass_df is not None and not ccass_df.empty:
            result["has_data"] = True
            ccass_df = ccass_df.sort_values("trade_date", ascending=False)
            
            if len(ccass_df) > 0:
                latest = ccass_df.iloc[0]
                result["latest_ratio"] = float(latest.get("ratio", 0)) if pd.notna(latest.get("ratio")) else None
                
                # 计算变化
                if len(ccass_df) >= 5:
                    prev = ccass_df.iloc[4]
                    if result["latest_ratio"] and pd.notna(prev.get("ratio")):
                        result["ratio_change"] = round(result["latest_ratio"] - float(prev.get("ratio")), 2)
                        
                        # 判断趋势
                        if result["ratio_change"] > 0.5:
                            result["trend"] = "increasing"
                            result["signals"].append("港资持续加仓")
                        elif result["ratio_change"] < -0.5:
                            result["trend"] = "decreasing"
                            result["signals"].append("港资减仓")
                        else:
                            result["trend"] = "stable"
                
                # 参与者数量变化
                if pd.notna(latest.get("holders")) and len(ccass_df) >= 2:
                    prev_holders = ccass_df.iloc[1].get("holders")
                    if pd.notna(prev_holders):
                        result["holder_change"] = int(latest.get("holders")) - int(prev_holders)
                        if result["holder_change"] > 5:
                            result["signals"].append("参与机构增加")
                        elif result["holder_change"] < -5:
                            result["signals"].append("参与机构减少")
    
    except Exception as e:
        print(f"中央结算系统持股分析失败: {e}")
    
    return result


def comprehensive_chip_analysis(ts_code: str) -> Dict[str, Any]:
    """综合筹码分析
    
    参数:
        ts_code: 股票代码
    
    返回:
        综合分析结果
    """
    # 筹码分布分析
    chip_dist = analyze_chip_distribution(ts_code)
    
    # 机构调研分析
    institution = analyze_institution_survey(ts_code)
    
    # 港资持股分析
    ccass = analyze_ccass_holding(ts_code)
    
    # 综合评分（0-100）
    score = 50  # 基础分
    
    # 筹码因素（40%权重）
    if chip_dist.get("has_data"):
        winner_rate = chip_dist.get("winner_rate", 50)
        if 30 <= winner_rate <= 70:  # 筹码结构健康
            score += 10
        if chip_dist.get("chip_concentration", 100) < 30:  # 筹码集中
            score += 10
        if "底部特征" in str(chip_dist.get("signals", [])):
            score += 10
        if "成本重心上移" in str(chip_dist.get("signals", [])):
            score += 5
        elif "成本重心下移" in str(chip_dist.get("signals", [])):
            score -= 5
    
    # 机构因素（30%权重）
    if institution.get("has_data"):
        if institution.get("institution_interest") == "高":
            score += 15
        elif institution.get("institution_interest") == "中":
            score += 8
        if "近期调研频繁" in str(institution.get("signals", [])):
            score += 5
    
    # 港资因素（30%权重）
    if ccass.get("has_data"):
        if ccass.get("trend") == "increasing":
            score += 15
        elif ccass.get("trend") == "decreasing":
            score -= 10
        if ccass.get("ratio_change", 0) > 1:
            score += 5
    
    score = min(100, max(0, score))
    
    return {
        "chip_distribution": chip_dist,
        "institution_survey": institution,
        "ccass_holding": ccass,
        "comprehensive_score": round(score, 1),
        "investment_suggestion": (
            "强烈推荐" if score >= 80 else
            "推荐" if score >= 65 else
            "中性" if score >= 45 else
            "谨慎" if score >= 30 else
            "回避"
        )
    }