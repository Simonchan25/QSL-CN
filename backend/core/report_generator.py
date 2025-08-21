"""
自动报告生成系统 - 早报、午报、晚报
"""
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
from .tushare_client import _call_api
from .mock_data import is_mock_mode, get_mock_macro_data, get_mock_stock_basic, get_mock_daily
from .concept_manager import get_concept_manager
from .analyze import run_pipeline, resolve_by_name
from nlp.ollama_client import summarize

class ReportGenerator:
    """报告生成器"""
    
    def __init__(self):
        self.cache_dir = os.path.join(os.path.dirname(__file__), '../.cache/reports')
        os.makedirs(self.cache_dir, exist_ok=True)
        self.concept_mgr = get_concept_manager()
    
    def generate_morning_report(self, date: str = None) -> Dict:
        """
        生成早报 (08:30)
        内容：市场开盘前瞻、宏观数据、热点概念、重点关注股票
        """
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        print(f"[早报] 开始生成 {date} 早报")
        
        # 1. 市场概况
        market_overview = self._get_market_overview()
        
        # 2. 宏观数据
        macro_data = self._get_macro_summary()
        
        # 3. 热点概念
        hot_concepts = self._get_hot_concepts()
        
        # 4. 重点关注股票
        focus_stocks = self._get_focus_stocks("morning")
        
        # 5. 今日看点
        today_highlights = self._get_today_highlights()
        
        # 6. 风险提示
        risk_alerts = self._get_risk_alerts()
        
        report_data = {
            "type": "morning",
            "date": date,
            "generated_at": datetime.now().isoformat(),
            "sections": {
                "market_overview": market_overview,
                "macro_data": macro_data,
                "hot_concepts": hot_concepts,
                "focus_stocks": focus_stocks,
                "today_highlights": today_highlights,
                "risk_alerts": risk_alerts
            }
        }
        
        # 7. AI总结
        report_data["ai_summary"] = self._generate_ai_summary(report_data, "morning")
        
        # 保存报告
        self._save_report(report_data)
        print(f"[早报] 生成完成")
        
        return report_data
    
    def generate_noon_report(self, date: str = None) -> Dict:
        """
        生成午报 (12:00)
        内容：上午盘面回顾、资金流向、涨跌停分析、下午展望
        """
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        print(f"[午报] 开始生成 {date} 午报")
        
        # 1. 上午盘面回顾
        morning_review = self._get_morning_review()
        
        # 2. 资金流向分析
        fund_flow = self._get_fund_flow_analysis()
        
        # 3. 涨跌停分析
        limit_analysis = self._get_limit_analysis()
        
        # 4. 板块表现
        sector_performance = self._get_sector_performance()
        
        # 5. 下午预期
        afternoon_outlook = self._get_afternoon_outlook()
        
        report_data = {
            "type": "noon",
            "date": date,
            "generated_at": datetime.now().isoformat(),
            "sections": {
                "morning_review": morning_review,
                "fund_flow": fund_flow,
                "limit_analysis": limit_analysis,
                "sector_performance": sector_performance,
                "afternoon_outlook": afternoon_outlook
            }
        }
        
        # AI总结
        report_data["ai_summary"] = self._generate_ai_summary(report_data, "noon")
        
        self._save_report(report_data)
        print(f"[午报] 生成完成")
        
        return report_data
    
    def generate_evening_report(self, date: str = None) -> Dict:
        """
        生成晚报 (18:00)
        内容：全天总结、个股复盘、明日策略、风险预警
        """
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        print(f"[晚报] 开始生成 {date} 晚报")
        
        # 1. 全天市场总结
        daily_summary = self._get_daily_summary()
        
        # 2. 个股复盘
        stock_review = self._get_stock_review()
        
        # 3. 资金流向总结
        fund_summary = self._get_fund_summary()
        
        # 4. 热点板块回顾
        sector_review = self._get_sector_review()
        
        # 5. 明日策略
        tomorrow_strategy = self._get_tomorrow_strategy()
        
        # 6. 风险预警
        risk_warning = self._get_risk_warning()
        
        report_data = {
            "type": "evening",
            "date": date,
            "generated_at": datetime.now().isoformat(),
            "sections": {
                "daily_summary": daily_summary,
                "stock_review": stock_review,
                "fund_summary": fund_summary,
                "sector_review": sector_review,
                "tomorrow_strategy": tomorrow_strategy,
                "risk_warning": risk_warning
            }
        }
        
        # AI总结
        report_data["ai_summary"] = self._generate_ai_summary(report_data, "evening")
        
        self._save_report(report_data)
        print(f"[晚报] 生成完成")
        
        return report_data
    
    def _get_market_overview(self) -> Dict:
        """获取市场概况"""
        try:
            # 获取主要指数
            indices = ["000001.SH", "399001.SZ", "399006.SZ"]  # 上证、深证、创业板
            index_data = []
            
            for index_code in indices:
                try:
                    if is_mock_mode():
                        # 模拟数据
                        data = {
                            "name": {"000001.SH": "上证指数", "399001.SZ": "深证成指", "399006.SZ": "创业板指"}[index_code],
                            "close": 3200 + (hash(index_code) % 500),
                            "pct_chg": (hash(index_code) % 400 - 200) / 100,
                            "volume": 100000000 + (hash(index_code) % 50000000)
                        }
                    else:
                        # 真实数据
                        df = _call_api('index_daily', ts_code=index_code, limit=1)
                        if not df.empty:
                            data = {
                                "name": index_code,
                                "close": df.iloc[0]['close'],
                                "pct_chg": df.iloc[0]['pct_chg'],
                                "volume": df.iloc[0]['vol']
                            }
                        else:
                            continue
                    
                    index_data.append(data)
                except Exception as e:
                    print(f"[市场概况] 获取{index_code}失败: {e}")
            
            return {
                "indices": index_data,
                "market_sentiment": self._calculate_market_sentiment(index_data),
                "trading_volume": sum(d.get('volume', 0) for d in index_data)
            }
        except Exception as e:
            print(f"[市场概况] 获取失败: {e}")
            return {"error": str(e)}
    
    def _calculate_market_sentiment(self, index_data: List[Dict]) -> str:
        """计算市场情绪"""
        if not index_data:
            return "中性"
        
        avg_change = sum(d.get('pct_chg', 0) for d in index_data) / len(index_data)
        
        if avg_change > 1:
            return "乐观"
        elif avg_change > 0.5:
            return "偏乐观"
        elif avg_change > -0.5:
            return "中性"
        elif avg_change > -1:
            return "偏悲观"
        else:
            return "悲观"
    
    def _get_macro_summary(self) -> Dict:
        """获取宏观数据摘要"""
        try:
            if is_mock_mode():
                macro_data = get_mock_macro_data()
                return {
                    "cpi": macro_data["cpi"].iloc[0].to_dict() if not macro_data["cpi"].empty else {},
                    "pmi": macro_data["pmi"].iloc[0].to_dict() if not macro_data["pmi"].empty else {},
                    "m2": macro_data["money_supply"].iloc[0].to_dict() if not macro_data["money_supply"].empty else {},
                    "shibor": macro_data["shibor"].iloc[0].to_dict() if not macro_data["shibor"].empty else {}
                }
            else:
                # 真实数据
                cpi_df = _call_api('cn_cpi', limit=1)
                pmi_df = _call_api('cn_pmi', limit=1)
                m2_df = _call_api('cn_m', limit=1)
                shibor_df = _call_api('shibor', limit=1)
                
                return {
                    "cpi": cpi_df.iloc[0].to_dict() if not cpi_df.empty else {},
                    "pmi": pmi_df.iloc[0].to_dict() if not pmi_df.empty else {},
                    "m2": m2_df.iloc[0].to_dict() if not m2_df.empty else {},
                    "shibor": shibor_df.iloc[0].to_dict() if not shibor_df.empty else {}
                }
        except Exception as e:
            print(f"[宏观数据] 获取失败: {e}")
            return {"error": str(e)}
    
    def _get_hot_concepts(self) -> List[Dict]:
        """获取热点概念"""
        try:
            hot_concepts = self.concept_mgr.get_hot_concepts(limit=5)
            
            # 为每个概念计算平均涨跌幅
            for concept in hot_concepts:
                concept_stocks = self.concept_mgr.find_concept_stocks(concept['name'])
                if concept_stocks:
                    # 取第一个匹配的概念
                    stocks = list(concept_stocks.values())[0][:10]  # 取前10只
                    avg_change = self._calculate_avg_change(stocks)
                    concept['avg_change'] = avg_change
                else:
                    concept['avg_change'] = 0
            
            # 按涨跌幅排序
            hot_concepts.sort(key=lambda x: x['avg_change'], reverse=True)
            return hot_concepts
        except Exception as e:
            print(f"[热点概念] 获取失败: {e}")
            return []
    
    def _calculate_avg_change(self, stock_codes: List[str]) -> float:
        """计算股票平均涨跌幅"""
        changes = []
        for code in stock_codes[:5]:  # 只计算前5只
            try:
                if is_mock_mode():
                    # 模拟涨跌幅
                    change = (hash(code) % 400 - 200) / 100
                else:
                    df = _call_api('daily', ts_code=code, limit=1)
                    if not df.empty:
                        change = df.iloc[0]['pct_chg']
                    else:
                        continue
                changes.append(change)
            except:
                continue
        
        return sum(changes) / len(changes) if changes else 0
    
    def _get_focus_stocks(self, period: str) -> List[Dict]:
        """获取重点关注股票"""
        try:
            # 根据不同时段选择不同的选股策略
            if period == "morning":
                # 早盘关注：高开、缺口、概念热点
                return self._get_gap_stocks() + self._get_concept_leaders()
            elif period == "noon":
                # 午盘关注：量价异动、资金流入
                return self._get_volume_active_stocks()
            else:
                # 晚报关注：涨停、强势股
                return self._get_limit_up_stocks()
        except Exception as e:
            print(f"[重点股票] 获取失败: {e}")
            return []
    
    def _get_gap_stocks(self) -> List[Dict]:
        """获取跳空股票"""
        # 模拟数据
        return [
            {"code": "000001.SZ", "name": "平安银行", "gap_pct": 2.1, "reason": "高开缺口"},
            {"code": "600519.SH", "name": "贵州茅台", "gap_pct": -1.5, "reason": "低开缺口"}
        ]
    
    def _get_concept_leaders(self) -> List[Dict]:
        """获取概念龙头"""
        hot_concepts = self._get_hot_concepts()[:3]
        leaders = []
        
        for concept in hot_concepts:
            concept_stocks = self.concept_mgr.find_concept_stocks(concept['name'])
            if concept_stocks:
                stocks = list(concept_stocks.values())[0][:1]  # 取龙头
                if stocks:
                    leaders.append({
                        "code": stocks[0],
                        "name": "概念龙头",  # 这里可以查询真实名称
                        "concept": concept['name'],
                        "reason": f"{concept['name']}龙头"
                    })
        
        return leaders
    
    def _get_volume_active_stocks(self) -> List[Dict]:
        """获取量价异动股票"""
        # 模拟数据
        return [
            {"code": "002230.SZ", "name": "科大讯飞", "volume_ratio": 3.2, "pct_chg": 5.1},
            {"code": "300750.SZ", "name": "宁德时代", "volume_ratio": 2.8, "pct_chg": 3.2}
        ]
    
    def _get_limit_up_stocks(self) -> List[Dict]:
        """获取涨停股票"""
        # 模拟数据
        return [
            {"code": "002555.SZ", "name": "三七互娱", "limit_time": "09:30", "reason": "游戏概念"},
            {"code": "300124.SZ", "name": "汇川技术", "limit_time": "10:15", "reason": "工控设备"}
        ]
    
    def _get_today_highlights(self) -> List[str]:
        """获取今日看点"""
        return [
            "重要会议：中央经济工作会议召开",
            "数据发布：12月PMI数据公布",
            "热点关注：AI概念股表现活跃",
            "资金动向：北向资金净流入预期"
        ]
    
    def _get_risk_alerts(self) -> List[str]:
        """获取风险提示"""
        return [
            "美股期货下跌，外部环境偏负面",
            "创业板指数接近阻力位，注意回调风险",
            "题材股炒作较热，警惕追高风险"
        ]
    
    def _get_morning_review(self) -> Dict:
        """上午盘面回顾"""
        return {
            "opening": "三大指数低开高走",
            "trend": "震荡上行",
            "volume": "成交量温和放大",
            "highlight": "AI概念股领涨"
        }
    
    def _get_fund_flow_analysis(self) -> Dict:
        """资金流向分析"""
        return {
            "main_net": 15.6,  # 亿元
            "retail_net": -8.3,
            "north_net": 12.4,
            "most_inflow_sector": "人工智能",
            "most_outflow_sector": "地产"
        }
    
    def _get_limit_analysis(self) -> Dict:
        """涨跌停分析"""
        return {
            "limit_up_count": 45,
            "limit_down_count": 8,
            "main_themes": ["人工智能", "新能源", "军工"],
            "limit_up_stocks": self._get_limit_up_stocks()
        }
    
    def _get_sector_performance(self) -> List[Dict]:
        """板块表现"""
        return [
            {"name": "人工智能", "change": 4.2, "lead_stock": "科大讯飞"},
            {"name": "新能源车", "change": 2.1, "lead_stock": "宁德时代"},
            {"name": "白酒", "change": -1.3, "lead_stock": "贵州茅台"}
        ]
    
    def _get_afternoon_outlook(self) -> Dict:
        """下午展望"""
        return {
            "trend_expect": "震荡为主",
            "key_levels": [3200, 3180],
            "watch_sectors": ["AI", "新能源"],
            "strategy": "逢低关注优质个股"
        }
    
    def _get_daily_summary(self) -> Dict:
        """全天市场总结"""
        return {
            "performance": "三大指数收涨",
            "volume": "成交量较昨日放大20%",
            "money_effect": "赚钱效应显现",
            "hot_theme": "AI概念全天活跃"
        }
    
    def _get_stock_review(self) -> List[Dict]:
        """个股复盘"""
        return [
            {"code": "002230.SZ", "name": "科大讯飞", "change": 8.5, "reason": "AI概念龙头", "volume_ratio": 3.2},
            {"code": "300750.SZ", "name": "宁德时代", "change": 5.1, "reason": "新能源龙头", "volume_ratio": 2.1}
        ]
    
    def _get_fund_summary(self) -> Dict:
        """资金流向总结"""
        return {
            "total_turnover": 892.5,  # 亿元
            "main_net_inflow": 34.2,
            "north_net_inflow": 25.6,
            "active_sectors": ["人工智能", "新能源", "军工"]
        }
    
    def _get_sector_review(self) -> List[Dict]:
        """热点板块回顾"""
        return [
            {"name": "人工智能", "change": 6.8, "reason": "政策催化+技术突破"},
            {"name": "新能源车", "change": 3.2, "reason": "销量数据超预期"}
        ]
    
    def _get_tomorrow_strategy(self) -> Dict:
        """明日策略"""
        return {
            "market_view": "震荡偏强",
            "operation": "积极参与",
            "focus_direction": ["AI回调机会", "新能源龙头"],
            "risk_control": "控制仓位，分批建仓"
        }
    
    def _get_risk_warning(self) -> List[str]:
        """风险预警"""
        return [
            "题材股涨幅较大，注意获利回吐风险",
            "外围市场波动，关注隔夜消息影响",
            "年底资金面偏紧，谨慎追高"
        ]
    
    def _generate_ai_summary(self, report_data: Dict, report_type: str) -> str:
        """生成AI总结"""
        try:
            if report_type == "morning":
                prompt = (
                    "请基于以下数据生成专业的A股早报总结，包括：\n"
                    "1. 市场开盘前瞻\n"
                    "2. 宏观环境分析\n"
                    "3. 热点概念解读\n"
                    "4. 投资策略建议\n"
                    "要求简洁专业，300字以内。"
                )
            elif report_type == "noon":
                prompt = (
                    "请基于以下数据生成专业的A股午报总结，包括：\n"
                    "1. 上午盘面回顾\n"
                    "2. 资金流向分析\n"
                    "3. 下午操作建议\n"
                    "要求简洁专业，250字以内。"
                )
            else:  # evening
                prompt = (
                    "请基于以下数据生成专业的A股晚报总结，包括：\n"
                    "1. 全天市场复盘\n"
                    "2. 热点板块分析\n"
                    "3. 明日投资策略\n"
                    "要求简洁专业，400字以内。"
                )
            
            # 构造总结数据
            summary_data = {
                "report_type": report_type,
                "sections": report_data["sections"]
            }
            
            # 调用Ollama生成总结
            ai_summary = summarize(summary_data)
            return ai_summary
            
        except Exception as e:
            print(f"[AI总结] 生成失败: {e}")
            return f"AI总结生成失败: {e}"
    
    def _save_report(self, report_data: Dict):
        """保存报告到文件"""
        try:
            filename = f"{report_data['date']}_{report_data['type']}.json"
            filepath = os.path.join(self.cache_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
                
            print(f"[报告] 已保存到 {filepath}")
        except Exception as e:
            print(f"[报告] 保存失败: {e}")
    
    def get_latest_report(self, report_type: str) -> Optional[Dict]:
        """获取最新报告"""
        try:
            # 查找最新的报告文件
            files = [f for f in os.listdir(self.cache_dir) if f.endswith(f'_{report_type}.json')]
            if not files:
                return None
            
            latest_file = sorted(files)[-1]
            filepath = os.path.join(self.cache_dir, latest_file)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[报告] 获取失败: {e}")
            return None
    
    def get_report_history(self, days: int = 7) -> List[Dict]:
        """获取历史报告列表"""
        try:
            files = [f for f in os.listdir(self.cache_dir) if f.endswith('.json')]
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

# 单例
_report_generator = None

def get_report_generator() -> ReportGenerator:
    """获取报告生成器单例"""
    global _report_generator
    if _report_generator is None:
        _report_generator = ReportGenerator()
    return _report_generator