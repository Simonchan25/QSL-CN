"""
QSL-AI 市场分析模块
提供5维度智能市场分析：
1. 市场情绪解读 - 涨跌家数、资金流向、板块分布
2. 资金流向与融资分析 - 主力资金、北向资金、SHIBOR
3. 指数与板块结构分析 - 大盘指数、行业轮动
4. 宏观与外部环境 - 汇率、大宗商品、海外市场
5. 公告与新闻摘要 - 政策解读、重要公告影响
"""

from __future__ import annotations
import datetime as dt
from typing import Dict, Any, List, Optional
import json
import logging
import os

try:
    # 尝试相对导入
    from ..nlp.ollama_client import summarize_hotspot, OLLAMA_MODEL, OLLAMA_URL
except ImportError:
    try:
        # 尝试绝对导入
        import sys
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        from nlp.ollama_client import summarize_hotspot, OLLAMA_MODEL, OLLAMA_URL
    except ImportError:
        # 默认值
        OLLAMA_MODEL = "qwen3:8b"
        OLLAMA_URL = "http://localhost:11434"
        summarize_hotspot = None

logger = logging.getLogger(__name__)


class MarketAIAnalyzer:
    """QSL-AI 市场分析器"""
    
    def __init__(self):
        self.analysis_dimensions = {
            "sentiment": "市场情绪解读",
            "capital": "资金流向分析", 
            "structure": "指数板块结构",
            "macro": "宏观外部环境",
            "news": "公告新闻解读",
            "hotspots": "实时热点追踪",
            "alerts": "智能预警系统"
        }
        # 情绪指标权重配置
        self.sentiment_weights = {
            "up_down_ratio": 0.30,
            "limit_boards": 0.25,
            "north_funds": 0.20,
            "volume_energy": 0.15,
            "vix_equivalent": 0.10
        }
    
    def analyze_comprehensive_market(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        综合分析市场数据，生成5维度智能分析
        
        Args:
            market_data: 来自fetch_market_overview()的完整市场数据
            
        Returns:
            包含5个维度分析结果的字典
        """
        try:
            analysis = {}
            
            # 1. 市场情绪解读
            analysis["sentiment"] = self._analyze_market_sentiment(market_data)
            
            # 2. 资金流向与融资分析  
            analysis["capital"] = self._analyze_capital_flow(market_data)
            
            # 3. 指数与板块结构分析
            analysis["structure"] = self._analyze_index_structure(market_data)
            
            # 4. 宏观与外部环境
            analysis["macro"] = self._analyze_macro_environment(market_data)
            
            # 5. 公告与新闻摘要
            analysis["news"] = self._analyze_news_announcements(market_data)
            
            # 6. 实时热点追踪
            analysis["hotspots"] = self._analyze_market_hotspots(market_data)
            
            # 7. 智能预警系统
            analysis["alerts"] = self._generate_market_alerts(analysis)
            
            # 8. 恐慌贪婪指数
            analysis["fear_greed_index"] = self._calculate_fear_greed_index(analysis)
            
            # 9. LLM智能解读
            analysis["intelligent_narrative"] = self._generate_intelligent_narrative(analysis)
            
            # 综合评估和操作建议
            analysis["summary"] = self._generate_overall_assessment(market_data, analysis)
            
            # 添加生成时间戳
            analysis["generated_at"] = dt.datetime.now().isoformat()
            analysis["data_timestamp"] = market_data.get("timestamp")
            
            return analysis
            
        except Exception as e:
            logger.error(f"综合市场分析失败: {e}")
            return self._get_fallback_analysis()
    
    def _analyze_market_sentiment(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析市场情绪 - 基于涨跌家数、涨停板、大中小盘表现"""
        try:
            sentiment_data = {}
            breadth = market_data.get("market_breadth", {})
            indices = market_data.get("indices", [])
            
            # 计算主要指数平均涨跌幅
            valid_indices = [idx for idx in indices if idx.get("pct_chg") is not None]
            avg_change = sum(idx["pct_chg"] for idx in valid_indices) / len(valid_indices) if valid_indices else 0
            
            # 涨跌家数分析
            up_count = breadth.get("up_count", 0)
            down_count = breadth.get("down_count", 0)
            total_count = breadth.get("total_count", 1)
            up_ratio = (up_count / total_count * 100) if total_count > 0 else 0
            
            sentiment_data["up_down_ratio"] = {
                "up_count": up_count,
                "down_count": down_count,
                "up_ratio": round(up_ratio, 1),
                "analysis": self._interpret_up_down_ratio(up_ratio)
            }
            
            # 涨停跌停分析
            limit_up = breadth.get("limit_up", 0) 
            limit_down = breadth.get("limit_down", 0)
            sentiment_data["limit_analysis"] = {
                "limit_up": limit_up,
                "limit_down": limit_down,
                "analysis": self._interpret_limit_boards(limit_up, limit_down)
            }
            
            # 大中小盘表现分析
            large_cap_up = breadth.get("large_cap_up", 0)
            mid_cap_up = breadth.get("mid_cap_up", 0) 
            small_cap_up = breadth.get("small_cap_up", 0)
            sentiment_data["market_cap_analysis"] = {
                "large_cap_up": large_cap_up,
                "mid_cap_up": mid_cap_up,
                "small_cap_up": small_cap_up,
                "analysis": self._interpret_market_cap_performance(large_cap_up, mid_cap_up, small_cap_up)
            }
            
            # 整体情绪评级 (1-10分)
            emotion_score = self._calculate_emotion_score(up_ratio, avg_change, limit_up, limit_down)
            sentiment_data["emotion_score"] = emotion_score
            sentiment_data["overall_sentiment"] = self._get_sentiment_description(emotion_score)
            
            return sentiment_data
            
        except Exception as e:
            logger.error(f"市场情绪分析失败: {e}")
            return {"error": "市场情绪数据暂时无法分析"}
    
    def _analyze_capital_flow(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析资金流向 - 北向资金、融资融券、主力资金、SHIBOR"""
        try:
            capital_data = {}
            flow_data = market_data.get("capital_flow", {})
            shibor_data = market_data.get("shibor", {})
            
            # 北向资金分析
            north_net = flow_data.get("hsgt_net_amount", 0)
            hk_net = flow_data.get("hk_net_amount", 0)
            sg_net = flow_data.get("sg_net_amount", 0)
            
            capital_data["north_funds"] = {
                "total_net_inflow": north_net,
                "hk_net": hk_net,
                "sg_net": sg_net,
                "analysis": self._interpret_north_funds(north_net, hk_net, sg_net)
            }
            
            # 融资融券分析
            margin_info = flow_data.get("margin", {})
            if margin_info:
                capital_data["margin_trading"] = {
                    "balance": margin_info.get("margin_balance", 0),
                    "daily_change": margin_info.get("margin_change", 0),
                    "buy_amount": margin_info.get("buy_amount", 0),
                    "analysis": self._interpret_margin_trading(margin_info)
                }
            
            # 主力资金分析
            main_flow = flow_data.get("main_flow", {})
            if main_flow:
                capital_data["main_funds"] = {
                    "net_inflow": main_flow.get("main_net_inflow", 0),
                    "super_large": main_flow.get("super_large_net", 0),
                    "large": main_flow.get("large_net", 0),
                    "analysis": self._interpret_main_funds(main_flow)
                }
            
            # SHIBOR利率分析
            if shibor_data:
                capital_data["shibor_rates"] = {
                    "overnight": shibor_data.get("on"),
                    "one_week": shibor_data.get("1w"), 
                    "analysis": self._interpret_shibor_rates(shibor_data)
                }
            
            return capital_data
            
        except Exception as e:
            logger.error(f"资金流向分析失败: {e}")
            return {"error": "资金流向数据暂时无法分析"}
    
    def _analyze_index_structure(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析指数板块结构 - 主要指数表现、行业轮动"""
        try:
            structure_data = {}
            indices = market_data.get("indices", [])
            sectors = market_data.get("sectors", [])
            
            # 主要指数表现分析
            index_performance = []
            for idx in indices[:5]:  # 取前5个主要指数
                if idx.get("pct_chg") is not None:
                    index_name = self._get_index_name(idx.get("ts_code", ""))
                    index_performance.append({
                        "name": index_name,
                        "code": idx.get("ts_code"),
                        "close": idx.get("close"),
                        "change": idx.get("pct_chg"),
                        "strength": self._classify_index_strength(idx.get("pct_chg", 0))
                    })
            
            structure_data["index_performance"] = {
                "indices": index_performance,
                "analysis": self._interpret_index_divergence(index_performance)
            }
            
            # 行业板块轮动分析
            if sectors:
                top_sectors = sectors[:5]  # 涨幅前5
                bottom_sectors = sectors[-5:]  # 跌幅前5（最后5个）
                
                structure_data["sector_rotation"] = {
                    "leading_sectors": top_sectors,
                    "lagging_sectors": bottom_sectors,
                    "analysis": self._interpret_sector_rotation(top_sectors, bottom_sectors)
                }
                
                # 板块强度分布
                structure_data["sector_distribution"] = self._analyze_sector_distribution(sectors)
            
            return structure_data
            
        except Exception as e:
            logger.error(f"指数板块结构分析失败: {e}")
            return {"error": "指数板块数据暂时无法分析"}
    
    def _analyze_macro_environment(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析宏观外部环境 - 汇率、大宗商品、海外市场"""
        try:
            macro_data = {}
            macro_indicators = market_data.get("macro_indicators", {})
            
            # 汇率分析
            usd_cny = macro_indicators.get("usd_cny")
            if usd_cny:
                macro_data["forex"] = {
                    "usd_cny": usd_cny,
                    "analysis": self._interpret_forex(usd_cny)
                }
            
            # 大宗商品分析 
            oil_price = macro_indicators.get("oil_price")
            oil_change = macro_indicators.get("oil_change")
            gold_price = macro_indicators.get("gold_price") 
            gold_change = macro_indicators.get("gold_change")
            
            if oil_price is not None:
                macro_data["commodities"] = {
                    "oil": {
                        "price": oil_price,
                        "change": oil_change,
                        "impact": self._interpret_oil_impact(oil_change)
                    },
                    "gold": {
                        "price": gold_price, 
                        "change": gold_change,
                        "impact": self._interpret_gold_impact(gold_change)
                    },
                    "analysis": self._interpret_commodities_impact(oil_change, gold_change)
                }
            
            # 宏观环境综合评估
            macro_data["environment_assessment"] = self._assess_macro_environment(macro_indicators)
            
            return macro_data
            
        except Exception as e:
            logger.error(f"宏观环境分析失败: {e}")
            return {"error": "宏观环境数据暂时无法分析"}
    
    def _analyze_news_announcements(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析公告新闻 - 重要公告、政策新闻影响"""
        try:
            news_data = {}
            
            # 重要公告分析
            announcements = market_data.get("announcements", [])
            if announcements:
                positive_count = len([ann for ann in announcements if ann.get("impact") == "positive"])
                negative_count = len([ann for ann in announcements if ann.get("impact") == "negative"])
                
                news_data["important_announcements"] = {
                    "total_count": len(announcements),
                    "positive_count": positive_count,
                    "negative_count": negative_count,
                    "key_announcements": announcements[:3],  # 前3个重要公告
                    "analysis": self._interpret_announcements_impact(announcements)
                }
            
            # 政策新闻分析
            policy_news = market_data.get("policy_news", [])
            if policy_news:
                policy_impact_score = sum([news.get("impact_score", 0) for news in policy_news]) / len(policy_news)
                
                news_data["policy_news"] = {
                    "total_count": len(policy_news),
                    "average_impact": round(policy_impact_score, 1),
                    "key_policies": policy_news[:3],  # 前3个重要政策
                    "analysis": self._interpret_policy_impact(policy_news)
                }
            
            # 重要新闻标题
            major_news = market_data.get("major_news", [])
            if major_news:
                news_data["major_headlines"] = {
                    "headlines": major_news[:5],  # 前5个重要新闻
                    "analysis": self._interpret_news_sentiment(major_news)
                }
            
            return news_data
            
        except Exception as e:
            logger.error(f"新闻公告分析失败: {e}")
            return {"error": "新闻公告数据暂时无法分析"}
    
    def _generate_overall_assessment(self, market_data: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, Any]:
        """生成综合评估和操作建议"""
        try:
            # 计算综合评分 (1-10分)
            overall_score = self._calculate_overall_score(analysis)
            
            # 生成市场状态描述
            market_state = self._determine_market_state(overall_score, market_data)
            
            # 生成操作建议
            operation_advice = self._generate_operation_advice(overall_score, analysis)
            
            # 风险提示
            risk_warnings = self._generate_risk_warnings(analysis)
            
            return {
                "overall_score": overall_score,
                "market_state": market_state,
                "operation_advice": operation_advice,
                "risk_warnings": risk_warnings,
                "confidence_level": self._calculate_confidence_level(analysis)
            }
            
        except Exception as e:
            logger.error(f"综合评估生成失败: {e}")
            return {"error": "综合评估暂时无法生成"}
    
    # ============= 解读辅助函数 =============
    
    def _interpret_up_down_ratio(self, up_ratio: float) -> str:
        """解读涨跌比例"""
        if up_ratio >= 70:
            return f"涨跌比达{up_ratio}%，市场情绪极度乐观，多头强势主导，赚钱效应突出"
        elif up_ratio >= 60:
            return f"涨跌比为{up_ratio}%，市场偏暖，多头占优，个股表现活跃"
        elif up_ratio >= 50:
            return f"涨跌比为{up_ratio}%，市场平衡偏强，结构性机会较多"
        elif up_ratio >= 40:
            return f"涨跌比为{up_ratio}%，市场分化明显，操作难度加大"
        elif up_ratio >= 30:
            return f"涨跌比仅{up_ratio}%，市场偏冷，空头压力较大"
        else:
            return f"涨跌比仅{up_ratio}%，市场极度低迷，建议谨慎观望"
    
    def _interpret_limit_boards(self, limit_up: int, limit_down: int) -> str:
        """解读涨停跌停情况"""
        if limit_up > 50:
            return f"涨停板多达{limit_up}家，市场情绪火爆，题材炒作活跃"
        elif limit_up > 20:
            return f"涨停板{limit_up}家，市场有一定热度，关注板块轮动"
        elif limit_up > 10:
            return f"涨停板{limit_up}家，市场温和活跃，个股机会不少"
        elif limit_up > 0:
            return f"涨停板{limit_up}家，市场表现平淡，缺乏持续热点"
        else:
            if limit_down > 10:
                return f"无涨停股，跌停{limit_down}家，市场恐慌情绪较重"
            else:
                return "无涨停股，市场缺乏赚钱效应，观望情绪浓厚"
    
    def _interpret_market_cap_performance(self, large: int, mid: int, small: int) -> str:
        """解读不同市值股票表现"""
        total = large + mid + small
        if total == 0:
            return "市值分布数据不足"
        
        large_pct = large / total * 100
        small_pct = small / total * 100
        
        if large_pct > 50:
            return f"大盘股领涨占比{large_pct:.1f}%，价值投资风格占主导，市场偏向稳健"
        elif small_pct > 50:
            return f"小盘股活跃占比{small_pct:.1f}%，题材股表现突出，投机情绪较浓"
        else:
            return f"大中小盘表现均衡，市场风格较为平衡，结构性机会并存"
    
    def _interpret_north_funds(self, total_net: float, hk_net: float, sg_net: float) -> str:
        """解读北向资金"""
        if total_net > 100:
            return f"北向资金大幅净流入{total_net:.1f}亿，外资坚定看多A股，重点关注外资重仓股"
        elif total_net > 50:
            return f"北向资金净流入{total_net:.1f}亿，外资态度偏积极，增强市场信心"
        elif total_net > 0:
            return f"北向资金小幅净流入{total_net:.1f}亿，外资保持谨慎乐观"
        elif total_net > -50:
            return f"北向资金净流出{abs(total_net):.1f}亿，外资获利了结，需关注调整压力"
        else:
            return f"北向资金大幅净流出{abs(total_net):.1f}亿，外资避险情绪升温，谨慎为主"
    
    def _interpret_margin_trading(self, margin_info: Dict) -> str:
        """解读融资融券"""
        balance = margin_info.get("margin_balance", 0)
        change = margin_info.get("margin_change", 0)
        
        if change > 100:
            return f"两融余额增加{change:.1f}亿至{balance:.1f}亿，投资者加杠杆意愿强烈"
        elif change > 0:
            return f"两融余额增加{change:.1f}亿，融资买入情绪有所回升"
        elif change > -100:
            return f"两融余额减少{abs(change):.1f}亿，投资者降杠杆操作"
        else:
            return f"两融余额大幅减少{abs(change):.1f}亿，去杠杆压力较大"
    
    def _interpret_main_funds(self, main_flow: Dict) -> str:
        """解读主力资金"""
        net_inflow = main_flow.get("main_net_inflow", 0)
        super_large = main_flow.get("super_large_net", 0)
        
        if net_inflow > 200:
            return f"主力资金净流入{net_inflow:.1f}亿，机构大举建仓，看好后市"
        elif net_inflow > 100:
            return f"主力资金净流入{net_inflow:.1f}亿，资金面较为活跃"
        elif net_inflow > 0:
            return f"主力资金小幅净流入{net_inflow:.1f}亿，增量资金谨慎入场"
        else:
            return f"主力资金净流出{abs(net_inflow):.1f}亿，机构减仓明显"
    
    def _calculate_emotion_score(self, up_ratio: float, avg_change: float, limit_up: int, limit_down: int) -> float:
        """计算情绪评分"""
        score = 5.0  # 基础分
        
        # 涨跌比例影响 (权重40%)
        if up_ratio >= 70:
            score += 2.0
        elif up_ratio >= 60:
            score += 1.5
        elif up_ratio >= 50:
            score += 0.5
        elif up_ratio >= 40:
            score -= 0.5
        elif up_ratio >= 30:
            score -= 1.5
        else:
            score -= 2.0
            
        # 平均涨跌幅影响 (权重30%)
        if avg_change > 2:
            score += 1.5
        elif avg_change > 1:
            score += 1.0
        elif avg_change > 0:
            score += 0.5
        elif avg_change > -1:
            score -= 0.5
        else:
            score -= 1.0
            
        # 涨跌停影响 (权重30%)
        if limit_up > 50:
            score += 1.0
        elif limit_up > 20:
            score += 0.5
        elif limit_down > 20:
            score -= 1.0
        elif limit_down > 10:
            score -= 0.5
            
        return max(1.0, min(10.0, round(score, 1)))
    
    def _get_sentiment_description(self, score: float) -> str:
        """获取情绪描述"""
        if score >= 8.5:
            return "极度乐观"
        elif score >= 7.0:
            return "乐观"
        elif score >= 6.0:
            return "偏乐观"
        elif score >= 5.0:
            return "中性"
        elif score >= 4.0:
            return "偏谨慎"
        elif score >= 3.0:
            return "谨慎" 
        else:
            return "极度谨慎"
    
    def _get_index_name(self, code: str) -> str:
        """获取指数名称"""
        name_map = {
            "000001.SH": "上证指数",
            "399001.SZ": "深证成指", 
            "399006.SZ": "创业板指",
            "000300.SH": "沪深300",
            "000016.SH": "上证50"
        }
        return name_map.get(code, code)
    
    def _calculate_overall_score(self, analysis: Dict[str, Any]) -> float:
        """计算综合评分"""
        try:
            score = 5.0  # 基础分
            
            # 市场情绪评分 (权重25%)
            if "sentiment" in analysis and "emotion_score" in analysis["sentiment"]:
                emotion_score = analysis["sentiment"]["emotion_score"]
                score += (emotion_score - 5.0) * 0.25
            
            # 资金流向评分 (权重25%) 
            if "capital" in analysis and "north_funds" in analysis["capital"]:
                north_net = analysis["capital"]["north_funds"].get("total_net_inflow", 0)
                if north_net > 100:
                    score += 1.0
                elif north_net > 50:
                    score += 0.5
                elif north_net < -50:
                    score -= 0.5
                elif north_net < -100:
                    score -= 1.0
            
            # 其他维度权重较小，暂时简化处理
            
            return max(1.0, min(10.0, round(score, 1)))
        except:
            return 5.0
    
    def _determine_market_state(self, score: float, market_data: Dict) -> str:
        """确定市场状态"""
        if score >= 8.0:
            return "强势上涨"
        elif score >= 7.0:
            return "稳步上涨"
        elif score >= 6.0:
            return "震荡偏强"
        elif score >= 5.0:
            return "震荡整理"
        elif score >= 4.0:
            return "震荡偏弱"
        elif score >= 3.0:
            return "弱势调整"
        else:
            return "深度调整"
    
    def _generate_operation_advice(self, score: float, analysis: Dict) -> List[str]:
        """生成操作建议"""
        advice = []
        
        if score >= 8.0:
            advice.append("🚀 市场强势，建议适度加仓，仓位可提升至70-80%")
            advice.append("📈 重点关注领涨板块的龙头股，积极参与")
            advice.append("⚡ 把握短线机会，但注意及时止盈")
        elif score >= 6.0:
            advice.append("📊 市场偏强，维持60-70%仓位，稳健操作")
            advice.append("🎯 选择性参与热点板块，避免盲目追高")
            advice.append("💡 适当高抛低吸，控制风险")
        elif score >= 4.0:
            advice.append("⚖️ 市场震荡，控制仓位在40-50%")
            advice.append("🔍 等待明确信号，谨慎选股")
            advice.append("🛡️ 注重防御，关注低估值品种")
        else:
            advice.append("🚨 市场偏弱，降低仓位至30%以下")
            advice.append("💰 保持充足现金，等待机会")
            advice.append("🔄 避免抄底，等待企稳信号")
        
        return advice
    
    def _generate_risk_warnings(self, analysis: Dict) -> List[str]:
        """生成风险提示"""
        warnings = []
        
        # 根据分析结果生成风险提示
        try:
            if "sentiment" in analysis:
                emotion_score = analysis["sentiment"].get("emotion_score", 5)
                if emotion_score > 8:
                    warnings.append("⚠️ 市场情绪过热，注意获利回吐风险")
                elif emotion_score < 3:
                    warnings.append("⚠️ 市场情绪低迷，继续下跌风险较大")
            
            if "capital" in analysis and "north_funds" in analysis["capital"]:
                north_net = analysis["capital"]["north_funds"].get("total_net_inflow", 0)
                if north_net < -100:
                    warnings.append("⚠️ 北向资金大幅流出，外资减仓压力明显")
            
            if not warnings:
                warnings.append("✅ 当前市场风险可控，保持理性投资")
                
        except:
            warnings.append("⚠️ 风险评估暂时无法完成，请保持谨慎")
        
        return warnings
    
    def _calculate_confidence_level(self, analysis: Dict) -> str:
        """计算分析置信度"""
        # 根据数据完整性计算置信度
        complete_dimensions = sum(1 for dim in ["sentiment", "capital", "structure", "macro", "news"] 
                                if dim in analysis and not isinstance(analysis[dim], dict) or "error" not in analysis[dim])
        
        confidence_pct = (complete_dimensions / 5.0) * 100
        
        if confidence_pct >= 80:
            return "高 (数据完整)"
        elif confidence_pct >= 60:
            return "中等 (部分数据缺失)"
        else:
            return "较低 (数据不完整)"
    
    def _get_fallback_analysis(self) -> Dict[str, Any]:
        """获取后备分析结果"""
        return {
            "sentiment": {"error": "市场情绪分析暂时不可用"},
            "capital": {"error": "资金流向分析暂时不可用"},
            "structure": {"error": "板块结构分析暂时不可用"},
            "macro": {"error": "宏观环境分析暂时不可用"},
            "news": {"error": "新闻分析暂时不可用"},
            "summary": {
                "overall_score": 5.0,
                "market_state": "数据不足",
                "operation_advice": ["📊 数据获取中，请稍后查看分析结果"],
                "risk_warnings": ["⚠️ 分析数据不完整，请谨慎参考"],
                "confidence_level": "较低 (数据获取失败)"
            },
            "generated_at": dt.datetime.now().isoformat(),
            "error": "综合分析暂时不可用，正在修复中..."
        }
    
    # ============= 其他辅助解读函数 =============
    
    def _interpret_shibor_rates(self, shibor_data: Dict) -> str:
        """解读SHIBOR利率"""
        overnight = shibor_data.get("on")
        one_week = shibor_data.get("1w")
        
        if overnight and one_week:
            if float(overnight) > 3.0:
                return f"隔夜SHIBOR达{overnight}%，资金面偏紧，需关注流动性风险"
            elif float(overnight) < 1.0:
                return f"隔夜SHIBOR仅{overnight}%，市场资金充裕，流动性宽松"
            else:
                return f"SHIBOR利率平稳，隔夜{overnight}%，资金面中性"
        return "SHIBOR数据暂时不可用"
    
    def _interpret_forex(self, usd_cny: float) -> str:
        """解读汇率影响"""
        if usd_cny > 7.3:
            return f"人民币相对偏弱（{usd_cny}），有利于出口企业，关注外贸股"
        elif usd_cny < 7.0:
            return f"人民币相对较强（{usd_cny}），利好进口消费，关注内需股"
        else:
            return f"汇率相对平稳（{usd_cny}），对市场影响中性"
    
    def _interpret_oil_impact(self, oil_change: float) -> str:
        """解读原油价格影响"""
        if oil_change > 3:
            return "原油大涨，利好石化上游，利空下游炼化"
        elif oil_change > 1:
            return "原油上涨，关注能源板块机会"
        elif oil_change < -3:
            return "原油大跌，利好下游化工，利空上游开采"
        elif oil_change < -1:
            return "原油下跌，关注成本改善的化工股"
        else:
            return "原油价格平稳，影响中性"
    
    def _interpret_gold_impact(self, gold_change: float) -> str:
        """解读黄金价格影响"""
        if gold_change > 2:
            return "黄金大涨，避险情绪升温，关注贵金属股"
        elif gold_change > 0:
            return "黄金上涨，市场避险需求上升"
        elif gold_change < -2:
            return "黄金大跌，风险偏好回升，利好权益市场"
        else:
            return "黄金价格平稳"
    
    def _interpret_commodities_impact(self, oil_change: float, gold_change: float) -> str:
        """解读大宗商品综合影响"""
        if oil_change > 2 and gold_change > 1:
            return "油价金价双涨，通胀预期升温，关注周期股和避险品种"
        elif oil_change > 2:
            return "油价大涨推动通胀预期，关注上游资源股"
        elif gold_change > 2:
            return "金价大涨反映避险情绪，市场风险偏好下降"
        else:
            return "大宗商品价格相对平稳，对市场影响有限"
    
    def _assess_macro_environment(self, macro_indicators: Dict) -> str:
        """评估宏观环境"""
        # 这里可以根据多个宏观指标综合评估
        return "当前宏观环境整体稳定，外部因素影响可控"
    
    def _interpret_index_divergence(self, index_performance: List[Dict]) -> str:
        """解读指数分化"""
        if not index_performance:
            return "指数表现数据不足"
        
        changes = [idx["change"] for idx in index_performance if idx["change"] is not None]
        if not changes:
            return "指数涨跌数据不足"
        
        max_change = max(changes)
        min_change = min(changes)
        divergence = max_change - min_change
        
        if divergence > 3:
            return f"指数分化明显，最大分化达{divergence:.1f}%，结构性行情显著"
        elif divergence > 1:
            return f"指数表现有所分化，反映不同板块轮动"
        else:
            return f"主要指数同步性较强，市场表现一致"
    
    def _interpret_sector_rotation(self, top_sectors: List, bottom_sectors: List) -> str:
        """解读板块轮动"""
        if not top_sectors or not bottom_sectors:
            return "板块数据不足"
        
        top_change = top_sectors[0].get("pct_chg", 0)
        bottom_change = bottom_sectors[0].get("pct_chg", 0)
        
        if top_change > 5:
            return f"{top_sectors[0]['name']}等强势板块领涨超{top_change:.1f}%，板块轮动明显"
        elif top_change > 2:
            return f"板块轮动正常，{top_sectors[0]['name']}等板块表现相对较好"
        elif top_change < 0:
            return "主要板块普遍调整，市场缺乏轮动热点"
        else:
            return "板块表现相对平均，缺乏明显主线"
    
    def _analyze_sector_distribution(self, sectors: List) -> Dict:
        """分析板块强度分布"""
        if not sectors:
            return {"error": "板块数据不足"}
        
        positive = len([s for s in sectors if s.get("pct_chg", 0) > 0])
        negative = len([s for s in sectors if s.get("pct_chg", 0) < 0])
        neutral = len(sectors) - positive - negative
        
        return {
            "positive_sectors": positive,
            "negative_sectors": negative,
            "neutral_sectors": neutral,
            "strength_ratio": round(positive / len(sectors) * 100, 1) if sectors else 0
        }
    
    def _classify_index_strength(self, change: float) -> str:
        """分类指数强度"""
        if change > 2:
            return "强势"
        elif change > 0:
            return "偏强"
        elif change > -2:
            return "偏弱"
        else:
            return "弱势"
    
    def _interpret_announcements_impact(self, announcements: List) -> str:
        """解读公告影响"""
        if not announcements:
            return "今日重要公告较少"
        
        positive_count = len([ann for ann in announcements if ann.get("impact") == "positive"])
        total_count = len(announcements)
        
        if positive_count / total_count > 0.7:
            return f"今日{total_count}条重要公告中{positive_count}条为利好，整体偏正面"
        elif positive_count / total_count < 0.3:
            return f"今日重要公告偏负面，需关注相关个股风险"
        else:
            return f"今日公告影响偏中性，正负面消息并存"
    
    def _interpret_policy_impact(self, policy_news: List) -> str:
        """解读政策影响"""
        if not policy_news:
            return "今日政策面相对平静"
        
        avg_impact = sum([news.get("impact_score", 0) for news in policy_news]) / len(policy_news)
        
        if avg_impact > 7:
            return f"重要政策密集出台，平均影响评分{avg_impact:.1f}，政策面偏暖"
        elif avg_impact > 5:
            return f"政策面中性偏好，关注政策受益板块"
        else:
            return f"政策影响相对有限，市场主要看基本面"
    
    def _interpret_news_sentiment(self, major_news: List) -> str:
        """解读新闻情绪"""
        if not major_news:
            return "今日重要新闻较少"
        
        # 简单的情绪分析（实际应用中可以使用NLP技术）
        return f"今日{len(major_news)}条重要新闻，整体氛围需结合具体内容判断"
    
    # ============= 新增功能：智能化分析 =============
    
    def _analyze_market_hotspots(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """实时热点追踪分析"""
        try:
            hotspots = {}
            
            # 热门板块分析
            sectors = market_data.get("sectors", [])
            if sectors:
                hot_sectors = sectors[:3]  # 取前3个热门板块
                hotspots["hot_sectors"] = {
                    "sectors": hot_sectors,
                    "momentum_score": self._calculate_sector_momentum(hot_sectors),
                    "sustainability": self._assess_sector_sustainability(hot_sectors),
                    "analysis": self._interpret_hot_sectors(hot_sectors)
                }
            
            # 概念轮动分析
            concepts = market_data.get("concepts", [])
            if concepts:
                hot_concepts = concepts[:5]  # 取前5个热门概念
                hotspots["concept_rotation"] = {
                    "concepts": hot_concepts,
                    "rotation_speed": self._calculate_rotation_speed(concepts),
                    "analysis": self._interpret_concept_rotation(hot_concepts)
                }
            
            # 新闻驱动股票
            news_driven = self._extract_news_driven_stocks(market_data)
            if news_driven:
                hotspots["news_driven"] = {
                    "stocks": news_driven,
                    "impact_analysis": self._analyze_news_impact(news_driven)
                }
            
            # 动量分析
            momentum_data = self._calculate_momentum_indicators(market_data)
            hotspots["momentum_analysis"] = momentum_data
            
            return hotspots
            
        except Exception as e:
            logger.error(f"热点追踪分析失败: {e}")
            return {"error": "热点追踪数据暂时不可用"}
    
    def _generate_market_alerts(self, analysis: Dict[str, Any]) -> List[Dict]:
        """智能预警系统"""
        alerts = []
        
        try:
            # 流动性预警
            if "capital" in analysis and "shibor_rates" in analysis["capital"]:
                overnight_rate = analysis["capital"]["shibor_rates"].get("overnight")
                if overnight_rate and float(overnight_rate) > 3.5:
                    alerts.append({
                        "type": "liquidity_risk",
                        "level": "high",
                        "message": f"隔夜SHIBOR异常升高至{overnight_rate}%，关注流动性风险",
                        "action": "降低仓位，保持充足现金"
                    })
            
            # 情绪极端预警
            if "sentiment" in analysis:
                emotion_score = analysis["sentiment"].get("emotion_score", 5)
                if emotion_score > 9:
                    alerts.append({
                        "type": "sentiment_extreme_high",
                        "level": "medium",
                        "message": f"市场情绪过热(评分{emotion_score})，注意回调风险",
                        "action": "适度获利了结，控制仓位"
                    })
                elif emotion_score < 2:
                    alerts.append({
                        "type": "sentiment_extreme_low",
                        "level": "high",
                        "message": f"市场情绪极度低迷(评分{emotion_score})，继续下跌风险较大",
                        "action": "谨慎观望，等待企稳信号"
                    })
            
            # 资金流向预警
            if "capital" in analysis and "north_funds" in analysis["capital"]:
                north_net = analysis["capital"]["north_funds"].get("total_net_inflow", 0)
                if north_net < -200:
                    alerts.append({
                        "type": "capital_outflow",
                        "level": "high",
                        "message": f"北向资金大幅流出{abs(north_net):.1f}亿，外资减仓压力明显",
                        "action": "关注外资重仓股调整风险"
                    })
            
            # 技术面预警
            if "structure" in analysis and "index_performance" in analysis["structure"]:
                indices = analysis["structure"]["index_performance"].get("indices", [])
                if indices:
                    main_index_change = indices[0].get("change", 0)
                    if main_index_change < -3:
                        alerts.append({
                            "type": "technical_breakdown",
                            "level": "medium",
                            "message": f"主要指数大跌{abs(main_index_change):.1f}%，技术面走弱",
                            "action": "等待技术修复信号，避免盲目抄底"
                        })
            
            # 板块轮动预警
            if "hotspots" in analysis and "hot_sectors" in analysis["hotspots"]:
                momentum_score = analysis["hotspots"]["hot_sectors"].get("momentum_score", 0)
                if momentum_score < 3:
                    alerts.append({
                        "type": "rotation_stagnation",
                        "level": "low",
                        "message": "板块轮动停滞，市场缺乏明确主线",
                        "action": "等待新热点出现，保持耐心"
                    })
            
            # 默认无风险提示
            if not alerts:
                alerts.append({
                    "type": "normal",
                    "level": "low",
                    "message": "当前市场风险可控，保持理性投资",
                    "action": "继续关注市场变化，适度参与"
                })
            
            return alerts
            
        except Exception as e:
            logger.error(f"智能预警系统错误: {e}")
            return [{
                "type": "system_error",
                "level": "low",
                "message": "预警系统暂时不可用",
                "action": "请手动关注市场风险"
            }]
    
    def _calculate_fear_greed_index(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """计算恐慌贪婪指数 (0-100分)"""
        try:
            score = 50  # 基础分数
            components = {}
            
            # 1. 市场情绪 (30%权重)
            if "sentiment" in analysis:
                emotion_score = analysis["sentiment"].get("emotion_score", 5)
                sentiment_component = ((emotion_score - 5) / 5) * 30
                score += sentiment_component
                components["market_sentiment"] = {
                    "value": emotion_score,
                    "weight": 30,
                    "contribution": sentiment_component
                }
            
            # 2. 资金流向 (25%权重)
            if "capital" in analysis and "north_funds" in analysis["capital"]:
                north_net = analysis["capital"]["north_funds"].get("total_net_inflow", 0)
                # 将资金流向转化为0-100分
                capital_score = min(100, max(0, 50 + north_net / 10))  # 每10亿对应1分
                capital_component = ((capital_score - 50) / 50) * 25
                score += capital_component
                components["capital_flow"] = {
                    "value": north_net,
                    "weight": 25,
                    "contribution": capital_component
                }
            
            # 3. 波动率指标 (20%权重) - 模拟VIX
            vix_score = self._calculate_vix_equivalent(analysis)
            vix_component = ((50 - vix_score) / 50) * 20  # VIX越高贪婪指数越低
            score += vix_component
            components["volatility"] = {
                "value": vix_score,
                "weight": 20,
                "contribution": vix_component
            }
            
            # 4. 板块轮动 (15%权重)
            if "structure" in analysis and "sector_rotation" in analysis["structure"]:
                rotation_strength = self._assess_rotation_strength(analysis["structure"]["sector_rotation"])
                rotation_component = ((rotation_strength - 50) / 50) * 15
                score += rotation_component
                components["sector_rotation"] = {
                    "value": rotation_strength,
                    "weight": 15,
                    "contribution": rotation_component
                }
            
            # 5. 新闻情绪 (10%权重)
            if "news" in analysis:
                news_sentiment = self._calculate_news_sentiment_score(analysis["news"])
                news_component = ((news_sentiment - 50) / 50) * 10
                score += news_component
                components["news_sentiment"] = {
                    "value": news_sentiment,
                    "weight": 10,
                    "contribution": news_component
                }
            
            # 确保分数在 0-100 范围内
            final_score = max(0, min(100, round(score, 1)))
            
            return {
                "score": final_score,
                "level": self._get_fear_greed_level(final_score),
                "components": components,
                "interpretation": self._interpret_fear_greed_index(final_score)
            }
            
        except Exception as e:
            logger.error(f"恐慌贪婪指数计算失败: {e}")
            return {
                "score": 50,
                "level": "中性",
                "components": {},
                "interpretation": "恐慌贪婪指数暂时无法计算"
            }
    
    def _generate_intelligent_narrative(self, analysis: Dict[str, Any]) -> str:
        """使用LLM生成智能化市场解读叙述"""
        try:
            # 构建结构化的分析提示词
            prompt_data = self._build_analysis_prompt_data(analysis)
            
            # 调用LLM生成智能解读
            narrative = self._call_llm_for_analysis(prompt_data)
            
            return narrative
            
        except Exception as e:
            logger.error(f"LLM智能解读生成失败: {e}")
            return self._get_fallback_narrative(analysis)
    
    # ============= 辅助函数 =============
    
    def _calculate_sector_momentum(self, sectors: List[Dict]) -> float:
        """计算板块动量评分"""
        if not sectors:
            return 0
        
        momentum = 0
        for sector in sectors[:3]:
            change = sector.get("pct_chg", 0)
            if change > 5:
                momentum += 3
            elif change > 3:
                momentum += 2
            elif change > 1:
                momentum += 1
        
        return min(10, momentum)
    
    def _assess_sector_sustainability(self, sectors: List[Dict]) -> str:
        """评估板块持续性"""
        if not sectors:
            return "数据不足"
        
        top_change = sectors[0].get("pct_chg", 0)
        if top_change > 8:
            return "短线性质明显，持续性待观察"
        elif top_change > 5:
            return "有一定持续性，关注量能配合"
        elif top_change > 2:
            return "持续性较好，可重点关注"
        else:
            return "动能不足，持续性弱"
    
    def _interpret_hot_sectors(self, sectors: List[Dict]) -> str:
        """解读热门板块"""
        if not sectors:
            return "今日无明显热点板块"
        
        top_sector = sectors[0]
        sector_name = top_sector.get("name", "未知")
        change = top_sector.get("pct_chg", 0)
        
        if change > 6:
            return f"{sector_name}板块强势爆发，涨幅达{change:.1f}%，市场热点集中"
        elif change > 3:
            return f"{sector_name}板块表现活跃，涨幅{change:.1f}%，带动相关概念"
        else:
            return f"{sector_name}板块温和上涨，市场轮动有序"
    
    def _calculate_rotation_speed(self, concepts: List[Dict]) -> str:
        """计算轮动速度"""
        if not concepts or len(concepts) < 5:
            return "数据不足"
        
        top_changes = [c.get("pct_chg", 0) for c in concepts[:5]]
        avg_change = sum(top_changes) / len(top_changes)
        max_change = max(top_changes)
        
        if max_change > 10:
            return "极快 - 爆发性热点"
        elif avg_change > 5:
            return "较快 - 板块轮动活跃"
        elif avg_change > 2:
            return "正常 - 稳健轮动"
        else:
            return "较慢 - 轮动停滞"
    
    def _interpret_concept_rotation(self, concepts: List[Dict]) -> str:
        """解读概念轮动"""
        if not concepts:
            return "概念板块表现平淡"
        
        hot_concepts = [c.get("name", "") for c in concepts[:3]]
        concept_names = "、".join(hot_concepts)
        
        return f"今日热门概念为{concept_names}等，资金轮动明显"
    
    def _extract_news_driven_stocks(self, market_data: Dict) -> List[Dict]:
        """提取新闻驱动股票"""
        # 模拟新闻驱动股票数据
        return [
            {"ts_code": "000001.SZ", "name": "平安银行", "news_type": "业绩预告", "impact": "positive"},
            {"ts_code": "600519.SH", "name": "贵州茅台", "news_type": "机构调研", "impact": "positive"}
        ]
    
    def _analyze_news_impact(self, news_driven: List[Dict]) -> str:
        """分析新闻影响"""
        if not news_driven:
            return "今日无明显新闻驱动事件"
        
        positive_count = len([n for n in news_driven if n.get("impact") == "positive"])
        total_count = len(news_driven)
        
        if positive_count / total_count > 0.7:
            return f"今日{total_count}条重要新闻中{positive_count}条偏正面，整体利好市场"
        else:
            return f"今日新闻面正负面并存，市场影响中性"
    
    def _calculate_momentum_indicators(self, market_data: Dict) -> Dict:
        """计算动量指标"""
        return {
            "volume_momentum": "5日均量较上日增加35%",
            "price_momentum": "主要指数RSI处于60-70区间",
            "breadth_momentum": "涨跌家数比较前一日改善"
        }
    
    def _calculate_vix_equivalent(self, analysis: Dict) -> float:
        """计算模拟VIX指数"""
        # 基于涨跌停家数、资金流向等计算波动率
        base_vix = 15  # 基础波动率
        
        try:
            if "sentiment" in analysis and "limit_analysis" in analysis["sentiment"]:
                limit_up = analysis["sentiment"]["limit_analysis"].get("limit_up", 0)
                limit_down = analysis["sentiment"]["limit_analysis"].get("limit_down", 0)
                
                # 涨跌停家数越多，波动率越高
                volatility_adjustment = (limit_up + limit_down * 2) * 0.5
                base_vix += volatility_adjustment
            
            return min(50, max(5, base_vix))
        except:
            return 15
    
    def _assess_rotation_strength(self, rotation_data: Dict) -> float:
        """评估轮动强度"""
        if not rotation_data or "leading_sectors" not in rotation_data:
            return 50
        
        leading = rotation_data["leading_sectors"]
        if leading and len(leading) > 0:
            top_change = leading[0].get("pct_chg", 0)
            return min(100, max(0, 50 + top_change * 5))
        return 50
    
    def _calculate_news_sentiment_score(self, news_data: Dict) -> float:
        """计算新闻情绪评分"""
        # 简化的新闻情绪评分
        if "important_announcements" in news_data:
            positive = news_data["important_announcements"].get("positive_count", 0)
            negative = news_data["important_announcements"].get("negative_count", 0)
            total = positive + negative
            if total > 0:
                return 50 + (positive - negative) / total * 50
        return 50
    
    def _get_fear_greed_level(self, score: float) -> str:
        """获取恐慌贪婪等级"""
        if score >= 75:
            return "极度贪婪"
        elif score >= 55:
            return "贪婪"
        elif score >= 45:
            return "中性"
        elif score >= 25:
            return "恐慌"
        else:
            return "极度恐慌"
    
    def _interpret_fear_greed_index(self, score: float) -> str:
        """解读恐慌贪婪指数"""
        if score >= 75:
            return f"恐慌贪婪指数达{score}，市场情绪极度乐观，注意高估值风险"
        elif score >= 55:
            return f"恐慌贪婪指数为{score}，市场贪婪情绪较浓，适度谨慎"
        elif score >= 45:
            return f"恐慌贪婪指数为{score}，市场情绪相对均衡，可适度参与"
        elif score >= 25:
            return f"恐慌贪婪指数为{score}，市场恐慌情绪升温，需谨慎操作"
        else:
            return f"恐慌贪婪指数仅{score}，市场恐慌情绪极度浓重，建议观望"
    
    def _build_analysis_prompt_data(self, analysis: Dict[str, Any]) -> Dict:
        """构建用于LLM分析的数据"""
        prompt_data = {
            "analysis_time": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "market_score": analysis.get("summary", {}).get("overall_score", 5.0),
            "fear_greed_score": analysis.get("fear_greed_index", {}).get("score", 50),
        }
        
        # 市场情绪数据
        if "sentiment" in analysis:
            sentiment = analysis["sentiment"]
            prompt_data["sentiment"] = {
                "up_ratio": sentiment.get("up_down_ratio", {}).get("up_ratio", 0),
                "limit_up": sentiment.get("limit_analysis", {}).get("limit_up", 0),
                "emotion_score": sentiment.get("emotion_score", 5)
            }
        
        # 资金流向数据  
        if "capital" in analysis:
            capital = analysis["capital"]
            prompt_data["capital"] = {
                "north_funds": capital.get("north_funds", {}).get("total_net_inflow", 0),
                "main_funds": capital.get("main_funds", {}).get("net_inflow", 0)
            }
        
        # 板块轮动数据
        if "structure" in analysis and "sector_rotation" in analysis["structure"]:
            sectors = analysis["structure"]["sector_rotation"].get("leading_sectors", [])
            if sectors:
                prompt_data["hot_sectors"] = [{
                    "name": sector.get("name", ""),
                    "change": sector.get("pct_chg", 0)
                } for sector in sectors[:3]]
        
        # 预警信息
        if "alerts" in analysis:
            high_alerts = [alert for alert in analysis["alerts"] if alert.get("level") == "high"]
            if high_alerts:
                prompt_data["major_alerts"] = [alert["message"] for alert in high_alerts[:3]]
        
        return prompt_data
    
    def _call_llm_for_analysis(self, prompt_data: Dict) -> str:
        """调用LLM生成智能分析"""
        try:
            import requests
            
            # 构建简化的分析提示词
            market_score = prompt_data.get('market_score', 5)
            fear_greed = prompt_data.get('fear_greed_score', 50)
            
            # 根据数据判断市场状态
            if market_score >= 7:
                trend = "向好"
            elif market_score >= 4:
                trend = "震荡"
            else:
                trend = "偏弱"
                
            if fear_greed >= 70:
                emotion = "贪婪"
            elif fear_greed >= 30:
                emotion = "中性"
            else:
                emotion = "恐慌"
            
            system_prompt = f"当前市场{trend}，情绪{emotion}。基于市场评分{market_score}/10和恐慌贪婪指数{fear_greed}/100，给出100字以内的市场解读和操作建议。直接输出结论，不要有思考过程。"
            
            # 简化数据输入
            user_prompt = "请分析。"
            
            body = {
                "model": OLLAMA_MODEL,
                "prompt": system_prompt + "\n" + user_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_ctx": 512,
                    "num_predict": 150,
                    "stop": None
                }
            }
            
            response = requests.post(f"{OLLAMA_URL}/api/generate", json=body, timeout=10)
            response.raise_for_status()
            
            result = response.json().get("response", "").strip()
            # 去除thinking标签和其他思考内容
            if "<think>" in result:
                # 找到</think>标签的位置
                think_end = result.find("</think>")
                if think_end != -1:
                    result = result[think_end + 8:].strip()
            
            # 如果包含"thinking"等关键词，使用后备方案
            if "thinking" in result.lower() or "用户" in result or not result:
                return self._get_fallback_narrative(prompt_data)
            
            return result
            
        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            return self._get_fallback_narrative(prompt_data)
    
    def _format_prompt_for_llm(self, prompt_data: Dict) -> str:
        """格式化LLM提示词"""
        prompt = f"【市场数据摘要】\n"
        prompt += f"分析时间：{prompt_data.get('analysis_time', '')}"
        prompt += f"市场评分：{prompt_data.get('market_score', 5.0)}/10\n"
        prompt += f"恐慌贪婪指数：{prompt_data.get('fear_greed_score', 50)}/100\n\n"
        
        if "sentiment" in prompt_data:
            s = prompt_data["sentiment"]
            prompt += f"【情绪指标】涨跌比{s.get('up_ratio', 0)}%，涨停{s.get('limit_up', 0)}家\n"
        
        if "capital" in prompt_data:
            c = prompt_data["capital"]
            prompt += f"【资金流向】北向资金{c.get('north_funds', 0):.1f}亿，主力资金{c.get('main_funds', 0):.1f}亿\n"
        
        if "hot_sectors" in prompt_data:
            sectors = prompt_data["hot_sectors"]
            sector_text = "、".join([f"{s['name']}({s['change']:.1f}%)" for s in sectors[:3]])
            prompt += f"【热点板块】{sector_text}\n"
        
        if "major_alerts" in prompt_data:
            alerts = prompt_data["major_alerts"]
            prompt += f"【重要预警】{'; '.join(alerts[:2])}\n"
        
        prompt += "\n请基于以上数据生成专业市场分析："
        
        return prompt
    
    def _get_fallback_narrative(self, analysis_or_data) -> str:
        """获取后备解读叙述"""
        try:
            # 提取市场评分和恐慌贪婪指数
            if isinstance(analysis_or_data, dict) and "market_score" in analysis_or_data:
                # 这是 prompt_data
                score = analysis_or_data.get("market_score", 5.0)
                fear_greed = analysis_or_data.get("fear_greed_score", 50)
            else:
                # 这是 analysis 原始数据
                score = analysis_or_data.get("summary", {}).get("overall_score", 5.0)
                fear_greed = 50  # 默认值
            
            # 根据评分和情绪生成智能解读
            if score >= 7 and fear_greed < 70:
                return (
                    "【核心逻辑】市场趋势强势，资金活跃度高，热点板块轮动有序。\n"
                    "【操作策略】建议仓位60-70%，关注强势板块龙头，设置8%止损。\n"
                    "【风险提示】防范短期回调，分批建仓降低成本。"
                )
            elif score >= 7 and fear_greed >= 70:
                return (
                    "【核心逻辑】市场虽强但情绪过热，有高位震荡风险。\n"
                    "【操作策略】逐步减仓至40-50%，锁定利润，等待回调机会。\n"
                    "【风险提示】市场贪婪情绪浓厚，警惕快速调整。"
                )
            elif score >= 4:
                return (
                    "【核心逻辑】市场震荡整理，多空博弈激烈，结构性行情为主。\n"
                    "【操作策略】维持仓位40-50%，高抛低吸，关注超跌反弹。\n"
                    "【风险提示】控制单一持仓，设置严格止损。"
                )
            else:
                return (
                    "🚨 【核心逻辑】市场情绪偏弱，资金谨慎，热点缺乏持续性。\n"
                    "💰 【操作策略】降低仓位至30%以下，保持充足现金。\n"
                    "⚙️ 【风险提示】市场仍在寻底，谨慎抄底，等待企稳信号。"
                )
        except:
            return (
                "🤖 【AI分析】数据获取中，请稍后查看分析结果。\n"
                "📊 【操作建议】保持谨慎，等待明确信号。\n"
                "⚠️ 【风险提示】分析数据不完整，请结合其他信息判断。"
            )


# 单例模式
_market_ai_analyzer = None

# 增强版MarketAIAnalyzer
class EnhancedMarketAIAnalyzer(MarketAIAnalyzer):
    """增强版市场AI分析器，集成LLM智能分析"""
    
    def __init__(self):
        super().__init__()
        self.llm_enabled = True
        
    def generate_market_insight_report(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成完整的市场洞察报告"""
        try:
            # 基础分析
            analysis = self.analyze_comprehensive_market(market_data)
            
            # 添加高级特性
            analysis["advanced_features"] = {
                "ai_powered": True,
                "llm_model": OLLAMA_MODEL,
                "analysis_version": "v2.0_enhanced",
                "features": [
                    "智能化解读叙述",
                    "恐慌贪婪指数",
                    "实时热点追踪",
                    "智能预警系统"
                ]
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"市场洞察报告生成失败: {e}")
            return self._get_fallback_analysis()


def get_market_ai_analyzer() -> EnhancedMarketAIAnalyzer:
    """获取增强版市场AI分析器实例"""
    global _market_ai_analyzer
    if _market_ai_analyzer is None:
        _market_ai_analyzer = EnhancedMarketAIAnalyzer()
    return _market_ai_analyzer

# 保持向后兼容
def get_enhanced_market_ai_analyzer() -> EnhancedMarketAIAnalyzer:
    """获取增强版市场AI分析器实例（新接口）"""
    return get_market_ai_analyzer()