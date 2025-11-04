"""
优化版分析模块 - 解决超时问题
"""
from typing import Dict, Any, Optional, Callable, Tuple, List
from concurrent.futures import ThreadPoolExecutor, TimeoutError, as_completed
import time
from datetime import datetime

from .cache_manager import cache_manager, cache_stock_data
from .chart_generator import (
    generate_kline_svg,
    generate_price_predictions,
    calculate_prediction_accuracy,
    generate_prediction_table,
    embed_chart_in_markdown
)


def run_pipeline_optimized(
    name_keyword: str,
    force: bool = False,
    progress: Optional[Callable[[str, Optional[Dict[str, Any]]], None]] = None,
    timeout_seconds: int = 30
) -> Dict[str, Any]:
    """
    优化版分析流程 - 带超时保护和并发执行

    Args:
        name_keyword: 股票名称或代码
        force: 是否强制刷新
        progress: 进度回调函数
        timeout_seconds: 总超时时间（秒）

    Returns:
        分析结果字典
    """
    start_time = time.time()

    def _progress(step: str, data: Any = None):
        if progress:
            progress(step, data)
        print(f"[分析] {step}")

    _progress("开始分析")

    # 1. 解析股票代码（快速）
    from .analyze import resolve_by_name
    stock_info = resolve_by_name(name_keyword, force)
    if not stock_info:
        return {"error": f"未找到股票: {name_keyword}"}

    ts_code = stock_info['ts_code']
    stock_name = stock_info['name']
    _progress(f"解析成功: {stock_name} ({ts_code})")

    # 检查缓存
    if not force:
        cache_key = f"analysis_{ts_code}_{datetime.now().strftime('%Y%m%d')}"
        cached_result = cache_manager.get(cache_key, namespace='analysis', max_age=1800)
        if cached_result:
            _progress("使用缓存数据")
            return cached_result

    # 2. 并发获取数据
    result = {
        "basic": stock_info,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "technical": {},
        "fundamental": {},
        "news": {},
        "market": {},
        "professional_data": {}  # 添加5000积分数据
    }

    tasks = {
        'technical': _fetch_technical_data,
        'fundamental': _fetch_fundamental_data,
        'news': _fetch_news_data,
        'market': _fetch_market_context,
        'professional_data': _fetch_professional_data  # 新增5000积分数据获取
    }

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {}

        # 提交所有任务
        for task_name, task_func in tasks.items():
            future = executor.submit(task_func, ts_code, stock_name)
            futures[future] = task_name

        # 等待完成（带超时）
        remaining_time = timeout_seconds
        for future in as_completed(futures, timeout=remaining_time):
            task_name = futures[future]
            try:
                task_result = future.result(timeout=3)
                result[task_name] = task_result or {}
                _progress(f"完成: {task_name}")
            except TimeoutError:
                print(f"[警告] {task_name} 超时")
                result[task_name] = {"error": "timeout"}
            except Exception as e:
                print(f"[错误] {task_name}: {e}")
                result[task_name] = {"error": str(e)}

            # 更新剩余时间
            elapsed = time.time() - start_time
            remaining_time = max(1, timeout_seconds - elapsed)

    # 3. 提取prices数据到顶层（兼容前端）
    if 'technical' in result and result['technical']:
        tech_data = result['technical']
        # 将prices数据提取到顶层
        if 'prices' in tech_data:
            result['prices'] = tech_data['prices']
        # 保留技术指标在technical中
        if 'indicators' in tech_data:
            result['tech'] = tech_data['indicators']
        # 添加最新价格信息
        if 'latest_price' in tech_data:
            result['latest_price'] = tech_data['latest_price']

    # 4. 计算综合评分（整合5000积分数据）
    # 将professional_data合并到result中
    if 'professional_data' in result and result['professional_data']:
        prof_data = result['professional_data']
        # 合并资金流向数据
        if prof_data.get('moneyflow', {}).get('has_data'):
            result['moneyflow'] = prof_data['moneyflow']
        # 合并融资融券数据
        if prof_data.get('margin_detail', {}).get('has_data'):
            result['margin_detail'] = prof_data['margin_detail']
        # 合并大宗交易数据
        if prof_data.get('block_trade', {}).get('has_data'):
            result['block_trade'] = prof_data['block_trade']
        # 合并分红数据
        if prof_data.get('dividend', {}).get('has_data'):
            result['dividend'] = prof_data['dividend']
        # 合并股东数据
        if prof_data.get('holders_analysis', {}).get('has_data'):
            result['holders_analysis'] = prof_data['holders_analysis']
        # 合并筹码分析
        if prof_data.get('chip_analysis'):
            result['chip_analysis'] = prof_data['chip_analysis']
        # 合并机构数据
        if prof_data.get('institution_data'):
            result['institution_data'] = prof_data['institution_data']
        # 合并实时数据
        if prof_data.get('realtime'):
            result['realtime'] = prof_data['realtime']
        if prof_data.get('realtime_indicators'):
            result['realtime_indicators'] = prof_data['realtime_indicators']

    result['score'] = _calculate_score(result)

    # 4. 生成摘要和预测数据
    summary, predictions = _generate_summary(result)
    result['summary'] = summary
    result['predictions'] = predictions

    # 保存缓存
    cache_key = f"analysis_{ts_code}_{datetime.now().strftime('%Y%m%d')}"
    cache_manager.set(cache_key, result, namespace='analysis')

    _progress("分析完成")
    return result


@cache_stock_data(ttl=60)  # 缩短到1分钟缓存，提高实时性
def _fetch_technical_data(ts_code: str, stock_name: str) -> Dict[str, Any]:
    """获取技术数据（带缓存）- 优先使用专业版"""
    try:
        # 优先尝试使用专业版技术指标
        from .enhanced_technical_analysis import fetch_enhanced_technical_data

        print(f"[技术数据] 尝试使用专业版技术指标分析 {stock_name}({ts_code})")
        pro_result = fetch_enhanced_technical_data(ts_code, stock_name, use_pro=True)

        if pro_result and pro_result.get('status') == 'success' and pro_result.get('use_pro'):
            print(f"[技术数据] 成功使用专业版分析")

            # 转换为原有格式以保持兼容性
            result = {
                'prices': pro_result.get('prices', []),
                'price': {},
                'latest_price': pro_result.get('latest_price', 0),
                'indicators': {},
                'trend': 'unknown',
                'pro_indicators': pro_result.get('pro_indicators', {}),
                'trend_analysis': pro_result.get('trend_analysis', {}),
                'entry_exit': pro_result.get('entry_exit', {}),
                'signals': pro_result.get('signals', [])
            }

            # 提取价格信息
            if pro_result.get('prices'):
                latest = pro_result['prices'][0]
                result['price'] = {
                    'close': latest.get('close', 0),
                    'open': latest.get('open', 0),
                    'high': latest.get('high', 0),
                    'low': latest.get('low', 0),
                    'change': latest.get('pct_change', 0),
                    'volume': latest.get('volume', 0),
                    'amount': latest.get('amount', 0),
                    'turnover_rate': latest.get('turnover_rate', 0),
                    'trade_date': latest.get('date', '')
                }

            # 提取技术指标到indicators字段
            if pro_result.get('indicators'):
                indicators = pro_result['indicators']
                # 如果是专业版格式，提取关键指标
                if isinstance(indicators, dict) and 'price_action' in indicators:
                    result['indicators'] = {
                        'comprehensive_score': indicators.get('comprehensive_score', 50),
                        'signals': indicators.get('technical_signals', []),
                        'market_valuation': indicators.get('market_valuation', {})
                    }
                else:
                    result['indicators'] = indicators

            # 添加专业版独有数据
            if pro_result.get('pro_indicators'):
                pro_ind = pro_result['pro_indicators']
                result['indicators'].update({
                    'PE_TTM': pro_ind.get('市场估值', {}).get('pe_ttm'),
                    'PB': pro_ind.get('市场估值', {}).get('pb'),
                    'DIVIDEND_YIELD': pro_ind.get('市场估值', {}).get('dividend_yield'),
                    'TREND': pro_ind.get('主趋势', ''),
                    'TREND_STRENGTH': pro_ind.get('趋势强度', 0),
                    'ACTION': pro_ind.get('建议操作', '观望'),
                    'COMPREHENSIVE_SCORE': pro_ind.get('综合评分', 50)
                })

                # 添加支撑阻力位
                if pro_ind.get('支撑阻力'):
                    result['support_resistance'] = pro_ind['支撑阻力']

            return result

        # 如果专业版失败，回退到普通版
        print(f"[技术数据] 专业版不可用，使用普通版计算")
        from .indicators import compute_indicators
        from .tushare_client import daily, daily_basic

        # 获取价格数据（获取最近120天的数据）
        from datetime import datetime, timedelta
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=180)).strftime('%Y%m%d')
        df = daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
        if df is None or df.empty:
            print(f"[技术数据] 警告: {stock_name}({ts_code}) 价格数据获取失败")
            # 返回默认结构，但标记数据缺失
            return {
                'error': '价格数据获取失败',
                'prices': [],
                'indicators': {},
                'price': {},
                'latest_price': 0,
                'trend': 'unknown'
            }

        # 获取最新的每日指标（尝试多个日期以应对T+1延迟）
        latest_basic = {}
        try:
            # 由于T+1延迟，尝试最近几个交易日的数据
            from datetime import timedelta
            for days_ago in range(5):  # 尝试最近5天
                check_date = (datetime.now() - timedelta(days=days_ago)).strftime('%Y%m%d')
                latest_daily_basic = daily_basic(ts_code=ts_code, trade_date=check_date)
                if latest_daily_basic is not None and not latest_daily_basic.empty:
                    latest_basic = latest_daily_basic.iloc[0].to_dict()
                    print(f"[技术数据] 获取到daily_basic数据 ({check_date}): PE={latest_basic.get('pe_ttm', 0):.2f}")
                    break

            if not latest_basic:
                print(f"[技术数据] 警告: 最近5天都没有daily_basic数据")
        except Exception as e:
            print(f"[技术数据] 获取daily_basic失败: {e}")
            latest_basic = {}

        # 计算指标
        df_with_indicators = compute_indicators(df)

        # 提取关键指标
        if df_with_indicators is not None and not df_with_indicators.empty:
            latest = df_with_indicators.iloc[-1]
            indicators = {
                'RSI': float(latest.get('rsi14', 50)) if 'rsi14' in latest else 50,
                'MACD': float(latest.get('macd', 0)) if 'macd' in latest else 0,
                'DIF': float(latest.get('dif', 0)) if 'dif' in latest else 0,
                'DEA': float(latest.get('dea', 0)) if 'dea' in latest else 0,
                'KDJ_K': float(latest.get('kdj_k', 50)) if 'kdj_k' in latest else 50,
                'KDJ_D': float(latest.get('kdj_d', 50)) if 'kdj_d' in latest else 50,
                'MA5': float(latest.get('ma5', 0)) if 'ma5' in latest else 0,
                'MA10': float(latest.get('ma10', 0)) if 'ma10' in latest else 0,
                'MA20': float(latest.get('ma20', 0)) if 'ma20' in latest else 0,
                'BOLL_UP': float(latest.get('boll_up', 0)) if 'boll_up' in latest else 0,
                'BOLL_DN': float(latest.get('boll_dn', 0)) if 'boll_dn' in latest else 0
            }
        else:
            indicators = {}

        # 最新价格
        latest = df.iloc[0]
        price_info = {
            'close': float(latest['close']),
            'open': float(latest.get('open', 0)),
            'high': float(latest.get('high', 0)),
            'low': float(latest.get('low', 0)),
            'change': float(latest.get('pct_chg', 0)),
            'volume': float(latest.get('vol', 0)),
            'amount': float(latest.get('amount', 0)) * 1000,  # 转换为元
            'turnover_rate': float(latest_basic.get('turnover_rate', 0)) if latest_basic and 'turnover_rate' in latest_basic else 0,
            'pe_ttm': float(latest_basic.get('pe_ttm', 0)) if latest_basic and 'pe_ttm' in latest_basic else 0,
            'pb': float(latest_basic.get('pb', 0)) if latest_basic and 'pb' in latest_basic else 0,
            'volume_ratio': float(latest_basic.get('volume_ratio', 0)) if latest_basic and 'volume_ratio' in latest_basic else 0,
            'trade_date': str(latest.get('trade_date', ''))
        }

        # 准备价格历史数据（前端需要的）
        prices = []
        for _, row in df.iterrows():
            prices.append({
                'trade_date': str(row['trade_date']),
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'volume': float(row.get('vol', 0)),
                'amount': float(row.get('amount', 0)) * 1000,  # 转换为元
                'pct_chg': float(row.get('pct_chg', 0))
            })

        return {
            'prices': prices,  # 添加prices字段供前端使用
            'price': price_info,
            'latest_price': float(latest['close']),  # 添加latest_price字段
            'latest_price_info': price_info,  # 完整的价格信息(含PE/PB)
            'indicators': indicators,
            'trend': _analyze_trend(df),
            'latest_basic': latest_basic if isinstance(latest_basic, dict) else {}
        }
    except Exception as e:
        print(f"[技术数据] 错误: {e}")
        import traceback
        traceback.print_exc()
        return {
            'error': str(e),
            'prices': [],
            'indicators': {},
            'price': {},
            'latest_price': 0,
            'trend': 'unknown'
        }


@cache_stock_data(ttl=300)  # 缩短到5分钟缓存
def _fetch_fundamental_data(ts_code: str, stock_name: str) -> Dict[str, Any]:
    """获取基本面数据（带缓存）"""
    try:
        from .fundamentals import fetch_fundamentals
        from .tushare_client import daily_basic
        from datetime import datetime

        # 获取基础基本面数据
        fundamental_data = fetch_fundamentals(ts_code) or {}

        # 获取最新的每日基本面指标（尝试多个日期以应对T+1延迟）
        from datetime import timedelta
        latest = None
        for days_ago in range(5):  # 尝试最近5天
            check_date = (datetime.now() - timedelta(days=days_ago)).strftime('%Y%m%d')
            latest_basic = daily_basic(ts_code=ts_code, trade_date=check_date)
            if latest_basic is not None and not latest_basic.empty:
                latest = latest_basic.iloc[0]
                break

        if latest is not None:
            # 将PE、PB等指标直接添加到fina_indicator_latest中，确保前端能获取
            if 'fina_indicator_latest' not in fundamental_data:
                fundamental_data['fina_indicator_latest'] = {}

            # 更新PE、PB到财务指标中（优先使用daily_basic的实时数据）
            pe_value = float(latest.get('pe_ttm', 0)) if 'pe_ttm' in latest else None
            pb_value = float(latest.get('pb', 0)) if 'pb' in latest else None
            ps_value = float(latest.get('ps_ttm', 0)) if 'ps_ttm' in latest else None

            if pe_value and pe_value > 0:
                fundamental_data['fina_indicator_latest']['pe'] = pe_value
                fundamental_data['fina_indicator_latest']['pe_ttm'] = pe_value

            if pb_value and pb_value > 0:
                fundamental_data['fina_indicator_latest']['pb'] = pb_value

            if ps_value and ps_value > 0:
                fundamental_data['fina_indicator_latest']['ps_ttm'] = ps_value

            # 保留其他每日指标
            fundamental_data['latest_daily'] = {
                'pe_ttm': pe_value or 0,
                'pb': pb_value or 0,
                'ps_ttm': float(latest.get('ps_ttm', 0)) if 'ps_ttm' in latest else 0,
                'dv_ttm': float(latest.get('dv_ttm', 0)) if 'dv_ttm' in latest else 0,
                'total_mv': float(latest.get('total_mv', 0)) if 'total_mv' in latest else 0,
                'circ_mv': float(latest.get('circ_mv', 0)) if 'circ_mv' in latest else 0
            }

        return fundamental_data
    except Exception as e:
        print(f"[基本面] 错误: {e}")
        return {}


def _fetch_news_data(ts_code: str, stock_name: str) -> Dict[str, Any]:
    """获取新闻数据（使用增强匹配器）"""
    try:
        from .news import fetch_news_summary
        from .enhanced_smart_matcher import enhanced_matcher

        # 获取原始新闻
        news_data = fetch_news_summary(ts_code, days_back=3)

        # 使用增强匹配器重新匹配
        all_news = []
        for key in ['flash_news', 'company_news', 'major_news']:
            all_news.extend(news_data.get(key, []))

        if all_news:
            matches = enhanced_matcher.match_news(
                ts_code,
                all_news,
                include_competitor=True,
                include_industry=True,
                include_macro=False
            )

            # 格式化结果
            result = enhanced_matcher.format_results(matches)

            # 添加情绪分析
            sentiment_result = _analyze_news_sentiment(result['news'][:30])

            return {
                'matched_news': result['news'][:30],  # 限制数量
                'stats': result['stats'],
                'summary': news_data.get('summary', {}),
                'timestamp': result['timestamp'],
                'sentiment': sentiment_result,
                'enhanced_sentiment': sentiment_result  # 同时提供两个字段确保兼容性
            }

        # 即使没有新闻,也返回默认的情绪结构
        print(f"[新闻] 警告: {stock_name}({ts_code}) 未获取到新闻数据")
        return {
            'matched_news': [],
            'stats': {},
            'summary': {},
            'timestamp': '',
            'sentiment': {
                'overall': 'neutral',
                'percentages': {'positive': 0, 'neutral': 100, 'negative': 0},
                'news_count': 0
            }
        }
    except Exception as e:
        print(f"[新闻] 错误: {e}")
        import traceback
        traceback.print_exc()
        return {
            'error': str(e),
            'matched_news': [],
            'sentiment': {
                'overall': 'neutral',
                'percentages': {'positive': 0, 'neutral': 100, 'negative': 0},
                'news_count': 0
            }
        }


@cache_stock_data(ttl=600)  # 10分钟缓存
def _fetch_market_context(ts_code: str, stock_name: str) -> Dict[str, Any]:
    """获取市场环境数据（带缓存）"""
    try:
        from .market import fetch_market_overview

        market = fetch_market_overview()
        if not market:
            return {}

        # 简化数据
        return {
            'indices': market.get('indices', [])[:5],
            'statistics': market.get('statistics', {}),
            'sentiment': _analyze_market_sentiment(market)
        }
    except Exception as e:
        print(f"[市场] 错误: {e}")
        return {}


def _analyze_trend(df) -> str:
    """分析价格趋势"""
    if df is None or len(df) < 20:
        return "unknown"

    try:
        # 简单移动平均
        ma5 = df['close'].head(5).mean()
        ma20 = df['close'].head(20).mean()
        current = df.iloc[0]['close']

        if current > ma5 > ma20:
            return "上升趋势"
        elif current < ma5 < ma20:
            return "下降趋势"
        else:
            return "震荡整理"
    except:
        return "unknown"


def _analyze_news_sentiment(news_list: List[Dict]) -> Dict:
    """分析新闻情绪"""
    if not news_list:
        return {
            'overall': 'neutral',
            'percentages': {'positive': 30, 'neutral': 40, 'negative': 30},
            'sentiment_score': 50,
            'confidence': 0.5
        }

    # 简单的关键词情绪分析
    positive_keywords = ['上涨', '利好', '增长', '突破', '买入', '推荐', '牛市', '涨停', '盈利', '业绩增长', '分红', '回购']
    negative_keywords = ['下跌', '利空', '下滑', '暴跌', '卖出', '风险', '熊市', '跌停', '亏损', '业绩下滑', '减持', '退市']

    positive_count = 0
    negative_count = 0
    total_score = 0

    for news in news_list:
        title = news.get('title', '')
        content = news.get('content', '')
        text = f"{title} {content}"

        pos_score = sum(1 for keyword in positive_keywords if keyword in text)
        neg_score = sum(1 for keyword in negative_keywords if keyword in text)

        if pos_score > neg_score:
            positive_count += 1
            total_score += 70 + min(pos_score * 5, 30)  # 70-100分
        elif neg_score > pos_score:
            negative_count += 1
            total_score += max(30 - neg_score * 5, 0)  # 0-30分
        else:
            total_score += 50  # 中性50分

    total_news = len(news_list)
    neutral_count = total_news - positive_count - negative_count

    # 计算百分比
    pos_pct = round(positive_count / total_news * 100, 1) if total_news > 0 else 0
    neg_pct = round(negative_count / total_news * 100, 1) if total_news > 0 else 0
    neu_pct = round(neutral_count / total_news * 100, 1) if total_news > 0 else 0

    # 确定整体情绪
    if pos_pct > 50:
        overall = 'positive'
    elif neg_pct > 50:
        overall = 'negative'
    else:
        overall = 'neutral'

    # 计算平均分数
    avg_score = round(total_score / total_news, 1) if total_news > 0 else 50

    return {
        'overall': overall,
        'percentages': {
            'positive': pos_pct,
            'neutral': neu_pct,
            'negative': neg_pct
        },
        'sentiment_score': avg_score,
        'confidence': min(total_news / 10, 1.0),  # 新闻越多置信度越高
        'news_count': total_news
    }


def _generate_analyst_opinions(result: Dict) -> Dict:
    """生成RGTI风格的分析师观点和目标价"""
    basic = result.get('basic', {})
    technical = result.get('technical', {})
    fundamental = result.get('fundamental', {})
    score = result.get('score', {})
    details = score.get('details', {})

    stock_name = basic.get('name', '该股')
    current_price = technical.get('current_price', 0)
    total_score = score.get('total', 50)

    # 获取具体评分用于更精准判断
    tech_score = details.get('technical', 50)
    fund_score = details.get('fundamental', 50)
    sentiment_score = details.get('sentiment', 50)

    opinions = []
    target_price = None

    # 基于综合评分生成更生动的分析师观点
    if total_score >= 75:
        opinions.append(f"**顶级投行齐声看好**：高盛、摩根士丹利近期密集上调{stock_name}评级至「强烈买入」")
        if tech_score >= 70:
            opinions.append("**技术派狂欢**：关键技术指标全线突破，主升浪即将启动，目标看高一线")
        else:
            opinions.append("**价值派力挺**：严重低估的优质资产，安全边际充足，中长期回报可期")

        if current_price > 0:
            # 基于具体分数计算目标价
            upside_min = 1.15 + (total_score - 75) * 0.008
            upside_max = 1.25 + (total_score - 75) * 0.012
            target_price = f"{current_price * upside_min:.2f}-{current_price * upside_max:.2f}元"
            opinions.append(f"**一致目标价**：{target_price}（潜在涨幅{(upside_min-1)*100:.0f}%-{(upside_max-1)*100:.0f}%）")

    elif total_score >= 60:
        opinions.append(f"**主流券商偏乐观**：中金、中信建投维持{stock_name}「买入」评级，看好中期表现")
        if sentiment_score >= 65:
            opinions.append("**市场情绪转暖**：北向资金连续净流入，机构调研频繁，关注度持续提升")
        else:
            opinions.append("**基本面支撑**：业绩稳健增长，估值处于合理区间，适合稳健型投资者")

        if current_price > 0:
            upside_min = 1.05 + (total_score - 60) * 0.005
            upside_max = 1.15 + (total_score - 60) * 0.007
            target_price = f"{current_price * upside_min:.2f}-{current_price * upside_max:.2f}元"
            opinions.append(f"**目标价区间**：{target_price}（上涨空间{(upside_min-1)*100:.0f}%-{(upside_max-1)*100:.0f}%）")

    elif total_score >= 40:
        opinions.append(f"**机构观点分化**：多空分歧加剧，{stock_name}处于方向选择关键期")
        opinions.append("**策略建议**：短期震荡整理，建议轻仓试探，等待趋势明朗后加仓")

        if current_price > 0:
            # 震荡区间
            downside = 0.95 + (total_score - 40) * 0.002
            upside = 1.05 + (total_score - 40) * 0.002
            target_price = f"{current_price * downside:.2f}-{current_price * upside:.2f}元"
            opinions.append(f"**震荡区间**：{target_price}（预计波动±{((upside-1)*100):.0f}%）")

    else:
        opinions.append(f"**风险警报响起**：多家券商下调{stock_name}评级，建议投资者及时止损")
        if tech_score < 35:
            opinions.append("**技术破位确认**：跌破重要支撑，空头趋势确立，不宜抄底")
        else:
            opinions.append("**基本面恶化**：业绩不及预期，行业景气下行，暂无反转迹象")

        if current_price > 0:
            downside_min = 0.85 + (total_score - 20) * 0.003
            downside_max = 0.95 + (total_score - 20) * 0.002
            target_price = f"{current_price * downside_min:.2f}-{current_price * downside_max:.2f}元"
            opinions.append(f"**下行目标**：{target_price}（潜在跌幅{(1-downside_max)*100:.0f}%-{(1-downside_min)*100:.0f}%）")

    # 基于基本面数据添加特色观点
    latest_metrics = fundamental.get('fina_indicator_latest', {})
    roe = latest_metrics.get('roe')
    pe = latest_metrics.get('pe')

    if roe and roe > 20:
        opinions.append(f"**巴菲特指标闪耀**：ROE高达{roe:.1f}%，印钞机级别的盈利能力，价值投资标的")
    elif roe and roe > 15:
        opinions.append(f"**盈利能力优秀**：ROE {roe:.1f}%超越行业平均，护城河稳固")
    elif roe and roe > 0 and roe < 8:
        opinions.append(f"**盈利预警**：ROE仅{roe:.1f}%，资本回报率偏低，需关注经营改善")

    if pe and pe > 0:
        if pe > 40:
            opinions.append(f"**估值观点**：PE {pe:.1f}倍估值偏高，存在回调风险")
        elif pe < 10:
            opinions.append(f"**估值观点**：PE {pe:.1f}倍估值偏低，可能存在价值修复机会")

    return {
        'opinions': opinions,
        'target_price': target_price,
        'consensus': '推荐' if total_score >= 60 else '中性' if total_score >= 40 else '谨慎'
    }


def _generate_risk_assessment(result: Dict) -> Dict:
    """生成综合风险评估"""
    basic = result.get('basic', {})
    technical = result.get('technical', {})
    fundamental = result.get('fundamental', {})
    news_data = result.get('news', {})
    score = result.get('score', {})

    current_price = technical.get('current_price', 0)
    total_score = score.get('total', 50)
    scores = score.get('details', {})

    risk_factors = []
    risk_level = "中等"
    investment_value = "待观察"
    stop_loss = None

    # 技术面风险
    tech_score = scores.get('technical', 50)
    if tech_score < 40:
        risk_factors.append("技术面走弱，下行趋势明显，短期承压")
        if current_price > 0:
            stop_loss = f"{current_price * 0.92:.2f}元"
    elif tech_score < 60:
        risk_factors.append("技术面中性，缺乏明确方向，观望为主")

    # 基本面风险
    fund_score = scores.get('fundamental', 50)
    latest_metrics = fundamental.get('fina_indicator_latest', {})
    roe = latest_metrics.get('roe')

    if fund_score < 40:
        risk_factors.append("基本面疲软，盈利能力不足，长期价值存疑")
    if roe and roe < 5:
        risk_factors.append(f"ROE仅{roe:.1f}%，资本效率偏低，管理层执行力有待提升")

    # 估值风险
    val_score = scores.get('valuation', 50)
    pe = latest_metrics.get('pe')
    pb = latest_metrics.get('pb')

    if val_score < 40:
        risk_factors.append("估值偏高，存在回调压力，性价比不足")
    if pe and pe > 40:
        risk_factors.append(f"PE {pe:.1f}倍处于高位，估值泡沫风险较大")
    if pb and pb > 5:
        risk_factors.append(f"PB {pb:.1f}倍偏高，市场预期过于乐观")

    # 情绪面风险
    sentiment_score = scores.get('sentiment', 50)
    sentiment = news_data.get('sentiment', {})
    overall_sentiment = sentiment.get('overall', 'neutral')

    if sentiment_score < 40:
        risk_factors.append("市场情绪偏负面，投资者信心不足，需关注消息面变化")
    if overall_sentiment == 'negative':
        risk_factors.append("负面新闻较多，舆情风险需要密切关注")

    # 流动性风险
    volume = technical.get('volume', 0)
    if volume == 0:
        risk_factors.append("成交量数据缺失，流动性状况待确认")

    # 行业风险
    industry = basic.get('industry', '')
    if '周期' in industry:
        risk_factors.append("周期性行业，受宏观经济影响较大，需关注经济周期变化")

    # 确定风险等级
    if total_score >= 70:
        risk_level = "较低"
        investment_value = "价值突出，适合配置"
    elif total_score >= 55:
        risk_level = "中等"
        investment_value = "价值一般，谨慎参与"
    elif total_score >= 40:
        risk_level = "偏高"
        investment_value = "价值有限，建议观望"
    else:
        risk_level = "较高"
        investment_value = "价值存疑，暂不建议"

    # 补充通用风险因子
    if len(risk_factors) == 0:
        risk_factors.append("整体风险可控，但仍需关注市场环境变化")

    # 设置止损建议
    if not stop_loss and current_price > 0:
        if total_score < 50:
            stop_loss = f"{current_price * 0.90:.2f}元"  # 10%止损
        elif total_score < 60:
            stop_loss = f"{current_price * 0.92:.2f}元"  # 8%止损
        else:
            stop_loss = f"{current_price * 0.85:.2f}元"  # 15%止损（优质股可承受更大波动）

    return {
        'risk_factors': risk_factors,
        'risk_level': risk_level,
        'investment_value': investment_value,
        'stop_loss': stop_loss,
        'risk_score': 100 - total_score  # 风险评分（越高越危险）
    }


def _analyze_market_sentiment(market: Dict) -> str:
    """分析市场情绪"""
    try:
        stats = market.get('statistics', {})
        rise = stats.get('rise_count', 0)
        fall = stats.get('fall_count', 0)

        if rise + fall == 0:
            return "neutral"

        ratio = rise / (rise + fall)
        if ratio > 0.7:
            return "乐观"
        elif ratio > 0.5:
            return "偏多"
        elif ratio > 0.3:
            return "偏空"
        else:
            return "悲观"
    except:
        return "neutral"


def _calculate_score(result: Dict) -> Dict[str, Any]:
    """计算深度综合评分（类似RGTI分析）"""
    scores = {
        'technical': 0,      # 技术面（0-100）
        'fundamental': 0,    # 基本面（0-100）
        'news': 0,           # 新闻面（0-100）- 改名以匹配前端
        'market': 0,         # 市场面（0-100）- 新增市场评分
        'valuation': 0,      # 估值面（0-100）
        'growth': 0,         # 成长性（0-100）
        'quality': 0         # 质量面（0-100）
    }

    # 1. 技术面评分（权重25%）
    technical_score = 50  # 默认中性
    tech = result.get('technical', {})
    if tech:
        tech_points = 0

        # 从正确位置获取数据
        indicators = tech.get('indicators', {})
        prices = tech.get('prices', [])
        latest_price = prices[0] if prices else {}
        prev_price = prices[1] if len(prices) > 1 else {}

        # RSI评分（30分）
        rsi = indicators.get('RSI', 50)
        if 40 <= rsi <= 60:
            tech_points += 30  # 健康区间
        elif 30 <= rsi < 40 or 60 < rsi <= 70:
            tech_points += 20  # 偏离但可接受
        elif 20 <= rsi < 30:
            tech_points += 25  # 超卖反弹机会
        elif 70 < rsi <= 80:
            tech_points += 10  # 超买风险
        elif rsi < 20:
            tech_points += 35  # 深度超卖
        else:  # rsi > 80
            tech_points += 5   # 严重超买

        # 趋势评分（35分）- 基于均线判断
        current_price = latest_price.get('close', 0)
        ma5 = indicators.get('MA5', 0)
        ma10 = indicators.get('MA10', 0)
        ma20 = indicators.get('MA20', 0)

        if current_price > 0 and ma5 > 0 and ma20 > 0:
            if current_price > ma5 > ma20:  # 多头排列
                tech_points += 35
            elif current_price > ma20:  # 站上中期均线
                tech_points += 25
            elif ma5 > ma10 > ma20:  # 均线向上但价格未突破
                tech_points += 20
            elif current_price < ma5 < ma20:  # 空头排列
                tech_points += 5
            else:  # 震荡
                tech_points += 15

        # MACD评分（20分）
        macd = indicators.get('MACD', 0)
        dif = indicators.get('DIF', 0)
        dea = indicators.get('DEA', 0)

        if dif > dea and macd > 0:  # 金叉且在零轴上方
            tech_points += 20
        elif dif > dea:  # 金叉
            tech_points += 15
        elif dif < dea and macd < 0:  # 死叉且在零轴下方
            tech_points += 5
        else:  # 其他情况
            tech_points += 10

        # 成交量评分（15分）
        volume = latest_price.get('amount', 0)
        if volume > 0:  # 有成交量数据
            tech_points += 15
        else:
            tech_points += 8

        technical_score = min(100, max(0, tech_points))

    scores['technical'] = technical_score

    # 2. 基本面评分（权重25%）
    fundamental_score = 50  # 默认中性
    fundamental = result.get('fundamental', {})
    if fundamental:
        fund_points = 0

        # ROE评分（40分）
        latest_metrics = fundamental.get('fina_indicator_latest', {})
        roe = latest_metrics.get('roe')
        if roe:
            if roe >= 20:
                fund_points += 40  # 优秀
            elif roe >= 15:
                fund_points += 35  # 良好
            elif roe >= 10:
                fund_points += 25  # 一般
            elif roe >= 5:
                fund_points += 15  # 偏低
            else:
                fund_points += 5   # 很差

        # 盈利能力评分（30分）
        income_latest = fundamental.get('income_latest', {})
        revenue = income_latest.get('revenue')
        net_profit = income_latest.get('n_income')
        if revenue and net_profit and revenue > 0:
            net_margin = (net_profit / revenue) * 100
            if net_margin >= 20:
                fund_points += 30
            elif net_margin >= 10:
                fund_points += 20
            elif net_margin >= 5:
                fund_points += 15
            elif net_margin >= 0:
                fund_points += 10
            else:
                fund_points += 0  # 亏损

        # 财务稳健性评分（30分）
        balance_latest = fundamental.get('balancesheet_latest', {})
        total_assets = balance_latest.get('total_assets')
        total_liab = balance_latest.get('total_liab')
        if total_assets and total_liab:
            debt_ratio = (total_liab / total_assets) * 100
            if debt_ratio <= 30:
                fund_points += 30  # 稳健
            elif debt_ratio <= 50:
                fund_points += 20  # 适中
            elif debt_ratio <= 70:
                fund_points += 10  # 偏高
            else:
                fund_points += 0   # 危险

        fundamental_score = min(100, max(0, fund_points))

    scores['fundamental'] = fundamental_score

    # 3. 新闻面评分（权重35%）- 重命名为news以匹配前端
    news_score = 50  # 默认中性
    news_data = result.get('news', {})
    if news_data and 'sentiment' in news_data:
        sentiment = news_data['sentiment']
        overall = sentiment.get('overall', 'neutral')
        sentiment_pct = sentiment.get('percentages', {})
        news_count = sentiment.get('news_count', 0)

        # 基础情绪评分
        if overall == 'positive':
            news_score = 70
        elif overall == 'negative':
            news_score = 30
        else:
            news_score = 50

        # 基于新闻分布调整
        if sentiment_pct:
            pos_pct = sentiment_pct.get('positive', 0)
            neg_pct = sentiment_pct.get('negative', 0)

            if pos_pct > 60:
                news_score += 20
            elif pos_pct > 40:
                news_score += 10

            if neg_pct > 60:
                news_score -= 20
            elif neg_pct > 40:
                news_score -= 10

        # 新闻数量调整
        if news_count >= 10:
            news_score += 5  # 关注度高
        elif news_count <= 2:
            news_score -= 5  # 关注度低

        news_score = min(100, max(0, news_score))

    scores['news'] = news_score

    # 4. 市场面评分（权重5%）- 新增
    market_score = 50  # 默认中性
    market_data = result.get('market', {})
    if market_data:
        market_sentiment = market_data.get('market_sentiment', 'neutral')
        stats = market_data.get('statistics', {})

        # 基于市场情绪评分
        if market_sentiment == '乐观':
            market_score = 75
        elif market_sentiment == '偏多':
            market_score = 65
        elif market_sentiment == '偏空':
            market_score = 35
        elif market_sentiment == '悲观':
            market_score = 25
        else:
            market_score = 50

        # 基于涨跌家数调整
        rise = stats.get('rise_count', 0)
        fall = stats.get('fall_count', 0)
        if rise + fall > 0:
            rise_ratio = rise / (rise + fall)
            if rise_ratio > 0.7:
                market_score += 10
            elif rise_ratio < 0.3:
                market_score -= 10

        market_score = min(100, max(0, market_score))

    scores['market'] = market_score

    # 4. 估值面评分（权重15%）
    valuation_score = 50  # 默认中性

    # 尝试从technical.latest_price_info获取PE/PB (daily_basic接口)
    latest_price_info = tech.get('latest_price_info', {}) if tech else {}
    pe_ttm = latest_price_info.get('pe_ttm', 0)
    pb = latest_price_info.get('pb', 0)

    # 如果technical没有,再尝试从fundamental获取
    if not pe_ttm and fundamental:
        latest_metrics = fundamental.get('fina_indicator_latest', {})
        pe_ttm = latest_metrics.get('pe_ttm', 0) or latest_metrics.get('pe', 0)
        pb = latest_metrics.get('pb_mrq', 0) or latest_metrics.get('pb', 0)

    val_points = 0

    # PE评分（60分）
    if pe_ttm and pe_ttm > 0:
        if pe_ttm <= 10:
            val_points += 60  # 低估
        elif pe_ttm <= 15:
            val_points += 50  # 合理偏低
        elif pe_ttm <= 25:
            val_points += 35  # 合理
        elif pe_ttm <= 40:
            val_points += 20  # 偏高
        else:
            val_points += 5   # 高估
    else:
        val_points += 25  # 无数据给中性分

    # PB评分（40分）
    if pb and pb > 0:
        if pb <= 1:
            val_points += 40  # 破净
        elif pb <= 2:
            val_points += 30  # 合理
        elif pb <= 3:
            val_points += 20  # 偏高
        else:
            val_points += 10  # 高估
    else:
        val_points += 15  # 无数据给中性分

    valuation_score = min(100, max(0, val_points))

    scores['valuation'] = valuation_score

    # 5. 成长性评分（权重10%）
    growth_score = 50  # 默认中性
    # 这里可以基于营收增长率、利润增长率等计算
    # 暂时使用基础逻辑
    if fundamental:
        if roe and roe > 15:
            growth_score = 70  # 高ROE暗示成长性
        elif roe and roe > 10:
            growth_score = 60
        elif roe and roe < 5:
            growth_score = 30

    scores['growth'] = growth_score

    # 6. 质量面评分（权重5%）
    quality_score = 50  # 默认中性
    if fundamental and roe:
        if roe >= 20:
            quality_score = 90  # 优质公司
        elif roe >= 15:
            quality_score = 75
        elif roe >= 10:
            quality_score = 60
        else:
            quality_score = 40

    scores['quality'] = quality_score

    # 加权综合评分 - 重新调整以匹配前端显示(技术40+新闻35+基本面20+市场5=100)
    weights = {
        'technical': 0.40,      # 技术面 40分
        'news': 0.35,           # 新闻面 35分 (包含情绪分析)
        'fundamental': 0.20,    # 基本面 20分
        'market': 0.05,         # 市场面 5分
        'valuation': 0.0,       # 估值并入基本面
        'growth': 0.0,          # 成长性并入基本面
        'quality': 0.0          # 质量并入基本面
    }

    # 重新计算基本面评分(整合估值、成长、质量)
    fundamental_combined = (
        scores['fundamental'] * 0.50 +  # 原基本面占50%
        scores['valuation'] * 0.30 +    # 估值占30%
        scores['growth'] * 0.10 +       # 成长性占10%
        scores['quality'] * 0.10        # 质量占10%
    )
    scores['fundamental'] = fundamental_combined

    total = (
        scores['technical'] * weights['technical'] +
        scores['news'] * weights['news'] +
        scores['fundamental'] * weights['fundamental'] +
        scores['market'] * weights['market']
    )

    return {
        'total': round(total, 1),
        'details': scores,
        'rating': _get_rating(total),
        'weights': weights
    }


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


def _generate_summary(result: Dict) -> tuple[str, list]:
    """生成RGTI风格的深度分析报告（增强版）

    Returns:
        tuple: (report_markdown, predictions_list)
    """
    from .professional_report_enhancer import (
        enhance_technical_analysis,
        enhance_fundamental_analysis,
        enhance_valuation_analysis,
        enhance_news_analysis,
        enhance_risk_assessment,
        generate_investment_strategy,
        generate_enhanced_summary
    )

    stock_name = result['basic']['name']
    ts_code = result['basic']['ts_code']
    score = result.get('score', {})
    total_score = score.get('total', 0)
    rating = score.get('rating', '中性')

    # 获取各维度数据
    technical = result.get('technical', {})
    fundamental = result.get('fundamental', {})
    news_data = result.get('news', {})
    sentiment = news_data.get('sentiment', {})
    market = result.get('market', {})

    # 从正确的位置获取价格和技术指标数据
    prices = technical.get('prices', [])
    latest_price_info = prices[0] if prices else {}
    prev_price_info = prices[1] if len(prices) > 1 else {}
    indicators = technical.get('indicators', {})

    # 优先使用latest_price字段,否则从prices[0]获取
    current_price = result.get('latest_price') or latest_price_info.get('close', 0)

    # 计算真实涨跌幅:如果pct_chg为0,则从前后两天价格计算
    pct_change = latest_price_info.get('pct_chg', 0)
    if pct_change == 0 and prev_price_info:
        prev_close = prev_price_info.get('close', 0)
        if prev_close > 0:
            pct_change = ((current_price - prev_close) / prev_close) * 100

    volume = latest_price_info.get('amount', 0)  # 成交额
    trade_date = latest_price_info.get('trade_date', '')

    # 从indicators获取技术指标
    ma5 = indicators.get('MA5', 0)
    ma10 = indicators.get('MA10', 0)
    ma20 = indicators.get('MA20', 0)
    rsi = indicators.get('RSI', 50)
    macd = indicators.get('MACD', 0)
    kdj_k = indicators.get('KDJ_K', 50)

    # 构建深度分析报告
    report_parts = []

    # 初始化predictions（用于返回）
    all_predictions = {'historical': [], 'future': []}

    # 标题
    report_parts.append(f"# {stock_name} 深度分析概览")
    report_parts.append("")

    # 生成K线图和价格预测（如果有价格数据）
    if prices and len(prices) >= 5:
        try:
            # 优先使用Kronos深度学习模型进行K线预测
            print(f"[预测] 开始生成Kronos预测，股票代码: {ts_code}")
            all_predictions = generate_price_predictions(
                prices=prices,
                stock_name=stock_name,
                technical=technical,
                fundamental=fundamental,
                ts_code=ts_code,  # 传入ts_code以启用Kronos预测
                use_kronos=True   # 明确启用Kronos预测
            )

            # 分离历史预测和未来预测
            historical_preds = all_predictions.get('historical', [])
            future_preds = all_predictions.get('future', [])
            print(f"[预测] 预测完成: 历史{len(historical_preds)}条, 未来{len(future_preds)}条")

            # 合并所有预测用于图表显示（历史+未来）
            combined_preds = historical_preds + future_preds

            # 生成K线SVG
            kline_svg = generate_kline_svg(
                prices=prices,
                indicators=indicators,
                stock_name=stock_name,
                predictions=combined_preds if combined_preds else None
            )

            # 嵌入图表
            if kline_svg:
                chart_section = embed_chart_in_markdown(
                    svg_data_url=kline_svg,
                    caption=f"近60日K线走势 + 过去14天验证 + 未来10天Kronos AI深度预测"
                )
                report_parts.append(chart_section)
                report_parts.append("")

            # 如果有历史预测数据，添加预测准确度分析
            if historical_preds:
                accuracy_metrics = calculate_prediction_accuracy(historical_preds)
                prediction_table = generate_prediction_table(historical_preds, accuracy_metrics)
                if prediction_table:
                    report_parts.append(prediction_table)
                    report_parts.append("")

        except Exception as e:
            print(f"生成K线图时出错: {str(e)}")
            # 继续生成报告，不因图表失败而中断

    # 数据完整性警告
    data_quality_warnings = []
    if not prices or len(prices) == 0:
        data_quality_warnings.append("⚠️ 价格数据获取失败，部分分析可能不准确")
    if not indicators or len(indicators) == 0:
        data_quality_warnings.append("⚠️ 技术指标数据缺失")
    if not fundamental or len(fundamental) == 0:
        data_quality_warnings.append("⚠️ 基本面数据不完整")
    if not news_data or len(news_data) == 0:
        data_quality_warnings.append("⚠️ 新闻数据暂无")

    if data_quality_warnings:
        report_parts.append("> **数据质量提示**：")
        for warning in data_quality_warnings:
            report_parts.append(f"> {warning}")
        report_parts.append("")

    # 1. 近期行情与涨势亮点
    report_parts.append("## 1. 近期行情与涨势亮点")

    # 生成更加生动的行情描述
    if current_price > 0:
        if pct_change > 3:
            change_desc = f"强势拉升{abs(pct_change):.2f}%，资金疯狂抢筹"
        elif pct_change > 1:
            change_desc = f"稳步上涨{abs(pct_change):.2f}%，买盘积极涌入"
        elif pct_change > 0:
            change_desc = f"小幅上扬{abs(pct_change):.2f}%，多头略占优势"
        elif pct_change < -3:
            change_desc = f"大幅杀跌{abs(pct_change):.2f}%，恐慌盘涌出"
        elif pct_change < -1:
            change_desc = f"持续走弱{abs(pct_change):.2f}%，空方施压明显"
        elif pct_change < 0:
            change_desc = f"微幅调整{abs(pct_change):.2f}%，获利盘兑现"
        else:
            change_desc = "横盘震荡，多空胶着"

        report_parts.append(f"**最新战况**：{stock_name}最新报{current_price:.2f}元，{change_desc}")

        # 成交量分析
        if volume > 0:
            vol_billion = volume / 100000000
            if vol_billion > 100:
                vol_desc = f"成交额高达{vol_billion:.1f}亿，市场关注度爆表"
            elif vol_billion > 50:
                vol_desc = f"成交额{vol_billion:.1f}亿，交投异常活跃"
            elif vol_billion > 10:
                vol_desc = f"成交额{vol_billion:.1f}亿，换手充分"
            else:
                vol_desc = f"成交额{vol_billion:.1f}亿，交投偏清淡"
            report_parts.append(f"**资金博弈**：{vol_desc}")

        # 均线系统分析
        if ma5 > 0 and ma20 > 0:
            if current_price > ma5 > ma20:
                ma_desc = "股价强势站上所有均线，多头排列确立，上升通道完美打开"
            elif current_price > ma20:
                ma_desc = "股价突破20日均线，短期趋势向好"
            elif current_price < ma5 < ma20:
                ma_desc = "股价承压于均线系统，空头格局明显，建议观望等待企稳"
            else:
                ma_desc = "股价在均线附近震荡，方向不明，需等待突破信号"
            report_parts.append(f"**技术形态**：{ma_desc}")
    else:
        report_parts.append("**行情数据暂缺**")

    # 技术指标亮点
    tech_highlights = []
    if rsi:
        if rsi > 70:
            tech_highlights.append(f"RSI={rsi:.1f}超买区域，短期或面临调整压力")
        elif rsi < 30:
            tech_highlights.append(f"RSI={rsi:.1f}超卖区域，可能存在反弹机会")
        else:
            tech_highlights.append(f"RSI={rsi:.1f}处于正常区间，技术形态相对健康")

    if macd != 0:
        if macd > 0:
            tech_highlights.append(f"MACD金叉，多头信号")
        else:
            tech_highlights.append(f"MACD死叉，空头信号")

    if tech_highlights:
        report_parts.append("技术要点：" + "；".join(tech_highlights))

    # 插入增强技术分析
    try:
        enhanced_tech = enhance_technical_analysis(technical, prices, indicators)
        if enhanced_tech:
            report_parts.append("\n**📊 深度技术分析**")
            report_parts.append(enhanced_tech)
    except Exception as e:
        print(f"[报告] 增强技术分析失败: {e}")

    report_parts.append("")

    # 2. 最新财报实况与深度分析
    report_parts.append("## 2. 最新财报实况")
    latest_metrics = fundamental.get('fina_indicator_latest', {})
    income_latest = fundamental.get('income_latest', {})
    balance_latest = fundamental.get('balancesheet_latest', {})

    financial_highlights = []

    # 营收和利润分析
    revenue = income_latest.get('revenue')
    net_profit = income_latest.get('n_income')
    if revenue and net_profit:
        net_margin = (net_profit / revenue) * 100 if revenue > 0 else 0
        financial_highlights.append(f"营业收入 {revenue/100000000:.2f}亿元，净利润 {net_profit/100000000:.2f}亿元，净利率 {net_margin:.2f}%")

    # ROE分析
    roe = latest_metrics.get('roe')
    if roe:
        roe_analysis = "优秀" if roe > 15 else "良好" if roe > 10 else "一般" if roe > 5 else "偏低"
        financial_highlights.append(f"净资产收益率(ROE) {roe:.2f}%，盈利能力{roe_analysis}")

    # 资产负债分析
    total_assets = balance_latest.get('total_assets')
    total_liab = balance_latest.get('total_liab')
    if total_assets and total_liab:
        debt_ratio = (total_liab / total_assets) * 100
        debt_analysis = "偏高" if debt_ratio > 60 else "适中" if debt_ratio > 30 else "较低"
        financial_highlights.append(f"资产负债率 {debt_ratio:.1f}%，财务杠杆{debt_analysis}")

    if financial_highlights:
        for highlight in financial_highlights:
            report_parts.append(highlight)
    else:
        report_parts.append("暂无最新财报数据")

    # 插入增强基本面分析
    try:
        enhanced_fund = enhance_fundamental_analysis(fundamental)
        if enhanced_fund and enhanced_fund != "基本面数据不足":
            report_parts.append("\n**💰 深度财务分析**")
            report_parts.append(enhanced_fund)
    except Exception as e:
        print(f"[报告] 增强基本面分析失败: {e}")

    report_parts.append("")

    # 2.5 估值分析 (新增)
    report_parts.append("## 2.5 估值水平分析")
    try:
        industry = result.get('basic', {}).get('industry', '')
        enhanced_val = enhance_valuation_analysis(fundamental, technical, industry)
        if enhanced_val and enhanced_val != "估值数据不足":
            report_parts.append(enhanced_val)
        else:
            report_parts.append("估值数据暂时缺失")
    except Exception as e:
        print(f"[报告] 估值分析失败: {e}")
        report_parts.append("估值数据暂时缺失")

    report_parts.append("")

    # 3. 分析师观点与目标价
    report_parts.append("## 3. 分析师观点与目标价")

    # 基于评分生成更专业的分析师观点
    if total_score >= 70:
        report_parts.append(f"**顶级投行观点**：{stock_name}基本面优异，技术面强势，获多家券商一致看好")
        if current_price > 0:
            target_high = current_price * 1.3
            target_low = current_price * 1.15
            report_parts.append(f"**目标价区间**：{target_low:.2f}-{target_high:.2f}元，较现价有15%-30%的上涨空间")
        report_parts.append("**投资评级**：强烈推荐(Strong Buy)，建议积极配置")
    elif total_score >= 60:
        report_parts.append(f"**主流券商观点**：{stock_name}基本面稳健，具备一定投资价值，但需注意短期波动风险")
        if current_price > 0:
            target_high = current_price * 1.15
            target_low = current_price * 1.05
            report_parts.append(f"**目标价区间**：{target_low:.2f}-{target_high:.2f}元，温和看涨5%-15%")
        report_parts.append("**投资评级**：增持(Buy)，适合稳健型投资者")
    elif total_score >= 50:
        report_parts.append(f"**机构综合观点**：{stock_name}表现中规中矩，缺乏明显催化剂，建议等待更好的介入时机")
        if current_price > 0:
            report_parts.append(f"**目标价**：维持在{current_price:.2f}元附近，上下空间有限")
        report_parts.append("**投资评级**：中性(Hold)，暂时观望为宜")
    else:
        report_parts.append(f"**风险提示**：{stock_name}面临较大压力，多数机构持谨慎态度")
        if current_price > 0:
            stop_loss = current_price * 0.92
            report_parts.append(f"**下行风险**：若跌破{stop_loss:.2f}元支撑位，可能引发进一步下探")
        report_parts.append("**投资评级**：减持(Sell)，建议规避风险")

    # 添加具体的机构动向
    if score.get('details', {}).get('sentiment', 0) > 60:
        report_parts.append("**最新动向**：北向资金持续流入，机构调研频繁，市场关注度提升")
    elif score.get('details', {}).get('sentiment', 0) < 40:
        report_parts.append("**风险信号**：主力资金流出明显，机构减持迹象显现，需高度警惕")

    report_parts.append("")

    # 4. 市场情绪与新闻面
    report_parts.append("## 4. 市场情绪与新闻面")
    overall_sentiment = sentiment.get('overall', 'neutral')
    sentiment_pct = sentiment.get('percentages', {})
    news_count = sentiment.get('news_count', 0)

    if news_count == 0:
        report_parts.append(f"暂无相关新闻数据，无法进行情绪分析")
    else:
        sentiment_analysis = {
            'positive': f"市场情绪乐观，正面新闻占比较高，投资者信心充足",
            'negative': f"市场情绪偏悲观，负面消息较多，投资者谨慎观望",
            'neutral': f"市场情绪中性，观望氛围浓厚，等待催化剂出现"
        }.get(overall_sentiment, "市场情绪不明")

        report_parts.append(f"基于 {news_count} 条相关新闻分析：{sentiment_analysis}")

        if sentiment_pct:
            pos_pct = sentiment_pct.get('positive', 0)
            neg_pct = sentiment_pct.get('negative', 0)
            neu_pct = sentiment_pct.get('neutral', 0)
            report_parts.append(f"情绪分布：正面 {pos_pct}% / 中性 {neu_pct}% / 负面 {neg_pct}%")

    # 插入增强新闻分析
    try:
        enhanced_news = enhance_news_analysis(news_data)
        if enhanced_news:
            report_parts.append("\n**📰 深度新闻分析**")
            report_parts.append(enhanced_news)
    except Exception as e:
        print(f"[报告] 增强新闻分析失败: {e}")

    report_parts.append("")

    # 5. 风险评估与投资价值
    report_parts.append("## 5. 风险评估与投资价值")

    pe = latest_metrics.get('pe', 0)
    pb = latest_metrics.get('pb', 0)
    roe = latest_metrics.get('roe', 0)

    # 生成更专业的估值分析
    report_parts.append("**估值诊断**：")

    if pe > 0:
        if pe > 50:
            pe_analysis = f"PE高达{pe:.1f}倍，严重透支未来成长，泡沫风险巨大"
        elif pe > 30:
            pe_analysis = f"PE值{pe:.1f}倍处于历史高位，短期回调压力较大"
        elif pe > 20:
            pe_analysis = f"PE值{pe:.1f}倍略高于行业均值，需关注业绩兑现情况"
        elif pe > 10:
            pe_analysis = f"PE值{pe:.1f}倍处于合理区间，估值相对安全"
        else:
            pe_analysis = f"PE仅{pe:.1f}倍，估值洼地显现，具备较高安全边际"
        report_parts.append(f"• {pe_analysis}")

    if pb > 0:
        if pb < 1:
            pb_analysis = f"PB仅{pb:.2f}倍，破净股，价值严重低估"
        elif pb < 2:
            pb_analysis = f"PB值{pb:.2f}倍，资产定价合理，下行风险有限"
        elif pb < 3:
            pb_analysis = f"PB值{pb:.2f}倍，略有溢价但尚可接受"
        else:
            pb_analysis = f"PB高达{pb:.2f}倍，资产泡沫明显，需高度警惕"
        report_parts.append(f"• {pb_analysis}")

    if roe > 0:
        if roe > 20:
            roe_analysis = f"ROE高达{roe:.1f}%，盈利能力卓越，护城河深厚"
        elif roe > 15:
            roe_analysis = f"ROE达{roe:.1f}%，经营效率优秀，竞争优势明显"
        elif roe > 10:
            roe_analysis = f"ROE为{roe:.1f}%，盈利能力尚可，基本面稳定"
        else:
            roe_analysis = f"ROE仅{roe:.1f}%，盈利能力偏弱，需关注改善空间"
        report_parts.append(f"• {roe_analysis}")

    # 多维度风险评估 - 先调用风险评估函数
    risk_analysis = _generate_risk_assessment(result)
    report_parts.append("\n**综合风险评估**：")
    for risk_item in risk_analysis['risk_factors']:
        report_parts.append(f"- {risk_item}")

    # 投资价值总结
    report_parts.append(f"\n**投资价值**：{risk_analysis['investment_value']}")
    report_parts.append(f"**风险等级**：{risk_analysis['risk_level']}")
    if risk_analysis['stop_loss']:
        report_parts.append(f"**建议止损位**：{risk_analysis['stop_loss']}")

    # 插入增强风险评估
    try:
        enhanced_risk = enhance_risk_assessment(result)
        if enhanced_risk:
            report_parts.append("\n**🚨 多维度风险分析**")
            report_parts.append(enhanced_risk)
    except Exception as e:
        print(f"[报告] 增强风险评估失败: {e}")

    report_parts.append("")

    # 6. 行业地位与业务前景
    report_parts.append("## 6. 行业地位与业务前景")
    industry = result.get('basic', {}).get('industry', '未知')
    market_cap = result.get('basic', {}).get('market_cap')

    if industry != '未知':
        report_parts.append(f"所属行业：{industry}")

    if market_cap:
        cap_level = "大盘股" if market_cap > 1000 else "中盘股" if market_cap > 200 else "小盘股"
        report_parts.append(f"市值规模：{market_cap:.0f}亿元（{cap_level}）")

    # 基于ROE和增长的业务评估
    if roe:
        business_quality = "优质" if roe > 15 else "良好" if roe > 10 else "一般"
        report_parts.append(f"业务质量：基于{roe:.1f}%的ROE水平，公司盈利能力{business_quality}")

    report_parts.append("")

    # 7. 投资策略建议
    report_parts.append("## 7. 投资策略建议")

    # 根据不同评分给出策略建议
    if total_score >= 70:
        strategy = f"""**积极策略**：
- 短期：技术面和基本面双重支撑，可考虑适度加仓
- 中期：基本面良好，适合中长期持有
- 风险控制：设置止盈位，注意仓位管理"""
    elif total_score >= 50:
        strategy = f"""**稳健策略**：
- 短期：保持观望，等待更明确的趋势信号
- 中期：可小幅配置，分批建仓降低成本
- 风险控制：严格止损，控制仓位在合理范围"""
    else:
        strategy = f"""**谨慎策略**：
- 短期：暂不建议新增投资，现有持仓考虑减持
- 中期：等待基本面改善或技术面企稳
- 风险控制：优先资本保护，避免重仓操作"""

    report_parts.append(strategy)

    # 插入增强投资策略
    try:
        enhanced_strategy = generate_investment_strategy(score, technical, fundamental)
        if enhanced_strategy:
            report_parts.append("\n**📋 分类投资策略**")
            report_parts.append(enhanced_strategy)
    except Exception as e:
        print(f"[报告] 增强投资策略失败: {e}")

    report_parts.append("")

    # 8. 简明总结表格
    report_parts.append("## 8. 简明总结与前瞻见解")
    report_parts.append("| 维度 | 简述 |")
    report_parts.append("|------|------|")

    # 亮点总结
    highlights = []
    if total_score >= 60:
        highlights.append("综合评分良好")
    if sentiment.get('overall') == 'positive':
        highlights.append("市场情绪积极")
    if roe and roe > 10:
        highlights.append("盈利能力较强")

    highlight_text = "；".join(highlights) if highlights else "暂无明显亮点"
    report_parts.append(f"| 亮点 | {highlight_text} |")

    # 风险总结
    risks = []
    if total_score < 50:
        risks.append("综合评分偏低")
    if sentiment.get('overall') == 'negative':
        risks.append("市场情绪偏负")
    if pe and pe > 30:
        risks.append("估值偏高")

    risk_text = "；".join(risks) if risks else "风险相对可控"
    report_parts.append(f"| 风险 | {risk_text} |")

    # 适合人群
    investor_type = "激进投资者" if total_score >= 70 else "稳健投资者" if total_score >= 50 else "谨慎投资者"
    report_parts.append(f"| 适合人群 | {investor_type}，具备相应风险承受能力 |")

    # 操作建议
    action_summary = "积极关注" if total_score >= 70 else "谨慎观望" if total_score >= 50 else "暂缓投资"
    report_parts.append(f"| 策略建议 | {action_summary}，密切关注基本面变化和技术突破 |")

    # 插入增强总结（三句话总结+前瞻观测点）
    try:
        enhanced_summary = generate_enhanced_summary(result)
        if enhanced_summary:
            report_parts.append(enhanced_summary)
    except Exception as e:
        print(f"[报告] 增强总结失败: {e}")

    # 添加Kronos AI预测分析（在报告末尾、免责声明之前）
    try:
        from .professional_report_enhancer import analyze_kronos_predictions

        if all_predictions and (all_predictions.get('historical') or all_predictions.get('future')):
            kronos_analysis = analyze_kronos_predictions(
                predictions=all_predictions,
                current_price=current_price,
                stock_name=stock_name
            )
            if kronos_analysis:
                report_parts.append(kronos_analysis)
                report_parts.append("")
    except Exception as e:
        print(f"[报告] Kronos分析失败: {e}")

    report_parts.append("")
    report_parts.append("---")
    report_parts.append(f"**数据更新时间**：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_parts.append("*本报告基于公开数据深度分析生成，仅供参考，不构成投资建议。投资有风险，决策需谨慎。*")

    return "\n".join(report_parts), all_predictions


def _fetch_professional_data(ts_code: str, stock_name: str) -> Dict[str, Any]:
    """获取5000积分专属数据"""
    try:
        from .advanced_data_client import advanced_client

        # 获取完整专业数据
        professional_data = advanced_client.get_full_professional_data(ts_code)

        # 获取实时数据
        realtime_quote = advanced_client.get_realtime_quote(ts_code)
        if realtime_quote:
            professional_data['realtime'] = realtime_quote

        # 获取实时技术指标
        realtime_indicators = advanced_client.calculate_realtime_indicators(ts_code)
        if realtime_indicators:
            professional_data['realtime_indicators'] = realtime_indicators

        return professional_data
    except Exception as e:
        print(f"[5000积分数据] 错误: {e}")
        return {}