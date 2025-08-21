"""
评分因子分解模块 - 提供详细的评分解释
"""
from typing import Dict, List, Tuple
import pandas as pd
import numpy as np

class ScoringFactors:
    """评分因子计算和解释"""
    
    @staticmethod
    def technical_factors(data: dict) -> Dict[str, Tuple[float, str]]:
        """
        技术面因子分解
        返回: {因子名: (得分, 解释)}
        """
        factors = {}
        total = 0
        
        # RSI因子 (0-30分)
        rsi = data.get('tech_last_rsi', 50)
        if rsi:
            if 30 <= rsi <= 70:
                rsi_score = 10
                rsi_desc = f"RSI={rsi:.1f} 中性区间"
            elif rsi < 30:
                rsi_score = 15
                rsi_desc = f"RSI={rsi:.1f} 超卖区间(机会)"
            elif rsi > 70:
                rsi_score = 5
                rsi_desc = f"RSI={rsi:.1f} 超买区间(谨慎)"
            else:
                rsi_score = 5
                rsi_desc = f"RSI={rsi:.1f}"
            factors["RSI指标"] = (rsi_score, rsi_desc)
            total += rsi_score
        
        # MACD因子 (0-20分)
        macd_signal = data.get('tech_signal', '')
        if macd_signal:
            if '金叉' in macd_signal:
                macd_score = 20
                macd_desc = "MACD金叉(强势信号)"
            elif '死叉' in macd_signal:
                macd_score = 0
                macd_desc = "MACD死叉(弱势信号)"
            elif '上升' in macd_signal:
                macd_score = 15
                macd_desc = "MACD上升趋势"
            elif '下降' in macd_signal:
                macd_score = 5
                macd_desc = "MACD下降趋势"
            else:
                macd_score = 10
                macd_desc = "MACD中性"
            factors["MACD信号"] = (macd_score, macd_desc)
            total += macd_score
        
        # 成交量因子 (0-20分)
        volume_ratio = data.get('volume_ratio', 1.0)
        if volume_ratio:
            if volume_ratio > 2.0:
                vol_score = 20
                vol_desc = f"放量突破(量比={volume_ratio:.2f})"
            elif volume_ratio > 1.5:
                vol_score = 15
                vol_desc = f"温和放量(量比={volume_ratio:.2f})"
            elif volume_ratio > 1.0:
                vol_score = 10
                vol_desc = f"正常成交(量比={volume_ratio:.2f})"
            else:
                vol_score = 5
                vol_desc = f"缩量(量比={volume_ratio:.2f})"
            factors["成交量"] = (vol_score, vol_desc)
            total += vol_score
        
        # 涨跌幅因子 (0-15分)
        pct_chg = data.get('recent_pct_chg', 0)
        if pct_chg is not None:
            if pct_chg > 5:
                chg_score = 15
                chg_desc = f"强势上涨({pct_chg:.1f}%)"
            elif pct_chg > 2:
                chg_score = 12
                chg_desc = f"温和上涨({pct_chg:.1f}%)"
            elif pct_chg > 0:
                chg_score = 8
                chg_desc = f"小幅上涨({pct_chg:.1f}%)"
            elif pct_chg > -2:
                chg_score = 5
                chg_desc = f"小幅下跌({pct_chg:.1f}%)"
            else:
                chg_score = 0
                chg_desc = f"明显下跌({pct_chg:.1f}%)"
            factors["近期涨跌"] = (chg_score, chg_desc)
            total += chg_score
        
        # 连板因子 (0-15分)
        consecutive_up = data.get('consecutive_up_days', 0)
        if consecutive_up > 0:
            board_score = min(consecutive_up * 5, 15)
            board_desc = f"{consecutive_up}连板"
            factors["连板效应"] = (board_score, board_desc)
            total += board_score
        
        return factors, total
    
    @staticmethod
    def sentiment_factors(data: dict) -> Dict[str, Tuple[float, str]]:
        """
        情绪面因子分解
        返回: {因子名: (得分, 解释)}
        """
        factors = {}
        total = 0
        
        # 主力资金因子 (0-30分)
        main_net = data.get('main_net_inflow', 0)
        if main_net != 0:
            if main_net > 100000000:  # 1亿
                fund_score = 30
                fund_desc = f"主力大幅净流入({main_net/100000000:.1f}亿)"
            elif main_net > 50000000:  # 5千万
                fund_score = 25
                fund_desc = f"主力净流入({main_net/10000000:.1f}千万)"
            elif main_net > 0:
                fund_score = 15
                fund_desc = f"主力小幅流入({main_net/10000:.0f}万)"
            elif main_net > -50000000:
                fund_score = 10
                fund_desc = f"主力小幅流出({abs(main_net)/10000:.0f}万)"
            else:
                fund_score = 0
                fund_desc = f"主力大幅流出({abs(main_net)/100000000:.1f}亿)"
            factors["主力资金"] = (fund_score, fund_desc)
            total += fund_score
        
        # 北向资金因子 (0-25分)
        north_net = data.get('north_net_buy', 0)
        if north_net != 0:
            if north_net > 10000000:  # 1千万
                north_score = 25
                north_desc = f"北向大幅买入({north_net/10000000:.1f}千万)"
            elif north_net > 1000000:  # 100万
                north_score = 20
                north_desc = f"北向买入({north_net/10000:.0f}万)"
            elif north_net > 0:
                north_score = 15
                north_desc = f"北向小幅买入"
            else:
                north_score = 5
                north_desc = f"北向卖出({abs(north_net)/10000:.0f}万)"
            factors["北向资金"] = (north_score, north_desc)
            total += north_score
        
        # 新闻情绪因子 (0-25分)
        sentiment = data.get('news_sentiment', {})
        positive = sentiment.get('positive', 0)
        negative = sentiment.get('negative', 0)
        if positive > 0 or negative > 0:
            if positive > 70:
                news_score = 25
                news_desc = f"极度乐观(正面{positive}%)"
            elif positive > 50:
                news_score = 20
                news_desc = f"偏乐观(正面{positive}%)"
            elif positive > 30:
                news_score = 15
                news_desc = f"中性(正面{positive}%)"
            else:
                news_score = 5
                news_desc = f"偏悲观(负面{negative}%)"
            factors["新闻情绪"] = (news_score, news_desc)
            total += news_score
        
        # 融资融券因子 (0-20分)
        margin_change = data.get('margin_change_pct', 0)
        if margin_change != 0:
            if margin_change > 10:
                margin_score = 20
                margin_desc = f"融资大增({margin_change:.1f}%)"
            elif margin_change > 0:
                margin_score = 15
                margin_desc = f"融资增加({margin_change:.1f}%)"
            else:
                margin_score = 10
                margin_desc = f"融资减少({margin_change:.1f}%)"
            factors["融资融券"] = (margin_score, margin_desc)
            total += margin_score
        
        return factors, total
    
    @staticmethod
    def fundamental_factors(data: dict) -> Dict[str, Tuple[float, str]]:
        """
        基本面因子分解
        返回: {因子名: (得分, 解释)}
        """
        factors = {}
        total = 0
        
        # ROE因子 (0-25分)
        roe = data.get('roe', 0)
        if roe:
            if roe > 20:
                roe_score = 25
                roe_desc = f"ROE={roe:.1f}% 优秀"
            elif roe > 15:
                roe_score = 20
                roe_desc = f"ROE={roe:.1f}% 良好"
            elif roe > 10:
                roe_score = 15
                roe_desc = f"ROE={roe:.1f}% 一般"
            else:
                roe_score = 5
                roe_desc = f"ROE={roe:.1f}% 较低"
            factors["净资产收益率"] = (roe_score, roe_desc)
            total += roe_score
        
        # 营收增长因子 (0-25分)
        revenue_growth = data.get('revenue_yoy', 0)
        if revenue_growth is not None:
            if revenue_growth > 30:
                rev_score = 25
                rev_desc = f"高速增长({revenue_growth:.1f}%)"
            elif revenue_growth > 15:
                rev_score = 20
                rev_desc = f"快速增长({revenue_growth:.1f}%)"
            elif revenue_growth > 0:
                rev_score = 15
                rev_desc = f"稳定增长({revenue_growth:.1f}%)"
            else:
                rev_score = 5
                rev_desc = f"负增长({revenue_growth:.1f}%)"
            factors["营收增长"] = (rev_score, rev_desc)
            total += rev_score
        
        # 估值因子 (0-25分)
        pe = data.get('pe_ttm', 0)
        industry_pe = data.get('industry_avg_pe', 30)  # 行业平均PE
        if pe and pe > 0:
            pe_ratio = pe / industry_pe if industry_pe else 1
            if pe_ratio < 0.7:
                pe_score = 25
                pe_desc = f"低估值(PE={pe:.1f}, 行业{industry_pe:.1f})"
            elif pe_ratio < 1:
                pe_score = 20
                pe_desc = f"合理估值(PE={pe:.1f})"
            elif pe_ratio < 1.3:
                pe_score = 15
                pe_desc = f"略高估值(PE={pe:.1f})"
            else:
                pe_score = 5
                pe_desc = f"高估值(PE={pe:.1f})"
            factors["估值水平"] = (pe_score, pe_desc)
            total += pe_score
        
        # 现金流因子 (0-25分)
        cash_flow = data.get('free_cash_flow', 0)
        if cash_flow != 0:
            if cash_flow > 0:
                cash_score = 20
                cash_desc = f"现金流正向"
            else:
                cash_score = 10
                cash_desc = f"现金流负向"
            factors["现金流"] = (cash_score, cash_desc)
            total += cash_score
        
        return factors, total
    
    @staticmethod
    def macro_factors(data: dict) -> Dict[str, Tuple[float, str]]:
        """
        宏观因子分解
        返回: {因子名: (得分, 解释)}
        """
        factors = {}
        total = 0
        
        # PMI因子
        pmi = data.get('pmi', 50)
        if pmi:
            if pmi > 52:
                pmi_score = 25
                pmi_desc = f"PMI={pmi:.1f} 强扩张"
            elif pmi > 50:
                pmi_score = 20
                pmi_desc = f"PMI={pmi:.1f} 扩张区"
            else:
                pmi_score = 10
                pmi_desc = f"PMI={pmi:.1f} 收缩区"
            factors["PMI指数"] = (pmi_score, pmi_desc)
            total += pmi_score
        
        # M2增速因子
        m2_yoy = data.get('m2_yoy', 0)
        if m2_yoy:
            if m2_yoy > 10:
                m2_score = 25
                m2_desc = f"M2增速={m2_yoy:.1f}% 流动性充裕"
            elif m2_yoy > 8:
                m2_score = 20
                m2_desc = f"M2增速={m2_yoy:.1f}% 流动性适中"
            else:
                m2_score = 10
                m2_desc = f"M2增速={m2_yoy:.1f}% 流动性偏紧"
            factors["货币供应"] = (m2_score, m2_desc)
            total += m2_score
        
        # 利率因子
        shibor = data.get('shibor_3m', 2.5)
        if shibor:
            if shibor < 2.0:
                rate_score = 25
                rate_desc = f"利率={shibor:.2f}% 宽松环境"
            elif shibor < 3.0:
                rate_score = 20
                rate_desc = f"利率={shibor:.2f}% 中性环境"
            else:
                rate_score = 10
                rate_desc = f"利率={shibor:.2f}% 偏紧环境"
            factors["利率环境"] = (rate_score, rate_desc)
            total += rate_score
        
        return factors, total
    
    @staticmethod
    def calculate_explainable_score(data: dict) -> dict:
        """
        计算可解释的综合评分
        """
        # 获取各维度因子
        tech_factors, tech_total = ScoringFactors.technical_factors(data)
        sent_factors, sent_total = ScoringFactors.sentiment_factors(data)
        fund_factors, fund_total = ScoringFactors.fundamental_factors(data)
        macro_factors, macro_total = ScoringFactors.macro_factors(data)
        
        # 计算加权总分
        weighted_score = (
            tech_total * 0.4 +
            sent_total * 0.35 +
            fund_total * 0.2 +
            macro_total * 0.05
        )
        
        return {
            "total_score": round(weighted_score, 1),
            "dimensions": {
                "technical": {
                    "score": tech_total,
                    "weight": 0.4,
                    "weighted_score": round(tech_total * 0.4, 1),
                    "factors": tech_factors
                },
                "sentiment": {
                    "score": sent_total,
                    "weight": 0.35,
                    "weighted_score": round(sent_total * 0.35, 1),
                    "factors": sent_factors
                },
                "fundamental": {
                    "score": fund_total,
                    "weight": 0.2,
                    "weighted_score": round(fund_total * 0.2, 1),
                    "factors": fund_factors
                },
                "macro": {
                    "score": macro_total,
                    "weight": 0.05,
                    "weighted_score": round(macro_total * 0.05, 1),
                    "factors": macro_factors
                }
            },
            "explanation": _generate_explanation(weighted_score)
        }

def _generate_explanation(score: float) -> str:
    """生成总体评价"""
    if score >= 80:
        return "强烈推荐：多维度指标表现优异，具有较强投资价值"
    elif score >= 60:
        return "推荐关注：整体表现良好，部分指标突出"
    elif score >= 40:
        return "中性观望：指标表现一般，建议持续跟踪"
    elif score >= 20:
        return "谨慎对待：多项指标偏弱，存在一定风险"
    else:
        return "不建议：指标表现较差，风险较大"