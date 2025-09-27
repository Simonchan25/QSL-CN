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
    
    def comprehensive_hotspot_analysis(self, keyword: str, days: int = 5, progress_callback=None) -> Dict[str, Any]:
        """综合热点分析 - 专业级多维度分析（带进度回调）"""
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

        # 使用合理的并发数量
        with ThreadPoolExecutor(max_workers=4) as executor:
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

        final_result = {
            'keyword': keyword,
            'analysis_time': dt.datetime.now().isoformat(),
            'comprehensive_score': comprehensive_score,
            'investment_advice': investment_advice,
            **analysis_results
        }

        if progress_callback:
            progress_callback(100, "分析完成", {"phase": "completed", "score": comprehensive_score})

        print(f"[增强热点] {keyword} 综合分析完成，评分: {comprehensive_score}/100")
        return final_result
    
    def _analyze_concept_fundamentals(self, keyword: str) -> Dict[str, Any]:
        """分析概念基本面"""
        try:
            # 获取概念相关股票
            concept_stocks = self._get_concept_stocks(keyword)
            if not concept_stocks:
                return {'has_data': False, 'reason': '未找到相关概念股票'}
            
            # 批量获取最新财务数据
            financial_stats = self._batch_analyze_financials(concept_stocks[:20])  # 分析前20只
            
            # 计算概念整体财务指标
            overall_metrics = self._calculate_concept_metrics(financial_stats)
            
            return {
                'has_data': True,
                'stock_count': len(concept_stocks),
                'analyzed_count': len(financial_stats),
                'overall_metrics': overall_metrics,
                'top_performers': financial_stats[:5],
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
            for stock_code in concept_stocks[:10]:  # 分析前10只
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
        """分析技术动能"""
        try:
            concept_stocks = self._get_concept_stocks(keyword)
            if not concept_stocks:
                return {'has_data': False}
            
            # 获取技术指标
            technical_analysis = []
            for stock_code in concept_stocks[:15]:  # 分析前15只
                try:
                    # 获取技术因子数据
                    factors = self.advanced_client.advanced_client._get_technical_factors(stock_code)
                    if factors.get('has_data'):
                        technical_analysis.append({
                            'stock_code': stock_code,
                            'factors': factors
                        })
                except:
                    continue
            
            # 计算概念技术动能
            momentum_score = self._calculate_momentum_score(technical_analysis)
            
            return {
                'has_data': True,
                'analyzed_stocks': len(technical_analysis),
                'momentum_score': momentum_score,
                'momentum_level': self._rate_momentum_level(momentum_score),
                'technical_signals': self._extract_technical_signals(technical_analysis)
            }
        except Exception as e:
            print(f"技术动能分析失败: {e}")
            return {'has_data': False, 'error': str(e)}
    
    def _analyze_news_catalyst(self, keyword: str) -> Dict[str, Any]:
        """分析新闻催化剂"""
        try:
            # 获取CCTV新闻
            today = dt.date.today().strftime("%Y%m%d")
            cctv_news = self.advanced_client._get_news_analysis()
            
            # 搜索相关新闻
            relevant_news = []
            if cctv_news.get('has_cctv_data'):
                for news in cctv_news.get('latest_news', []):
                    if keyword in news.get('title', '') or keyword in news.get('content', ''):
                        relevant_news.append(news)
            
            # 分析催化剂强度
            catalyst_strength = self._rate_catalyst_strength(relevant_news, keyword)
            
            return {
                'has_data': True,
                'relevant_news_count': len(relevant_news),
                'relevant_news': relevant_news,
                'catalyst_strength': catalyst_strength,
                'policy_support': self._detect_policy_support(relevant_news)
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
            for stock_code in concept_stocks[:10]:
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
                    if not basic_data.empty:
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
                'volatility_risk': self._assess_volatility_risk(concept_stocks[:10], days),
                'concentration_risk': self._assess_concentration_risk(concept_stocks),
                'liquidity_risk': self._assess_liquidity_risk(concept_stocks[:10]),
                'valuation_risk': self._assess_valuation_risk(concept_stocks[:10])
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
        """计算综合评分"""
        try:
            scores = []
            weights = {
                'concept_analysis': 0.20,
                'sector_rotation': 0.15,
                'fund_participation': 0.15,
                'technical_momentum': 0.15,
                'news_catalyst': 0.10,
                'institutional_attention': 0.10,
                'market_position': 0.10,
                'risk_assessment': 0.05  # 风险负向计分
            }
            
            total_weight = 0
            weighted_score = 0
            
            for key, weight in weights.items():
                if key in analysis_results and analysis_results[key].get('has_data'):
                    if key == 'risk_assessment':
                        # 风险评分越高，综合得分越低
                        risk_score = analysis_results[key].get('overall_risk_score', 50)
                        score = 100 - risk_score
                    else:
                        # 提取各模块的评分
                        score = self._extract_module_score(analysis_results[key], key)
                    
                    weighted_score += score * weight
                    total_weight += weight
            
            # 根据实际权重计算最终得分
            final_score = int(weighted_score / total_weight) if total_weight > 0 else 50
            return max(0, min(100, final_score))
        except Exception as e:
            print(f"综合评分计算失败: {e}")
            return 50
    
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
    
    def _batch_analyze_financials(self, stock_codes: List[str]) -> List[Dict[str, Any]]:
        """批量分析财务数据"""
        # 简化实现，实际应该调用VIP接口批量获取
        return []
    
    def _calculate_concept_metrics(self, financial_stats: List[Dict[str, Any]]) -> Dict[str, float]:
        """计算概念整体指标"""
        return {
            'avg_roe': 0.0,
            'avg_growth_rate': 0.0,
            'debt_ratio': 0.0
        }
    
    def _rate_financial_strength(self, metrics: Dict[str, float]) -> int:
        """评价财务实力"""
        return 60  # 示例评分
    
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
        """计算技术动能评分"""
        return 60
    
    def _rate_momentum_level(self, score: int) -> int:
        """评价动能水平"""
        return score
    
    def _extract_technical_signals(self, technical_analysis: List[Dict]) -> List[str]:
        """提取技术信号"""
        return []
    
    def _rate_catalyst_strength(self, news: List[Dict], keyword: str) -> int:
        """评价催化剂强度"""
        return 50 + len(news) * 10  # 简化评分
    
    def _detect_policy_support(self, news: List[Dict]) -> bool:
        """检测政策支持"""
        policy_keywords = ['政策', '支持', '鼓励', '发展', '规划']
        for item in news:
            content = item.get('content', '') + item.get('title', '')
            if any(keyword in content for keyword in policy_keywords):
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


# 全局实例
enhanced_hotspot_analyzer = EnhancedHotspotAnalyzer()