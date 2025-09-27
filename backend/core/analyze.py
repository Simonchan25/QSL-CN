import datetime as dt
from typing import Optional, Dict, Any, List, cast, Callable
from concurrent.futures import ThreadPoolExecutor
import pandas as pd

from .tushare_client import (
    stock_basic, daily, anns,
    top10_holders, top10_floatholders, stk_holdertrade,
    block_trade, margin_detail, top_list, top_inst,
    moneyflow, moneyflow_ths, moneyflow_dc, dividend, suspend_d
)
from .indicators import compute_indicators, build_tech_signal
from .fundamentals import fetch_fundamentals
from .macro import fetch_macro_snapshot
from .news import fetch_news_summary, format_news_for_llm, analyze_news_sentiment
from .sentiment import enhanced_sentiment_analysis
from .chip_analysis import comprehensive_chip_analysis
from .insight_builder import build_stock_insights
from nlp.ollama_client import summarize

PRICE_YEARS = 2
MAX_NEWS = 15


def _date_str(days_ago: int) -> str:
    d = dt.date.today() - dt.timedelta(days=days_ago)
    return d.strftime("%Y%m%d")


def resolve_by_name(name_keyword: str, force: bool = False) -> Optional[dict]:
    """通过股票名称解析股票信息（优先使用本地完整映射）"""
    import json, os
    
    # 1) 加载本地完整映射表
    mapping_path = os.path.join(os.path.dirname(__file__), 'symbol_map.json')
    try:
        with open(mapping_path, 'r', encoding='utf-8') as f:
            stock_list = json.load(f)
    except Exception as e:
        print(f"[映射] 无法加载股票映射表: {e}")
        return None
    
    kw = str(name_keyword).strip()
    candidates = []
    
    # 2) 搜索逻辑：股票代码 > 别名 > 精确匹配 > 部分匹配
    for stock in stock_list:
        ts_code = stock.get('ts_code')
        name = stock.get('name', '')
        aliases = stock.get('aliases', [])
        
        # 股票代码精确匹配（最高优先级）
        if kw == ts_code or kw == ts_code.split('.')[0]:
            candidates.append((stock, -1))
        # 别名匹配
        elif kw in aliases:
            candidates.append((stock, 0))
        # 精确名称匹配
        elif kw == name:
            candidates.append((stock, 1))
        # 部分匹配
        elif kw in name or name in kw:
            name_diff = abs(len(name) - len(kw))
            candidates.append((stock, 2 + name_diff))
    
    if not candidates:
        print(f"[映射] 未找到匹配的股票: {kw}")
        return None
    
    # 按优先级排序
    candidates.sort(key=lambda x: x[1])
    best_match = candidates[0][0]
    
    # 转换为兼容格式
    result = {
        'ts_code': best_match.get('ts_code'),
        'symbol': best_match.get('ts_code', '').split('.')[0],
        'name': best_match.get('name'),
        'industry': best_match.get('industry'),
        'area': best_match.get('area'),
        'market': '主板',  # 默认值
        'list_status': 'L'
    }
    
    print(f"[映射] 找到股票: {result['name']} ({result['ts_code']})")
    return result


def _get_data_freshness_info(tech: Dict[str, Any], fundamental: Dict[str, Any], 
                           capital_flow: Dict[str, Any], margin: Dict[str, Any]) -> Dict[str, Any]:
    """获取数据时效性信息，帮助用户理解各类数据的更新频率"""
    from datetime import datetime, timedelta
    
    today = datetime.now().date()
    
    # 获取最新交易日期（用于实时数据）
    latest_trading_date = None
    for source in ['tushare', 'ths']:
        if source in capital_flow and 'trade_date' in capital_flow[source]:
            trade_date_str = capital_flow[source]['trade_date']
            if trade_date_str:
                latest_trading_date = trade_date_str
                break
    
    # 如果没有从资金流获取到，从融资融券数据获取
    if not latest_trading_date and 'latest' in margin and 'trade_date' in margin['latest']:
        latest_trading_date = margin['latest']['trade_date']
    
    # 获取最新财务数据日期
    latest_financial_date = None
    if 'fina_indicator_latest' in fundamental and 'end_date' in fundamental['fina_indicator_latest']:
        latest_financial_date = fundamental['fina_indicator_latest']['end_date']
    
    freshness_info = {
        "analysis_time": today.strftime("%Y-%m-%d %H:%M"),
        "data_sources": {
            "real_time_data": {
                "description": "股价、技术指标、资金流向、融资融券等数据",
                "update_frequency": "交易日实时更新",
                "latest_date": latest_trading_date,
                "data_types": ["股价", "技术指标(RSI/MACD)", "资金流向", "融资融券", "龙虎榜"]
            },
            "financial_data": {
                "description": "财务指标、利润表、资产负债表等数据", 
                "update_frequency": "季度更新",
                "latest_date": latest_financial_date,
                "data_types": ["财务指标", "利润表", "资产负债表", "现金流量表"]
            },
            "holder_data": {
                "description": "股东持股、增减持等数据",
                "update_frequency": "季度更新", 
                "latest_date": latest_financial_date,
                "data_types": ["十大股东", "十大流通股东", "股东增减持"]
            }
        },
        "data_quality": {
            "real_time_completeness": "高",
            "financial_data_lag": f"约{_calculate_quarter_lag(latest_financial_date)}个月延迟（正常）",
            "overall_status": "正常"
        }
    }
    
    return freshness_info


def _calculate_quarter_lag(financial_date_str: str) -> int:
    """计算财务数据的季度延迟"""
    if not financial_date_str:
        return 0
    
    try:
        from datetime import datetime
        financial_date = datetime.strptime(financial_date_str, "%Y%m%d").date()
        today = datetime.now().date()
        
        # 计算月份差异
        months_diff = (today.year - financial_date.year) * 12 + (today.month - financial_date.month)
        return max(0, months_diff)
    except:
        return 0


def _calculate_data_age(date_str: str) -> int:
    """计算数据的天数差异"""
    if not date_str:
        return 999
    
    try:
        from datetime import datetime
        data_date = datetime.strptime(str(date_str), "%Y%m%d").date()
        today = datetime.now().date()
        return (today - data_date).days
    except:
        return 999


def _scorecard(tech: Dict[str, Any], fundamental: Dict[str, Any], macro: Dict[str, Any], 
               sentiment: Dict[str, Any] = None, enhanced_sentiment: Dict[str, Any] = None) -> Dict[str, Any]:
    # 新权重分配：技术面40%，情绪面35%，基本面20%，宏观5%
    score_fund = 0.0  # 基本面满分20
    score_tech = 0.0  # 技术面满分40
    score_sentiment = 0.0  # 情绪面满分35
    score_macro = 0.0  # 宏观满分5

    # 基本面评分（满分20）
    latest = (fundamental or {}).get("fina_indicator_latest", {})
    roe = latest.get("roe")
    net_margin = latest.get("netprofit_margin")
    debt_ratio = None
    bal = (fundamental or {}).get("balance_recent") or []
    if bal:
        debt_ratio = bal[0].get("debt_ratio")

    inc = (fundamental or {}).get("income_recent") or []
    rev_trend = 0
    profit_trend = 0
    if inc:
        take = inc[:4]
        revenues = [float(x.get("revenue")) for x in take if x.get("revenue") is not None]
        profits = [float(x.get("n_income")) for x in take if x.get("n_income") is not None]
        if len(revenues) >= 2:
            rev_trend = 1 if revenues[0] >= revenues[-1] else -1
        if len(profits) >= 2:
            profit_trend = 1 if profits[0] >= profits[-1] else -1

    if roe is not None:
        score_fund += max(0.0, min(8.0, float(roe) / 20.0 * 8.0))
    if net_margin is not None:
        score_fund += max(0.0, min(4.0, float(net_margin) / 20.0 * 4.0))
    if debt_ratio is not None:
        dr = float(debt_ratio)
        if dr < 0.3:
            score_fund += 3.0
        elif dr < 0.6:
            score_fund += 2.0
        elif dr < 0.8:
            score_fund += 1.0
    score_fund += (2.0 if rev_trend > 0 else 0.0) + (3.0 if profit_trend > 0 else 0.0)
    score_fund = min(20.0, max(0.0, score_fund))

    # 技术面评分（满分40）
    rsi = tech.get("tech_last_rsi")
    dif = tech.get("tech_last_dif")
    dea = tech.get("tech_last_dea")
    close = tech.get("tech_last_close")
    signal = tech.get("tech_signal") or ""
    
    if rsi is not None:
        if 40 <= rsi <= 60:
            score_tech += 15  # 中性区间，健康
        elif rsi < 30:
            score_tech += 10  # 超卖，可能反弹
        elif rsi > 70:
            score_tech += 5   # 超买，风险
        else:
            score_tech += 8
    
    if dif is not None and dea is not None:
        score_tech += 15 if dif > dea else 5  # 金叉/死叉
    
    if isinstance(signal, str):
        if "收盘<=下轨" in signal:
            score_tech += 8  # 下轨支撑
        elif "收盘>=上轨" in signal:
            score_tech += 3  # 上轨压力
        else:
            score_tech += 5
    
    score_tech = min(40.0, max(0.0, score_tech))

    # 情绪面评分（满分35）
    # 优先使用增强情绪分析的结果
    if isinstance(enhanced_sentiment, dict) and enhanced_sentiment.get('sentiment_score'):
        # 直接使用增强情纪分析的评分，并按比例转换到满分35分
        score_sentiment = enhanced_sentiment['sentiment_score'] * 0.35
    elif isinstance(sentiment, dict) and sentiment:
        overall = sentiment.get("overall", "neutral")
        percentages = sentiment.get("percentages", {})
        pos_pct = percentages.get("positive", 0)
        neg_pct = percentages.get("negative", 0)
        
        # 基础情绪得分
        if overall == "positive":
            score_sentiment += 20
        elif overall == "neutral":
            score_sentiment += 10
        else:  # negative
            score_sentiment += 5
        
        # 细化评分
        if pos_pct > 60:
            score_sentiment += 10
        elif pos_pct > 40:
            score_sentiment += 7
        elif pos_pct > 20:
            score_sentiment += 4
        
        # 负面新闻惩罚
        if neg_pct > 40:
            score_sentiment -= 5
        elif neg_pct > 20:
            score_sentiment -= 2
        
        score_sentiment = min(35.0, max(0.0, score_sentiment))

    # 宏观评分（满分5）
    m2 = (macro or {}).get("m2_latest", {}).get("m2_yoy")
    on_shibor = (macro or {}).get("shibor_latest", {}).get("on")
    try:
        m2 = float(m2) if m2 is not None else None
    except Exception:
        m2 = None
    try:
        on_shibor = float(on_shibor) if on_shibor is not None else None
    except Exception:
        on_shibor = None
    
    if m2 is not None:
        if m2 >= 8:
            score_macro += 2
        elif m2 >= 5:
            score_macro += 1
    
    if on_shibor is not None:
        if on_shibor <= 1.5:
            score_macro += 2
        elif on_shibor <= 2.0:
            score_macro += 1
    
    score_macro = min(5.0, max(0.0, score_macro))

    total = round(score_fund + score_tech + score_sentiment + score_macro, 1)

    # 确定评级
    if total >= 80:
        rating = "强烈推荐"
        suggestion = "买入"
    elif total >= 70:
        rating = "推荐"
        suggestion = "买入"
    elif total >= 60:
        rating = "中性偏多"
        suggestion = "持有"
    elif total >= 50:
        rating = "中性"
        suggestion = "观望"
    elif total >= 40:
        rating = "中性偏空"
        suggestion = "减持"
    else:
        rating = "不推荐"
        suggestion = "卖出"

    return {
        "total_score": total,
        "rating": rating,
        "suggestion": suggestion,
        "details": {
            "fundamental": round(score_fund, 1),
            "technical": round(score_tech, 1),
            "sentiment": round(score_sentiment, 1),
            "macro": round(score_macro, 1),
        },
        # 保持向后兼容
        "score_total": total,
        "score_fundamental": round(score_fund, 1),
        "score_technical": round(score_tech, 1),
        "score_sentiment": round(score_sentiment, 1),
        "score_macro": round(score_macro, 1),
    }


def run_pipeline(
    name_keyword: str,
    force: bool = False,
    progress: Optional[Callable[[str, Optional[Dict[str, Any]]], None]] = None,
) -> Dict[str, Any]:
    """
    运行分析流程
    优先使用优化版本，失败时回退到原版本
    """
    try:
        from .analyze_optimized import run_pipeline_optimized
        print("[分析] 使用优化版本")
        return run_pipeline_optimized(name_keyword, force, progress, timeout_seconds=30)
    except Exception as e:
        print(f"[分析] 优化版本失败: {e}，回退到原版本")
        return run_pipeline_original(name_keyword, force, progress)


def run_pipeline_original(
    name_keyword: str,
    force: bool = False,
    progress: Optional[Callable[[str, Optional[Dict[str, Any]]], None]] = None,
) -> Dict[str, Any]:
    # 定义分析步骤和对应的进度百分比
    progress_steps = {
        "resolve:start": (5, "开始解析股票"),
        "resolve:done": (10, "股票解析完成"),
        "fetch:parallel:start": (15, "开始获取数据"),
        "fetch:parallel:done": (30, "数据获取完成"),
        "compute:technical": (40, "技术指标计算"),
        "fetch:announcements": (45, "获取公告信息"),
        "compute:news_sentiment": (50, "新闻情绪分析"),
        "compute:enhanced_sentiment": (60, "增强情绪分析"),
        "compute:chip_analysis": (70, "筹码分析"),
        "compute:scorecard": (80, "综合评分"),
        "llm:summary:start": (85, "开始AI分析"),
        "llm:summary:done": (95, "AI分析完成"),
        "complete": (100, "分析完成")
    }
    
    current_progress = 0
    
    def _emit(step: str, payload: Optional[Dict[str, Any]] = None) -> None:
        nonlocal current_progress
        if progress is not None:
            try:
                # 查找当前步骤对应的进度百分比
                if step in progress_steps:
                    current_progress, desc = progress_steps[step]
                    # 添加进度百分比到payload
                    enhanced_payload = payload or {}
                    enhanced_payload["progress_percent"] = current_progress
                    enhanced_payload["progress_desc"] = desc
                    progress(step, enhanced_payload)
                else:
                    progress(step, payload or {})
            except Exception:
                pass
    # 允许直接输入代码以绕开对 stock_basic 的频控：
    def _guess_ts_code(s: str) -> Optional[str]:
        t = s.strip().upper()
        import re
        if re.fullmatch(r"\d{6}\.(SH|SZ|BJ)", t):
            return t
        if re.fullmatch(r"\d{6}", t):
            sym = t
            if sym.startswith(("600", "601", "603", "605", "688")):
                return f"{sym}.SH"
            if sym.startswith(("000", "001", "002", "003", "300", "301")):
                return f"{sym}.SZ"
            if sym.startswith(("430", "83", "87", "88")):
                return f"{sym}.BJ"
        return None

    _emit("resolve:start", {"input": name_keyword})
    
    # 智能缓存清理：根据force模式和交易时间自动清理过期缓存
    try:
        from .cache_cleaner import ensure_fresh_data
        if force:
            # force模式：强制清理所有缓存
            cache_result = ensure_fresh_data(force=True)
        else:
            # 智能模式：根据交易时间和股票代码进行适当清理
            cache_result = ensure_fresh_data()
        _emit("cache:clean", {
            "cleaned_files": cache_result.get("cleaned_files", 0),
            "action": cache_result.get("action", "none")
        })
    except Exception as e:
        print(f"[警告] 缓存清理失败: {e}")
    ts_code_guess = _guess_ts_code(name_keyword)
    base: Dict[str, Any] = {}
    if ts_code_guess:
        ts_code = ts_code_guess
        # 从本地映射获取完整信息
        import json, os
        mapping_path = os.path.join(os.path.dirname(__file__), 'symbol_map.json')
        stock_name = name_keyword  # 默认值
        stock_industry = None
        stock_area = None
        
        try:
            with open(mapping_path, 'r', encoding='utf-8') as f:
                items = json.load(f)
            for item in items:
                if item.get('ts_code') == ts_code:
                    stock_name = item.get('name', name_keyword)
                    stock_industry = item.get('industry')
                    stock_area = item.get('area')
                    break
        except Exception:
            print(f"[警告] 无法从本地映射获取{ts_code}的信息")
            pass
        
        # 构建基本信息，包含行业和地区
        base = {
            "ts_code": ts_code, 
            "symbol": ts_code.split(".")[0], 
            "name": stock_name
        }
        if stock_industry:
            base["industry"] = stock_industry
        if stock_area:
            base["area"] = stock_area
        
        print(f"[调试] 构建的基本信息: {base}")
    else:
        base_resolved = resolve_by_name(name_keyword, force=force)
        if not base_resolved:
            raise ValueError(f"未找到包含'{name_keyword}'的A股")
        base = base_resolved
        ts_code = base["ts_code"]
    _emit("resolve:done", {"base": base})

    # 使用交易日期助手获取最新交易日期
    from .trading_date_helper import get_latest_trading_date, get_recent_trading_dates
    
    # 获取最新交易日期作为结束日期
    end = get_latest_trading_date()
    start = (dt.date.today() - dt.timedelta(days=365 * PRICE_YEARS + 30)).strftime("%Y%m%d")
    
    # 获取最近的交易日期列表，用于确保数据获取
    recent_dates = get_recent_trading_dates(5)
    _emit("fetch:parallel:start", {"ts_code": ts_code})

    # 并发抓取（受全局限速影响，但可与非TS计算重叠）
    with ThreadPoolExecutor(max_workers=4) as ex:  # 减少并发数避免API限流
        fut_px = ex.submit(daily, ts_code, start, end, force)
        fut_fund = ex.submit(fetch_fundamentals, ts_code, force)
        fut_macro = ex.submit(fetch_macro_snapshot)
        fut_news = ex.submit(fetch_news_summary, ts_code, 7)
        fut_anns = ex.submit(anns, ts_code, MAX_NEWS, force)
        # 新增更多数据获取
        fut_holders = ex.submit(top10_holders, ts_code, force)
        fut_floatholders = ex.submit(top10_floatholders, ts_code, force)
        fut_holdertrade = ex.submit(stk_holdertrade, ts_code=ts_code, start_date=start, end_date=end, force=force)
        fut_block = ex.submit(block_trade, ts_code=ts_code, force=force)
        fut_margin = ex.submit(margin_detail, ts_code=ts_code, force=force)
        fut_toplist = ex.submit(top_list, trade_date=end, force=force)
        # 新增资金流向和分红数据 - 使用最近交易日期范围确保获取最新数据
        money_start_date = recent_dates[-1] if recent_dates else start  # 使用最近交易日的最后一天作为起始日期
        fut_moneyflow = ex.submit(moneyflow, ts_code=ts_code, start_date=money_start_date, end_date=end, force=force)
        fut_moneyflow_ths = ex.submit(moneyflow_ths, ts_code=ts_code, start_date=money_start_date, end_date=end, force=force)
        fut_dividend = ex.submit(dividend, ts_code=ts_code, force=force)

        # 使用安全的方式获取结果，避免单个future失败导致整个请求失败
        def safe_get_result(future, default=None, name="data"):
            """Safety wrapper for future.result() with error handling"""
            try:
                return future.result(timeout=10)  # 设置超时避免无限等待
            except Exception as e:
                _emit("fetch:error", {"source": name, "error": str(e)[:100]})
                return default

        px = safe_get_result(fut_px, pd.DataFrame(), "prices")
        fundamental = safe_get_result(fut_fund, {}, "fundamental")
        news_summary = safe_get_result(fut_news, {}, "news_summary")
        macro = safe_get_result(fut_macro, {}, "macro")
        news_df = safe_get_result(fut_anns, pd.DataFrame(), "announcements")
        # 获取新增数据结果
        holders_df = safe_get_result(fut_holders, pd.DataFrame(), "holders")
        floatholders_df = safe_get_result(fut_floatholders, pd.DataFrame(), "floatholders")
        holdertrade_df = safe_get_result(fut_holdertrade, pd.DataFrame(), "holdertrade")
        block_df = safe_get_result(fut_block, pd.DataFrame(), "block_trade")
        margin_df = safe_get_result(fut_margin, pd.DataFrame(), "margin")
        toplist_df = safe_get_result(fut_toplist, pd.DataFrame(), "toplist")
        # 获取资金流向和分红数据结果
        moneyflow_df = safe_get_result(fut_moneyflow, pd.DataFrame(), "moneyflow")
        moneyflow_ths_df = safe_get_result(fut_moneyflow_ths, pd.DataFrame(), "moneyflow_ths")
        dividend_df = safe_get_result(fut_dividend, pd.DataFrame(), "dividend")

    _emit("fetch:parallel:done", {
        "px_rows": int(0 if px is None else len(px)),
        "fundamental_keys": list(fundamental.keys() if isinstance(fundamental, dict) else []),
        "macro_keys": list(macro.keys() if isinstance(macro, dict) else []),
    })
    tech: Dict[str, Any] = {}
    if not px.empty:
        px = px.sort_values("trade_date").reset_index(drop=True)
        px = compute_indicators(px)
        last = px.iloc[-1]

        # 验证数据新鲜度
        latest_trade_date = str(last.get("trade_date", ""))
        data_age_days = _calculate_data_age(latest_trade_date)

        def _calc_pct_change(period: int) -> Optional[float]:
            if len(px) <= period:
                return None
            try:
                last_close_val = float(px.iloc[-1]["close"])
                base_close_val = float(px.iloc[-1 - period]["close"])
            except (TypeError, ValueError, KeyError):
                return None
            if base_close_val == 0:
                return None
            return (last_close_val / base_close_val - 1) * 100

        return_1d = _calc_pct_change(1)
        return_5d = _calc_pct_change(5)
        return_20d = _calc_pct_change(20)
        return_60d = _calc_pct_change(60)

        high_52w = None
        low_52w = None
        if {"high", "low"}.issubset(px.columns):
            window = px.tail(min(len(px), 252))
            if not window.empty:
                try:
                    high_52w = float(window["high"].max())
                    low_52w = float(window["low"].min())
                except (TypeError, ValueError):
                    high_52w = None
                    low_52w = None

        tech = {
            # 基础价格和日期信息
            "tech_last_close": float(last.get("close")) if pd.notna(last.get("close")) else None,
            "tech_last_high": float(last.get("high")) if pd.notna(last.get("high")) else None,
            "tech_last_low": float(last.get("low")) if pd.notna(last.get("low")) else None,
            "tech_last_vol": float(last.get("vol")) if pd.notna(last.get("vol")) else None,
            "tech_data_date": latest_trade_date,
            "tech_data_age_days": data_age_days,
            "tech_data_rows": len(px),
            "tech_data_quality": "正常" if data_age_days <= 3 else "延迟",
            "tech_return_1d": round(return_1d, 2) if return_1d is not None else None,
            "tech_return_5d": round(return_5d, 2) if return_5d is not None else None,
            "tech_return_20d": round(return_20d, 2) if return_20d is not None else None,
            "tech_return_60d": round(return_60d, 2) if return_60d is not None else None,
            "tech_52w_high": round(high_52w, 2) if high_52w is not None else None,
            "tech_52w_low": round(low_52w, 2) if low_52w is not None else None,

            # RSI指标
            "tech_last_rsi": round(float(last.get("rsi14")), 2) if pd.notna(last.get("rsi14")) else None,

            # MACD指标系列
            "tech_last_macd": round(float(last.get("macd")), 4) if pd.notna(last.get("macd")) else None,
            "tech_last_dif": round(float(last.get("dif")), 4) if pd.notna(last.get("dif")) else None,
            "tech_last_dea": round(float(last.get("dea")), 4) if pd.notna(last.get("dea")) else None,
            
            # 移动平均线系列
            "tech_last_ma5": round(float(last.get("ma5")), 2) if pd.notna(last.get("ma5")) else None,
            "tech_last_ma10": round(float(last.get("ma10")), 2) if pd.notna(last.get("ma10")) else None,
            "tech_last_ma20": round(float(last.get("ma20")), 2) if pd.notna(last.get("ma20")) else None,
            "tech_last_ma30": round(float(last.get("ma30")), 2) if pd.notna(last.get("ma30")) else None,
            "tech_last_ma60": round(float(last.get("ma60")), 2) if pd.notna(last.get("ma60")) else None,
            
            # 布林带指标
            "tech_last_boll_up": round(float(last.get("boll_up")), 2) if pd.notna(last.get("boll_up")) else None,
            "tech_last_boll_mid": round(float(last.get("boll_mid")), 2) if pd.notna(last.get("boll_mid")) else None,
            "tech_last_boll_dn": round(float(last.get("boll_dn")), 2) if pd.notna(last.get("boll_dn")) else None,
            
            # KDJ指标
            "tech_last_kdj_k": round(float(last.get("kdj_k")), 2) if pd.notna(last.get("kdj_k")) else None,
            "tech_last_kdj_d": round(float(last.get("kdj_d")), 2) if pd.notna(last.get("kdj_d")) else None,
            "tech_last_kdj_j": round(float(last.get("kdj_j")), 2) if pd.notna(last.get("kdj_j")) else None,
            
            # 威廉指标
            "tech_last_wr": round(float(last.get("wr")), 2) if pd.notna(last.get("wr")) else None,
            
            # 成交量相关指标
            "tech_last_vol_ma5": round(float(last.get("vol_ma5")), 0) if pd.notna(last.get("vol_ma5")) else None,
            "tech_last_vol_ma10": round(float(last.get("vol_ma10")), 0) if pd.notna(last.get("vol_ma10")) else None,
            "tech_last_vol_ma20": round(float(last.get("vol_ma20")), 0) if pd.notna(last.get("vol_ma20")) else None,
            "tech_last_vol_ratio": round(float(last.get("vol_ratio")), 2) if pd.notna(last.get("vol_ratio")) else None,
            "tech_last_pvt": round(float(last.get("pvt")), 0) if pd.notna(last.get("pvt")) else None,
            "tech_last_vr": round(float(last.get("vr")), 2) if pd.notna(last.get("vr")) else None,
            
            # 综合技术信号
            "tech_signal": build_tech_signal(last),
        }
    _emit("compute:technical", tech)

    # fundamental 已在并发阶段获取

    # 获取公司公告
    news_list: List[Dict[str, Any]] = []
    if not news_df.empty:
        news_df = news_df.sort_values("ann_date", ascending=False).head(MAX_NEWS)
        for _, r in news_df.iterrows():
            news_list.append(
                {
                    "ann_date": r.get("ann_date"),
                    "title": r.get("title"),
                    "seq": r.get("ann_id") or r.get("seq"),
                }
            )
    
    _emit("fetch:announcements", {"count": len(news_list)})
    # 获取全面的新闻资讯（已并发获取）
    news_sentiment = analyze_news_sentiment(news_summary)
    _emit("compute:news_sentiment", news_sentiment)
    
    # 增强情绪分析 - 包含资金流向、融资融券、北向资金等
    _emit("compute:enhanced_sentiment", {"status": "analyzing"})
    try:
        sentiment_analysis = enhanced_sentiment_analysis(ts_code, news_summary)
    except Exception as e:
        _emit("compute:enhanced_sentiment", {"status": "error", "error": str(e)[:100]})
        # 返回空对象，不显示默认值
        sentiment_analysis = None
    _emit("compute:sentiment", sentiment_analysis or {})
    
    # 筹码分析 - 包含筹码分布、机构调研、港资持股等（5000积分功能）
    _emit("compute:chip_analysis", {"status": "analyzing"})
    chip_analysis = comprehensive_chip_analysis(ts_code)
    _emit("compute:chip_analysis", chip_analysis)
    
    # 高级数据分析 - 5000积分专业版
    from .advanced_data_client import advanced_client
    advanced_data = advanced_client.get_comprehensive_stock_data(ts_code)
    _emit("compute:advanced_analysis", {
        "data_sources": len([k for k, v in advanced_data.items() if v.get('has_data', False)]),
        "total_modules": len(advanced_data)
    })
    
    macro = fetch_macro_snapshot()

    score = _scorecard(tech, fundamental, macro, news_sentiment, sentiment_analysis)
    _emit("compute:scorecard", score)

    # 准备LLM分析的数据
    llm_data = {
        "股票基本信息": base,
        "基本面摘要": fundamental,
        "技术面末日": tech,
        "公告列表": news_list,
        "新闻资讯": format_news_for_llm(news_summary, max_items=10),
        "新闻情绪": news_sentiment,
        "情绪分析": sentiment_analysis,  # 添加增强情绪分析
        "筹码分析": chip_analysis,  # 添加5000积分的筹码分析数据
        "高级数据分析": advanced_data,  # 添加5000积分专业版高级数据
        "宏观快照": macro,
        "评分卡": score,
    }
    
    _emit("llm:summary:start", None)
    llm_summary = summarize(llm_data)
    _emit("llm:summary:done", {"length": len(llm_summary or "")})

    # 处理股东数据
    holders_info = {}
    if not holders_df.empty and isinstance(holders_df, pd.DataFrame):
        latest_holders = holders_df.head(10).to_dict('records')
        holders_info["top10_holders"] = latest_holders
        # 计算股权集中度
        if 'hold_ratio' in holders_df.columns:
            holders_info["concentration"] = holders_df['hold_ratio'].head(10).sum()
    
    if not floatholders_df.empty and isinstance(floatholders_df, pd.DataFrame):
        holders_info["top10_floatholders"] = floatholders_df.head(10).to_dict('records')
    
    # 处理股东增减持数据
    holder_trade_info = {}
    if not holdertrade_df.empty and isinstance(holdertrade_df, pd.DataFrame):
        recent_trades = holdertrade_df.head(20).to_dict('records')
        holder_trade_info["recent_trades"] = recent_trades
        # 统计增持减持情况
        if 'change_vol' in holdertrade_df.columns:
            holder_trade_info["net_buy"] = holdertrade_df['change_vol'].sum()
    
    # 处理大宗交易数据
    block_trade_info = {}
    if not block_df.empty and isinstance(block_df, pd.DataFrame):
        block_trade_info["recent_blocks"] = block_df.head(10).to_dict('records')
        if 'deal_amount' in block_df.columns:
            block_trade_info["total_amount"] = block_df['deal_amount'].sum()
    
    # 处理融资融券数据
    margin_info = {}
    if not margin_df.empty and isinstance(margin_df, pd.DataFrame):
        latest_margin = margin_df.iloc[0].to_dict() if len(margin_df) > 0 else {}
        margin_info["latest"] = latest_margin
        # 计算融资融券余额变化
        if len(margin_df) > 1 and 'rzye' in margin_df.columns:
            margin_info["rzye_change"] = float(margin_df.iloc[0]['rzye'] - margin_df.iloc[1]['rzye']) if pd.notna(margin_df.iloc[0]['rzye']) and pd.notna(margin_df.iloc[1]['rzye']) else 0
    
    # 处理龙虎榜数据
    dragon_tiger_info = {}
    if not toplist_df.empty and isinstance(toplist_df, pd.DataFrame):
        # 检查是否有该股票上榜
        if 'ts_code' in toplist_df.columns:
            stock_on_list = toplist_df[toplist_df['ts_code'] == ts_code]
            if not stock_on_list.empty:
                dragon_tiger_info["on_list"] = True
                dragon_tiger_info["details"] = stock_on_list.to_dict('records')
            else:
                dragon_tiger_info["on_list"] = False
    
    # 处理个股资金流向数据
    capital_flow_info = {}
    
    # 处理TuShare原始资金流向
    if not moneyflow_df.empty and isinstance(moneyflow_df, pd.DataFrame):
        latest_flow = moneyflow_df.iloc[0] if len(moneyflow_df) > 0 else None
        if latest_flow is not None:
            capital_flow_info["tushare"] = {
                "net_amount": float(latest_flow.get("net_mf_amount", 0)) if pd.notna(latest_flow.get("net_mf_amount")) else 0,
                "buy_lg_amount": float(latest_flow.get("buy_lg_amount", 0)) if pd.notna(latest_flow.get("buy_lg_amount")) else 0,
                "sell_lg_amount": float(latest_flow.get("sell_lg_amount", 0)) if pd.notna(latest_flow.get("sell_lg_amount")) else 0,
                "trade_date": latest_flow.get("trade_date")
            }
    
    # 处理同花顺资金流向
    if not moneyflow_ths_df.empty and isinstance(moneyflow_ths_df, pd.DataFrame):
        latest_ths = moneyflow_ths_df.iloc[0] if len(moneyflow_ths_df) > 0 else None
        if latest_ths is not None:
            capital_flow_info["ths"] = {
                "net_amount": float(latest_ths.get("net_amount", 0)) if pd.notna(latest_ths.get("net_amount")) else 0,
                "buy_lg_amount": float(latest_ths.get("buy_lg_amount", 0)) if pd.notna(latest_ths.get("buy_lg_amount")) else 0,
                "buy_lg_amount_rate": float(latest_ths.get("buy_lg_amount_rate", 0)) if pd.notna(latest_ths.get("buy_lg_amount_rate")) else 0,
                "trade_date": latest_ths.get("trade_date")
            }
    
    # 处理分红送股数据
    dividend_info = {}
    if not dividend_df.empty and isinstance(dividend_df, pd.DataFrame):
        # 获取最近的分红记录
        recent_dividends = dividend_df.head(10).to_dict('records') if len(dividend_df) > 0 else []
        dividend_info["recent_dividends"] = recent_dividends
        
        # 计算年度分红统计
        if len(dividend_df) > 0:
            dividend_info["total_records"] = len(dividend_df)
            # 统计已实施的分红
            implemented = dividend_df[dividend_df['div_proc'] == '实施'] if 'div_proc' in dividend_df.columns else pd.DataFrame()
            if not implemented.empty and 'cash_div' in implemented.columns:
                dividend_info["total_cash_div"] = float(implemented['cash_div'].sum()) if pd.notna(implemented['cash_div'].sum()) else 0
    
    # 发送完成事件
    _emit("complete", {"status": "success"})
    
    # 添加数据时效性标识
    data_freshness = _get_data_freshness_info(tech, fundamental, capital_flow_info, margin_info)
    
    # 构建结果，只添加有效数据
    result = {
        "basic": base,
        "technical": tech if tech else {},
        "fundamental": fundamental if fundamental else {},
    }

    # 只在有数据时添加字段
    if news_list:
        result["announcements"] = news_list

    if news_summary and isinstance(news_summary, dict):
        news_data = {}
        if news_summary.get("summary"):
            news_data["summary"] = news_summary.get("summary")
        if news_sentiment:
            news_data["sentiment"] = news_sentiment
        if news_summary.get("flash_news"):
            news_data["flash_news"] = news_summary.get("flash_news", [])[:10]
        if news_summary.get("major_news"):
            news_data["major_news"] = news_summary.get("major_news", [])[:5]
        if news_summary.get("stock_news"):
            news_data["stock_news"] = news_summary.get("stock_news", [])[:10]
        if news_summary.get("cctv_news"):
            news_data["cctv_news"] = news_summary.get("cctv_news", [])[:3]
        if news_data:
            result["news"] = news_data

    # 添加数据字段（只要有数据就添加）
    if sentiment_analysis:
        result["sentiment"] = sentiment_analysis
    if chip_analysis:
        result["chip_analysis"] = chip_analysis
    if holders_info:
        result["holders"] = holders_info
    if holder_trade_info:
        result["holder_trade"] = holder_trade_info
    if block_trade_info:
        result["block_trade"] = block_trade_info
    if margin_info:
        result["margin"] = margin_info
    if dragon_tiger_info:
        result["dragon_tiger"] = dragon_tiger_info
    if capital_flow_info:
        result["capital_flow"] = capital_flow_info
    if dividend_info:
        result["dividend"] = dividend_info

    # 添加其他重要字段
    result["macro"] = macro
    result["scorecard"] = score
    result["llm_summary"] = llm_summary
    result["data_freshness"] = data_freshness  # 数据时效性信息

    try:
        result["insights"] = build_stock_insights(result)
    except Exception as exc:
        print(f"[警告] 构建个股洞察失败: {exc}")
        result["insights"] = {}

    return result
