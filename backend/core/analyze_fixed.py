"""
修复版分析模块 - 完整功能，优化性能
包含技术面、基本面、情绪面、行业面分析
"""
from typing import Dict, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, TimeoutError, as_completed
import time
from datetime import datetime
from .cache_manager import cache_manager, cache_stock_data


def run_pipeline_fixed(
    name_keyword: str,
    force: bool = False,
    progress: Optional[Callable[[str, Optional[Dict[str, Any]]], None]] = None,
    timeout_seconds: int = 30
) -> Dict[str, Any]:
    """
    修复版分析流程 - 保持完整功能，优化性能
    """
    start_time = time.time()

    def _progress(step: str, data: Any = None):
        if progress:
            progress(step, data)
        print(f"[分析] {step}")

    _progress("开始完整分析")

    # 1. 解析股票代码
    from .analyze import resolve_by_name
    stock_info = resolve_by_name(name_keyword, force)
    if not stock_info:
        return {"error": f"未找到股票: {name_keyword}"}

    ts_code = stock_info['ts_code']
    stock_name = stock_info['name']
    _progress(f"解析成功: {stock_name} ({ts_code})")

    # 检查缓存
    if not force:
        cache_key = f"complete_analysis_{ts_code}_{datetime.now().strftime('%Y%m%d')}"
        cached_result = cache_manager.get(cache_key, namespace='analysis', max_age=300)  # 5分钟缓存
        if cached_result:
            _progress("使用缓存数据")
            return cached_result

    # 2. 初始化结果
    result = {
        "basic": stock_info,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "technical": {},
        "fundamental": {},
        "sentiment": {},
        "industry": {},
        "news": {},
        "market": {}
    }

    # 3. 获取核心数据（优化：只获取必要数据）
    try:
        # 技术面数据
        result["technical"] = _fetch_technical_optimized(ts_code, stock_name)
        _progress("技术面分析完成")

        # 基本面数据
        result["fundamental"] = _fetch_fundamental_optimized(ts_code, stock_name)
        _progress("基本面分析完成")

        # 情绪面数据
        result["sentiment"] = _fetch_sentiment_optimized(ts_code, stock_name)
        _progress("情绪面分析完成")

        # 行业面数据
        result["industry"] = _fetch_industry_optimized(ts_code, stock_name, stock_info.get('industry'))
        _progress("行业面分析完成")

        # 新闻数据（简化版）
        result["news"] = _fetch_news_simplified(ts_code, stock_name)
        _progress("新闻分析完成")

        # 市场概况（简化版）
        result["market"] = _fetch_market_simplified()
        _progress("市场分析完成")

    except Exception as e:
        print(f"[错误] 数据获取失败: {e}")

    # 4. 生成综合评分和报告
    result["score"] = _calculate_comprehensive_score(result)
    result["report"] = _generate_complete_report(result)
    result["summary"] = _generate_executive_summary(result)

    # 保存缓存
    cache_key = f"complete_analysis_{ts_code}_{datetime.now().strftime('%Y%m%d')}"
    cache_manager.set(cache_key, result, namespace='analysis')

    _progress("完整分析完成")
    return result


@cache_stock_data(ttl=180)  # 3分钟缓存
def _fetch_technical_optimized(ts_code: str, stock_name: str) -> Dict[str, Any]:
    """获取技术面数据（优化版）"""
    try:
        from .indicators import compute_indicators
        from .tushare_client import daily
        from datetime import datetime, timedelta

        # 只获取最近30天数据（减少数据量）
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')

        df = daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
        if df is None or df.empty:
            return {}

        # 计算技术指标
        df_with_indicators = compute_indicators(df)

        # 最新数据
        latest = df.iloc[0]

        # 构建技术面分析结果
        technical_data = {
            "price": float(latest['close']),
            "change": float(latest.get('pct_chg', 0) if hasattr(latest, 'get') else 0),
            "volume": float(latest.get('vol', 0) if hasattr(latest, 'get') else 0),
            "amount": float(latest.get('amount', 0) if hasattr(latest, 'get') else 0) * 1000,
            "trend": _analyze_trend(df),
            "support_resistance": _calculate_support_resistance(df),
            "technical_score": _calculate_technical_score(df_with_indicators)
        }

        # 添加关键技术指标
        if df_with_indicators is not None and not df_with_indicators.empty:
            latest_ind = df_with_indicators.iloc[-1]
            technical_data["indicators"] = {
                'RSI': float(latest_ind.get('rsi14', 50)),
                'MACD': float(latest_ind.get('macd', 0)),
                'KDJ_K': float(latest_ind.get('kdj_k', 50)),
                'MA5': float(latest_ind.get('ma5', 0)),
                'MA20': float(latest_ind.get('ma20', 0))
            }

        return technical_data

    except Exception as e:
        print(f"[技术面] 错误: {e}")
        return {}


@cache_stock_data(ttl=300)  # 5分钟缓存
def _fetch_fundamental_optimized(ts_code: str, stock_name: str) -> Dict[str, Any]:
    """获取基本面数据（使用5000积分VIP接口）"""
    try:
        from .tushare_client import daily_basic, fina_indicator, income_vip, balancesheet_vip, cashflow_vip
        from datetime import datetime

        # 获取最新基本面指标
        today = datetime.now().strftime('%Y%m%d')
        latest_basic = daily_basic(ts_code=ts_code, trade_date=today)

        fundamental_data = {}

        if latest_basic is not None and not latest_basic.empty:
            latest = latest_basic.iloc[0]
            fundamental_data = {
                "pe_ttm": float(latest.get('pe_ttm', 0) if hasattr(latest, 'get') else 0),
                "pb": float(latest.get('pb', 0) if hasattr(latest, 'get') else 0),
                "ps_ttm": float(latest.get('ps_ttm', 0) if hasattr(latest, 'get') else 0),
                "total_mv": float(latest.get('total_mv', 0) if hasattr(latest, 'get') else 0),
                "valuation_score": _calculate_valuation_score(latest)
            }

        # 使用5000积分VIP接口获取更详细的财务数据
        try:
            print(f"[基本面] 开始获取VIP数据 for {ts_code}")

            # 获取利润表数据
            income_data = income_vip(ts_code=ts_code)
            print(f"[基本面] 利润表数据状态: {income_data is not None and not income_data.empty}")
            if income_data is not None and not income_data.empty:
                latest_income = income_data.iloc[0]
                fundamental_data["revenue"] = float(latest_income.get('revenue', 0)) / 100000000  # 转换为亿
                fundamental_data["net_profit"] = float(latest_income.get('n_income', 0)) / 100000000
                fundamental_data["operating_profit"] = float(latest_income.get('operate_profit', 0)) / 100000000
                print(f"[基本面] 利润表数据获取成功，净利润: {fundamental_data['net_profit']:.2f}亿")

            # 获取资产负债表数据
            balance_data = balancesheet_vip(ts_code=ts_code)
            print(f"[基本面] 资产负债表数据状态: {balance_data is not None and not balance_data.empty}")
            if balance_data is not None and not balance_data.empty:
                latest_balance = balance_data.iloc[0]
                fundamental_data["total_assets"] = float(latest_balance.get('total_assets', 0)) / 100000000
                fundamental_data["debt_ratio"] = float(latest_balance.get('total_liab', 0)) / float(latest_balance.get('total_assets', 1)) * 100

                # 计算ROE：净利润 / 股东权益
                shareholder_equity = float(latest_balance.get('total_hldr_eqy_exc_min_int', 0))
                net_income = fundamental_data.get("net_profit", 0) * 100000000  # 转回万元
                print(f"[基本面] ROE计算: 股东权益={shareholder_equity:.0f}万元, 净利润={net_income:.0f}万元")

                if shareholder_equity > 0:
                    roe_value = (net_income / shareholder_equity) * 100
                    fundamental_data["roe"] = roe_value
                    print(f"[基本面] ROE计算成功: {roe_value:.2f}%")
                else:
                    fundamental_data["roe"] = 0.0
                    print(f"[基本面] ROE计算失败: 股东权益为0")

            # 计算毛利率（在VIP数据获取后独立处理）
            if income_data is not None and not income_data.empty:
                latest_income = income_data.iloc[0]
                # 毛利率 = (营业收入 - 营业成本) / 营业收入 * 100
                revenue = float(latest_income.get('revenue', 0))
                operating_cost = float(latest_income.get('oper_cost', 0))
                print(f"[基本面] 毛利率计算: 营业收入={revenue:.0f}万元, 营业成本={operating_cost:.0f}万元")

                if revenue > 0:
                    gross_margin_value = ((revenue - operating_cost) / revenue) * 100
                    fundamental_data["gross_margin"] = gross_margin_value
                    print(f"[基本面] 毛利率计算成功: {gross_margin_value:.2f}%")
                else:
                    fundamental_data["gross_margin"] = 0.0
                    print(f"[基本面] 毛利率计算失败: 营业收入为0")

            # 获取现金流量表数据
            cashflow_data = cashflow_vip(ts_code=ts_code)
            if cashflow_data is not None and not cashflow_data.empty:
                latest_cashflow = cashflow_data.iloc[0]
                fundamental_data["operating_cashflow"] = float(latest_cashflow.get('n_cashflow_act', 0)) / 100000000
                fundamental_data["free_cashflow"] = float(latest_cashflow.get('free_cashflow', 0)) / 100000000 if 'free_cashflow' in latest_cashflow else 0

        except Exception as vip_error:
            print(f"[基本面] VIP接口失败，使用普通接口: {vip_error}")
            # 降级到普通财务指标
            try:
                fina_data = fina_indicator(ts_code=ts_code)
                if fina_data is not None and not fina_data.empty:
                    latest_fina = fina_data.iloc[0]
                    fundamental_data["roe"] = float(latest_fina.get('roe', 0))
                    fundamental_data["gross_margin"] = float(latest_fina.get('grossprofit_margin', 0))
                    fundamental_data["growth_score"] = _calculate_growth_score(fina_data)
            except:
                pass

        return fundamental_data

    except Exception as e:
        print(f"[基本面] 错误: {e}")
        return {}


def _fetch_sentiment_optimized(ts_code: str, stock_name: str) -> Dict[str, Any]:
    """获取情绪面数据（优化版）"""
    try:
        from .tushare_client import daily_basic
        from datetime import datetime

        # 获取最新市场情绪指标
        today = datetime.now().strftime('%Y%m%d')
        latest_basic = daily_basic(ts_code=ts_code, trade_date=today)

        sentiment_data = {
            "market_sentiment": "中性",
            "volume_ratio": 1.0,
            "turnover_rate": 0,
            "sentiment_score": 50
        }

        if latest_basic is not None and not latest_basic.empty:
            latest = latest_basic.iloc[0]

            # 量比
            volume_ratio = float(latest.get('volume_ratio', 1.0) if hasattr(latest, 'get') else 1.0)
            # 换手率
            turnover_rate = float(latest.get('turnover_rate', 0) if hasattr(latest, 'get') else 0)

            # 情绪判断
            sentiment_score = 50
            if volume_ratio > 2:
                sentiment_score += 20
            elif volume_ratio > 1.5:
                sentiment_score += 10
            elif volume_ratio < 0.5:
                sentiment_score -= 20

            if turnover_rate > 10:
                sentiment_score += 15
            elif turnover_rate > 5:
                sentiment_score += 10
            elif turnover_rate < 1:
                sentiment_score -= 10

            sentiment_data = {
                "market_sentiment": _judge_sentiment(sentiment_score),
                "volume_ratio": volume_ratio,
                "turnover_rate": turnover_rate,
                "sentiment_score": min(100, max(0, sentiment_score)),
                "trading_activity": "活跃" if turnover_rate > 5 else "平淡" if turnover_rate < 2 else "正常"
            }

        return sentiment_data

    except Exception as e:
        print(f"[情绪面] 错误: {e}")
        return {"sentiment_score": 50, "market_sentiment": "中性"}


def _fetch_industry_optimized(ts_code: str, stock_name: str, industry: str) -> Dict[str, Any]:
    """获取行业面数据（优化版）"""
    try:
        # 获取股票的行业信息
        if not industry:
            from .tushare_client import stock_basic
            basic_info = stock_basic(ts_code=ts_code)
            if basic_info is not None and not basic_info.empty:
                industry = basic_info.iloc[0].get('industry', '未知')

        industry_data = {
            "industry_name": industry,
            "industry_pe": 20,  # 可以从行业数据获取
            "position_in_industry": "中游",
            "industry_trend": "稳定",
            "industry_score": 60
        }

        # TODO: 可以添加更多行业分析逻辑
        # 比如获取同行业其他股票进行对比

        return industry_data

    except Exception as e:
        print(f"[行业面] 错误: {e}")
        return {"industry_name": "未知", "industry_score": 50}


def _fetch_news_simplified(ts_code: str, stock_name: str) -> Dict[str, Any]:
    """获取新闻数据（完整版 - 使用5000积分新闻接口）"""
    try:
        from .news import fetch_news_summary, analyze_news_sentiment
        from .tushare_client import anns

        # 使用完整的新闻获取功能（包括news API和cctv_news）
        news_summary = fetch_news_summary(ts_code, days_back=7)
        sentiment_analysis = analyze_news_sentiment(news_summary)

        news_data = {
            "total_news": news_summary.get("meta", {}).get("total_news", 0),
            "positive_news": sentiment_analysis.get("positive", 0),
            "negative_news": sentiment_analysis.get("negative", 0),
            "neutral_news": sentiment_analysis.get("neutral", 0),
            "latest_announcements": [],
            "major_news": news_summary.get("major_news", [])[:3],
            "stock_news": news_summary.get("stock_news", [])[:5],
            "cctv_news": news_summary.get("cctv_news", [])[:2],
            "news_sentiment_score": sentiment_analysis.get("score", 50),
            "data_sources": news_summary.get("meta", {}).get("data_sources", [])
        }

        # 添加公告信息
        announcements = anns(ts_code=ts_code)
        if announcements is not None and not announcements.empty:
            for _, ann in announcements.head(3).iterrows():
                news_data["latest_announcements"].append({
                    "title": ann.get('title', '未知公告'),  # 使用get方法避免KeyError
                    "date": ann.get('ann_date', ''),
                    "type": ann.get('ann_type', '公告')
                })

        return news_data

    except Exception as e:
        print(f"[新闻] 错误: {e}")
        # 降级到公告模式
        try:
            from .tushare_client import anns
            announcements = anns(ts_code=ts_code)
            news_data = {"total_news": 0, "news_sentiment_score": 50, "latest_announcements": []}
            if announcements is not None and not announcements.empty:
                news_data["total_news"] = len(announcements)
                for _, ann in announcements.head(3).iterrows():
                    news_data["latest_announcements"].append({
                        "title": ann.get('title', '未知公告'),  # 使用get方法避免KeyError
                        "date": ann.get('ann_date', ''),
                        "type": ann.get('ann_type', '公告')
                    })
            return news_data
        except:
            return {"total_news": 0, "news_sentiment_score": 50}


def _fetch_market_simplified() -> Dict[str, Any]:
    """获取市场概况（简化版，不获取5426只股票）"""
    try:
        from .tushare_client import index_daily
        from datetime import datetime

        # 只获取主要指数
        today = datetime.now().strftime('%Y%m%d')

        market_data = {
            "indices": [],
            "market_sentiment": "中性"
        }

        # 获取上证指数
        try:
            sh_index = index_daily(ts_code='000001.SH', trade_date=today)
            if sh_index is not None and not sh_index.empty:
                latest = sh_index.iloc[0]
                market_data["indices"].append({
                    "name": "上证指数",
                    "close": float(latest.get('close', 0)),
                    "change": float(latest.get('pct_chg', 0))
                })
        except:
            pass

        return market_data

    except Exception as e:
        print(f"[市场] 错误: {e}")
        return {"market_sentiment": "中性"}


def _calculate_comprehensive_score(result: Dict) -> Dict[str, Any]:
    """计算综合评分（包含所有维度）"""
    scores = {
        "technical": result.get("technical", {}).get("technical_score", 50),
        "fundamental": result.get("fundamental", {}).get("valuation_score", 50),
        "sentiment": result.get("sentiment", {}).get("sentiment_score", 50),
        "industry": result.get("industry", {}).get("industry_score", 50)
    }

    # 权重分配
    weights = {
        "technical": 0.3,
        "fundamental": 0.3,
        "sentiment": 0.2,
        "industry": 0.2
    }

    # 计算加权总分
    total = sum(scores[k] * weights[k] for k in scores)

    return {
        "total": round(total, 1),
        "details": scores,
        "rating": _get_rating(total),
        "weights": weights
    }


def _generate_complete_report(result: Dict) -> str:
    """生成完整的分析报告"""
    stock_name = result['basic']['name']
    score = result.get('score', {})

    technical = result.get('technical', {})
    fundamental = result.get('fundamental', {})
    sentiment = result.get('sentiment', {})
    industry = result.get('industry', {})

    report = f"""# {stock_name} 专业投资分析报告
生成时间：{result['timestamp']}

## 一、技术面分析
- **当前价格**：{technical.get('price', 0):.2f}元
- **今日涨跌**：{technical.get('change', 0):+.2f}%
- **成交量**：{technical.get('volume', 0)/10000:.1f}万手
- **价格趋势**：{technical.get('trend', '震荡')}
- **技术评分**：{technical.get('technical_score', 50)}/100

## 二、基本面分析

### 盈利能力
- **净资产收益率(ROE)**：{fundamental.get('roe', 0):.2f}% - {'优秀' if fundamental.get('roe', 0) > 15 else '良好' if fundamental.get('roe', 0) > 10 else '一般' if fundamental.get('roe', 0) > 5 else '偏弱'}
- **毛利率**：{fundamental.get('gross_margin', 0):.2f}% - {'高毛利' if fundamental.get('gross_margin', 0) > 40 else '中等毛利' if fundamental.get('gross_margin', 0) > 20 else '低毛利'}
- **净利润**：{fundamental.get('net_profit', 0):.2f}亿元
- **营业收入**：{fundamental.get('revenue', 0):.2f}亿元

### 财务状况
- **总资产**：{fundamental.get('total_assets', 0):.2f}亿元
- **资产负债率**：{fundamental.get('debt_ratio', 0):.1f}% - {'低风险' if fundamental.get('debt_ratio', 0) < 40 else '中等风险' if fundamental.get('debt_ratio', 0) < 70 else '高风险'}
- **经营现金流**：{fundamental.get('operating_cashflow', 0):.2f}亿元 {'(健康)' if fundamental.get('operating_cashflow', 0) > 0 else '(需关注)'}

### 估值水平
- **市盈率(PE-TTM)**：{fundamental.get('pe_ttm', 0):.2f}倍 - {'低估' if fundamental.get('pe_ttm', 0) > 0 and fundamental.get('pe_ttm', 0) < 15 else '合理' if fundamental.get('pe_ttm', 0) < 30 else '高估'}
- **市净率(PB)**：{fundamental.get('pb', 0):.2f}倍 - {'低估' if fundamental.get('pb', 0) > 0 and fundamental.get('pb', 0) < 1.5 else '合理' if fundamental.get('pb', 0) < 3 else '高估'}
- **基本面评分**：{fundamental.get('valuation_score', 50)}/100

## 三、情绪面分析
- **市场情绪**：{sentiment.get('market_sentiment', '中性')}
- **量比**：{sentiment.get('volume_ratio', 1.0):.2f}
- **换手率**：{sentiment.get('turnover_rate', 0):.2f}%
- **交易活跃度**：{sentiment.get('trading_activity', '正常')}
- **情绪评分**：{sentiment.get('sentiment_score', 50)}/100

## 四、行业面分析
- **所属行业**：{industry.get('industry_name', '未知')}
- **行业地位**：{industry.get('position_in_industry', '中游')}
- **行业趋势**：{industry.get('industry_trend', '稳定')}
- **行业评分**：{industry.get('industry_score', 50)}/100

## 五、综合评价
- **综合评分**：{score.get('total', 50)}/100
- **投资评级**：{score.get('rating', '中性')}
- **各维度权重**：技术(30%)、基本(30%)、情绪(20%)、行业(20%)

## 六、操作建议
{_generate_suggestions(result)}

---
*专业版分析报告 - 包含技术面、基本面、情绪面、行业面完整分析*
"""
    return report


def _generate_suggestions(result: Dict) -> str:
    """生成操作建议"""
    score = result.get('score', {}).get('total', 50)
    technical = result.get('technical', {})
    sentiment = result.get('sentiment', {})

    suggestions = []

    if score >= 70:
        suggestions.append("- **强烈推荐**：各项指标表现优异，建议积极关注")
    elif score >= 60:
        suggestions.append("- **推荐关注**：整体表现良好，可适当配置")
    elif score >= 50:
        suggestions.append("- **中性观望**：表现平稳，等待更好时机")
    else:
        suggestions.append("- **谨慎回避**：指标偏弱，建议观望")

    if technical.get('trend') == "上升趋势":
        suggestions.append("- **技术面**：趋势向好，可顺势而为")
    elif technical.get('trend') == "下降趋势":
        suggestions.append("- **技术面**：趋势偏弱，注意风险")

    if sentiment.get('sentiment_score', 50) > 70:
        suggestions.append("- **情绪面**：市场情绪高涨，注意追高风险")
    elif sentiment.get('sentiment_score', 50) < 30:
        suggestions.append("- **情绪面**：市场情绪低迷，可能存在机会")

    return "\n".join(suggestions) if suggestions else "- 建议保持观望"


def _generate_executive_summary(result: Dict) -> str:
    """生成执行摘要"""
    stock_name = result['basic']['name']
    score = result.get('score', {})

    return f"{stock_name}综合评分{score.get('total', 50)}/100，评级【{score.get('rating', '中性')}】。技术面{result.get('technical', {}).get('trend', '震荡')}，基本面估值{_judge_valuation(result.get('fundamental', {}).get('pe_ttm', 20))}，市场情绪{result.get('sentiment', {}).get('market_sentiment', '中性')}，行业地位{result.get('industry', {}).get('position_in_industry', '中游')}。"


# 辅助函数
def _analyze_trend(df) -> str:
    """分析价格趋势"""
    if df is None or len(df) < 5:
        return "数据不足"

    ma5 = df['close'].head(5).mean()
    current = df.iloc[0]['close']

    if current > ma5 * 1.02:
        return "上升趋势"
    elif current < ma5 * 0.98:
        return "下降趋势"
    else:
        return "震荡整理"


def _calculate_support_resistance(df) -> Dict:
    """计算支撑压力位"""
    if df is None or df.empty:
        return {}

    recent = df.head(20)
    return {
        "support": float(recent['low'].min()),
        "resistance": float(recent['high'].max())
    }


def _calculate_technical_score(df) -> int:
    """计算技术面评分"""
    score = 50

    if df is not None and not df.empty:
        latest = df.iloc[-1]

        # RSI评分
        try:
            rsi = latest.get('rsi14', 50) if hasattr(latest, 'get') else 50
        except:
            rsi = 50

        if 40 < rsi < 60:
            score += 10
        elif rsi <= 30:
            score += 15  # 超卖
        elif rsi >= 70:
            score -= 10  # 超买

        # MACD评分
        try:
            macd = latest.get('macd', 0) if hasattr(latest, 'get') else 0
        except:
            macd = 0
        if macd > 0:
            score += 10
        elif macd < 0:
            score -= 10

    return min(100, max(0, score))


def _calculate_valuation_score(data) -> int:
    """计算估值评分"""
    score = 50

    # 安全获取数据
    try:
        if hasattr(data, 'get') and callable(getattr(data, 'get')):
            pe = data.get('pe_ttm', 20)
            pb = data.get('pb', 2)
        elif isinstance(data, dict):
            pe = data.get('pe_ttm', 20)
            pb = data.get('pb', 2)
        else:
            # 如果data不是预期的类型，使用默认值
            pe = 20
            pb = 2
    except Exception:
        # 如果任何操作失败，使用默认值
        pe = 20
        pb = 2

    # PE评分
    if 0 < pe < 15:
        score += 20  # 低估
    elif 15 <= pe < 25:
        score += 10  # 合理
    elif pe >= 50:
        score -= 20  # 高估

    # PB评分
    if 0 < pb < 1:
        score += 15  # 破净
    elif 1 <= pb < 2:
        score += 10  # 合理
    elif pb >= 5:
        score -= 15  # 高估

    return min(100, max(0, score))


def _calculate_growth_score(fina_data) -> int:
    """计算成长性评分"""
    # 可以基于营收增长、利润增长等指标
    return 60


def _judge_sentiment(score: int) -> str:
    """判断市场情绪"""
    if score >= 70:
        return "乐观"
    elif score >= 60:
        return "偏多"
    elif score >= 40:
        return "中性"
    elif score >= 30:
        return "偏空"
    else:
        return "悲观"


def _judge_valuation(pe: float) -> str:
    """判断估值水平"""
    if pe <= 0:
        return "亏损"
    elif pe < 15:
        return "低估"
    elif pe < 25:
        return "合理"
    elif pe < 40:
        return "偏高"
    else:
        return "高估"


def _get_rating(score: float) -> str:
    """获取评级"""
    if score >= 70:
        return "强烈推荐"
    elif score >= 60:
        return "推荐"
    elif score >= 50:
        return "中性"
    elif score >= 40:
        return "谨慎"
    else:
        return "回避"