"""
股票技术面因子专业版接口
使用 stk_factor_pro 接口获取全面的技术指标数据
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from .tushare_client import _call_api, cached

class StkFactorProClient:
    """股票技术面因子专业版客户端"""

    # 关键技术指标映射
    CORE_INDICATORS = {
        'trend': ['ma_qfq_5', 'ma_qfq_10', 'ma_qfq_20', 'ma_qfq_60', 'ema_qfq_20'],
        'momentum': ['rsi_qfq_6', 'rsi_qfq_12', 'rsi_qfq_24', 'macd_qfq', 'macd_dif_qfq', 'macd_dea_qfq'],
        'volatility': ['atr_qfq', 'boll_upper_qfq', 'boll_mid_qfq', 'boll_lower_qfq'],
        'volume': ['vr_qfq', 'obv_qfq', 'mfi_qfq', 'volume_ratio'],
        'overbought': ['kdj_k_qfq', 'kdj_d_qfq', 'kdj_qfq', 'cci_qfq', 'wr_qfq'],
        'market': ['pe', 'pe_ttm', 'pb', 'ps_ttm', 'dv_ttm', 'total_mv', 'circ_mv'],
        'special': ['updays', 'downdays', 'topdays', 'lowdays'],
        'emotion': ['brar_ar_qfq', 'brar_br_qfq', 'psy_qfq', 'psyma_qfq'],
        'channel': ['ktn_upper_qfq', 'ktn_mid_qfq', 'ktn_down_qfq', 'taq_up_qfq', 'taq_mid_qfq', 'taq_down_qfq']
    }

    @staticmethod
    @cached
    def get_stk_factor_pro(ts_code: str = None,
                          trade_date: str = None,
                          start_date: str = None,
                          end_date: str = None) -> pd.DataFrame:
        """
        获取股票技术面因子数据

        Args:
            ts_code: 股票代码
            trade_date: 交易日期(单日查询)
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            包含所有技术指标的DataFrame
        """
        try:
            df = _call_api('stk_factor_pro',
                         ts_code=ts_code,
                         trade_date=trade_date,
                         start_date=start_date,
                         end_date=end_date)

            if df is not None and not df.empty:
                # 按日期排序
                df = df.sort_values('trade_date', ascending=False)
            return df

        except Exception as e:
            print(f"获取stk_factor_pro数据失败: {e}")
            return pd.DataFrame()

    @staticmethod
    def analyze_technical_factors(df: pd.DataFrame) -> Dict[str, Any]:
        """
        分析技术因子并生成信号

        Args:
            df: stk_factor_pro返回的数据

        Returns:
            技术分析结果字典
        """
        if df is None or df.empty:
            return {"status": "no_data"}

        # 获取最新一条数据
        latest = df.iloc[0]

        analysis = {
            "trade_date": str(latest.get('trade_date', '')),
            "price_action": {},
            "technical_signals": [],
            "market_valuation": {},
            "special_patterns": {},
            "comprehensive_score": 50  # 基础分
        }

        # 1. 价格走势分析
        analysis['price_action'] = {
            "close": float(latest.get('close_qfq', 0)),
            "change_pct": float(latest.get('pct_chg', 0)),
            "volume_ratio": float(latest.get('volume_ratio', 1)),
            "turnover_rate": float(latest.get('turnover_rate_f', 0))
        }

        # 2. 趋势信号
        signals = []
        score = 50

        # MA趋势
        ma5 = latest.get('ma_qfq_5')
        ma20 = latest.get('ma_qfq_20')
        ma60 = latest.get('ma_qfq_60')
        close = latest.get('close_qfq')

        if pd.notna(ma5) and pd.notna(ma20) and pd.notna(ma60) and pd.notna(close):
            if close > ma5 > ma20 > ma60:
                signals.append("强势多头排列")
                score += 15
            elif close > ma20:
                signals.append("中期趋势向上")
                score += 8
            elif close < ma5 < ma20 < ma60:
                signals.append("空头排列")
                score -= 15
            elif close < ma20:
                signals.append("中期趋势向下")
                score -= 8

        # 3. 动量指标
        rsi = latest.get('rsi_qfq_12')
        if pd.notna(rsi):
            if rsi > 80:
                signals.append(f"RSI超买({rsi:.1f})")
                score -= 5
            elif rsi < 20:
                signals.append(f"RSI超卖({rsi:.1f})")
                score += 5
            elif rsi > 60:
                signals.append(f"RSI偏强({rsi:.1f})")
                score += 3
            elif rsi < 40:
                signals.append(f"RSI偏弱({rsi:.1f})")
                score -= 3

        # MACD
        macd = latest.get('macd_qfq')
        dif = latest.get('macd_dif_qfq')
        dea = latest.get('macd_dea_qfq')
        if pd.notna(dif) and pd.notna(dea):
            if dif > dea and dif > 0:
                signals.append("MACD金叉且在零轴上")
                score += 10
            elif dif > dea:
                signals.append("MACD金叉")
                score += 5
            elif dif < dea and dif < 0:
                signals.append("MACD死叉且在零轴下")
                score -= 10
            elif dif < dea:
                signals.append("MACD死叉")
                score -= 5

        # 4. KDJ指标
        kdj_k = latest.get('kdj_k_qfq')
        kdj_d = latest.get('kdj_d_qfq')
        kdj_j = latest.get('kdj_qfq')
        if pd.notna(kdj_k) and pd.notna(kdj_d):
            if kdj_k > 80 and kdj_d > 80:
                signals.append("KDJ高位钝化")
                score -= 3
            elif kdj_k < 20 and kdj_d < 20:
                signals.append("KDJ低位超卖")
                score += 5
            elif kdj_k > kdj_d and kdj_k < 50:
                signals.append("KDJ低位金叉")
                score += 8

        # 5. 布林带
        boll_up = latest.get('boll_upper_qfq')
        boll_mid = latest.get('boll_mid_qfq')
        boll_down = latest.get('boll_lower_qfq')
        if pd.notna(boll_up) and pd.notna(boll_down) and pd.notna(close):
            if close >= boll_up:
                signals.append("突破布林上轨")
                score += 5
            elif close <= boll_down:
                signals.append("跌破布林下轨")
                score -= 5

            # 布林带宽度
            band_width = (boll_up - boll_down) / boll_mid * 100 if boll_mid else 0
            if band_width < 5:
                signals.append("布林带收窄(变盘信号)")

        # 6. 特殊形态
        updays = latest.get('updays', 0)
        downdays = latest.get('downdays', 0)
        topdays = latest.get('topdays', 0)
        lowdays = latest.get('lowdays', 0)

        special = []
        if updays > 5:
            special.append(f"连涨{int(updays)}天")
            score += min(updays * 2, 10)
        elif downdays > 5:
            special.append(f"连跌{int(downdays)}天")
            score -= min(downdays * 2, 10)

        if topdays and topdays <= 20:
            special.append(f"近{int(topdays)}日新高")
            score += 8
        elif lowdays and lowdays <= 20:
            special.append(f"近{int(lowdays)}日新低")
            score -= 8

        analysis['special_patterns'] = special

        # 7. 市场估值
        analysis['market_valuation'] = {
            "pe": float(latest.get('pe', 0)) if pd.notna(latest.get('pe')) else None,
            "pe_ttm": float(latest.get('pe_ttm', 0)) if pd.notna(latest.get('pe_ttm')) else None,
            "pb": float(latest.get('pb', 0)) if pd.notna(latest.get('pb')) else None,
            "ps_ttm": float(latest.get('ps_ttm', 0)) if pd.notna(latest.get('ps_ttm')) else None,
            "dividend_yield": float(latest.get('dv_ttm', 0)) if pd.notna(latest.get('dv_ttm')) else None,
            "total_mv": float(latest.get('total_mv', 0)) / 10000 if pd.notna(latest.get('total_mv')) else None,  # 转换为亿
            "circ_mv": float(latest.get('circ_mv', 0)) / 10000 if pd.notna(latest.get('circ_mv')) else None  # 转换为亿
        }

        # 8. 成交量分析
        volume_ratio = latest.get('volume_ratio')
        vr = latest.get('vr_qfq')
        if pd.notna(volume_ratio):
            if volume_ratio > 3:
                signals.append(f"巨量(量比{volume_ratio:.1f})")
                score += 5
            elif volume_ratio > 2:
                signals.append(f"放量(量比{volume_ratio:.1f})")
                score += 3
            elif volume_ratio < 0.5:
                signals.append(f"缩量(量比{volume_ratio:.1f})")
                score -= 3

        # 9. 资金流向 (MFI)
        mfi = latest.get('mfi_qfq')
        if pd.notna(mfi):
            if mfi > 80:
                signals.append(f"资金流入过度(MFI:{mfi:.1f})")
                score -= 3
            elif mfi < 20:
                signals.append(f"资金流出过度(MFI:{mfi:.1f})")
                score += 3

        # 10. ATR波动率
        atr = latest.get('atr_qfq')
        if pd.notna(atr) and pd.notna(close) and close > 0:
            atr_ratio = atr / close * 100
            if atr_ratio > 5:
                signals.append(f"高波动(ATR:{atr_ratio:.1f}%)")
            elif atr_ratio < 2:
                signals.append(f"低波动(ATR:{atr_ratio:.1f}%)")

        analysis['technical_signals'] = signals
        analysis['comprehensive_score'] = min(100, max(0, score))

        return analysis

    @staticmethod
    def get_trend_analysis(df: pd.DataFrame, days: int = 20) -> Dict[str, Any]:
        """
        获取趋势分析

        Args:
            df: 技术因子数据
            days: 分析天数

        Returns:
            趋势分析结果
        """
        if df is None or df.empty or len(df) < days:
            return {"trend": "insufficient_data"}

        # 取最近N天数据
        recent_df = df.head(days)

        trend_analysis = {
            "primary_trend": "",
            "trend_strength": 0,
            "support_resistance": {},
            "volatility_trend": ""
        }

        # 分析主趋势
        start_close = recent_df.iloc[-1]['close_qfq']
        end_close = recent_df.iloc[0]['close_qfq']
        change_pct = (end_close - start_close) / start_close * 100

        if change_pct > 10:
            trend_analysis['primary_trend'] = "强势上涨"
            trend_analysis['trend_strength'] = min(100, 50 + change_pct * 2)
        elif change_pct > 3:
            trend_analysis['primary_trend'] = "温和上涨"
            trend_analysis['trend_strength'] = 50 + change_pct * 3
        elif change_pct > -3:
            trend_analysis['primary_trend'] = "横盘整理"
            trend_analysis['trend_strength'] = 50
        elif change_pct > -10:
            trend_analysis['primary_trend'] = "温和下跌"
            trend_analysis['trend_strength'] = 50 + change_pct * 3
        else:
            trend_analysis['primary_trend'] = "快速下跌"
            trend_analysis['trend_strength'] = max(0, 50 + change_pct * 2)

        # 计算支撑阻力
        high_price = recent_df['high_qfq'].max()
        low_price = recent_df['low_qfq'].min()
        pivot = (high_price + low_price + end_close) / 3

        trend_analysis['support_resistance'] = {
            "resistance_2": round(pivot + (high_price - low_price), 2),
            "resistance_1": round(2 * pivot - low_price, 2),
            "pivot": round(pivot, 2),
            "support_1": round(2 * pivot - high_price, 2),
            "support_2": round(pivot - (high_price - low_price), 2),
            "recent_high": round(high_price, 2),
            "recent_low": round(low_price, 2)
        }

        # 波动率趋势
        if 'atr_qfq' in recent_df.columns:
            atr_trend = recent_df['atr_qfq'].iloc[:5].mean() - recent_df['atr_qfq'].iloc[-5:].mean()
            if atr_trend > 0:
                trend_analysis['volatility_trend'] = "波动率上升"
            else:
                trend_analysis['volatility_trend'] = "波动率下降"

        return trend_analysis

    @staticmethod
    def get_entry_exit_signals(df: pd.DataFrame) -> Dict[str, Any]:
        """
        生成买卖信号建议

        Args:
            df: 技术因子数据

        Returns:
            买卖信号字典
        """
        if df is None or df.empty:
            return {"status": "no_data"}

        latest = df.iloc[0]
        signals = {
            "buy_signals": [],
            "sell_signals": [],
            "neutral_signals": [],
            "signal_strength": "neutral",
            "suggested_action": "观望"
        }

        buy_score = 0
        sell_score = 0

        # 检查各种买入信号
        # 1. RSI超卖
        rsi = latest.get('rsi_qfq_12')
        if pd.notna(rsi) and rsi < 30:
            signals['buy_signals'].append("RSI超卖")
            buy_score += 2
        elif pd.notna(rsi) and rsi > 70:
            signals['sell_signals'].append("RSI超买")
            sell_score += 2

        # 2. KDJ金叉
        kdj_k = latest.get('kdj_k_qfq')
        kdj_d = latest.get('kdj_d_qfq')
        if pd.notna(kdj_k) and pd.notna(kdj_d):
            if kdj_k > kdj_d and kdj_k < 50:
                signals['buy_signals'].append("KDJ低位金叉")
                buy_score += 3
            elif kdj_k < kdj_d and kdj_k > 50:
                signals['sell_signals'].append("KDJ高位死叉")
                sell_score += 3

        # 3. MACD信号
        dif = latest.get('macd_dif_qfq')
        dea = latest.get('macd_dea_qfq')
        if pd.notna(dif) and pd.notna(dea):
            if dif > dea and dif < 0:
                signals['buy_signals'].append("MACD零轴下金叉")
                buy_score += 3
            elif dif < dea and dif > 0:
                signals['sell_signals'].append("MACD零轴上死叉")
                sell_score += 3

        # 4. 布林带信号
        close = latest.get('close_qfq')
        boll_down = latest.get('boll_lower_qfq')
        boll_up = latest.get('boll_upper_qfq')
        if pd.notna(close) and pd.notna(boll_down) and pd.notna(boll_up):
            if close <= boll_down:
                signals['buy_signals'].append("触及布林下轨")
                buy_score += 2
            elif close >= boll_up:
                signals['sell_signals'].append("触及布林上轨")
                sell_score += 2

        # 5. 成交量配合
        volume_ratio = latest.get('volume_ratio')
        pct_chg = latest.get('pct_chg')
        if pd.notna(volume_ratio) and pd.notna(pct_chg):
            if volume_ratio > 2 and pct_chg > 3:
                signals['buy_signals'].append("放量上涨")
                buy_score += 2
            elif volume_ratio > 2 and pct_chg < -3:
                signals['sell_signals'].append("放量下跌")
                sell_score += 2

        # 6. 连续形态
        updays = latest.get('updays', 0)
        downdays = latest.get('downdays', 0)
        if updays > 3:
            signals['neutral_signals'].append(f"连涨{int(updays)}天(注意回调)")
            sell_score += 1
        elif downdays > 3:
            signals['neutral_signals'].append(f"连跌{int(downdays)}天(关注反弹)")
            buy_score += 1

        # 综合评判
        net_score = buy_score - sell_score
        if net_score >= 5:
            signals['signal_strength'] = "strong_buy"
            signals['suggested_action'] = "积极买入"
        elif net_score >= 3:
            signals['signal_strength'] = "buy"
            signals['suggested_action'] = "适度买入"
        elif net_score <= -5:
            signals['signal_strength'] = "strong_sell"
            signals['suggested_action'] = "及时卖出"
        elif net_score <= -3:
            signals['signal_strength'] = "sell"
            signals['suggested_action'] = "适度减仓"
        else:
            signals['signal_strength'] = "neutral"
            signals['suggested_action'] = "观望等待"

        return signals