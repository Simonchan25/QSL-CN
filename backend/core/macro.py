from typing import Dict, Any
import pandas as pd
from .tushare_client import (
    cpi, ppi, money_supply, shibor,
    cn_gdp, cn_pmi, fx_reserves, stk_limit
)


def fetch_macro_snapshot() -> Dict[str, Any]:
    """获取宏观经济快照数据"""
    out: Dict[str, Any] = {}

    # CPI数据
    _cpi = cpi()
    if not _cpi.empty:
        _cpi = _cpi.sort_values("month", ascending=False).reset_index(drop=True)
        latest = _cpi.iloc[0]
        out["cpi_latest"] = {
            "month": latest.get("month"),
            "cpi": latest.get("cpi"),
            "cpi_yoy": latest.get("cpi_yoy"),
            "cpi_mom": latest.get("cpi_mom"),
        }
        # 近6个月趋势
        if len(_cpi) >= 6:
            out["cpi_trend"] = _cpi.head(6)[["month", "cpi_yoy"]].to_dict(orient="records")

    # PPI数据
    _ppi = ppi()
    if not _ppi.empty:
        _ppi = _ppi.sort_values("month", ascending=False).reset_index(drop=True)
        latest = _ppi.iloc[0]
        out["ppi_latest"] = {
            "month": latest.get("month"),
            "ppi_yoy": latest.get("ppi_yoy"),
            "ppi_mom": latest.get("ppi_mom"),
        }

    # 货币供应量
    _ms = money_supply()
    if not _ms.empty:
        _ms = _ms.sort_values("month", ascending=False).reset_index(drop=True)
        latest = _ms.iloc[0]
        out["money_supply_latest"] = {
            "month": latest.get("month"),
            "m0_yoy": latest.get("m0_yoy"),
            "m1_yoy": latest.get("m1_yoy"),
            "m2_yoy": latest.get("m2_yoy"),
        }
        # M1-M2剪刀差（流动性指标）
        if latest.get("m1_yoy") and latest.get("m2_yoy"):
            try:
                m1 = float(latest.get("m1_yoy"))
                m2 = float(latest.get("m2_yoy"))
                out["m1_m2_gap"] = round(m1 - m2, 2)
            except:
                pass

    # SHIBOR利率
    _shb = shibor()
    if not _shb.empty:
        _shb = _shb.sort_values("date", ascending=False).reset_index(drop=True)
        latest = _shb.iloc[0]
        out["shibor_latest"] = {
            "date": latest.get("date"),
            "on": latest.get("on"),    # 隔夜
            "1w": latest.get("1w"),     # 1周
            "1m": latest.get("1m"),     # 1月
            "3m": latest.get("3m"),     # 3月
        }

    # GDP数据
    _gdp = cn_gdp()
    if not _gdp.empty:
        _gdp = _gdp.sort_values("quarter", ascending=False).reset_index(drop=True)
        latest = _gdp.iloc[0]
        out["gdp_latest"] = {
            "quarter": latest.get("quarter"),
            "gdp": latest.get("gdp"),
            "gdp_yoy": latest.get("gdp_yoy"),
        }

    # PMI数据
    _pmi = cn_pmi()
    if not _pmi.empty:
        _pmi = _pmi.sort_values("month", ascending=False).reset_index(drop=True)
        latest = _pmi.iloc[0]
        out["pmi_latest"] = {
            "month": latest.get("month"),
            "pmi": latest.get("pmi"),
            "pmi_mfg": latest.get("pmi_mfg"),      # 制造业PMI
            "pmi_non_mfg": latest.get("pmi_non_mfg"), # 非制造业PMI
        }
        # PMI景气判断
        if latest.get("pmi_mfg"):
            try:
                pmi_val = float(latest.get("pmi_mfg"))
                if pmi_val >= 50:
                    out["pmi_signal"] = "扩张区间"
                else:
                    out["pmi_signal"] = "收缩区间"
            except:
                pass

    # 外汇储备
    _fx = fx_reserves()
    if not _fx.empty:
        _fx = _fx.sort_values("month", ascending=False).reset_index(drop=True)
        latest = _fx.iloc[0]
        out["fx_reserves_latest"] = {
            "month": latest.get("month"),
            "reserves": latest.get("reserves"),
            "reserves_yoy": latest.get("reserves_yoy"),
        }

    # 保持向后兼容
    if "money_supply_latest" in out:
        out["m2_latest"] = {
            "month": out["money_supply_latest"]["month"],
            "m2_yoy": out["money_supply_latest"]["m2_yoy"]
        }

    return out


def analyze_market_liquidity(trade_date: str = None) -> Dict[str, Any]:
    """分析市场流动性和风险偏好"""
    import datetime as dt
    
    if not trade_date:
        trade_date = dt.date.today().strftime("%Y%m%d")
    
    result = {
        "limit_stats": {},
        "market_sentiment": "neutral",
        "risk_appetite": "medium"
    }
    
    # 获取涨跌停统计
    try:
        limit_data = stk_limit(trade_date=trade_date)
        if not limit_data.empty:
            up_limit_count = len(limit_data[limit_data["up_limit"] > 0])
            down_limit_count = len(limit_data[limit_data["down_limit"] > 0])
            
            result["limit_stats"] = {
                "up_limit_count": up_limit_count,
                "down_limit_count": down_limit_count,
                "limit_ratio": round(up_limit_count / (up_limit_count + down_limit_count + 1) * 100, 2)
            }
            
            # 判断市场情绪
            if up_limit_count > 100:
                result["market_sentiment"] = "extremely_bullish"
                result["risk_appetite"] = "high"
            elif up_limit_count > 50:
                result["market_sentiment"] = "bullish"
                result["risk_appetite"] = "medium_high"
            elif down_limit_count > 100:
                result["market_sentiment"] = "extremely_bearish"
                result["risk_appetite"] = "low"
            elif down_limit_count > 50:
                result["market_sentiment"] = "bearish"
                result["risk_appetite"] = "medium_low"
    except:
        pass
    
    return result


def calculate_macro_score(macro_data: Dict[str, Any]) -> float:
    """计算宏观经济评分"""
    score = 50  # 基础分
    
    # GDP增速
    gdp_yoy = macro_data.get("gdp_latest", {}).get("gdp_yoy")
    if gdp_yoy:
        try:
            gdp_val = float(gdp_yoy)
            if gdp_val >= 6:
                score += 10
            elif gdp_val >= 5:
                score += 5
            elif gdp_val < 4:
                score -= 10
        except:
            pass
    
    # CPI通胀
    cpi_yoy = macro_data.get("cpi_latest", {}).get("cpi_yoy")
    if cpi_yoy:
        try:
            cpi_val = float(cpi_yoy)
            if 1 <= cpi_val <= 3:
                score += 5  # 温和通胀
            elif cpi_val > 5:
                score -= 10  # 高通胀
            elif cpi_val < 0:
                score -= 5   # 通缩风险
        except:
            pass
    
    # PMI景气度
    pmi_mfg = macro_data.get("pmi_latest", {}).get("pmi_mfg")
    if pmi_mfg:
        try:
            pmi_val = float(pmi_mfg)
            if pmi_val >= 52:
                score += 10  # 强劲扩张
            elif pmi_val >= 50:
                score += 5   # 温和扩张
            elif pmi_val < 48:
                score -= 10  # 明显收缩
            else:
                score -= 5   # 轻微收缩
        except:
            pass
    
    # M2货币供应
    m2_yoy = macro_data.get("money_supply_latest", {}).get("m2_yoy")
    if m2_yoy:
        try:
            m2_val = float(m2_yoy)
            if 8 <= m2_val <= 12:
                score += 5   # 流动性合理
            elif m2_val > 15:
                score += 3   # 流动性充裕
            elif m2_val < 6:
                score -= 5   # 流动性紧张
        except:
            pass
    
    # 利率水平
    shibor_on = macro_data.get("shibor_latest", {}).get("on")
    if shibor_on:
        try:
            rate = float(shibor_on)
            if rate <= 1.5:
                score += 5   # 低利率环境
            elif rate >= 3:
                score -= 5   # 高利率环境
        except:
            pass
    
    return min(100, max(0, score))