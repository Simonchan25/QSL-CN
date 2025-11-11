"""
专业报告生成系统 V2 - 严格按照早报模版标准
"""
import os
import json
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()
from .tushare_client import (
    _call_api, stock_basic, daily, daily_basic,
    top_list, top_inst, moneyflow_hsgt,
    new_share, share_float, block_trade, concept, concept_detail,
    anns, news, major_news, ths_hot,
    get_continuous_board_stocks, get_board_statistics, get_sector_board_analysis
)
from .advanced_data_client import advanced_client

# 尝试导入jieba，如果不可用则使用简单分词
try:
    import jieba
    JIEBA_AVAILABLE = True
except ImportError:
    JIEBA_AVAILABLE = False
from .concept_manager import get_concept_manager
from .analyze_optimized import run_pipeline_optimized as run_pipeline, resolve_by_name
from .market import fetch_market_overview, _get_market_highlights
from .stock_picker import get_top_picks
from .trading_plan import build_trading_plans_for_picks
from .insight_builder import build_report_summary
from nlp.ollama_client import summarize, summarize_morning, USE_LLM_FOR_MORNING
from .quantitative_metrics import (
    collect_quantitative_metrics,
    calculate_emotion_score,
    generate_enhanced_fallback_summary,
    generate_optimized_prompt
)

class CustomJSONEncoder(json.JSONEncoder):
    """自定义JSON编码器，处理NaN、inf等特殊值"""
    def default(self, obj):
        if isinstance(obj, (np.integer, np.floating)):
            if np.isnan(obj) or np.isinf(obj):
                return None
            return obj.item()
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif pd.isna(obj) or (isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj))):
            return None
        return super().default(obj)

def clean_data_for_json(data):
    """递归清理数据中的NaN、inf值和不可序列化对象"""
    if isinstance(data, dict):
        return {k: clean_data_for_json(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_data_for_json(item) for item in data]
    elif callable(data):  # 跳过function/method对象
        return None
    elif pd.isna(data) or (isinstance(data, float) and (math.isnan(data) or math.isinf(data))):
        return None
    elif isinstance(data, (np.integer, np.floating)):
        if np.isnan(data) or np.isinf(data):
            return None
        return data.item()
    elif isinstance(data, np.ndarray):
        return data.tolist()
    return data

class ProfessionalReportGeneratorV2:
    """专业A股报告生成器 V2 - 按照早报模版标准"""

    def __init__(self):
        self.cache_dir = os.path.join(os.path.dirname(__file__), '../.cache/reports')
        os.makedirs(self.cache_dir, exist_ok=True)
        self.concept_mgr = get_concept_manager()

    def generate_professional_morning_report(self, date: str = None) -> Dict:
        """
        生成专业早报 - 按照早报模版.md的7个部分结构
        """
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')

        print(f"[报告] 开始生成专业早报 {date}")

        # 按照早报模版的7个部分生成报告
        report = {
            "type": "professional_morning_report",
            "date": date,
            "generated_at": datetime.now().isoformat(),
            "template_version": "v2_professional",  # 改为前端期望的版本号
            "sections": {
                "pre_market_hotspots": self._generate_premarket_hotspots(date),    # No.1 盘前热点事件
                "announcement_highlights": self._generate_announcement_highlights(date),  # No.2 公告精选
                "global_markets": self._generate_global_markets(date),        # No.3 全球市场
                "board_analysis": self._generate_board_analysis(date),        # No.4 连板梯队和涨停事件
                "institution_analysis": self._generate_institution_analysis(date),  # No.5 机构席位和游资动向
                "historical_highs": self._generate_historical_highs(date),     # No.6 历史新高
                "popularity_rankings": self._generate_popularity_rankings(date)    # No.7 人气热榜
            }
        }

        # 生成AI专业总结
        report["professional_summary"] = self._generate_professional_ai_summary(report)

        try:
            report["insights"] = build_report_summary(report["sections"])
        except Exception as exc:
            print(f"[报告] 构建结构化摘要失败: {exc}")
            report["insights"] = {"highlights": [], "summary": "数据不足，需人工复核"}

        # 生成图表配置
        try:
            print(f"[报告] 生成可视化图表配置...")
            from .chart_metrics_collector import generate_charts_for_report
            report["charts"] = generate_charts_for_report(date, report)
        except Exception as exc:
            print(f"[报告] 生成图表配置失败: {exc}")
            import traceback
            traceback.print_exc()
            report["charts"] = {}

        return report

    def generate_comprehensive_market_report(self, date: str = None) -> Dict:
        """
        生成全市场综合分析报告 - 覆盖全A股5400+只股票
        """
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')

        print(f"[报告] 开始生成综合市场报告 {date}")

        # 导入必要的模块
        from .market_ai_analyzer import MarketAIAnalyzer
        from .market import fetch_market_overview

        try:
            # 获取市场数据
            market_data = fetch_market_overview()

            # AI分析
            analyzer = MarketAIAnalyzer()
            ai_analysis = analyzer.analyze_comprehensive_market(market_data)

            # 构建comprehensive_market格式报告
            report = {
                "type": "comprehensive_market",
                "date": date,
                "generated_at": datetime.now().isoformat(),
                "market_coverage": "全A股市场",
                "sections": {
                    "major_events": self._get_major_events_with_analysis(date),
                    "hot_sectors": self._get_hot_sectors_analysis(date, market_data),
                    "unusual_stocks": self._get_unusual_stocks_analysis(date),
                    "important_announcements": self._get_daily_announcements(date),
                    "capital_flow": self._get_capital_flow_analysis(date, market_data),
                    "market_sentiment": self._get_market_sentiment_analysis(date, market_data, ai_analysis),
                    "smart_alerts": ai_analysis.get("alerts", [])
                },
                "ai_summary": self._generate_comprehensive_ai_summary(market_data, ai_analysis)
            }

            # 保存报告
            self._save_comprehensive_report(report)

            try:
                report["insights"] = build_report_summary(report["sections"])
            except Exception as exc:
                print(f"[报告] 综合摘要生成失败: {exc}")
                report["insights"] = {"highlights": [], "summary": "数据不足，需人工复核"}
            return report

        except Exception as e:
            print(f"[错误] 生成综合市场报告失败: {e}")
            return {
                "type": "comprehensive_market",
                "date": date,
                "generated_at": datetime.now().isoformat(),
                "error": str(e),
                "sections": {}
            }

    def _generate_premarket_hotspots(self, date: str) -> Dict:
        """生成No.1 盘前热点事件"""
        print("[报告] 生成盘前热点事件...")

        # 获取昨日热门板块和个股
        yesterday_hot_sectors = self._get_yesterday_hot_sectors(date)

        # 获取重大事件（新闻）
        major_events = self._get_major_events_with_analysis(date)

        # 获取行业要闻
        industry_news = self._get_industry_news_digest(date)

        # 获取政策动态
        policy_updates = self._get_policy_updates(date)

        return {
            "title": "No.1 盘前热点事件",
            "yesterday_hot_sectors": yesterday_hot_sectors,  # 昨日热门板块
            "major_events": major_events,  # 重大事件
            "industry_news": industry_news,  # 行业要闻
            "policy_updates": policy_updates  # 政策动态
        }

    def _generate_announcement_highlights(self, date: str) -> Dict:
        """生成No.2 公告精选"""
        print("[报告] 生成公告精选...")

        # 获取日常公告
        daily_announcements = self._get_daily_announcements(date)

        # 获取业绩预告
        performance_announcements = self._get_performance_announcements(date)

        # 获取停复牌
        suspension_resumption = self._get_suspension_resumption(date)

        # 获取减持等风险提示
        risk_alerts = self._get_risk_alerts(date)

        return {
            "title": "No.2 公告精选",
            "daily_announcements": daily_announcements,
            "performance_announcements": performance_announcements,
            "suspension_resumption": suspension_resumption,
            "risk_alerts": risk_alerts
        }

    def _generate_global_markets(self, date: str) -> Dict:
        """生成No.3 全球市场"""
        print("[报告] 生成全球市场...")

        # 这里可以集成全球市场数据，目前返回基本结构
        return {
            "title": "No.3 全球市场",
            "us_markets": {
                "summary": "美股三大指数表现",
                "details": "待补充具体数据"
            },
            "china_concept_stocks": {
                "summary": "中概股表现",
                "details": "待补充具体数据"
            },
            "commodities": {
                "summary": "大宗商品",
                "details": "待补充具体数据"
            }
        }

    def _generate_board_analysis(self, date: str) -> Dict:
        """生成No.4 连板梯队和涨停事件"""
        print("[报告] 生成连板梯队和涨停事件...")

        # 获取连板梯队
        board_hierarchy = self._get_board_hierarchy(date)

        # 获取涨停事件分析
        limit_up_events = self._get_limit_up_events_with_themes(date)

        # 获取实时市场情绪
        market_mood = advanced_client.get_realtime_market_mood(trade_date=date.replace('-', ''))

        return {
            "title": "No.4 连板梯队和涨停事件",
            "board_hierarchy": board_hierarchy,
            "limit_up_events": limit_up_events,
            "market_mood": market_mood
        }

    def _generate_institution_analysis(self, date: str) -> Dict:
        """生成No.5 机构席位和游资动向"""
        print("[报告] 生成机构席位和游资动向...")

        # 获取龙虎榜数据
        dragon_tiger_data = self._get_dragon_tiger_analysis(date)

        return {
            "title": "No.5 机构席位和游资动向",
            "dragon_tiger_analysis": dragon_tiger_data
        }

    def _generate_historical_highs(self, date: str) -> Dict:
        """生成No.6 历史新高"""
        print("[报告] 生成历史新高...")

        # 获取创历史新高的股票
        historical_highs = self._get_historical_highs_with_themes(date)

        return {
            "title": "No.6 历史新高",
            "historical_highs": historical_highs
        }

    def _generate_popularity_rankings(self, date: str) -> Dict:
        """生成No.7 人气热榜"""
        print("[报告] 生成人气热榜...")

        # 获取热门股票排行
        popularity_rankings = self._get_popularity_rankings(date)

        return {
            "title": "No.7 人气热榜",
            "rankings": popularity_rankings
        }

    # === 辅助数据获取方法 ===

    def _get_yesterday_hot_sectors(self, date: str) -> List[Dict]:
        """获取昨日热门板块（包含板块涨幅和领涨个股） - 并发优化"""
        try:
            # 获取涨停股票
            limit_up = advanced_client.limit_list_d(trade_date=date.replace('-', ''), limit_type='U')

            sectors = []
            if not limit_up.empty:
                # 并发批量获取概念数据
                from concurrent.futures import ThreadPoolExecutor, as_completed

                stock_list = limit_up.head(50).to_dict('records')
                stock_concepts_map = {}

                with ThreadPoolExecutor(max_workers=10) as executor:
                    future_to_code = {
                        executor.submit(self._get_stock_concepts, stock['ts_code']): stock
                        for stock in stock_list
                    }

                    for future in as_completed(future_to_code):
                        stock = future_to_code[future]
                        try:
                            concepts = future.result(timeout=2)
                            stock_concepts_map[stock['ts_code']] = concepts
                        except:
                            stock_concepts_map[stock['ts_code']] = []

                # 按板块分类统计
                sector_stocks = {}
                for stock in stock_list:
                    concepts = stock_concepts_map.get(stock['ts_code'], [])
                    for concept in concepts[:3]:
                        if concept not in sector_stocks:
                            sector_stocks[concept] = []
                        sector_stocks[concept].append({
                            "name": stock['name'],
                            "code": stock['ts_code'][:6],
                            "change": f"+{stock.get('pct_chg', 10):.2f}%" if 'pct_chg' in stock else "+10%",
                            "volume": stock.get('amount', 0) / 100000000 if 'amount' in stock else 0
                        })

                # 按板块内股票数量排序，构建返回结果
                sorted_sectors = sorted(sector_stocks.items(), key=lambda x: len(x[1]), reverse=True)

                for sector_name, stocks in sorted_sectors[:8]:  # 增加到前8个热门板块
                    # 计算板块平均涨幅
                    avg_change = sum(float(s['change'].replace('+', '').replace('%', '')) for s in stocks) / len(stocks)
                    # 计算总成交额
                    total_volume = sum(s['volume'] for s in stocks)

                    sectors.append({
                        "sector": sector_name,
                        "sector_performance": f"+{avg_change:.1f}%",
                        "analysis": f"板块内{len(stocks)}只个股涨停，成交额{total_volume:.1f}亿元，市场关注度极高",
                        "leading_stocks": stocks[:5],  # 增加到5只领涨股
                        "stock_count": len(stocks),
                        "total_volume": total_volume,
                        "data_source": "limit_up_stocks"
                    })

            # 如果没有涨停股票，尝试获取涨幅较大的股票
            if not sectors:
                # 获取涨幅前100的股票
                try:
                    top_gainers = advanced_client.top_list(trade_date=date.replace('-', ''), ts_code='',
                                                         field='pct_chg', limit=100)
                    if not top_gainers.empty:
                        # 按概念分类涨幅较大的股票
                        concept_gainers = {}
                        for _, stock in top_gainers.iterrows():
                            if stock.get('pct_chg', 0) > 3:  # 涨幅大于3%
                                concepts = self._get_stock_concepts(stock['ts_code'])
                                for concept in concepts[:2]:
                                    if concept not in concept_gainers:
                                        concept_gainers[concept] = []
                                    concept_gainers[concept].append({
                                        "name": stock['name'],
                                        "code": stock['ts_code'][:6],
                                        "change": f"+{stock.get('pct_chg', 0):.2f}%"
                                    })

                        # 构建板块数据
                        for concept, stocks in list(concept_gainers.items())[:5]:
                            if len(stocks) >= 2:  # 至少2只股票
                                avg_change = sum(float(s['change'].replace('+', '').replace('%', '')) for s in stocks) / len(stocks)
                                sectors.append({
                                    "sector": concept,
                                    "sector_performance": f"+{avg_change:.1f}%",
                                    "analysis": f"板块内{len(stocks)}只个股表现活跃，平均涨幅{avg_change:.1f}%",
                                    "leading_stocks": stocks[:3],
                                    "stock_count": len(stocks),
                                    "data_source": "top_gainers"
                                })
                except Exception as inner_e:
                    print(f"[警告] 获取涨幅榜失败: {inner_e}")

            # 如果仍然没有数据，从基本市场数据获取
            if not sectors:
                sectors = self._get_market_sectors_fallback(date)

            return sectors if sectors else []
        except Exception as e:
            print(f"[错误] 获取昨日热门板块失败: {e}")
            # 数据获取失败，返回空列表
            return []

    def _get_market_sectors_fallback(self, date: str) -> List[Dict]:
        """
        获取市场板块数据的fallback方法
        使用Tushare的daily接口获取当日行情数据，按概念分组
        """
        try:
            print(f"[数据] 使用fallback方法获取市场板块数据: {date}")

            # 优先使用涨停股票数据
            trade_date = date.replace('-', '')
            gainers = pd.DataFrame()

            try:
                # 方案1：使用涨停股票数据（最优质的热点数据）
                from .advanced_data_client import advanced_client
                limit_up = advanced_client.limit_list_d(trade_date=trade_date, limit_type='U')
                if not limit_up.empty:
                    print(f"[数据] 找到{len(limit_up)}只涨停股票")
                    gainers = limit_up.head(100)
            except Exception as e:
                print(f"[数据] 涨停数据获取失败: {e}")

            # 方案2：如果涨停数据不足，使用龙虎榜数据补充
            if len(gainers) < 50:
                try:
                    from .market import top_list
                    top_list_data = top_list(trade_date=trade_date)
                    if not top_list_data.empty:
                        print(f"[数据] 补充{len(top_list_data)}只龙虎榜股票")
                        gainers = pd.concat([gainers, top_list_data.head(50)], ignore_index=True)
                except Exception as e:
                    print(f"[数据] 龙虎榜数据获取失败: {e}")

            if gainers.empty:
                print(f"[警告] 没有获取到{date}的热点股票数据，尝试使用最近交易日数据")
                # 尝试使用最近1-3个交易日的数据
                from .trading_date_helper import find_latest_trading_date_with_data
                for days_back in range(1, 4):
                    try:
                        from datetime import datetime, timedelta
                        fallback_date = (datetime.strptime(date, '%Y-%m-%d') - timedelta(days=days_back)).strftime('%Y-%m-%d')
                        fallback_trade_date = fallback_date.replace('-', '')

                        # 尝试涨停数据
                        limit_up_fallback = advanced_client.limit_list_d(trade_date=fallback_trade_date, limit_type='U')
                        if not limit_up_fallback.empty:
                            print(f"[数据] 使用{fallback_date}的涨停数据")
                            gainers = limit_up_fallback.head(100)
                            break
                    except:
                        continue

                if gainers.empty:
                    print(f"[警告] 最近3日也无数据，返回空列表")
                    return []

            print(f"[数据] 共找到{len(gainers)}只热点股票")

            # 按概念分组
            concept_groups = {}
            for _, stock in gainers.iterrows():
                # 获取股票所属概念
                concepts = self._get_stock_concepts(stock['ts_code'])

                for concept in concepts[:2]:  # 每只股票取前2个概念
                    if concept == "未知概念":
                        continue

                    if concept not in concept_groups:
                        concept_groups[concept] = []

                    # 获取涨幅（如果有pct_chg字段就用，否则默认+5%）
                    pct_chg = stock.get('pct_chg', 5.0) if 'pct_chg' in stock else 5.0

                    # 获取成交额（Tushare的amount字段单位是元，需转换为亿元）
                    volume_yuan = stock.get('amount', stock.get('total_mv', 0))
                    volume_yi = round(volume_yuan / 100000000, 2) if volume_yuan else 0  # 元 → 亿元

                    concept_groups[concept].append({
                        "name": stock.get('name', stock['ts_code'][:6]),
                        "code": stock['ts_code'][:6],
                        "change": f"+{pct_chg:.2f}%",
                        "volume": volume_yi  # 已转换为亿元
                    })

            # 构建板块数据
            sectors = []
            for concept, stocks in concept_groups.items():
                if len(stocks) < 2:  # 至少2只股票才算板块
                    continue

                # 计算板块平均涨幅
                avg_change = sum(float(s['change'].replace('+', '').replace('%', '')) for s in stocks) / len(stocks)

                # 计算总成交额
                total_volume = sum(s['volume'] for s in stocks)

                sectors.append({
                    "sector": concept,
                    "sector_performance": f"+{avg_change:.1f}%",
                    "analysis": f"板块内{len(stocks)}只个股表现活跃，平均涨幅{avg_change:.1f}%，成交额{total_volume:.1f}亿元",
                    "leading_stocks": stocks[:5],  # 最多显示5只领涨股
                    "stock_count": len(stocks),
                    "total_volume": total_volume,
                    "data_source": "tushare_daily"
                })

            # 按股票数量和平均涨幅排序
            sectors.sort(key=lambda x: (x['stock_count'], float(x['sector_performance'].replace('+', '').replace('%', ''))), reverse=True)

            # 验证数据
            validated_sectors = self._validate_sector_data(sectors[:10])

            print(f"[数据] 成功生成{len(validated_sectors)}个板块数据")
            return validated_sectors

        except Exception as e:
            print(f"[错误] fallback方法获取市场板块失败: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _validate_sector_data(self, sectors: List[Dict]) -> List[Dict]:
        """
        验证板块数据的有效性
        """
        validated = []

        for sector in sectors:
            try:
                # 验证必需字段存在
                if not all(key in sector for key in ['sector', 'sector_performance', 'analysis', 'leading_stocks']):
                    print(f"[警告] 板块数据缺少必需字段: {sector.get('sector', '未知')}")
                    continue

                # 验证涨跌幅在合理范围(-20% ~ +20%)
                performance_str = sector['sector_performance'].replace('+', '').replace('%', '')
                try:
                    performance_value = float(performance_str)
                    if performance_value < -20 or performance_value > 20:
                        print(f"[警告] 板块涨幅异常: {sector['sector']} = {performance_value}%")
                        continue
                except ValueError:
                    print(f"[警告] 板块涨幅格式错误: {sector['sector']} = {performance_str}")
                    continue

                # 验证股票数量
                if sector.get('stock_count', 0) < 1:
                    print(f"[警告] 板块股票数量为0: {sector['sector']}")
                    continue

                # 添加data_source字段（如果没有）
                if 'data_source' not in sector:
                    sector['data_source'] = 'unknown'

                validated.append(sector)

            except Exception as e:
                print(f"[错误] 验证板块数据失败: {e}")
                continue

        return validated

    def _get_policy_updates(self, date: str) -> List[Dict]:
        """获取政策动态（使用行业异动生成政策提示）"""
        try:
            # 获取重要新闻作为政策动态
            news_data = major_news(limit=10)

            policy_updates = []
            if not news_data.empty:
                for _, news in news_data.iterrows():
                    # 筛选包含政策关键词的新闻
                    policy_keywords = ['政策', '发布', '印发', '通知', '意见', '规划', '措施', '方案']
                    if any(keyword in news['title'] for keyword in policy_keywords):
                        policy_updates.append({
                            "title": news['title'],
                            "content": news.get('content', '')[:200] + "...",
                            "affected_sectors": self._analyze_affected_sectors(news['title']),
                            "impact_assessment": "利好相关板块发展"
                        })

            # Fallback: 如果没有政策新闻，基于行业异动生成政策关注提示
            if not policy_updates:
                print("[信息] 无政策新闻，生成政策关注提示")
                from .advanced_data_client import advanced_client
                trade_date = date.replace('-', '')
                limit_up = advanced_client.limit_list_d(trade_date=trade_date, limit_type='U')

                if not limit_up.empty:
                    # 统计行业分布
                    industry_counts = limit_up.groupby('industry').size().sort_values(ascending=False)
                    for industry, count in industry_counts.head(3).items():
                        policy_updates.append({
                            "title": f"关注{industry}行业政策动向",
                            "content": f"{industry}板块今日表现活跃（{count}只个股涨停），建议关注相关产业政策和行业规划，可能存在政策催化预期。",
                            "affected_sectors": [industry],
                            "impact_assessment": "中性，需跟踪政策落地情况"
                        })

            return policy_updates[:3]
        except Exception as e:
            print(f"[错误] 获取政策动态失败: {e}")
            return []

    def _get_yesterday_hot_stocks(self, date: str) -> List[Dict]:
        """获取昨日热点股票（保留原方法供其他地方调用）"""
        try:
            # 获取涨停股票
            limit_up = advanced_client.limit_list_d(trade_date=date.replace('-', ''), limit_type='U')

            if not limit_up.empty:
                # 按板块分类热点股票
                hot_stocks = {}
                for _, stock in limit_up.head(20).iterrows():
                    # 获取股票所属概念
                    concepts = self._get_stock_concepts(stock['ts_code'])
                    for concept in concepts[:3]:  # 取前3个概念
                        if concept not in hot_stocks:
                            hot_stocks[concept] = []
                        hot_stocks[concept].append(stock['name'])

                # 转换为模版格式
                result = []
                for concept, stocks in hot_stocks.items():
                    if stocks:  # 确保有股票
                        result.append(f"{concept}：{', '.join(stocks[:3])}")  # 每个概念最多3只股票
                return result[:8]  # 最多返回8个概念
            else:
                print(f"[警告] 没有涨停股票，日期: {date}")
                return []
        except Exception as e:
            print(f"[错误] 获取昨日热点失败: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _get_major_events_with_analysis(self, date: str) -> List[Dict]:
        """获取重大事件并分析"""
        try:
            # 获取重大新闻，增加超时保护
            import signal
            from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

            def get_news_with_timeout():
                return major_news(limit=10)

            # 使用线程池和超时控制
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(get_news_with_timeout)
                try:
                    major_news_data = future.result(timeout=15)  # 15秒超时
                except FutureTimeoutError:
                    print(f"[警告] 重大新闻API调用超时，使用fallback方案")
                    trade_date = self._get_last_trade_date(date)
                    return self._generate_events_from_limit_stocks(trade_date)

            events = []
            if not major_news_data.empty:
                for _, news in major_news_data.iterrows():
                    # 分析新闻相关股票
                    related_stocks = self._analyze_news_related_stocks(news['title'])

                    # 分析影响的板块
                    affected_sectors = self._analyze_affected_sectors(news['title'])

                    # 生成投资逻辑
                    investment_logic = self._generate_investment_logic(news['title'])

                    # 评估市场影响程度
                    impact_level = self._assess_market_impact(news['title'])

                    event = {
                        "title": news['title'],
                        "content": (news.get('content', '') or news['title'])[:300] + "...",  # 限制长度
                        "related_stocks": related_stocks,
                        "affected_sectors": affected_sectors,
                        "investment_logic": investment_logic,
                        "market_impact": impact_level,
                        "publish_time": news.get('datetime', ''),
                        "importance": "高" if any(keyword in news['title'] for keyword in ['央行', '证监会', '政策', '改革']) else "中"
                    }
                    events.append(event)

            # 如果没有获取到新闻，使用涨停股票生成事件
            if not events:
                print(f"[警告] 没有获取到重大新闻数据，使用涨停数据生成事件")
                # 获取最后交易日
                trade_date = self._get_last_trade_date(date)
                events = self._generate_events_from_limit_stocks(trade_date)
                if not events:
                    return []

            return events[:8]  # 返回前8个事件
        except Exception as e:
            print(f"[错误] 获取重大事件失败: {e}")
            import traceback
            traceback.print_exc()
            # 数据获取失败，返回空列表
            return []

    def _generate_events_from_limit_stocks(self, date: str) -> List[Dict]:
        """从涨停股票数据生成重大事件（fallback方案）"""
        try:
            from .advanced_data_client import advanced_client
            trade_date = date.replace('-', '')
            limit_up = advanced_client.limit_list_d(trade_date=trade_date, limit_type='U')

            if limit_up.empty:
                return []

            # 按行业分组
            events = []
            industry_groups = {}
            for _, stock in limit_up.head(30).iterrows():
                industry = stock.get('industry', '其他')
                if industry not in industry_groups:
                    industry_groups[industry] = []
                industry_groups[industry].append(stock)

            # 生成事件
            for industry, stocks in sorted(industry_groups.items(), key=lambda x: len(x[1]), reverse=True)[:5]:
                if len(stocks) >= 2:  # 至少2只股票才算事件
                    stock_names = [s['name'] for s in stocks[:3]]
                    event = {
                        "title": f"{industry}板块集体异动，{len(stocks)}只个股涨停",
                        "content": f"{industry}板块今日表现强势，包括{'、'.join(stock_names)}等{len(stocks)}只个股涨停，显示板块资金关注度较高，可能存在政策催化或业绩预期提升。",
                        "related_stocks": stock_names[:5],
                        "affected_sectors": [industry],
                        "investment_logic": f"关注{industry}板块的持续性，重点跟踪龙头股表现",
                        "market_impact": "中" if len(stocks) < 5 else "高",
                        "publish_time": date,
                        "importance": "中"
                    }
                    events.append(event)

            return events
        except Exception as e:
            print(f"[错误] 从涨停数据生成事件失败: {e}")
            return []

    def _get_last_trade_date(self, date: str) -> str:
        """获取最后一个交易日"""
        try:
            from .advanced_data_client import advanced_client
            current_date = datetime.strptime(date, '%Y-%m-%d')

            # 向前查找最多7天
            for i in range(7):
                check_date = (current_date - timedelta(days=i)).strftime('%Y%m%d')
                # 尝试获取该日期的涨停数据，如果有数据说明是交易日
                limit_up = advanced_client.limit_list_d(trade_date=check_date, limit_type='U')
                if limit_up is not None and len(limit_up) > 0:
                    print(f"[信息] 找到最后交易日: {check_date}")
                    return (current_date - timedelta(days=i)).strftime('%Y-%m-%d')

            # 如果找不到，返回原日期
            print(f"[警告] 未找到最近的交易日，使用原日期: {date}")
            return date
        except Exception as e:
            print(f"[错误] 获取最后交易日失败: {e}")
            return date

    def _get_industry_news_digest(self, date: str) -> List[Dict]:
        """获取行业要闻摘要（使用热点板块数据生成）"""
        try:
            # 由于Tushare免费版anns API字段有限，改用热点板块生成行业要闻
            # 获取最后交易日
            trade_date_str = self._get_last_trade_date(date)
            trade_date = trade_date_str.replace('-', '')
            from .advanced_data_client import advanced_client
            limit_up = advanced_client.limit_list_d(trade_date=trade_date, limit_type='U')

            news_digest = []
            if not limit_up.empty:
                # 按行业分类
                industry_dict = {}
                for _, stock in limit_up.head(50).iterrows():
                    industry = stock.get('industry', '其他')
                    if industry not in industry_dict:
                        industry_dict[industry] = []
                    industry_dict[industry].append(stock['name'])

                # 生成行业要闻
                for industry, stocks in sorted(industry_dict.items(), key=lambda x: len(x[1]), reverse=True)[:10]:
                    if len(stocks) >= 1:
                        digest_item = {
                            "company": industry,
                            "title": f"{industry}板块活跃，{len(stocks)}只个股涨停（{'、'.join(stocks[:3])}等）",
                            "type": "行业动态"
                        }
                        news_digest.append(digest_item)

            # 如果还是没数据，提供默认提示
            if not news_digest:
                news_digest = [{"company": "市场", "title": f"{date}暂无重大行业新闻", "type": "其他"}]

            return news_digest[:15]
        except Exception as e:
            print(f"[错误] 获取行业要闻失败: {e}")
            return [{"company": "系统", "title": "数据获取失败", "type": "其他"}]

    def _get_board_hierarchy(self, date: str) -> Dict:
        """获取连板梯队"""
        try:
            # 获取连板股票数据
            board_stocks = get_continuous_board_stocks(date.replace('-', ''))

            hierarchy = {}
            if board_stocks:
                # 按连板数分类
                for board_count, stocks in board_stocks.items():
                    hierarchy[f"{board_count}连板"] = [stock['name'] for stock in stocks[:5]]  # 每档最多5只

            return hierarchy
        except Exception as e:
            print(f"[错误] 获取连板梯队失败: {e}")
            return {}

    def _get_limit_up_events_with_themes(self, date: str) -> List[Dict]:
        """获取涨停事件及主题分析"""
        try:
            # 获取涨停股票
            limit_up_data = advanced_client.limit_list_d(trade_date=date.replace('-', ''), limit_type='U')

            if limit_up_data.empty:
                return []

            # 按概念分类涨停股票
            theme_analysis = {}
            for _, stock in limit_up_data.iterrows():
                concepts = self._get_stock_concepts(stock['ts_code'])
                for concept in concepts[:2]:  # 每只股票取前2个概念
                    if concept not in theme_analysis:
                        theme_analysis[concept] = []
                    theme_analysis[concept].append(stock['name'])

            # 生成主题事件
            events = []
            for theme, stocks in theme_analysis.items():
                if len(stocks) >= 2:  # 至少2只股票才算主题
                    event = {
                        "theme": theme,
                        "stocks": stocks[:5],  # 最多显示5只股票
                        "stock_count": len(stocks),
                        "analysis": f"{theme}板块活跃，{len(stocks)}只个股涨停"
                    }
                    events.append(event)

            return sorted(events, key=lambda x: x['stock_count'], reverse=True)[:10]
        except Exception as e:
            print(f"[错误] 获取涨停事件失败: {e}")
            return []

    def _get_popularity_rankings(self, date: str) -> Dict:
        """获取人气热榜"""
        try:
            # 获取热门股票数据
            hot_rank = ths_hot(trade_date=date.replace('-', ''))

            rankings = {
                "概念热榜": [],
                "个股热榜": []
            }

            if not hot_rank.empty:
                # 取前10个热门股票
                rankings["个股热榜"] = [
                    {
                        "name": stock['name'],
                        "reason": "市场关注度高"
                    }
                    for _, stock in hot_rank.head(10).iterrows()
                ]

            return rankings
        except Exception as e:
            print(f"[错误] 获取人气热榜失败: {e}")
            return {"概念热榜": [], "个股热榜": []}

    # === 辅助分析方法 ===

    def _get_stock_concepts(self, ts_code: str) -> List[str]:
        """获取股票所属概念"""
        try:
            concept_data = concept_detail(id='', ts_code=ts_code)
            if not concept_data.empty:
                return concept_data['concept_name'].tolist()[:5]  # 最多5个概念
        except:
            pass
        return ["未知概念"]

    def _analyze_news_related_stocks(self, title: str) -> List[str]:
        """分析新闻相关股票"""
        # 这里可以加入更复杂的NLP分析
        # 目前返回空列表，后续可以基于关键词匹配
        return []

    def _generate_investment_logic(self, title: str) -> str:
        """生成投资逻辑"""
        # 基于新闻标题关键词生成投资逻辑
        if "政策" in title or "支持" in title:
            return "政策驱动型机会，关注受益标的"
        elif "业绩" in title or "增长" in title:
            return "基本面改善，关注业绩确定性"
        elif "重组" in title or "收购" in title:
            return "并购重组机会，关注事件驱动"
        elif "创新" in title or "科技" in title:
            return "科技创新机会，关注龙头企业"
        else:
            return "关注事件后续发展和市场反应"

    def _assess_market_impact(self, title: str) -> str:
        """评估市场影响程度"""
        high_impact_keywords = ["央行", "证监会", "重大", "政策", "改革", "降准", "降息"]
        medium_impact_keywords = ["业绩", "增长", "投资", "发展", "支持"]

        if any(keyword in title for keyword in high_impact_keywords):
            return "重大影响"
        elif any(keyword in title for keyword in medium_impact_keywords):
            return "中等影响"
        else:
            return "影响有限"

    def _analyze_affected_sectors(self, title: str) -> List[str]:
        """分析新闻影响的板块"""
        sectors = []

        # 定义板块关键词映射
        sector_keywords = {
            "新能源": ["新能源", "光伏", "风电", "储能", "锂电"],
            "半导体": ["半导体", "芯片", "集成电路", "晶圆"],
            "人工智能": ["人工智能", "AI", "算力", "大模型", "机器学习"],
            "医药": ["医药", "医疗", "疫苗", "创新药", "生物"],
            "消费": ["消费", "零售", "餐饮", "白酒", "食品"],
            "金融": ["金融", "银行", "保险", "券商", "证券"],
            "地产": ["地产", "房地产", "楼市", "住房"],
            "军工": ["军工", "国防", "航天", "航空"],
        }

        for sector, keywords in sector_keywords.items():
            if any(keyword in title for keyword in keywords):
                sectors.append(sector)

        return sectors[:3] if sectors else ["相关板块"]

    def _classify_announcement_type(self, title: str) -> str:
        """分类公告类型"""
        if "减持" in title:
            return "减持"
        elif "重组" in title or "收购" in title:
            return "重组收购"
        elif "业绩" in title or "财报" in title:
            return "业绩"
        elif "停牌" in title or "复牌" in title:
            return "停复牌"
        else:
            return "其他"

    def _get_daily_announcements(self, date: str) -> List[Dict]:
        """获取日常公告"""
        try:
            # 使用平安银行作为默认股票获取公告数据
            announcements = anns(ts_code="000001.SZ")

            daily_anns = []
            if not announcements.empty:
                for _, ann in announcements.head(10).iterrows():
                    company_name = ann.get('name', ann.get('ts_code', '')[:6])
                    title = ann.get('title', ann.get('ann_title', ''))
                    daily_anns.append({
                        "company": company_name,
                        "title": title,
                        "type": self._classify_announcement_type(title)
                    })

            return daily_anns
        except Exception as e:
            print(f"[错误] 获取日常公告失败: {e}")
            return []

    def _get_performance_announcements(self, date: str) -> List[Dict]:
        """获取业绩预告"""
        # 可以从公告中筛选业绩相关
        return []

    def _get_suspension_resumption(self, date: str) -> Dict:
        """获取停复牌信息"""
        return {
            "suspension": [],  # 停牌
            "resumption": []   # 复牌
        }

    def _get_risk_alerts(self, date: str) -> List[Dict]:
        """获取风险提示（减持等）"""
        return []

    def _get_dragon_tiger_analysis(self, date: str) -> Dict:
        """获取龙虎榜分析"""
        return {
            "summary": "龙虎榜数据分析",
            "details": []
        }

    def _get_historical_highs_with_themes(self, date: str) -> List[Dict]:
        """获取创历史新高股票及主题分析"""
        return []

    def _generate_professional_ai_summary(self, report: Dict) -> str:
        """生成专业AI总结 - 集成量化指标"""
        try:
            date = report.get('date', '')

            # 1. 收集量化指标
            metrics = collect_quantitative_metrics(date)

            # 2. 提取sections数据
            sections_data = report.get('sections', {})
            hotspots_data = sections_data.get('pre_market_hotspots', {})
            board_data = sections_data.get('board_analysis', {})

            # 3. 生成优化的提示词（包含量化数据）
            detailed_prompt = generate_optimized_prompt(metrics, date, hotspots_data, board_data)

            # 4. 调用LLM或使用增强的fallback
            if USE_LLM_FOR_MORNING:
                summary = summarize_morning(detailed_prompt)
                return summary
            else:
                # 使用增强的fallback分析（基于量化指标）
                return generate_enhanced_fallback_summary(metrics, date)

        except Exception as e:
            print(f"[错误] 生成AI总结失败: {e}")
            # 尝试使用基础量化数据生成fallback
            try:
                metrics = collect_quantitative_metrics(report.get('date', ''))
                return generate_enhanced_fallback_summary(metrics, report.get('date', ''))
            except:
                return self._generate_detailed_fallback_summary(report)

    def _generate_detailed_fallback_summary(self, report: Dict) -> str:
        """生成基于真实数据的详细fallback分析"""
        try:
            sections = report.get('sections', {})
            date = report.get('date', '未知日期')

            # 提取关键数据
            hotspots = sections.get('pre_market_hotspots', {})
            board_analysis = sections.get('board_analysis', {})
            announcements = sections.get('announcement_highlights', {})
            popularity = sections.get('popularity_rankings', {})

            # 分析热门板块
            hot_sectors = hotspots.get('yesterday_hot_sectors', [])
            sector_summary = ""
            if hot_sectors:
                top_sectors = hot_sectors[:3]
                sector_names = [sector.get('sector', '未知板块') for sector in top_sectors]
                sector_summary = f"主要热点集中在{', '.join(sector_names)}等板块"
            else:
                sector_summary = "市场热点分散，缺乏明显主线"

            # 分析涨停情况
            board_mood = board_analysis.get('market_mood', {})
            limit_up_count = board_mood.get('limit_up', 0) if board_mood else 0
            limit_down_count = board_mood.get('limit_down', 0) if board_mood else 0

            # 分析市场情绪
            if limit_up_count >= 50:
                emotion_analysis = f"市场情绪火热，{limit_up_count}家涨停，赚钱效应显著"
                strategy_suggestion = "建议积极参与，仓位可提升至60-70%"
            elif limit_up_count >= 20:
                emotion_analysis = f"市场情绪偏暖，{limit_up_count}家涨停，结构性机会较多"
                strategy_suggestion = "建议稳健参与，仓位控制在40-50%"
            else:
                emotion_analysis = f"市场情绪谨慎，涨停仅{limit_up_count}家，操作难度较大"
                strategy_suggestion = "建议观望为主，仓位控制在20-30%以下"

            # 分析公告情况
            daily_anns = announcements.get('daily_announcements', [])
            announcement_summary = ""
            if daily_anns:
                ann_count = len(daily_anns)
                announcement_summary = f"今日重要公告{ann_count}项，需关注业绩和重组类机会"
            else:
                announcement_summary = "公告较少，事件驱动机会有限"

            # 构建专业分析报告
            summary = f"""【{date} A股市场专业分析】

一、【市场概况】
{emotion_analysis}。{sector_summary}，市场呈现{"强势" if limit_up_count >= 30 else "震荡" if limit_up_count >= 10 else "弱势"}格局。

二、【热点分析】
{sector_summary}。连板梯队{"完整" if limit_up_count >= 20 else "不完整"}，{"建议关注龙头品种" if limit_up_count >= 20 else "等待新热点形成"}。

三、【资金动向】
基于涨停数据分析，资金{"活跃度较高" if limit_up_count >= 30 else "活跃度一般" if limit_up_count >= 10 else "活跃度偏低"}，{"机构参与积极" if limit_up_count >= 30 else "机构态度谨慎"}。

四、【投资策略】
{strategy_suggestion}。操作上{"关注热点板块龙头" if limit_up_count >= 20 else "以防御性品种为主" if limit_up_count < 10 else "高抛低吸为主"}，严格控制风险。

五、【风险提示】
{"注意追高风险，适度获利了结" if limit_up_count >= 50 else "市场分化加剧，注意个股风险" if limit_up_count >= 10 else "系统性调整风险，控制仓位"}。{announcement_summary}。

【数据来源】基于{date}A股市场涨停数据、板块表现、公告信息等真实数据分析。

风险提示：股市有风险，投资需谨慎。以上分析仅供参考，不构成投资建议。"""

            return summary

        except Exception as e:
            print(f"[错误] 生成详细fallback分析失败: {e}")
            return f"""【{report.get('date', '今日')} A股市场分析】

市场概况：基于当前数据分析，市场呈现结构性特征。

投资建议：
1. 关注主流热点的持续性
2. 重视公告类投资机会
3. 控制仓位风险
4. 等待明确方向信号

风险提示：数据获取异常，建议谨慎操作。股市有风险，投资需谨慎。"""

    def _get_hot_sectors_analysis(self, date: str, market_data: Dict) -> Dict:
        """获取热门板块分析"""
        try:
            # 直接使用advanced_client获取涨停数据生成热点
            trade_date = date.replace('-', '')
            limit_up = advanced_client.limit_list_d(trade_date=trade_date, limit_type='U')

            # 按行业分组生成热点
            hotspots = []
            if not limit_up.empty:
                industry_groups = limit_up.groupby('industry')
                for industry, group in industry_groups:
                    if len(group) >= 2:  # 至少2只股票
                        stocks = group['name'].tolist()[:5]
                        hotspots.append({
                            'title': industry,
                            '热度': len(group) * 10,  # 涨停数量作为热度
                            '相关股票': [{'name': s} for s in stocks]
                        })

            # 从market_data中获取真实涨停数据
            board_stats = {
                "limit_up": 0,
                "limit_down": 0,
                "bomb_board": 0,
                "first_board": 0,
                "continuous_board": 0,
                "max_continuous": 0,
                "board_success_rate": 0
            }

            # 从market_data的market_breadth中获取涨停数据
            market_breadth = market_data.get("market_breadth", {})
            board_stats["limit_up"] = market_breadth.get("limit_up", 0)
            board_stats["limit_down"] = market_breadth.get("limit_down", 0)

            # 构建热点概念列表
            hot_concepts = []

            if hotspots:
                for i, hotspot in enumerate(hotspots[:10]):  # 取前10个热点
                    hot_concepts.append({
                        "name": hotspot.get("title", f"热点{i+1}"),
                        "reason": f"热度评分: {hotspot.get('热度', 0)}，相关股票: {len(hotspot.get('相关股票', []))}只",
                        "change_pct": min(hotspot.get("热度", 0) / 10, 10)  # 转换为涨幅百分比
                    })

            return {
                "top_sectors": [],
                "board_statistics": board_stats,
                "hot_concepts": hot_concepts,
                "analysis_date": date
            }

        except Exception as e:
            print(f"[错误] 获取热门板块分析失败: {e}")
            return {
                "top_sectors": [],
                "board_statistics": {
                    "limit_up": 0,
                    "limit_down": 0,
                    "bomb_board": 0,
                    "first_board": 0,
                    "continuous_board": 0,
                    "max_continuous": 0,
                    "board_success_rate": 0
                },
                "hot_concepts": [],
                "analysis_date": date
            }

    def _get_unusual_stocks_analysis(self, date: str) -> Dict:
        """获取异动股票分析"""
        return {
            "limit_up": [],
            "dragon_tiger": [],
            "block_trade": []
        }

    def _get_capital_flow_analysis(self, date: str, market_data: Dict) -> Dict:
        """获取资金流向分析"""
        try:
            capital_flow = market_data.get("capital_flow", {})
            return {
                "main_fund": capital_flow
            }
        except Exception as e:
            print(f"[错误] 获取资金流向分析失败: {e}")
            return {"main_fund": {}}

    def _get_market_sentiment_analysis(self, date: str, market_data: Dict, ai_analysis: Dict) -> Dict:
        """获取市场情绪分析"""
        try:
            # 从AI分析中提取情绪数据
            sentiment = ai_analysis.get("sentiment", {})
            limit_analysis = sentiment.get("limit_analysis", {})

            # 直接从market_data中获取涨停数据，因为这是最可靠的
            market_breadth = market_data.get("market_breadth", {})
            limit_up = market_breadth.get("limit_up", 0)
            limit_down = market_breadth.get("limit_down", 0)

            return {
                "涨停数": limit_up,
                "跌停数": limit_down,
                "炸板率": 0,
                "连板数": 0,
                "最高连板": 0,
                "情绪指数": sentiment.get("emotion_score", 50),
                "情绪判断": sentiment.get("emotion_level", "中性")
            }
        except Exception as e:
            print(f"[错误] 获取市场情绪分析失败: {e}")
            return {
                "涨停数": 0,
                "跌停数": 0,
                "炸板率": 0,
                "连板数": 0,
                "最高连板": 0,
                "情绪指数": 50,
                "情绪判断": "中性"
            }

    def _generate_comprehensive_ai_summary(self, market_data: Dict, ai_analysis: Dict) -> str:
        """生成综合AI总结"""
        try:
            # 构建详细的市场数据供LLM分析
            detailed_prompt_data = self._build_detailed_market_prompt(market_data, ai_analysis)

            # 构建专业的晨报分析提示词
            comprehensive_prompt = f"""
请基于以下A股市场综合数据，生成一份专业的全市场分析报告，严格按照以下7个部分结构：

{detailed_prompt_data}

请生成一份详细的市场综合分析报告，包括：

一、【市场概况与情绪研判】
- 基于涨跌家数、涨停数据等指标，分析当前市场整体情绪状态
- 给出具体的情绪评级（1-10分）和详细理由
- 分析市场参与者情绪变化趋势

二、【资金流向与博弈分析】
- 详细分析北向资金、主力资金、融资融券等资金流向
- 解读资金流向背后的投资逻辑和市场预期
- 分析不同资金之间的博弈状况

三、【板块轮动与热点挖掘】
- 识别当前市场主流热点和潜在轮动机会
- 分析领涨板块的持续性和投资价值
- 提示板块轮动的时间窗口和操作策略

四、【技术面分析与趋势判断】
- 基于主要指数表现分析技术面强弱
- 判断短期和中期市场趋势方向
- 识别关键的技术支撑和压力位

五、【风险因素与预警提示】
- 识别当前市场面临的主要风险点
- 提供具体的风险防控建议
- 设定明确的风险预警指标

六、【投资策略与仓位建议】
- 基于市场状态给出具体的仓位配置建议（精确到百分比）
- 提供不同风险偏好的投资策略
- 明确操作的时间节点和条件

七、【后市展望与关键变量】
- 分析影响后市走势的关键变量
- 预测可能的市场演化路径
- 提示需要重点关注的时间点和事件

要求：
1. 分析必须具体量化，避免空洞表述
2. 每个结论都要有数据支撑
3. 提供可执行的投资建议
4. 总字数控制在800-1200字
5. 语言专业简洁，逻辑清晰
6. 即使数据不完整也要基于现有信息给出有价值的分析
"""

            if USE_LLM_FOR_MORNING:
                summary = summarize_morning(comprehensive_prompt)
                return summary
            else:
                # 生成基于真实数据的详细分析，即使没有LLM也能提供价值
                return self._generate_fallback_detailed_analysis(market_data, ai_analysis)

        except Exception as e:
            print(f"[错误] 生成综合AI总结失败: {e}")
            # 即使发生错误也要尝试提供有价值的基础分析
            return self._generate_fallback_detailed_analysis(market_data, ai_analysis)

    def _build_detailed_market_prompt(self, market_data: Dict, ai_analysis: Dict) -> str:
        """构建详细的市场数据提示供LLM分析"""
        try:
            prompt_parts = []

            # 1. 市场宽度数据
            market_breadth = market_data.get("market_breadth", {})
            if market_breadth:
                up_count = market_breadth.get("up_count", 0) or 0
                down_count = market_breadth.get("down_count", 0) or 0
                total_count = market_breadth.get("total_count", 1) or 1
                limit_up = market_breadth.get("limit_up", 0) or 0
                limit_down = market_breadth.get("limit_down", 0) or 0
                up_ratio = (up_count / total_count * 100) if total_count > 0 else 0

                prompt_parts.append(f"""
【市场宽度数据】
涨跌家数：{up_count}↑/{down_count}↓，涨跌比{up_ratio:.1f}%
涨停跌停：{limit_up}家涨停/{limit_down}家跌停
参与股票总数：{total_count}只""")

            # 2. 指数表现数据
            indices = market_data.get("indices", [])
            if indices:
                index_info = []
                for idx in indices[:5]:
                    if idx.get("pct_chg") is not None:
                        name = self._get_index_display_name(idx.get("ts_code", ""))
                        change = idx.get("pct_chg", 0)
                        close = idx.get("close", 0)
                        index_info.append(f"{name}：{close:.2f}（{change:+.2f}%）")

                if index_info:
                    prompt_parts.append(f"""
【主要指数表现】
{chr(10).join(index_info)}""")

            # 3. 板块轮动数据
            sectors = market_data.get("sectors", [])
            if sectors:
                # 找出涨幅前5和跌幅前5的板块
                rising_sectors = [s for s in sectors if s.get("pct_chg", 0) > 0][:5]
                falling_sectors = [s for s in sectors if s.get("pct_chg", 0) < 0][-5:]

                if rising_sectors:
                    rising_info = [f"{s.get('name', '未知')}（{s.get('pct_chg', 0):+.2f}%）" for s in rising_sectors]
                    prompt_parts.append(f"""
【领涨板块TOP5】
{chr(10).join(rising_info)}""")

                if falling_sectors:
                    falling_info = [f"{s.get('name', '未知')}（{s.get('pct_chg', 0):+.2f}%）" for s in falling_sectors]
                    prompt_parts.append(f"""
【领跌板块TOP5】
{chr(10).join(falling_info)}""")

            # 4. 资金流向数据
            capital_flow = market_data.get("capital_flow", {})
            if capital_flow:
                hsgt_net = capital_flow.get("hsgt_net_amount", 0)
                if hsgt_net is not None:
                    prompt_parts.append(f"""
【资金流向数据】
北向资金净流入：{hsgt_net:.2f}亿元""")

            # 5. AI分析结果
            if ai_analysis:
                sentiment = ai_analysis.get("sentiment", {})
                if sentiment and "emotion_score" in sentiment:
                    emotion_score = sentiment.get("emotion_score", 5)
                    emotion_level = sentiment.get("emotion_level", "中性")
                    prompt_parts.append(f"""
【市场情绪分析】
情绪评分：{emotion_score}/10分（{emotion_level}）""")

            # 6. 时间信息
            from datetime import datetime
            current_time = datetime.now().strftime("%Y年%m月%d日 %H:%M")
            prompt_parts.append(f"""
【分析时间】{current_time}""")

            return "\n".join(prompt_parts)

        except Exception as e:
            print(f"[错误] 构建市场数据提示失败: {e}")
            return "【数据获取异常】基础市场数据暂时不可用，将基于历史经验提供分析建议。"

    def _generate_fallback_detailed_analysis(self, market_data: Dict, ai_analysis: Dict) -> str:
        """生成基于真实数据的详细分析（作为LLM的后备方案）"""
        try:
            analysis_parts = []

            # 一、市场概况与情绪研判
            market_breadth = market_data.get("market_breadth", {})
            up_count = market_breadth.get("up_count", 0) or 0
            down_count = market_breadth.get("down_count", 0) or 0
            total_count = market_breadth.get("total_count", 1) or 1
            limit_up = market_breadth.get("limit_up", 0) or 0
            limit_down = market_breadth.get("limit_down", 0) or 0

            up_ratio = (up_count / total_count * 100) if total_count > 0 else 50

            emotion_analysis = self._analyze_market_emotion_level(up_ratio, limit_up, limit_down)
            analysis_parts.append(f"【市场概况与情绪研判】\n{emotion_analysis}")

            # 二、资金流向与博弈分析
            capital_analysis = self._analyze_capital_flow_details(market_data.get("capital_flow", {}))
            analysis_parts.append(f"【资金流向与博弈分析】\n{capital_analysis}")

            # 三、板块轮动与热点挖掘
            sector_analysis = self._analyze_sector_rotation_details(market_data.get("sectors", []))
            analysis_parts.append(f"【板块轮动与热点挖掘】\n{sector_analysis}")

            # 四、技术面分析与趋势判断
            technical_analysis = self._analyze_technical_trend(market_data.get("indices", []))
            analysis_parts.append(f"【技术面分析与趋势判断】\n{technical_analysis}")

            # 五、风险因素与预警提示
            risk_analysis = self._analyze_market_risks(market_data, ai_analysis)
            analysis_parts.append(f"【风险因素与预警提示】\n{risk_analysis}")

            # 六、投资策略与仓位建议
            strategy_analysis = self._generate_investment_strategy(up_ratio, limit_up, limit_down)
            analysis_parts.append(f"【投资策略与仓位建议】\n{strategy_analysis}")

            # 七、后市展望与关键变量
            outlook_analysis = self._generate_market_outlook(market_data)
            analysis_parts.append(f"【后市展望与关键变量】\n{outlook_analysis}")

            return "\n\n".join(analysis_parts)

        except Exception as e:
            print(f"[错误] 生成详细分析失败: {e}")
            return "【市场分析】由于数据异常，建议投资者保持谨慎，关注市场变化，适度控制仓位。"

    def _get_index_display_name(self, code: str) -> str:
        """获取指数显示名称"""
        name_map = {
            "000001.SH": "上证指数",
            "399001.SZ": "深证成指",
            "399006.SZ": "创业板指",
            "000300.SH": "沪深300",
            "000016.SH": "上证50",
            "399905.SZ": "中证500",
            "000688.SH": "科创50"
        }
        return name_map.get(code, code)

    def _analyze_market_emotion_level(self, up_ratio: float, limit_up: int, limit_down: int) -> str:
        """分析市场情绪水平"""
        if up_ratio >= 70 and limit_up >= 30:
            return f"市场情绪极度乐观，涨跌比达{up_ratio:.1f}%，{limit_up}家涨停，赚钱效应显著。情绪评级9/10分，建议适度获利了结。"
        elif up_ratio >= 60 and limit_up >= 15:
            return f"市场情绪偏暖，涨跌比{up_ratio:.1f}%，{limit_up}家涨停，多头占优势。情绪评级7/10分，可维持积极仓位。"
        elif up_ratio >= 50:
            return f"市场情绪中性偏强，涨跌比{up_ratio:.1f}%，{limit_up}家涨停。情绪评级6/10分，结构性机会为主。"
        elif up_ratio >= 40:
            return f"市场情绪偏谨慎，涨跌比{up_ratio:.1f}%，市场分化明显。情绪评级4/10分，操作难度加大。"
        else:
            return f"市场情绪低迷，涨跌比仅{up_ratio:.1f}%，{limit_down}家跌停。情绪评级2/10分，建议观望为主。"

    def _analyze_capital_flow_details(self, capital_flow: Dict) -> str:
        """分析资金流向详情"""
        hsgt_net = capital_flow.get("hsgt_net_amount", 0)
        if hsgt_net is None:
            return "北向资金数据暂缺，建议关注盘面资金流向变化，重点观察主力资金和两融余额变化。"
        elif hsgt_net > 100:
            return f"北向资金大幅净流入{hsgt_net:.1f}亿元，外资坚定看多A股，预示中长期配置价值凸显。建议关注外资重仓的消费、医药、科技龙头。"
        elif hsgt_net > 50:
            return f"北向资金净流入{hsgt_net:.1f}亿元，外资态度积极，增强市场信心。重点关注MSCI成分股和外资偏好板块。"
        elif hsgt_net > 0:
            return f"北向资金小幅净流入{hsgt_net:.1f}亿元，外资保持谨慎乐观，建议跟踪其配置方向。"
        elif hsgt_net > -50:
            return f"北向资金净流出{abs(hsgt_net):.1f}亿元，外资获利了结，需关注外资重仓股调整风险。"
        else:
            return f"北向资金大幅净流出{abs(hsgt_net):.1f}亿元，外资避险情绪升温，建议降低仓位，谨慎为主。"

    def _analyze_sector_rotation_details(self, sectors: List[Dict]) -> str:
        """分析板块轮动详情"""
        if not sectors:
            return "板块数据暂缺，建议重点关注政策导向和市场热点变化。"

        rising_sectors = [s for s in sectors if s.get("pct_chg", 0) > 3][:3]
        if rising_sectors:
            sector_names = [s.get("name", "未知") for s in rising_sectors]
            changes = [s.get("pct_chg", 0) for s in rising_sectors]
            sector_info = "、".join([f"{name}({change:+.1f}%)" for name, change in zip(sector_names, changes)])
            return f"市场热点集中在{sector_info}等板块，建议重点关注龙头股票。板块轮动活跃，短线操作机会较多。"
        else:
            return "板块表现分化，缺乏明显主线。建议等待新热点出现，或关注超跌反弹机会。"

    def _analyze_technical_trend(self, indices: List[Dict]) -> str:
        """分析技术面趋势"""
        if not indices:
            return "指数数据暂缺，建议关注主要指数技术走势和成交量变化。"

        main_indices = indices[:3]  # 主要看前3个指数
        avg_change = sum(idx.get("pct_chg", 0) for idx in main_indices) / len(main_indices) if main_indices else 0

        if avg_change > 1:
            return f"主要指数平均涨幅{avg_change:.2f}%，技术面偏强，短期有望延续上涨态势。建议关注突破形态的品种。"
        elif avg_change > 0:
            return f"主要指数平均涨幅{avg_change:.2f}%，技术面温和偏强，震荡上行格局。适合高抛低吸操作。"
        elif avg_change > -1:
            return f"主要指数平均跌幅{abs(avg_change):.2f}%，技术面偏弱，短期调整压力较大。建议控制仓位。"
        else:
            return f"主要指数平均跌幅{abs(avg_change):.2f}%，技术面走弱，需要等待企稳信号。建议观望为主。"

    def _analyze_market_risks(self, market_data: Dict, ai_analysis: Dict) -> str:
        """分析市场风险"""
        risks = []

        # 基于涨停数分析
        market_breadth = market_data.get("market_breadth", {})
        limit_up = market_breadth.get("limit_up", 0) or 0
        limit_down = market_breadth.get("limit_down", 0) or 0

        if limit_down > 30:
            risks.append(f"系统性风险：{limit_down}家跌停，市场恐慌情绪严重")
        elif limit_up > 100:
            risks.append(f"过热风险：{limit_up}家涨停，市场情绪过于亢奋，注意回调")

        # 基于资金流向分析风险
        capital_flow = market_data.get("capital_flow", {})
        hsgt_net = capital_flow.get("hsgt_net_amount", 0)
        if hsgt_net and hsgt_net < -100:
            risks.append("外资流出风险：北向资金大幅流出，需防范外资减仓冲击")

        if not risks:
            risks.append("当前市场风险可控，建议保持正常仓位配置")

        return "；".join(risks) + "。"

    def _generate_investment_strategy(self, up_ratio: float, limit_up: int, limit_down: int) -> str:
        """生成投资策略"""
        if up_ratio >= 65 and limit_up >= 20:
            return "激进策略：仓位可提升至70-80%，重点参与热点板块龙头股；稳健策略：维持50-60%仓位，关注业绩确定性品种；保守策略：30-40%仓位，以防御性品种为主。"
        elif up_ratio >= 50:
            return "激进策略：维持50-60%仓位，择优参与结构性机会；稳健策略：40-50%仓位，高抛低吸为主；保守策略：20-30%仓位，观望为主。"
        else:
            return "激进策略：降低至30-40%仓位，等待确定性机会；稳健策略：20-30%仓位，控制风险为主；保守策略：10-20%仓位或空仓观望。"

    def _generate_market_outlook(self, market_data: Dict) -> str:
        """生成后市展望"""
        return "后市关键变量：1）政策面动向和资金面变化；2）主要板块轮动节奏；3）外资配置方向调整。建议重点关注月末资金面、重要会议时间窗口以及业绩披露期的投资机会。"

    def _save_comprehensive_report(self, report: Dict) -> str:
        """保存综合市场报告"""
        try:
            filename = f"{report['date']}_comprehensive_market_professional_v2.json"
            filepath = os.path.join(self.cache_dir, filename)

            # 清理数据中的NaN值
            clean_report = clean_data_for_json(report)

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(clean_report, f, ensure_ascii=False, indent=2, cls=CustomJSONEncoder)

            print(f"[报告] 综合市场报告已保存到 {filepath}")
            return filepath
        except Exception as e:
            print(f"[错误] 保存综合市场报告失败: {e}")
            return ""

    def save_report(self, report: Dict) -> str:
        """保存报告到本地文件"""
        try:
            filename = f"{report['date']}_professional_morning_report_v3.json"
            filepath = os.path.join(self.cache_dir, filename)

            # 清理数据中的NaN值
            clean_report = clean_data_for_json(report)

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(clean_report, f, ensure_ascii=False, indent=2, cls=CustomJSONEncoder)

            print(f"[报告] 专业早报已保存到 {filepath}")
            return filepath
        except Exception as e:
            print(f"[错误] 保存报告失败: {e}")
            return ""


# 单例
_professional_generator_v2 = None

def get_professional_generator_v2() -> ProfessionalReportGeneratorV2:
    """获取专业报告生成器V2单例"""
    global _professional_generator_v2
    if _professional_generator_v2 is None:
        _professional_generator_v2 = ProfessionalReportGeneratorV2()
    return _professional_generator_v2
