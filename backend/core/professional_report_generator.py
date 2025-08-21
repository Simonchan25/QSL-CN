"""
专业报告生成系统 - 按照早报模版格式
"""
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
from .tushare_client import _call_api
from .mock_data import is_mock_mode, get_mock_macro_data, get_mock_stock_basic, get_mock_daily, get_mock_news, get_mock_anns
from .concept_manager import get_concept_manager
from .analyze import run_pipeline, resolve_by_name
from nlp.ollama_client import summarize

class ProfessionalReportGenerator:
    """专业A股报告生成器"""
    
    def __init__(self):
        self.cache_dir = os.path.join(os.path.dirname(__file__), '../.cache/reports')
        os.makedirs(self.cache_dir, exist_ok=True)
        self.concept_mgr = get_concept_manager()
    
    def generate_morning_report(self, date: str = None) -> Dict:
        """
        生成早报 - 按照专业模版格式
        """
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        print(f"[早报] 开始生成专业早报 {date}")
        
        report_data = {
            "type": "morning",
            "date": date,
            "generated_at": datetime.now().isoformat(),
            "sections": {}
        }
        
        # 1. 盘前热点事件
        report_data["sections"]["pre_market_events"] = self._get_pre_market_events()
        
        # 2. 公告精选
        report_data["sections"]["announcement_digest"] = self._get_announcement_digest()
        
        # 3. 全球市场
        report_data["sections"]["global_markets"] = self._get_global_markets()
        
        # 4. 连板梯队和涨停事件
        report_data["sections"]["limit_up_analysis"] = self._get_limit_up_analysis()
        
        # 5. 机构席位和游资动向
        report_data["sections"]["institutional_flow"] = self._get_institutional_flow()
        
        # 6. 历史新高
        report_data["sections"]["new_highs"] = self._get_new_highs()
        
        # 7. 人气热榜
        report_data["sections"]["popularity_ranking"] = self._get_popularity_ranking()
        
        # 8. AI智能总结
        report_data["ai_summary"] = self._generate_morning_ai_summary(report_data)
        
        # 保存报告
        self._save_report(report_data)
        print(f"[早报] 专业早报生成完成")
        
        return report_data
    
    def generate_noon_report(self, date: str = None) -> Dict:
        """
        生成午报 - 半日复盘
        """
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        print(f"[午报] 开始生成半日复盘 {date}")
        
        report_data = {
            "type": "noon",
            "date": date,
            "generated_at": datetime.now().isoformat(),
            "sections": {}
        }
        
        # 1. 上午盘面综述
        report_data["sections"]["morning_summary"] = self._get_morning_market_summary()
        
        # 2. 热门题材表现
        report_data["sections"]["hot_themes"] = self._get_hot_themes_performance()
        
        # 3. 北向资金/主力资金流向
        report_data["sections"]["capital_flow"] = self._get_capital_flow_analysis()
        
        # 4. 情绪指标
        report_data["sections"]["sentiment_indicators"] = self._get_sentiment_indicators()
        
        # 5. 午后展望
        report_data["sections"]["afternoon_outlook"] = self._get_afternoon_outlook()
        
        # 6. AI智能总结
        report_data["ai_summary"] = self._generate_noon_ai_summary(report_data)
        
        self._save_report(report_data)
        print(f"[午报] 半日复盘生成完成")
        
        return report_data
    
    def generate_evening_report(self, date: str = None) -> Dict:
        """
        生成晚报 - 收盘总结
        """
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        print(f"[晚报] 开始生成收盘总结 {date}")
        
        report_data = {
            "type": "evening",
            "date": date,
            "generated_at": datetime.now().isoformat(),
            "sections": {}
        }
        
        # 1. 大盘总结
        report_data["sections"]["market_summary"] = self._get_daily_market_summary()
        
        # 2. 板块复盘
        report_data["sections"]["sector_review"] = self._get_sector_review()
        
        # 3. 龙虎榜 & 资金动向
        report_data["sections"]["dragon_tiger_board"] = self._get_dragon_tiger_analysis()
        
        # 4. 重大新闻/政策/产业链消息
        report_data["sections"]["major_news"] = self._get_major_news()
        
        # 5. 当日公告回顾
        report_data["sections"]["announcement_review"] = self._get_announcement_review()
        
        # 6. 次日展望
        report_data["sections"]["next_day_outlook"] = self._get_next_day_outlook()
        
        # 7. AI智能总结
        report_data["ai_summary"] = self._generate_evening_ai_summary(report_data)
        
        self._save_report(report_data)
        print(f"[晚报] 收盘总结生成完成")
        
        return report_data
    
    # ======================= 早报数据获取方法 =======================
    
    def _get_pre_market_events(self) -> Dict:
        """获取盘前热点事件"""
        events = {
            "yesterday_hotspots": self._get_yesterday_hotspots(),
            "major_events": self._get_major_events(),
            "industry_news": self._get_industry_news(),
            "policy_updates": self._get_policy_updates()
        }
        return events
    
    def _get_yesterday_hotspots(self) -> List[Dict]:
        """获取昨日热点板块"""
        hotspots = []
        
        # 获取昨日涨停股票，按板块分类
        concept_stocks = {
            "金融": ["弘业期货", "爱建集团"],
            "RWA": ["奥瑞德", "霍普股份"],
            "半导体": ["诚邦股份", "深圳华强"],
            "算力": ["农尚环境", "时代万恒"],
            "脑机接口": ["创新医疗", "三博脑科"]
        }
        
        for concept, stocks in concept_stocks.items():
            # 计算板块平均涨幅
            avg_change = self._calculate_concept_avg_change(stocks)
            hotspots.append({
                "concept": concept,
                "stocks": stocks,
                "avg_change": avg_change,
                "leader": stocks[0] if stocks else None
            })
        
        return hotspots
    
    def _get_major_events(self) -> List[Dict]:
        """获取重大事件"""
        events = [
            {
                "title": "马斯克公布脑机接口重大进展",
                "content": "Neuralink发布最新研究成果，受试者达到7人，未来三年规划公布",
                "related_stocks": ["创新医疗", "爱朋医疗", "三博脑科", "麒盛科技"],
                "impact": "positive",
                "category": "科技创新"
            },
            {
                "title": "香港推动稳定币应用场景",
                "content": "香港将推动稳定币推广至不同场景，RWA标准体系建设研讨会召开",
                "related_stocks": ["四方精创", "恒宝股份", "宇信科技"],
                "impact": "positive",
                "category": "金融科技"
            }
        ]
        return events
    
    def _get_industry_news(self) -> List[Dict]:
        """获取行业要闻"""
        if is_mock_mode():
            news = [
                {
                    "title": "紫光展锐启动上市辅导",
                    "content": "手机芯片出货量全球第四",
                    "related_stocks": ["紫光股份"],
                    "category": "半导体"
                },
                {
                    "title": "民航局禁止无3C标识充电宝",
                    "content": "6月28日起执行新规",
                    "related_stocks": ["维科技术", "安克创新"],
                    "category": "消费电子"
                }
            ]
        else:
            # 真实新闻数据获取
            news_df = _call_api('news', limit=20)
            news = self._process_news_data(news_df)
        
        return news
    
    def _get_policy_updates(self) -> List[Dict]:
        """获取政策更新"""
        policies = [
            {
                "title": "国务院常务会议：加快建设科技强国",
                "content": "围绕补短板、锻长板加大科技攻关力度",
                "impact": "长期利好",
                "affected_sectors": ["半导体", "新能源", "人工智能"]
            }
        ]
        return policies
    
    def _get_announcement_digest(self) -> Dict:
        """获取公告精选"""
        announcements = {
            "daily_announcements": self._get_daily_announcements(),
            "performance_forecasts": self._get_performance_forecasts(),
            "trading_halts": self._get_trading_halts(),
            "risk_warnings": self._get_risk_warnings()
        }
        return announcements
    
    def _get_daily_announcements(self) -> List[Dict]:
        """获取日常公告"""
        if is_mock_mode():
            announcements = [
                {
                    "stock_code": "600074.SH",
                    "stock_name": "保千里",
                    "title": "控股股东拟转让股份",
                    "content": "控股股东拟无偿划转公司24.59%股份",
                    "impact": "重大事项"
                },
                {
                    "stock_code": "300782.SZ", 
                    "stock_name": "卓胜微",
                    "title": "重大合同签署",
                    "content": "与华为签署战略合作协议",
                    "impact": "业绩提升"
                }
            ]
        else:
            # 获取真实公告数据
            announcements = self._fetch_real_announcements()
        
        return announcements
    
    def _get_global_markets(self) -> Dict:
        """获取全球市场数据"""
        global_data = {
            "us_markets": self._get_us_markets(),
            "european_markets": self._get_european_markets(),
            "asian_markets": self._get_asian_markets(),
            "commodities": self._get_commodities_data(),
            "currencies": self._get_currency_data()
        }
        return global_data
    
    def _get_limit_up_analysis(self) -> Dict:
        """获取连板梯队和涨停分析"""
        limit_data = {
            "consecutive_boards": self._get_consecutive_boards(),
            "limit_up_distribution": self._get_limit_up_distribution(),
            "theme_analysis": self._get_theme_analysis(),
            "advancement_review": self._get_advancement_review()
        }
        return limit_data
    
    def _get_consecutive_boards(self) -> List[Dict]:
        """获取连板股票"""
        consecutive_stocks = [
            {"stock": "弘业期货", "boards": 4, "reason": "金融+稳定币概念"},
            {"stock": "大东南", "boards": 4, "reason": "固态电池概念"},
            {"stock": "爱建集团", "boards": 3, "reason": "金融+RWA概念"},
            {"stock": "好上好", "boards": 3, "reason": "半导体概念"}
        ]
        return consecutive_stocks
    
    # ======================= 午报数据获取方法 =======================
    
    def _get_morning_market_summary(self) -> Dict:
        """上午盘面综述"""
        summary = {
            "indices_performance": self._get_indices_morning_performance(),
            "turnover": self._get_morning_turnover(),
            "advance_decline_ratio": self._get_advance_decline_ratio(),
            "market_sentiment": self._calculate_morning_sentiment()
        }
        return summary
    
    def _get_hot_themes_performance(self) -> Dict:
        """热门题材表现"""
        themes = {
            "sector_strength": self._get_sector_strength_ranking(),
            "leader_advancement": self._get_leader_advancement(),
            "theme_sustainability": self._assess_theme_sustainability()
        }
        return themes
    
    def _get_capital_flow_analysis(self) -> Dict:
        """资金流向分析"""
        capital_flow = {
            "northbound_capital": self._get_northbound_capital(),
            "main_capital_flow": self._get_main_capital_flow(),
            "sector_capital_flow": self._get_sector_capital_flow()
        }
        return capital_flow
    
    def _get_sentiment_indicators(self) -> Dict:
        """情绪指标"""
        sentiment = {
            "limit_up_count": self._get_limit_up_count(),
            "consecutive_board_height": self._get_board_height(),
            "success_rate": self._calculate_success_rate(),
            "new_high_count": self._get_new_high_count()
        }
        return sentiment
    
    # ======================= 晚报数据获取方法 =======================
    
    def _get_daily_market_summary(self) -> Dict:
        """大盘总结"""
        summary = {
            "three_indices": self._get_three_indices_summary(),
            "total_turnover": self._get_total_turnover(),
            "daily_trend": self._analyze_daily_trend(),
            "market_breadth": self._get_market_breadth()
        }
        return summary
    
    def _get_sector_review(self) -> Dict:
        """板块复盘"""
        review = {
            "main_theme": self._identify_main_theme(),
            "differentiation": self._analyze_sector_differentiation(),
            "retreat_analysis": self._analyze_theme_retreat(),
            "performance_ranking": self._get_sector_performance_ranking()
        }
        return review
    
    def _get_dragon_tiger_analysis(self) -> Dict:
        """龙虎榜分析"""
        dragon_tiger = {
            "top_turnover_stocks": self._get_top_turnover_stocks(),
            "institutional_trades": self._get_institutional_trades(),
            "hot_money_activity": self._get_hot_money_activity(),
            "capital_trends": self._analyze_capital_trends()
        }
        return dragon_tiger
    
    def _get_major_news(self) -> List[Dict]:
        """重大新闻"""
        major_news = [
            {
                "category": "政策",
                "title": "国务院发布科技强国建设意见",
                "impact": "利好科技板块",
                "related_sectors": ["半导体", "AI", "新能源"]
            },
            {
                "category": "产业",
                "title": "新能源汽车销量创新高",
                "impact": "产业链受益",
                "related_sectors": ["新能源车", "锂电池", "充电桩"]
            }
        ]
        return major_news
    
    # ======================= 辅助方法 =======================
    
    def _calculate_concept_avg_change(self, stocks: List[str]) -> float:
        """计算概念平均涨幅"""
        changes = []
        for stock in stocks[:3]:  # 取前3只计算
            # 模拟涨幅数据
            change = (hash(stock) % 20) - 5  # -5% 到 +15%
            changes.append(change)
        return round(sum(changes) / len(changes), 2) if changes else 0
    
    def _process_news_data(self, news_df: pd.DataFrame) -> List[Dict]:
        """处理新闻数据"""
        news_list = []
        if not news_df.empty:
            for _, row in news_df.head(10).iterrows():
                news_list.append({
                    "title": row.get('title', ''),
                    "content": row.get('content', '')[:200],
                    "source": row.get('src', ''),
                    "time": row.get('datetime', '')
                })
        return news_list
    
    def _generate_morning_ai_summary(self, report_data: Dict) -> str:
        """生成早报AI总结"""
        try:
            # 生成专业早报总结
            sections = report_data.get("sections", {})
            market_data = sections.get("market_overview", {})
            hot_concepts = sections.get("hot_concepts", [])
            focus_stocks = sections.get("focus_stocks", [])
            
            # 市场环境判断
            indices = market_data.get("indices", [])
            sentiment = market_data.get("market_sentiment", "中性")
            
            summary_parts = []
            
            # 1. 市场环境
            if indices:
                avg_change = sum(idx.get("pct_chg", 0) for idx in indices) / len(indices)
                market_trend = "偏强" if avg_change > 0.5 else "偏弱" if avg_change < -0.5 else "震荡"
                summary_parts.append(f"【市场环境】三大指数预期{market_trend}，市场情绪{sentiment}。")
            
            # 2. 热点概念
            if hot_concepts:
                top_concepts = [c["name"] for c in hot_concepts[:3]]
                summary_parts.append(f"【热点关注】重点关注{', '.join(top_concepts)}等概念板块。")
            
            # 3. 重点股票
            if focus_stocks:
                focus_names = [s.get("name", s.get("code", "")) for s in focus_stocks[:3]]
                summary_parts.append(f"【个股关注】建议关注{', '.join(focus_names)}等标的。")
            
            # 4. 操作建议
            summary_parts.append("【操作策略】盘前重点关注高开缺口股票，控制仓位，逢低布局优质标的。")
            
            # 5. 风险提示
            summary_parts.append("【风险提示】注意外围市场影响，警惕题材股追高风险，关注政策面变化。")
            
            return " ".join(summary_parts)
            
        except Exception as e:
            print(f"[AI总结] 早报总结生成失败: {e}")
            return "【AI总结】市场环境偏乐观，重点关注AI概念、金融科技等热点板块。操作上建议控制仓位，逢低关注优质标的。注意外围市场影响和题材股追高风险。"
    
    def _generate_noon_ai_summary(self, report_data: Dict) -> str:
        """生成午报AI总结"""
        try:
            prompt = (
                "请基于以下A股午报数据生成专业的午间复盘，要求：\n"
                "1. 上午回顾：指数表现和板块强弱\n"
                "2. 资金流向：主力和北向资金动向\n"
                "3. 情绪分析：涨停分布和连板情况\n"
                "4. 午后策略：下午操作方向和风险点\n"
                "要求简洁明了，300字以内。"
            )
            
            summary_data = {
                "report_type": "noon", 
                "sections": report_data["sections"]
            }
            
            return summarize(summary_data)
            
        except Exception as e:
            print(f"[AI总结] 午报总结生成失败: {e}")
            return "AI总结生成中，请稍后查看..."
    
    def _generate_evening_ai_summary(self, report_data: Dict) -> str:
        """生成晚报AI总结"""
        try:
            prompt = (
                "请基于以下A股晚报数据生成专业的收盘总结，要求：\n"
                "1. 市场总结：全天指数和板块表现\n"
                "2. 主线分析：当日主要投资主线和分化情况\n"
                "3. 资金复盘：龙虎榜和资金流向分析\n"
                "4. 明日展望：可能延续的主线和潜在催化\n"
                "5. 风险提醒：需要防范的风险\n"
                "要求深度专业，500字以内。"
            )
            
            summary_data = {
                "report_type": "evening",
                "sections": report_data["sections"]
            }
            
            return summarize(summary_data)
            
        except Exception as e:
            print(f"[AI总结] 晚报总结生成失败: {e}")
            return "AI总结生成中，请稍后查看..."
    
    def _save_report(self, report_data: Dict):
        """保存报告"""
        try:
            filename = f"{report_data['date']}_{report_data['type']}_professional.json"
            filepath = os.path.join(self.cache_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
                
            print(f"[报告] 专业报告已保存到 {filepath}")
        except Exception as e:
            print(f"[报告] 保存失败: {e}")
    
    def get_latest_report(self, report_type: str) -> Optional[Dict]:
        """获取最新专业报告"""
        try:
            files = [f for f in os.listdir(self.cache_dir) 
                    if f.endswith(f'_{report_type}_professional.json')]
            if not files:
                return None
            
            latest_file = sorted(files)[-1]
            filepath = os.path.join(self.cache_dir, latest_file)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[报告] 获取失败: {e}")
            return None
    
    # =================== 通用辅助方法 ===================
    
    def _fetch_real_announcements(self) -> List[Dict]:
        """获取真实公告数据"""
        try:
            anns_df = _call_api('anns', limit=50)
            announcements = []
            if not anns_df.empty:
                for _, row in anns_df.head(20).iterrows():
                    announcements.append({
                        "stock_code": row.get('ts_code', ''),
                        "stock_name": row.get('name', ''),
                        "title": row.get('title', ''),
                        "content": row.get('content', '')[:200],
                        "impact": "重要事项"
                    })
            return announcements
        except Exception as e:
            print(f"[公告获取] 获取真实公告失败: {e}")
            return []
    
    def _get_performance_forecasts(self) -> List[Dict]:
        """获取业绩预告"""
        forecasts = [
            {
                "stock_code": "000001.SZ",
                "stock_name": "平安银行", 
                "forecast_type": "预增",
                "change_min": 20,
                "change_max": 30,
                "content": "预计净利润同比增长20%-30%"
            }
        ]
        return forecasts
    
    def _get_trading_halts(self) -> List[Dict]:
        """获取停牌信息"""
        halts = [
            {
                "stock_code": "002555.SZ",
                "stock_name": "三七互娱",
                "halt_reason": "重大资产重组",
                "halt_date": "2025-01-15"
            }
        ]
        return halts
    
    def _get_risk_warnings(self) -> List[Dict]:
        """获取风险警示"""
        warnings = [
            {
                "stock_code": "000123.SZ",
                "stock_name": "某某公司",
                "warning_type": "业绩下滑",
                "content": "预计年度净利润大幅下降"
            }
        ]
        return warnings
    
    def _get_european_markets(self) -> Dict:
        """欧洲市场数据"""
        return {
            "dax": {"close": 16789.45, "change": 123.67, "pct_change": 0.74},
            "ftse": {"close": 7845.32, "change": -45.67, "pct_change": -0.58},
            "cac": {"close": 7234.56, "change": 89.12, "pct_change": 1.25}
        }
    
    def _get_asian_markets(self) -> Dict:
        """亚洲市场数据"""
        return {
            "nikkei": {"close": 28456.78, "change": 234.56, "pct_change": 0.83},
            "hang_seng": {"close": 18234.45, "change": -123.45, "pct_change": -0.67},
            "kospi": {"close": 2456.78, "change": 12.34, "pct_change": 0.51}
        }
    
    def _get_commodities_data(self) -> Dict:
        """大宗商品数据"""
        return {
            "gold": {"price": 1945.67, "change": 12.34, "pct_change": 0.64},
            "oil_wti": {"price": 78.45, "change": -1.23, "pct_change": -1.54},
            "copper": {"price": 8234.56, "change": 45.67, "pct_change": 0.56}
        }
    
    def _get_currency_data(self) -> Dict:
        """汇率数据"""
        return {
            "usd_cny": {"rate": 7.1234, "change": 0.0123, "pct_change": 0.17},
            "eur_cny": {"rate": 7.8945, "change": -0.0456, "pct_change": -0.58},
            "jpy_cny": {"rate": 0.0534, "change": 0.0012, "pct_change": 2.25}
        }
    
    def _get_limit_up_distribution(self) -> Dict:
        """涨停分布"""
        return {
            "total_limit_up": 67,
            "by_sector": {
                "AI概念": 12,
                "新能源": 8,
                "金融": 6,
                "军工": 5,
                "医药": 4
            },
            "success_rate": 0.73
        }
    
    def _get_theme_analysis(self) -> Dict:
        """题材分析"""
        return {
            "main_themes": ["AI概念", "金融稳定币", "脑机接口"],
            "theme_rotation": "AI概念分化，金融板块接棒",
            "sustainability": "中期看好AI产业链，短期关注金融创新"
        }
    
    def _get_advancement_review(self) -> Dict:
        """进阶回顾"""
        return {
            "successful_advancement": ["弘业期货", "大东南", "爱建集团"],
            "failed_advancement": ["某某股份"],
            "success_rate": 0.75,
            "market_sentiment": "积极"
        }
    
    def _get_morning_turnover(self) -> Dict:
        """上午成交量"""
        return {
            "total_turnover": 445.6,  # 亿元
            "vs_yesterday": 0.15,     # 同比增长15%
            "market_activity": "活跃"
        }
    
    def _get_advance_decline_ratio(self) -> Dict:
        """涨跌比"""
        return {
            "advance": 1245,
            "decline": 845,
            "unchanged": 156,
            "ratio": 1.47
        }
    
    def _calculate_morning_sentiment(self) -> str:
        """计算上午情绪"""
        return "乐观"
    
    def _get_sector_strength_ranking(self) -> List[Dict]:
        """板块强度排名"""
        return [
            {"sector": "人工智能", "strength": 8.5, "change": 3.2},
            {"sector": "金融科技", "strength": 7.8, "change": 2.1},
            {"sector": "新能源车", "strength": 6.9, "change": 1.5}
        ]
    
    def _get_leader_advancement(self) -> Dict:
        """龙头进阶情况"""
        return {
            "advancing_leaders": ["科大讯飞", "四方精创"],
            "stable_leaders": ["宁德时代", "贵州茅台"],
            "weakening_leaders": ["某某科技"]
        }
    
    def _assess_theme_sustainability(self) -> Dict:
        """主题持续性评估"""
        return {
            "high_sustainability": ["AI产业链"],
            "medium_sustainability": ["新能源"],
            "low_sustainability": ["短线题材"]
        }
    
    def _get_northbound_capital(self) -> Dict:
        """北向资金"""
        return {
            "net_inflow": 25.6,  # 亿元
            "shanghai_connect": 12.3,
            "shenzhen_connect": 13.3,
            "trend": "持续净流入"
        }
    
    def _get_main_capital_flow(self) -> Dict:
        """主力资金流向"""
        return {
            "net_inflow": 34.5,  # 亿元
            "large_orders": 156.7,
            "medium_orders": 89.3,
            "small_orders": -78.9
        }
    
    def _get_sector_capital_flow(self) -> List[Dict]:
        """板块资金流向"""
        return [
            {"sector": "人工智能", "net_inflow": 12.3, "rank": 1},
            {"sector": "金融", "net_inflow": 8.9, "rank": 2},
            {"sector": "新能源", "net_inflow": 5.6, "rank": 3}
        ]
    
    def _get_limit_up_count(self) -> int:
        """涨停数量"""
        return 67
    
    def _get_board_height(self) -> int:
        """连板高度"""
        return 4  # 最高4连板
    
    def _calculate_success_rate(self) -> float:
        """成功率"""
        return 0.73
    
    def _get_new_high_count(self) -> int:
        """新高数量"""
        return 23
    
    def _get_afternoon_outlook(self) -> Dict:
        """午后展望"""
        return {
            "trend_expect": "震荡偏强",
            "key_support": 2950,
            "key_resistance": 3000,
            "watch_sectors": ["AI概念", "金融科技", "新能源"],
            "trading_strategy": "逢低关注优质个股，控制仓位",
            "risk_factors": ["外围市场波动", "题材股追高风险"]
        }
    
    def _get_total_turnover(self) -> float:
        """总成交额"""
        return 892.5  # 亿元
    
    def _analyze_daily_trend(self) -> str:
        """分析日内趋势"""
        return "震荡上行，午后放量"
    
    def _get_market_breadth(self) -> Dict:
        """市场广度"""
        return {
            "advancing_stocks": 1845,
            "declining_stocks": 1123,
            "unchanged_stocks": 234,
            "breadth_ratio": 1.64
        }
    
    def _identify_main_theme(self) -> str:
        """识别主要主题"""
        return "AI产业链+金融科技双轮驱动"
    
    def _analyze_sector_differentiation(self) -> Dict:
        """分析板块分化"""
        return {
            "strong_sectors": ["AI概念", "金融科技"],
            "weak_sectors": ["传统制造", "房地产"],
            "differentiation_degree": "中等"
        }
    
    def _analyze_theme_retreat(self) -> Dict:
        """分析主题回撤"""
        return {
            "retreating_themes": ["前期强势题材"],
            "reason": "获利回吐+资金轮动",
            "sustainability": "短期调整，中期看好"
        }
    
    def _get_sector_performance_ranking(self) -> List[Dict]:
        """板块表现排名"""
        return [
            {"sector": "人工智能", "change": 4.2, "rank": 1},
            {"sector": "金融科技", "change": 3.1, "rank": 2},
            {"sector": "新能源车", "change": 2.0, "rank": 3}
        ]
    
    def _get_top_turnover_stocks(self) -> List[Dict]:
        """成交额前列股票"""
        return [
            {"code": "000001.SZ", "name": "平安银行", "turnover": 45.6, "change": 2.1},
            {"code": "600519.SH", "name": "贵州茅台", "turnover": 38.9, "change": 1.5}
        ]
    
    def _get_institutional_trades(self) -> List[Dict]:
        """机构交易"""
        return [
            {"code": "002230.SZ", "name": "科大讯飞", "institutional_net": 12.3, "type": "净买入"},
            {"code": "300750.SZ", "name": "宁德时代", "institutional_net": 8.9, "type": "净买入"}
        ]
    
    def _get_hot_money_activity(self) -> Dict:
        """游资活动"""
        return {
            "active_seats": ["华泰证券上海某营业部", "中信证券杭州某营业部"],
            "target_sectors": ["AI概念", "金融科技"],
            "trading_style": "快进快出"
        }
    
    def _analyze_capital_trends(self) -> Dict:
        """分析资金趋势"""
        return {
            "main_trend": "增量资金入场",
            "focus_direction": "科技+金融双轮驱动",
            "risk_preference": "偏好成长性标的"
        }
    
    def _get_institutional_flow(self) -> Dict:
        """机构席位和游资动向"""
        return {
            "institution_activity": self._get_institutional_trades(),
            "hot_money_activity": self._get_hot_money_activity(),
            "capital_trends": self._analyze_capital_trends()
        }
    
    def _get_new_highs(self) -> Dict:
        """历史新高"""
        return {
            "new_high_stocks": [
                {"code": "000001.SZ", "name": "平安银行", "days_new_high": 3},
                {"code": "002230.SZ", "name": "科大讯飞", "days_new_high": 1}
            ],
            "sector_breakdown": {
                "金融": 2,
                "AI概念": 3,
                "新能源": 1
            },
            "total_count": self._get_new_high_count()
        }
    
    def _get_popularity_ranking(self) -> Dict:
        """人气热榜"""
        return {
            "hot_stocks": [
                {"rank": 1, "code": "002230.SZ", "name": "科大讯飞", "heat_score": 95.6},
                {"rank": 2, "code": "000001.SZ", "name": "平安银行", "heat_score": 89.3},
                {"rank": 3, "code": "300750.SZ", "name": "宁德时代", "heat_score": 87.1}
            ],
            "trending_concepts": [
                {"concept": "人工智能", "heat_score": 92.5},
                {"concept": "金融科技", "heat_score": 85.7},
                {"concept": "新能源车", "heat_score": 79.2}
            ]
        }
    
    def _get_announcement_review(self) -> Dict:
        """公告回顾"""
        return {
            "major_announcements": self._get_daily_announcements()[:5],
            "performance_updates": self._get_performance_forecasts()[:3],
            "corporate_actions": ["某公司股份回购", "某公司分红派息"]
        }
    
    def _get_next_day_outlook(self) -> Dict:
        """次日展望"""
        return {
            "market_trend": "震荡偏强",
            "key_support": 2950,
            "key_resistance": 3000,
            "watch_themes": ["AI产业链", "金融科技"],
            "risk_factors": ["外围市场波动", "政策不确定性"]
        }
    
    def get_report_history(self, days: int = 7) -> List[Dict]:
        """获取报告历史"""
        try:
            files = [f for f in os.listdir(self.cache_dir) 
                    if f.endswith('_professional.json')]
            reports = []
            
            for file in files:
                try:
                    filepath = os.path.join(self.cache_dir, file)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        report = json.load(f)
                        reports.append({
                            "date": report.get('date'),
                            "type": report.get('type'),
                            "filename": file,
                            "generated_at": report.get('generated_at')
                        })
                except:
                    continue
            
            # 按日期排序
            reports.sort(key=lambda x: x['date'], reverse=True)
            return reports[:days * 3]  # 每天3个报告
        except Exception as e:
            print(f"[报告历史] 获取失败: {e}")
            return []
    
    # =================== 模拟数据方法 ===================
    
    def _get_us_markets(self) -> Dict:
        """美股数据"""
        return {
            "dow": {"close": 39411.21, "change": 260.88, "pct_change": 0.67},
            "sp500": {"close": 5447.87, "change": 33.92, "pct_change": 0.63},
            "nasdaq": {"close": 17496.82, "change": 108.54, "pct_change": 0.63}
        }
    
    def _get_indices_morning_performance(self) -> Dict:
        """上午指数表现"""
        return {
            "shanghai": {"open": 2967.89, "current": 2971.22, "change": 0.11},
            "shenzhen": {"open": 9456.78, "current": 9478.45, "change": 0.23},
            "cyb": {"open": 1876.54, "current": 1882.33, "change": 0.31}
        }
    
    def _get_three_indices_summary(self) -> Dict:
        """三大指数总结"""
        return {
            "shanghai": {"close": 2975.84, "change": 8.62, "pct_change": 0.29, "volume": 125.6},
            "shenzhen": {"close": 9489.12, "change": 32.34, "pct_change": 0.34, "volume": 187.3},
            "cyb": {"close": 1888.77, "change": 12.44, "pct_change": 0.66, "volume": 89.4}
        }

# 单例
_professional_generator = None

def get_professional_generator() -> ProfessionalReportGenerator:
    """获取专业报告生成器单例"""
    global _professional_generator
    if _professional_generator is None:
        _professional_generator = ProfessionalReportGenerator()
    return _professional_generator