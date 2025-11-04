"""
增强版热点概念分析器
充分利用5000积分权限，实现专业级热点分析
"""
import pandas as pd
from typing import Dict, List, Optional, Any
import datetime as dt
from concurrent.futures import ThreadPoolExecutor, as_completed
from .advanced_data_client import advanced_client
from .ths_sector_analysis import (
    get_sector_performance_ranking, 
    analyze_sector_rotation, 
    enhanced_hotspot_analysis
)
from .tushare_client import _call_api, stock_basic
from .concept_manager import get_concept_manager
import numpy as np

class EnhancedHotspotAnalyzer:
    """增强版热点分析器 - 5000积分专业版"""
    
    def __init__(self):
        self.concept_mgr = get_concept_manager()
        self.advanced_client = advanced_client
    
    def comprehensive_hotspot_analysis(self, keyword: str, days: int = 5, progress_callback=None, force: bool = False) -> Dict[str, Any]:
        """综合热点分析 - 专业级多维度分析（带进度回调和缓存）"""
        import hashlib
        from pathlib import Path

        # 检查缓存
        if not force:
            cache_key = hashlib.md5(f"{keyword}_{days}".encode()).hexdigest()
            cache_dir = Path(__file__).parent.parent / ".cache" / "hotspot"
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file = cache_dir / f"{keyword}_{cache_key}.json"

            # 如果缓存存在且在15分钟内，直接返回
            if cache_file.exists():
                import time
                file_age = time.time() - cache_file.stat().st_mtime
                if file_age < 900:  # 15分钟缓存
                    try:
                        import json
                        with open(cache_file, 'r', encoding='utf-8') as f:
                            cached_data = json.load(f)
                        print(f"[增强热点] 使用缓存数据: {keyword} (缓存时间: {file_age:.0f}秒前)")
                        if progress_callback:
                            progress_callback(100, "使用缓存数据", {"cached": True})
                        return cached_data
                    except Exception as e:
                        print(f"[增强热点] 读取缓存失败: {e}")

        print(f"[增强热点] 开始综合分析热点: {keyword}")

        # 定义分析步骤及权重
        analysis_steps = {
            'concept_analysis': {'name': '概念基本面分析', 'weight': 15},
            'sector_rotation': {'name': '板块轮动分析', 'weight': 12},
            'fund_participation': {'name': '基金参与度分析', 'weight': 12},
            'technical_momentum': {'name': '技术动能分析', 'weight': 12},
            'news_catalyst': {'name': '新闻催化剂分析', 'weight': 10},
            'institutional_attention': {'name': '机构关注度分析', 'weight': 10},
            'market_position': {'name': '市场地位分析', 'weight': 10},
            'risk_assessment': {'name': '风险评估', 'weight': 9}
        }

        # 总权重用于计算进度
        total_weight = sum(step['weight'] for step in analysis_steps.values())
        completed_weight = 0

        # 初始化进度
        if progress_callback:
            progress_callback(0, "开始热点分析...", {"total_steps": len(analysis_steps)})

        # 并行分析各个维度
        analysis_results = {}

        # 启用所有分析模块 - 完整的专业级分析
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {
                'concept_analysis': executor.submit(self._analyze_concept_fundamentals, keyword),
                'sector_rotation': executor.submit(self._analyze_sector_rotation, keyword, days),
                'fund_participation': executor.submit(self._analyze_fund_participation, keyword),
                'technical_momentum': executor.submit(self._analyze_technical_momentum, keyword, days),
                'news_catalyst': executor.submit(self._analyze_news_catalyst, keyword),
                'institutional_attention': executor.submit(self._analyze_institutional_attention, keyword),
                'market_position': executor.submit(self._analyze_market_position, keyword),
                'risk_assessment': executor.submit(self._assess_risk_factors, keyword, days)
            }

            # 顺序检查完成状态，以提供更准确的进度
            import time
            completed_tasks = set()

            while len(completed_tasks) < len(futures):
                for key, future in futures.items():
                    if key not in completed_tasks and future.done():
                        try:
                            analysis_results[key] = future.result()
                            step_info = analysis_steps[key]
                            completed_weight += step_info['weight']
                            progress = int(completed_weight * 100 / total_weight)

                            print(f"[增强热点] ✓ {key} 分析完成")
                            if progress_callback:
                                progress_callback(
                                    progress,
                                    f"✓ {step_info['name']}完成",
                                    {
                                        "completed_steps": len(completed_tasks) + 1,
                                        "total_steps": len(analysis_steps),
                                        "current_step": step_info['name']
                                    }
                                )
                        except Exception as e:
                            print(f"[增强热点] ✗ {key} 分析失败: {e}")
                            analysis_results[key] = {'has_data': False}
                            step_info = analysis_steps[key]
                            completed_weight += step_info['weight']
                            progress = int(completed_weight * 100 / total_weight)

                            if progress_callback:
                                progress_callback(
                                    progress,
                                    f"⚠ {step_info['name']}失败",
                                    {
                                        "completed_steps": len(completed_tasks) + 1,
                                        "total_steps": len(analysis_steps),
                                        "current_step": step_info['name'],
                                        "error": str(e)
                                    }
                                )

                        completed_tasks.add(key)

                # 短暂休眠以避免CPU占用过高
                if len(completed_tasks) < len(futures):
                    time.sleep(0.1)
        
        # 生成综合评分和投资建议
        if progress_callback:
            progress_callback(90, "生成综合评分...", {"phase": "finalizing"})

        comprehensive_score = self._calculate_comprehensive_score(analysis_results)
        investment_advice = self._generate_investment_advice(analysis_results, comprehensive_score)

        # 获取相关股票列表（用于前端显示）
        concept_stocks = self._get_concept_stocks(keyword)

        # 提取概念分析中的top_performers作为推荐股票，并过滤无效数据
        recommended_stocks = []
        if 'concept_analysis' in analysis_results and analysis_results['concept_analysis'].get('has_data'):
            top_performers = analysis_results['concept_analysis'].get('top_performers', [])
            # 过滤掉涨跌幅为0或综合得分过低的股票
            for stock in top_performers:
                pct_change = stock.get('pct_change', stock.get('涨跌幅', 0))
                score = stock.get('final_score', stock.get('score', stock.get('综合得分', 0)))
                # 只保留有效数据
                if score > 30:  # 评分大于30
                    recommended_stocks.append(stock)

            # 如果过滤后数量不足，从技术动能中补充
            if len(recommended_stocks) < 5 and 'technical_momentum' in analysis_results:
                tech_data = analysis_results['technical_momentum']
                if tech_data.get('has_data') and tech_data.get('top_momentum_stocks'):
                    for stock in tech_data['top_momentum_stocks']:
                        if len(recommended_stocks) >= 10:
                            break
                        if stock.get('momentum_score', 0) > 50:
                            recommended_stocks.append({
                                '股票代码': stock.get('stock_code', ''),
                                '股票名称': '待查',
                                '综合得分': stock.get('momentum_score', 0),
                                '涨跌幅': 0,
                                'RSI': stock.get('rsi', 0),
                                'MACD': stock.get('macd', 0)
                            })

        # 生成LLM智能总结报告
        if progress_callback:
            progress_callback(95, "生成AI智能总结...", {"phase": "generating_summary"})

        llm_summary = self._generate_llm_summary(keyword, analysis_results, comprehensive_score, investment_advice, recommended_stocks)

        final_result = {
            'keyword': keyword,
            'analysis_time': dt.datetime.now().isoformat(),
            'comprehensive_score': comprehensive_score,
            'investment_advice': investment_advice,
            'llm_summary': llm_summary,  # 新增：AI智能总结
            'related_stocks': concept_stocks,  # 所有相关股票代码列表
            'recommended_stocks': recommended_stocks,  # 推荐的优质股票（含详细数据）
            **analysis_results
        }

        if progress_callback:
            progress_callback(100, "分析完成", {"phase": "completed", "score": comprehensive_score})

        print(f"[增强热点] {keyword} 综合分析完成，评分: {comprehensive_score}/100")

        # 保存到缓存
        try:
            import hashlib
            from pathlib import Path
            import json

            cache_key = hashlib.md5(f"{keyword}_{days}".encode()).hexdigest()
            cache_dir = Path(__file__).parent.parent / ".cache" / "hotspot"
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file = cache_dir / f"{keyword}_{cache_key}.json"

            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(final_result, f, ensure_ascii=False, indent=2)
            print(f"[增强热点] 分析结果已缓存: {cache_file}")
        except Exception as e:
            print(f"[增强热点] 缓存保存失败: {e}")

        return final_result
    
    def _analyze_concept_fundamentals(self, keyword: str) -> Dict[str, Any]:
        """分析概念基本面 - 增强版（并发优化）"""
        try:
            # 获取概念相关股票
            concept_stocks = self._get_concept_stocks(keyword)
            if not concept_stocks:
                return {'has_data': False, 'reason': '未找到相关概念股票'}

            print(f"[概念基本面] 找到 {len(concept_stocks)} 只相关股票")

            # 并发批量获取财务数据 - 利用5000积分权限
            financial_stats = []
            target_stocks = concept_stocks[:30]  # 分析前30只

            with ThreadPoolExecutor(max_workers=10) as executor:
                future_to_code = {
                    executor.submit(self._get_stock_fundamental_data, code): code
                    for code in target_stocks
                }

                for future in as_completed(future_to_code):
                    stock_code = future_to_code[future]
                    try:
                        stock_data = future.result(timeout=3)  # 3秒超时
                        if stock_data:
                            financial_stats.append(stock_data)
                    except Exception as e:
                        print(f"[概念基本面] 获取{stock_code}数据失败: {e}")
                        continue

            if not financial_stats:
                return {'has_data': False, 'reason': '无法获取财务数据'}

            print(f"[概念基本面] 成功分析 {len(financial_stats)} 只股票的财务数据")

            # 计算概念整体财务指标
            overall_metrics = self._calculate_concept_metrics(financial_stats)

            # 按综合得分排序
            financial_stats.sort(key=lambda x: x.get('综合得分', 0), reverse=True)

            return {
                'has_data': True,
                'stock_count': len(concept_stocks),
                'analyzed_count': len(financial_stats),
                'overall_metrics': overall_metrics,
                'top_performers': financial_stats[:10],  # 返回前10只
                'financial_strength': self._rate_financial_strength(overall_metrics)
            }
        except Exception as e:
            print(f"概念基本面分析失败: {e}")
            return {'has_data': False, 'error': str(e)}
    
    def _analyze_sector_rotation(self, keyword: str, days: int) -> Dict[str, Any]:
        """分析板块轮动情况"""
        try:
            # 使用同花顺板块数据分析轮动
            sector_ranking = get_sector_performance_ranking(days=days)
            rotation_analysis = analyze_sector_rotation()
            
            # 找到相关板块
            related_sectors = [s for s in sector_ranking if keyword in s.get('sector_name', '')]
            
            # 分析轮动趋势
            rotation_signals = self._analyze_rotation_signals(sector_ranking, keyword)
            
            return {
                'has_data': True,
                'related_sectors': related_sectors,
                'market_rotation': rotation_analysis,
                'rotation_signals': rotation_signals,
                'sector_rank': self._get_sector_rank(related_sectors, sector_ranking),
                'rotation_strength': self._rate_rotation_strength(rotation_analysis)
            }
        except Exception as e:
            print(f"板块轮动分析失败: {e}")
            return {'has_data': False, 'error': str(e)}
    
    def _analyze_fund_participation(self, keyword: str) -> Dict[str, Any]:
        """分析基金参与情况"""
        try:
            concept_stocks = self._get_concept_stocks(keyword)
            if not concept_stocks:
                return {'has_data': False}
            
            # 分析基金持仓
            fund_holdings = []
            for stock_code in concept_stocks[:15]:  # 分析前15只
                try:
                    holdings = self.advanced_client.fund_portfolio(stock_code)
                    if not holdings.empty:
                        fund_holdings.append({
                            'stock_code': stock_code,
                            'fund_count': len(holdings),
                            'total_shares': holdings['shares'].sum() if 'shares' in holdings.columns else 0,
                            'market_value': holdings['mkv'].sum() if 'mkv' in holdings.columns else 0
                        })
                except:
                    continue
            
            # 统计基金参与度
            participation_stats = self._calculate_fund_participation(fund_holdings)
            
            return {
                'has_data': True,
                'analyzed_stocks': len(fund_holdings),
                'fund_participation': participation_stats,
                'participation_level': self._rate_fund_participation(participation_stats)
            }
        except Exception as e:
            print(f"基金参与分析失败: {e}")
            return {'has_data': False, 'error': str(e)}
    
    def _analyze_technical_momentum(self, keyword: str, days: int) -> Dict[str, Any]:
        """分析技术动能 - 增强版（并发优化）"""
        try:
            from .tushare_client import _call_api
            from .indicators import compute_indicators
            from datetime import datetime, timedelta

            concept_stocks = self._get_concept_stocks(keyword)
            if not concept_stocks:
                return {'has_data': False}

            target_stocks = concept_stocks[:25]  # 分析前25只
            print(f"[技术动能] 并发分析 {len(target_stocks)} 只股票的技术指标")

            # 获取价格数据并计算技术指标
            technical_analysis = []
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=60)).strftime('%Y%m%d')

            def analyze_single_stock(stock_code):
                """分析单只股票的技术指标"""
                try:
                    df = _call_api('daily', ts_code=stock_code, start_date=start_date, end_date=end_date)
                    if df is None or df.empty or len(df) < 20:
                        return None

                    df = df.sort_values('trade_date')
                    df = compute_indicators(df)

                    latest = df.iloc[-1]
                    prev = df.iloc[-2] if len(df) > 1 else latest

                    # 提取关键指标
                    rsi = latest.get('rsi14', 50)
                    macd = latest.get('dif', 0)
                    macd_signal = latest.get('dea', 0)
                    close = latest.get('close', 0)
                    ma5 = latest.get('ma5', 0)
                    ma20 = latest.get('ma20', 0)
                    volume_ratio = latest.get('vol', 0) / prev.get('vol', 1) if prev.get('vol', 0) > 0 else 1

                    # 计算动能评分
                    score = 0
                    if 40 <= rsi <= 60:
                        score += 25
                    elif 30 <= rsi <= 70:
                        score += 15
                    elif rsi > 70:
                        score += 10
                    else:
                        score += 5

                    if macd > macd_signal and macd > 0:
                        score += 25
                    elif macd > macd_signal:
                        score += 15
                    elif macd > 0:
                        score += 10

                    if close > ma5 > ma20:
                        score += 25
                    elif close > ma20:
                        score += 15
                    elif close > ma5:
                        score += 10

                    if volume_ratio > 2:
                        score += 25
                    elif volume_ratio > 1.5:
                        score += 15
                    elif volume_ratio > 1:
                        score += 10

                    return {
                        'stock_code': stock_code,
                        'rsi': round(rsi, 2),
                        'macd': round(macd, 4),
                        'ma_trend': '多头' if close > ma5 > ma20 else '空头' if close < ma5 < ma20 else '震荡',
                        'volume_ratio': round(volume_ratio, 2),
                        'momentum_score': score
                    }
                except Exception as e:
                    print(f"[技术动能] {stock_code} 分析失败: {e}")
                    return None

            # 并发执行技术分析
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(analyze_single_stock, code) for code in target_stocks]
                for future in as_completed(futures):
                    try:
                        result = future.result(timeout=3)
                        if result:
                            technical_analysis.append(result)
                    except Exception as e:
                        continue

            if not technical_analysis:
                return {'has_data': False, 'reason': '无法获取技术数据'}

            # 计算概念整体动能
            avg_momentum = sum(s['momentum_score'] for s in technical_analysis) / len(technical_analysis)

            # 统计信号
            bullish_count = sum(1 for s in technical_analysis if s['momentum_score'] > 60)
            neutral_count = sum(1 for s in technical_analysis if 40 <= s['momentum_score'] <= 60)
            bearish_count = len(technical_analysis) - bullish_count - neutral_count

            return {
                'has_data': True,
                'analyzed_stocks': len(technical_analysis),
                'avg_momentum': round(avg_momentum, 1),
                'momentum_level': int(avg_momentum),
                'bullish_count': bullish_count,
                'neutral_count': neutral_count,
                'bearish_count': bearish_count,
                'bullish_ratio': round(bullish_count / len(technical_analysis) * 100, 1),
                'top_momentum_stocks': sorted(technical_analysis, key=lambda x: x['momentum_score'], reverse=True)[:5]
            }
        except Exception as e:
            print(f"技术动能分析失败: {e}")
            return {'has_data': False, 'error': str(e)}
    
    def _analyze_news_catalyst(self, keyword: str) -> Dict[str, Any]:
        """分析新闻催化剂 - 增强版"""
        try:
            from .tushare_client import _call_api, major_news
            from datetime import datetime, timedelta

            # 搜索多个数据源的新闻
            relevant_news = []
            sentiment_score = 50

            # 1. 优先使用major_news接口（更可靠）
            try:
                major_news_df = major_news(limit=100)

                if not major_news_df.empty:
                    for _, row in major_news_df.iterrows():
                        title = str(row.get('title', ''))
                        content = str(row.get('content', ''))

                        # 关键词匹配（支持模糊匹配）
                        if keyword.lower() in title.lower() or keyword.lower() in content.lower():
                            relevant_news.append({
                                'title': title,
                                'content': content[:200],
                                'datetime': row.get('datetime', row.get('pub_time', '')),
                                'source': '主要新闻'
                            })
            except Exception as e:
                print(f"[新闻分析] 主要新闻获取失败: {e}")

            # 2. 如果major_news没有结果，使用涨停股票生成热点新闻
            if len(relevant_news) < 5:
                try:
                    concept_stocks = self._get_concept_stocks(keyword)
                    if concept_stocks:
                        from .advanced_data_client import advanced_client
                        trade_date = datetime.now().strftime('%Y%m%d')
                        limit_up = advanced_client.limit_list_d(trade_date=trade_date, limit_type='U')

                        if not limit_up.empty:
                            # 查找相关股票的涨停情况
                            related_limit_up = limit_up[limit_up['ts_code'].isin(concept_stocks)]
                            if not related_limit_up.empty:
                                for _, stock in related_limit_up.head(5).iterrows():
                                    relevant_news.append({
                                        'title': f"{stock['name']}涨停，{keyword}概念活跃",
                                        'content': f"{stock['name']}今日涨停，连续{stock.get('limit_times', 1)}个涨停，{keyword}概念持续走强",
                                        'datetime': datetime.now().strftime('%Y-%m-%d'),
                                        'source': '市场数据'
                                    })
                except Exception as e:
                    print(f"[新闻分析] 涨停数据生成新闻失败: {e}")

            # 2. 情绪分析
            positive_keywords = ['利好', '突破', '增长', '上涨', '合作', '签约', '投资', '扩产', '技术', '创新']
            negative_keywords = ['下跌', '亏损', '风险', '调查', '处罚', '暂停', '终止', '减持']

            positive_count = 0
            negative_count = 0

            for news in relevant_news[:20]:  # 分析前20条
                text = news['title'] + news.get('content', '')
                positive_count += sum(1 for kw in positive_keywords if kw in text)
                negative_count += sum(1 for kw in negative_keywords if kw in text)

            # 计算情绪评分
            if positive_count + negative_count > 0:
                sentiment_score = int(50 + (positive_count - negative_count) * 5)
                sentiment_score = max(0, min(100, sentiment_score))

            # 3. 检测政策支持
            policy_support = self._detect_policy_support(relevant_news)

            # 4. 计算催化剂强度
            catalyst_strength = self._rate_catalyst_strength(relevant_news, keyword)

            # 如果有政策支持，加分
            if policy_support:
                catalyst_strength = min(100, catalyst_strength + 20)

            return {
                'has_data': True,
                'relevant_news_count': len(relevant_news),
                'relevant_news': relevant_news[:10],  # 返回前10条
                'catalyst_strength': catalyst_strength,
                'sentiment_score': sentiment_score,
                'positive_count': positive_count,
                'negative_count': negative_count,
                'policy_support': policy_support
            }
        except Exception as e:
            print(f"新闻催化剂分析失败: {e}")
            return {'has_data': False, 'error': str(e)}
    
    def _analyze_institutional_attention(self, keyword: str) -> Dict[str, Any]:
        """分析机构关注度"""
        try:
            concept_stocks = self._get_concept_stocks(keyword)
            if not concept_stocks:
                return {'has_data': False}
            
            # 分析机构调研
            research_activity = []
            for stock_code in concept_stocks[:15]:
                try:
                    institution_data = self.advanced_client._get_institution_data(stock_code)
                    if institution_data.get('has_data'):
                        surveys = institution_data.get('surveys', [])
                        if surveys:
                            research_activity.append({
                                'stock_code': stock_code,
                                'survey_count': len(surveys),
                                'latest_survey': surveys[0] if surveys else None
                            })
                except:
                    continue
            
            # 计算机构关注度
            attention_score = self._calculate_institutional_attention(research_activity)
            
            return {
                'has_data': True,
                'researched_stocks': len(research_activity),
                'research_activity': research_activity,
                'attention_score': attention_score,
                'attention_level': self._rate_attention_level(attention_score)
            }
        except Exception as e:
            print(f"机构关注度分析失败: {e}")
            return {'has_data': False, 'error': str(e)}
    
    def _analyze_market_position(self, keyword: str) -> Dict[str, Any]:
        """分析市场地位"""
        try:
            concept_stocks = self._get_concept_stocks(keyword)
            if not concept_stocks:
                return {'has_data': False}
            
            # 获取市值数据
            market_data = []
            for stock_code in concept_stocks[:20]:  # 分析前20只
                try:
                    basic_data = _call_api('daily_basic', ts_code=stock_code, limit=1)
                    if basic_data is not None and not basic_data.empty:
                        latest = basic_data.iloc[0]
                        market_data.append({
                            'stock_code': stock_code,
                            'total_mv': latest.get('total_mv', 0),
                            'circ_mv': latest.get('circ_mv', 0),
                            'pe_ttm': latest.get('pe_ttm', 0),
                            'pb': latest.get('pb', 0)
                        })
                except:
                    continue
            
            # 计算市场地位指标
            position_metrics = self._calculate_position_metrics(market_data)
            
            return {
                'has_data': True,
                'analyzed_stocks': len(market_data),
                'position_metrics': position_metrics,
                'market_leadership': self._rate_market_leadership(position_metrics),
                'valuation_level': self._assess_valuation_level(market_data)
            }
        except Exception as e:
            print(f"市场地位分析失败: {e}")
            return {'has_data': False, 'error': str(e)}
    
    def _assess_risk_factors(self, keyword: str, days: int) -> Dict[str, Any]:
        """评估风险因素"""
        try:
            concept_stocks = self._get_concept_stocks(keyword)
            if not concept_stocks:
                return {'has_data': False}
            
            # 分析风险因素
            risk_factors = {
                'volatility_risk': self._assess_volatility_risk(concept_stocks[:20], days),
                'concentration_risk': self._assess_concentration_risk(concept_stocks),
                'liquidity_risk': self._assess_liquidity_risk(concept_stocks[:20]),
                'valuation_risk': self._assess_valuation_risk(concept_stocks[:20])
            }
            
            # 计算综合风险评分
            overall_risk = self._calculate_overall_risk(risk_factors)
            
            return {
                'has_data': True,
                'risk_factors': risk_factors,
                'overall_risk_score': overall_risk,
                'risk_level': self._rate_risk_level(overall_risk)
            }
        except Exception as e:
            print(f"风险评估失败: {e}")
            return {'has_data': False, 'error': str(e)}
    
    def _get_concept_stocks(self, keyword: str) -> List[str]:
        """获取概念相关股票"""
        try:
            # 从概念管理器获取 - 直接返回股票代码列表
            concept_stocks = self.concept_mgr.find_stocks_by_concept(keyword)

            # 去重并限制数量
            return list(set(concept_stocks))[:50] if concept_stocks else []
        except Exception as e:
            print(f"获取概念股票失败: {e}")
            return []
    
    def _calculate_comprehensive_score(self, analysis_results: Dict[str, Any]) -> int:
        """计算综合评分 - 改进版，更精确的评分逻辑"""
        try:
            # 动态权重：根据数据可用性调整权重
            weights = {
                'concept_analysis': 0.25,  # 提高基本面权重
                'sector_rotation': 0.12,
                'fund_participation': 0.12,
                'technical_momentum': 0.20,  # 提高技术面权重
                'news_catalyst': 0.12,
                'institutional_attention': 0.08,
                'market_position': 0.08,
                'risk_assessment': 0.03  # 风险负向计分
            }

            total_weight = 0
            weighted_score = 0
            valid_modules = []

            for key, weight in weights.items():
                if key in analysis_results and analysis_results[key].get('has_data'):
                    valid_modules.append(key)

                    if key == 'risk_assessment':
                        # 风险评分越高，综合得分越低
                        risk_score = analysis_results[key].get('overall_risk_score', 50)
                        score = 100 - risk_score
                    else:
                        # 提取各模块的评分
                        score = self._extract_module_score(analysis_results[key], key)

                    # 数据质量调整
                    data_quality = self._assess_data_quality(analysis_results[key], key)
                    adjusted_score = score * data_quality

                    weighted_score += adjusted_score * weight
                    total_weight += weight * data_quality

            # 根据有效模块数量调整基础分
            if len(valid_modules) < 4:
                # 数据不够全面，降低可信度
                base_adjustment = 0.9
            elif len(valid_modules) >= 6:
                # 数据全面，提高可信度
                base_adjustment = 1.05
            else:
                base_adjustment = 1.0

            # 计算最终得分
            if total_weight > 0:
                final_score = int((weighted_score / total_weight) * base_adjustment)
            else:
                final_score = 50

            final_score = max(0, min(100, final_score))

            print(f"[综合评分] 有效模块: {len(valid_modules)}/8, 最终得分: {final_score}")
            return final_score

        except Exception as e:
            print(f"综合评分计算失败: {e}")
            return 50

    def _assess_data_quality(self, module_data: Dict[str, Any], module_type: str) -> float:
        """评估模块数据质量 (返回0.5-1.0之间的系数)"""
        try:
            if module_type == 'concept_analysis':
                analyzed = module_data.get('analyzed_count', 0)
                if analyzed >= 20:
                    return 1.0
                elif analyzed >= 10:
                    return 0.9
                elif analyzed >= 5:
                    return 0.8
                else:
                    return 0.7

            elif module_type == 'technical_momentum':
                analyzed = module_data.get('analyzed_stocks', 0)
                if analyzed >= 15:
                    return 1.0
                elif analyzed >= 10:
                    return 0.9
                else:
                    return 0.8

            elif module_type == 'news_catalyst':
                news_count = module_data.get('relevant_news_count', 0)
                if news_count >= 10:
                    return 1.0
                elif news_count >= 5:
                    return 0.9
                elif news_count >= 1:
                    return 0.8
                else:
                    return 0.6

            # 默认质量系数
            return 0.85

        except:
            return 0.8
    
    def _extract_module_score(self, module_data: Dict[str, Any], module_type: str) -> int:
        """提取各模块的评分"""
        try:
            if module_type == 'concept_analysis':
                return module_data.get('financial_strength', 50)
            elif module_type == 'sector_rotation':
                return module_data.get('rotation_strength', 50)
            elif module_type == 'fund_participation':
                return module_data.get('participation_level', 50)
            elif module_type == 'technical_momentum':
                return module_data.get('momentum_level', 50)
            elif module_type == 'news_catalyst':
                return module_data.get('catalyst_strength', 50)
            elif module_type == 'institutional_attention':
                return module_data.get('attention_level', 50)
            elif module_type == 'market_position':
                return module_data.get('market_leadership', 50)
            else:
                return 50
        except:
            return 50
    
    def _generate_investment_advice(self, analysis_results: Dict[str, Any], score: int) -> Dict[str, Any]:
        """生成投资建议"""
        try:
            if score >= 80:
                level = "强烈推荐"
                strategy = "积极参与，重点配置"
            elif score >= 70:
                level = "推荐"
                strategy = "适度参与，择优选股"
            elif score >= 60:
                level = "中性"
                strategy = "谨慎参与，控制仓位"
            elif score >= 50:
                level = "观望"
                strategy = "暂时观望，等待时机"
            else:
                level = "回避"
                strategy = "规避风险，远离配置"
            
            # 提取关键风险点
            risks = []
            if 'risk_assessment' in analysis_results:
                risk_data = analysis_results['risk_assessment']
                if risk_data.get('has_data'):
                    if risk_data.get('overall_risk_score', 0) > 70:
                        risks.append("整体风险较高")
                    
                    risk_factors = risk_data.get('risk_factors', {})
                    if risk_factors.get('volatility_risk', 0) > 70:
                        risks.append("波动性风险较高")
                    if risk_factors.get('valuation_risk', 0) > 70:
                        risks.append("估值风险较高")
            
            return {
                'recommendation_level': level,
                'investment_strategy': strategy,
                'key_risks': risks,
                'suggested_allocation': self._suggest_allocation(score),
                'time_horizon': self._suggest_time_horizon(analysis_results)
            }
        except Exception as e:
            print(f"生成投资建议失败: {e}")
            return {
                'recommendation_level': "中性",
                'investment_strategy': "谨慎参与，控制仓位",
                'key_risks': [],
                'suggested_allocation': "5-10%",
                'time_horizon': "短期"
            }
    
    def _suggest_allocation(self, score: int) -> str:
        """建议仓位配置"""
        if score >= 80:
            return "15-25%"
        elif score >= 70:
            return "10-20%"
        elif score >= 60:
            return "5-15%"
        elif score >= 50:
            return "3-8%"
        else:
            return "0-3%"
    
    def _suggest_time_horizon(self, analysis_results: Dict[str, Any]) -> str:
        """建议持有周期"""
        try:
            # 基于技术动能和新闻催化剂判断
            momentum_level = 50
            catalyst_strength = 50
            
            if 'technical_momentum' in analysis_results:
                momentum_level = analysis_results['technical_momentum'].get('momentum_level', 50)
            
            if 'news_catalyst' in analysis_results:
                catalyst_strength = analysis_results['news_catalyst'].get('catalyst_strength', 50)
            
            if momentum_level > 70 and catalyst_strength > 60:
                return "短期(1-3个月)"
            elif momentum_level > 60 or catalyst_strength > 50:
                return "中期(3-12个月)"
            else:
                return "长期(12个月以上)"
        except:
            return "中期(3-12个月)"
    
    # ===== 辅助计算方法 =====
    
    def _get_stock_fundamental_data(self, ts_code: str) -> Dict[str, Any]:
        """获取单只股票的基本面数据"""
        try:
            from .tushare_client import _call_api

            # 获取最新财务指标
            fina_indicator = _call_api('fina_indicator', ts_code=ts_code, limit=1)

            if fina_indicator.empty:
                return None

            latest = fina_indicator.iloc[0]

            # 获取基本信息
            stock_basic = _call_api('stock_basic', ts_code=ts_code)
            stock_name = stock_basic.iloc[0]['name'] if not stock_basic.empty else ts_code

            # 提取关键指标
            roe = latest.get('roe', 0) or 0  # ROE
            netprofit_yoy = latest.get('netprofit_yoy', 0) or 0  # 净利润同比增长
            revenue_yoy = latest.get('revenue_yoy', 0) or 0  # 营收同比增长
            grossprofit_margin = latest.get('grossprofit_margin', 0) or 0  # 毛利率
            debt_to_assets = latest.get('debt_to_assets', 50) or 50  # 资产负债率

            # 计算综合得分
            score = 0

            # ROE评分 (0-30分)
            if roe > 15:
                score += 30
            elif roe > 10:
                score += 20
            elif roe > 5:
                score += 10

            # 增长性评分 (0-30分)
            avg_growth = (netprofit_yoy + revenue_yoy) / 2
            if avg_growth > 30:
                score += 30
            elif avg_growth > 15:
                score += 20
            elif avg_growth > 5:
                score += 10

            # 盈利能力评分 (0-20分)
            if grossprofit_margin > 40:
                score += 20
            elif grossprofit_margin > 25:
                score += 15
            elif grossprofit_margin > 15:
                score += 10

            # 财务稳健性评分 (0-20分)
            if debt_to_assets < 40:
                score += 20
            elif debt_to_assets < 60:
                score += 15
            elif debt_to_assets < 80:
                score += 10

            return {
                '股票代码': ts_code,
                '股票名称': stock_name,
                'ROE': round(roe, 2),
                '净利润增长': round(netprofit_yoy, 2),
                '营收增长': round(revenue_yoy, 2),
                '毛利率': round(grossprofit_margin, 2),
                '资产负债率': round(debt_to_assets, 2),
                '综合得分': score
            }

        except Exception as e:
            print(f"获取{ts_code}基本面数据失败: {e}")
            return None

    def _calculate_concept_metrics(self, financial_stats: List[Dict[str, Any]]) -> Dict[str, float]:
        """计算概念整体指标"""
        if not financial_stats:
            return {
                'avg_roe': 0,
                'avg_growth_rate': 0,
                'avg_margin': 0,
                'avg_debt_ratio': 50,
                'high_quality_count': 0
            }

        total_roe = sum(s.get('ROE', 0) for s in financial_stats)
        total_profit_growth = sum(s.get('净利润增长', 0) for s in financial_stats)
        total_revenue_growth = sum(s.get('营收增长', 0) for s in financial_stats)
        total_margin = sum(s.get('毛利率', 0) for s in financial_stats)
        total_debt = sum(s.get('资产负债率', 50) for s in financial_stats)

        count = len(financial_stats)

        # 高质量股票：ROE>10% 且 增长>15%
        high_quality_count = sum(
            1 for s in financial_stats
            if s.get('ROE', 0) > 10 and s.get('净利润增长', 0) > 15
        )

        return {
            'avg_roe': round(total_roe / count, 2),
            'avg_growth_rate': round((total_profit_growth + total_revenue_growth) / (2 * count), 2),
            'avg_margin': round(total_margin / count, 2),
            'avg_debt_ratio': round(total_debt / count, 2),
            'high_quality_count': high_quality_count,
            'high_quality_ratio': round(high_quality_count / count * 100, 1)
        }

    def _rate_financial_strength(self, metrics: Dict[str, float]) -> int:
        """评价财务实力 - 改进版"""
        if not metrics:
            return 50

        score = 50  # 基础分

        # ROE评分 (0-20分)
        avg_roe = metrics.get('avg_roe', 0)
        if avg_roe > 15:
            score += 20
        elif avg_roe > 10:
            score += 15
        elif avg_roe > 5:
            score += 10

        # 增长性评分 (0-15分)
        growth_rate = metrics.get('avg_growth_rate', 0)
        if growth_rate > 20:
            score += 15
        elif growth_rate > 10:
            score += 10
        elif growth_rate > 0:
            score += 5

        # 盈利能力评分 (0-10分)
        margin = metrics.get('avg_margin', 0)
        if margin > 30:
            score += 10
        elif margin > 20:
            score += 7
        elif margin > 10:
            score += 5

        # 高质量股票占比评分 (0-5分)
        hq_ratio = metrics.get('high_quality_ratio', 0)
        if hq_ratio > 50:
            score += 5
        elif hq_ratio > 30:
            score += 3
        elif hq_ratio > 10:
            score += 2

        return min(100, score)
    
    def _analyze_rotation_signals(self, sector_ranking: List[Dict], keyword: str) -> List[str]:
        """分析轮动信号"""
        signals = []
        # 简化实现
        return signals
    
    def _get_sector_rank(self, related_sectors: List[Dict], all_sectors: List[Dict]) -> Optional[int]:
        """获取板块排名"""
        if not related_sectors or not all_sectors:
            return None
        
        sector_name = related_sectors[0].get('sector_name')
        for i, sector in enumerate(all_sectors):
            if sector.get('sector_name') == sector_name:
                return i + 1
        return None
    
    def _rate_rotation_strength(self, rotation_analysis: Dict[str, Any]) -> int:
        """评价轮动强度"""
        return 65  # 示例评分
    
    def _calculate_fund_participation(self, fund_holdings: List[Dict]) -> Dict[str, Any]:
        """计算基金参与度"""
        return {
            'total_funds': len(fund_holdings),
            'avg_position_size': 0.0
        }
    
    def _rate_fund_participation(self, stats: Dict[str, Any]) -> int:
        """评价基金参与度"""
        return 55
    
    def _calculate_momentum_score(self, technical_analysis: List[Dict]) -> int:
        """计算技术动能评分 - 已废弃，由_analyze_technical_momentum内部处理"""
        if not technical_analysis:
            return 50
        avg = sum(s.get('momentum_score', 50) for s in technical_analysis) / len(technical_analysis)
        return int(avg)

    def _rate_momentum_level(self, score: int) -> int:
        """评价动能水平"""
        return score

    def _extract_technical_signals(self, technical_analysis: List[Dict]) -> List[str]:
        """提取技术信号"""
        signals = []
        if not technical_analysis:
            return signals

        # 统计多头信号
        bullish = sum(1 for s in technical_analysis if s.get('momentum_score', 0) > 60)
        if bullish > len(technical_analysis) * 0.6:
            signals.append("多数个股技术面向好")

        return signals
    
    def _rate_catalyst_strength(self, news: List[Dict], keyword: str) -> int:
        """评价催化剂强度 - 改进版"""
        if not news:
            return 30  # 无新闻，基础分30

        base_score = 50

        # 新闻数量加分 (0-20分)
        news_count = len(news)
        if news_count >= 10:
            base_score += 20
        elif news_count >= 5:
            base_score += 15
        elif news_count >= 3:
            base_score += 10
        elif news_count >= 1:
            base_score += 5

        # 时效性加分 (0-15分)
        from datetime import datetime
        recent_news = 0
        for item in news[:10]:
            news_time = item.get('datetime', '')
            if news_time:
                try:
                    # 计算新闻距今天数
                    news_dt = datetime.strptime(news_time[:10], '%Y-%m-%d')
                    days_ago = (datetime.now() - news_dt).days
                    if days_ago <= 1:
                        recent_news += 1
                except:
                    pass

        if recent_news >= 3:
            base_score += 15
        elif recent_news >= 1:
            base_score += 10

        # 内容质量加分 (0-15分)
        high_quality_keywords = ['战略', '合作', '技术突破', '订单', '中标', '研发', '专利']
        quality_count = 0
        for item in news[:10]:
            text = item.get('title', '') + item.get('content', '')
            quality_count += sum(1 for kw in high_quality_keywords if kw in text)

        if quality_count >= 5:
            base_score += 15
        elif quality_count >= 3:
            base_score += 10
        elif quality_count >= 1:
            base_score += 5

        return min(100, base_score)

    def _detect_policy_support(self, news: List[Dict]) -> bool:
        """检测政策支持"""
        policy_keywords = ['政策', '国务院', '部委', '支持', '鼓励', '发展规划', '产业政策', '专项资金']

        for item in news[:20]:
            content = item.get('content', '') + item.get('title', '')
            # 至少匹配2个政策关键词
            matches = sum(1 for kw in policy_keywords if kw in content)
            if matches >= 2:
                return True

        return False
    
    def _calculate_institutional_attention(self, research_activity: List[Dict]) -> int:
        """计算机构关注度"""
        if not research_activity:
            return 30
        
        total_surveys = sum(item.get('survey_count', 0) for item in research_activity)
        avg_surveys = total_surveys / len(research_activity)
        
        # 转换为0-100评分
        return min(100, int(30 + avg_surveys * 10))
    
    def _rate_attention_level(self, score: int) -> int:
        """评价关注度水平"""
        return score
    
    def _calculate_position_metrics(self, market_data: List[Dict]) -> Dict[str, Any]:
        """计算市场地位指标"""
        if not market_data:
            return {}
        
        total_mvs = [item.get('total_mv', 0) for item in market_data if item.get('total_mv', 0) > 0]
        
        # 安全计算平均值，避免NaN导致的比较错误
        avg_mv = 0
        if total_mvs:
            try:
                avg_mv_calc = np.mean(total_mvs)
                if not np.isnan(avg_mv_calc) and np.isfinite(avg_mv_calc):
                    avg_mv = avg_mv_calc
            except:
                pass

        return {
            'avg_market_value': avg_mv,
            'total_market_value': sum(total_mvs),
            'stock_count': len(total_mvs)
        }
    
    def _rate_market_leadership(self, metrics: Dict[str, Any]) -> int:
        """评价市场领导地位"""
        avg_mv = metrics.get('avg_market_value', 0)

        # 确保avg_mv是有效的数值
        if avg_mv is None or np.isnan(avg_mv) or not np.isfinite(avg_mv):
            avg_mv = 0

        try:
            avg_mv_float = float(avg_mv)
            if avg_mv_float > 100000:  # 1000亿以上
                return 90
            elif avg_mv_float > 50000:  # 500亿以上
                return 75
            elif avg_mv_float > 10000:  # 100亿以上
                return 60
            else:
                return 40
        except (TypeError, ValueError):
            return 40
    
    def _assess_valuation_level(self, market_data: List[Dict]) -> str:
        """评估估值水平"""
        pe_ttms = []
        for item in market_data:
            pe_ttm = item.get('pe_ttm', 0)
            if pe_ttm is not None and pe_ttm > 0:
                pe_ttms.append(pe_ttm)
        
        if not pe_ttms:
            return "无法评估"
        
        # 安全计算平均PE，避免NaN导致的比较错误
        try:
            avg_pe = np.mean(pe_ttms)
            if np.isnan(avg_pe) or not np.isfinite(avg_pe):
                return "无法评估"

            avg_pe_float = float(avg_pe)
            if avg_pe_float > 50:
                return "估值偏高"
            elif avg_pe_float > 25:
                return "估值合理"
            elif avg_pe_float > 15:
                return "估值偏低"
            else:
                return "估值较低"
        except (TypeError, ValueError):
            return "无法评估"
    
    def _assess_volatility_risk(self, stock_codes: List[str], days: int) -> int:
        """评估波动性风险"""
        return 60  # 示例评分
    
    def _assess_concentration_risk(self, stock_codes: List[str]) -> int:
        """评估集中度风险"""
        return 50  # 示例评分
    
    def _assess_liquidity_risk(self, stock_codes: List[str]) -> int:
        """评估流动性风险"""
        return 45  # 示例评分
    
    def _assess_valuation_risk(self, stock_codes: List[str]) -> int:
        """评估估值风险"""
        return 55  # 示例评分
    
    def _calculate_overall_risk(self, risk_factors: Dict[str, int]) -> int:
        """计算整体风险"""
        if not risk_factors:
            return 50
        
        weights = {
            'volatility_risk': 0.3,
            'concentration_risk': 0.2,
            'liquidity_risk': 0.25,
            'valuation_risk': 0.25
        }
        
        weighted_risk = sum(risk_factors.get(key, 50) * weight for key, weight in weights.items())
        return int(weighted_risk)
    
    def _rate_risk_level(self, risk_score: int) -> str:
        """评价风险水平"""
        if risk_score >= 80:
            return "高风险"
        elif risk_score >= 60:
            return "中高风险"
        elif risk_score >= 40:
            return "中等风险"
        elif risk_score >= 20:
            return "低风险"
        else:
            return "极低风险"

    def _generate_llm_summary(self, keyword: str, analysis_results: Dict, score: int, advice: Dict, stocks: List) -> str:
        """使用LLM生成专业的热点分析报告"""
        try:
            from nlp.ollama_client import summarize_hotspot

            # 整理分析数据
            concept_data = analysis_results.get('concept_analysis', {})
            tech_data = analysis_results.get('technical_momentum', {})
            news_data = analysis_results.get('news_catalyst', {})
            market_data = analysis_results.get('market_position', {})
            sector_data = analysis_results.get('sector_rotation', {})
            fund_data = analysis_results.get('fund_participation', {})
            inst_data = analysis_results.get('institutional_attention', {})
            risk_data = analysis_results.get('risk_assessment', {})

            # 构建更详细的提示词
            prompt = f"""请作为资深股票分析师，针对"{keyword}"热点概念，生成一份专业的投资分析报告。

## 综合评估
- **综合评分**: {score}/100
- **推荐等级**: {advice.get('recommendation_level', '中性')}
- **投资策略**: {advice.get('investment_strategy', '谨慎参与')}
- **建议仓位**: {advice.get('suggested_allocation', '5-10%')}
- **持有周期**: {advice.get('time_horizon', '中期')}

## 概念基本面分析
{self._format_concept_data_enhanced(concept_data)}

## 技术动能分析
{self._format_technical_data_enhanced(tech_data)}

## 板块轮动分析
{self._format_sector_data(sector_data)}

## 资金流向分析
{self._format_fund_data(fund_data)}

## 机构关注度
{self._format_institution_data(inst_data)}

## 市场地位
{self._format_market_data_enhanced(market_data)}

## 新闻催化剂
{self._format_news_data(news_data)}

## 风险评估
{self._format_risk_data(risk_data)}

## 优质标的推荐（前5只）
{self._format_stocks_data_enhanced(stocks[:5] if stocks else [])}

---

请基于以上完整的多维度数据，生成一份专业的热点分析报告：

# {keyword}热点深度分析

## 一、概念概述与市场表现
（结合概念基本面、市场地位、板块轮动等数据，概述该热点的整体情况）

## 二、技术面与资金流向
（分析技术动能、基金参与度、机构关注度等，判断市场资金态度）

## 三、基本面与成长性
（深入分析相关个股的财务质量、盈利能力、成长性等）

## 四、新闻催化与政策支持
（梳理新闻热点、政策支持、行业趋势等催化因素）

## 五、优质标的解析
（对推荐的优质股票进行逐一分析，说明推荐理由）

## 六、投资策略建议
（给出具体的操作建议：买入时机、仓位配置、止盈止损策略）

## 七、风险提示
（列出主要风险点，包括市场风险、政策风险、估值风险等）

---

**要求：**
1. 语言专业严谨，避免空话套话
2. 紧密结合实际数据进行分析，数据要具体到数字
3. 投资建议要明确、可操作
4. 风险提示要充分、具体
5. 使用Markdown格式，层级清晰
6. 字数控制在1500-2500字
"""

            # 调用LLM生成报告
            print(f"[LLM] 正在生成{keyword}的专业分析报告...")

            # 构造hotspot_data结构以适配summarize_hotspot
            #  summarize_hotspot期望的结构: keyword, stocks, analyzed_count, total_related_count, news
            hotspot_data_for_llm = {
                'keyword': keyword,
                'comprehensive_score': score,
                'investment_advice': advice,
                'analyzed_count': concept_data.get('analyzed_count', 0) if concept_data.get('has_data') else 0,
                'total_related_count': concept_data.get('stock_count', 0) if concept_data.get('has_data') else 0,
                'stocks': stocks[:10],  # 传递推荐股票
                'news': {
                    'news_count': news_data.get('relevant_news_count', 0) if news_data.get('has_data') else 0,
                    'relevant_news': news_data.get('relevant_news', []) if news_data.get('has_data') else [],
                    'sentiment_score': news_data.get('sentiment_score', 50) if news_data.get('has_data') else 50,
                    'catalyst_strength': news_data.get('catalyst_strength', 50) if news_data.get('has_data') else 50
                },
                # 添加完整分析结果供LLM参考
                'concept_analysis': concept_data,
                'technical_momentum': tech_data,
                'sector_rotation': sector_data,
                'fund_participation': fund_data,
                'institutional_attention': inst_data,
                'market_position': market_data,
                'risk_assessment': risk_data
            }

            summary = summarize_hotspot(hotspot_data_for_llm)

            if summary and len(summary) > 100:
                print(f"[LLM] 报告生成成功，长度: {len(summary)}字")
                return summary
            else:
                print(f"[LLM] 报告生成失败或内容过短，使用降级报告")
                return self._generate_fallback_summary(keyword, score, advice, stocks)

        except Exception as e:
            print(f"[LLM] 生成报告时出错: {e}")
            return self._generate_fallback_summary(keyword, score, advice, stocks)

    def _format_concept_data_enhanced(self, data: Dict) -> str:
        """格式化概念数据 - 增强版"""
        if not data or not data.get('has_data'):
            return "暂无数据"

        lines = []
        lines.append(f"- **相关个股数量**: {data.get('stock_count', 0)}只")
        lines.append(f"- **已分析个股**: {data.get('analyzed_count', 0)}只")

        metrics = data.get('overall_metrics', {})
        if metrics:
            lines.append(f"- **平均ROE**: {metrics.get('avg_roe', 0):.2f}%")
            lines.append(f"- **平均增长率**: {metrics.get('avg_growth_rate', 0):.2f}%")
            lines.append(f"- **平均毛利率**: {metrics.get('avg_margin', 0):.2f}%")
            lines.append(f"- **高质量股票占比**: {metrics.get('high_quality_ratio', 0):.1f}%")

        lines.append(f"- **财务实力评分**: {data.get('financial_strength', 50)}/100")

        return '\n'.join(lines)

    def _format_technical_data_enhanced(self, data: Dict) -> str:
        """格式化技术数据 - 增强版"""
        if not data or not data.get('has_data'):
            return "暂无数据"

        lines = []
        lines.append(f"- **已分析个股**: {data.get('analyzed_stocks', 0)}只")
        lines.append(f"- **平均动能评分**: {data.get('avg_momentum', 50):.1f}/100")
        lines.append(f"- **看多比例**: {data.get('bullish_ratio', 0):.1f}%")
        lines.append(f"- **看多个股**: {data.get('bullish_count', 0)}只")
        lines.append(f"- **中性个股**: {data.get('neutral_count', 0)}只")
        lines.append(f"- **看空个股**: {data.get('bearish_count', 0)}只")

        return '\n'.join(lines)

    def _format_sector_data(self, data: Dict) -> str:
        """格式化板块轮动数据"""
        if not data or not data.get('has_data'):
            return "暂无数据"

        lines = []
        related = data.get('related_sectors', [])
        if related:
            lines.append(f"- **相关板块数量**: {len(related)}个")

        rank = data.get('sector_rank')
        if rank:
            lines.append(f"- **板块排名**: 第{rank}名")

        lines.append(f"- **轮动强度评分**: {data.get('rotation_strength', 50)}/100")

        return '\n'.join(lines) if lines else "暂无详细数据"

    def _format_fund_data(self, data: Dict) -> str:
        """格式化基金参与度数据"""
        if not data or not data.get('has_data'):
            return "暂无数据"

        lines = []
        lines.append(f"- **已分析个股**: {data.get('analyzed_stocks', 0)}只")

        participation = data.get('fund_participation', {})
        if participation:
            lines.append(f"- **基金总数**: {participation.get('total_funds', 0)}只")

        lines.append(f"- **参与度评分**: {data.get('participation_level', 50)}/100")

        return '\n'.join(lines)

    def _format_institution_data(self, data: Dict) -> str:
        """格式化机构关注度数据"""
        if not data or not data.get('has_data'):
            return "暂无数据"

        lines = []
        lines.append(f"- **被调研个股**: {data.get('researched_stocks', 0)}只")
        lines.append(f"- **关注度评分**: {data.get('attention_score', 50)}/100")
        lines.append(f"- **关注度水平**: {data.get('attention_level', 50)}/100")

        return '\n'.join(lines)

    def _format_market_data_enhanced(self, data: Dict) -> str:
        """格式化市场地位数据 - 增强版"""
        if not data or not data.get('has_data'):
            return "暂无数据"

        lines = []
        lines.append(f"- **已分析个股**: {data.get('analyzed_stocks', 0)}只")

        metrics = data.get('position_metrics', {})
        if metrics:
            avg_mv = metrics.get('avg_market_value', 0)
            if avg_mv > 0:
                lines.append(f"- **平均市值**: {avg_mv:.2f}亿")
            total_mv = metrics.get('total_market_value', 0)
            if total_mv > 0:
                lines.append(f"- **总市值**: {total_mv:.2f}亿")

        lines.append(f"- **市场领导力评分**: {data.get('market_leadership', 50)}/100")
        lines.append(f"- **估值水平**: {data.get('valuation_level', '无法评估')}")

        return '\n'.join(lines)

    def _format_news_data(self, data: Dict) -> str:
        """格式化新闻催化剂数据"""
        if not data or not data.get('has_data'):
            return "暂无数据"

        lines = []
        lines.append(f"- **相关新闻数量**: {data.get('relevant_news_count', 0)}条")
        lines.append(f"- **催化剂强度**: {data.get('catalyst_strength', 50)}/100")
        lines.append(f"- **情绪评分**: {data.get('sentiment_score', 50)}/100")
        lines.append(f"- **正面新闻**: {data.get('positive_count', 0)}条")
        lines.append(f"- **负面新闻**: {data.get('negative_count', 0)}条")
        lines.append(f"- **政策支持**: {'是' if data.get('policy_support') else '否'}")

        return '\n'.join(lines)

    def _format_risk_data(self, data: Dict) -> str:
        """格式化风险评估数据"""
        if not data or not data.get('has_data'):
            return "暂无数据"

        lines = []
        lines.append(f"- **综合风险评分**: {data.get('overall_risk_score', 50)}/100")
        lines.append(f"- **风险等级**: {data.get('risk_level', '中等风险')}")

        risk_factors = data.get('risk_factors', {})
        if risk_factors:
            lines.append(f"- **波动性风险**: {risk_factors.get('volatility_risk', 50)}/100")
            lines.append(f"- **集中度风险**: {risk_factors.get('concentration_risk', 50)}/100")
            lines.append(f"- **流动性风险**: {risk_factors.get('liquidity_risk', 50)}/100")
            lines.append(f"- **估值风险**: {risk_factors.get('valuation_risk', 50)}/100")

        return '\n'.join(lines)

    def _format_stocks_data_enhanced(self, stocks: List) -> str:
        """格式化股票数据 - 增强版"""
        if not stocks:
            return "暂无优质标的"

        lines = []
        for i, stock in enumerate(stocks, 1):
            name = stock.get('股票名称', stock.get('name', '未知'))
            code = stock.get('股票代码', stock.get('ts_code', stock.get('code', '')))
            score = stock.get('综合得分', stock.get('final_score', stock.get('score', 0)))

            # 尝试获取其他指标
            roe = stock.get('ROE', 0)
            growth = stock.get('净利润增长', 0)

            line = f"{i}. **{name}** ({code})\n"
            line += f"   - 综合评分: {score:.1f}/100"
            if roe > 0:
                line += f"\n   - ROE: {roe:.2f}%"
            if growth != 0:
                line += f"\n   - 净利润增长: {growth:+.2f}%"

            lines.append(line)

        return '\n\n'.join(lines)

    def _format_concept_data(self, data: Dict) -> str:
        """格式化概念数据 - 保持向后兼容"""
        return self._format_concept_data_enhanced(data)

    def _format_technical_data(self, data: Dict) -> str:
        """格式化技术数据 - 保持向后兼容"""
        return self._format_technical_data_enhanced(data)

    def _format_market_data(self, data: Dict) -> str:
        """格式化市场数据 - 保持向后兼容"""
        return self._format_market_data_enhanced(data)

    def _format_stocks_data(self, stocks: List) -> str:
        """格式化股票数据 - 保持向后兼容"""
        return self._format_stocks_data_enhanced(stocks)

    def _generate_fallback_summary(self, keyword: str, score: int, advice: Dict, stocks: List) -> str:
        """生成简单的降级报告（当LLM不可用时）"""
        summary = f"""# {keyword}热点分析报告

## 综合评价

**综合评分**: {score}/100

本次分析针对"{keyword}"概念进行了多维度评估，综合评分为{score}分。

## 投资建议

- **推荐等级**: {advice.get('recommendation_level', '中性')}
- **投资策略**: {advice.get('investment_strategy', '谨慎观察市场动态')}
- **建议仓位**: {advice.get('suggested_allocation', '5-10%')}
- **持有周期**: {advice.get('time_horizon', '中期(3-6个月)')}

## 优质标的

"""
        if stocks and len(stocks) > 0:
            summary += "根据综合评分，以下是表现较好的相关个股：\n\n"
            for i, stock in enumerate(stocks[:5], 1):
                # 兼容中英文字段名
                name = stock.get('name', stock.get('股票名称', '未知'))
                code = stock.get('ts_code', stock.get('code', stock.get('股票代码', '')))
                s = stock.get('final_score', stock.get('score', stock.get('综合得分', 0)))
                pct = stock.get('pct_change', stock.get('涨跌幅', 0))
                summary += f"{i}. **{name}** ({code})\n   - 综合评分: {s:.1f}/100\n   - 涨跌幅: {pct:+.2f}%\n\n"
        else:
            summary += "暂无优质标的推荐。\n\n"

        summary += """## 风险提示

"""
        if advice.get('key_risks'):
            for risk in advice['key_risks']:
                summary += f"- {risk}\n"
        else:
            summary += "- 市场波动风险\n- 政策变化风险\n- 流动性风险\n"

        summary += "\n---\n*本报告由QSL-AI系统自动生成，仅供参考，不构成投资建议。*"

        return summary


# 全局实例
enhanced_hotspot_analyzer = EnhancedHotspotAnalyzer()